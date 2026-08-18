# INVENTO: Smart Multi-Tenant Inventory Management Solution

**INVENTO** is a SaaS-style, AI-powered inventory and business management platform designed to help organizations manage their day-to-day business operations from a single system.

The platform follows a **multi-tenant architecture**, allowing multiple independent organizations to use the same application while keeping their data completely isolated.

**Repository:** `https://github.com/B-chand/minor_project`

---

## 1. Project Overview

INVENTO provides an integrated platform for managing inventory, products, customers, suppliers, purchases, sales, staff, notifications, reports, analytics, and AI-assisted business intelligence.

Each organization registered on the platform is provisioned as an independent **tenant** and receives a unique **Business Code** such as `B1`, `B2`, etc. The Business Code is used together with the username and password during authentication.

### Core Business Operations

* Product and category management
* Inventory and stock management
* Stock movement tracking
* Supplier management
* Purchase management
* Customer management
* Sales management
* Staff management
* Notifications
* Reports and analytics
* Executive dashboard
* AI-powered forecasting and recommendations
* AI business intelligence
* AI inventory assistant

Tenant data isolation is enforced at the application and database-query level. Every tenant-owned record is associated with an `organization` foreign key, and API queries are automatically restricted to the authenticated user's organization.

The organization identity is derived from the authenticated user and is **never trusted from client-supplied data**.

---

# 2. Project Objectives

The primary objectives of INVENTO are:

1. **Multi-Tenant Architecture**
   Provide a single application instance capable of serving multiple independent organizations while maintaining strict data isolation.

2. **Secure Authentication**
   Implement JWT-based authentication using Business Code, username, and password.

3. **Role-Based Access Control**
   Provide different capabilities for Business Administrators and Staff members.

4. **Inventory Management**
   Track product quantities, stock thresholds, stock adjustments, and complete stock movement history.

5. **Sales and Purchase Management**
   Record sales and purchases while automatically updating inventory.

6. **Reporting and Analytics**
   Provide dashboards, transaction reports, low-stock monitoring, and saved custom reports.

7. **AI-Assisted Business Intelligence**
   Provide demand forecasting, restock recommendations, business insights, AI-generated summaries, and a natural-language business assistant.

8. **Tenant Data Isolation**
   Ensure that users can access only the data belonging to their organization.

---

# 3. Key Features

## 3.1 Multi-Tenant Architecture

Each tenant is represented by an `Organization` entity with:

* Unique UUID
* Organization/business profile
* Logo
* Unique Business Code

All organization-owned entities inherit from the shared `TenantModel`, which contains an `organization` foreign key.

### Tenant Isolation

Tenant isolation is enforced through three primary mechanisms:

#### 1. `TenantModelViewSet`

Automatically:

* Filters querysets using `request.user.organization`
* Assigns the authenticated user's organization when creating records
* Prevents users from accessing another organization's records

#### 2. `TenantScopedSerializerMixin`

Restricts writable foreign-key fields so that users can reference only records belonging to their own organization.

#### 3. Authenticated Organization Identity

The organization is always derived from the authenticated user.

Client-supplied organization identifiers are ignored or rejected.

A user belongs to exactly one organization and cannot switch between tenants.

---

# 4. Authentication and Role-Based Access Control

## 4.1 Registration

Organization registration creates:

1. A new organization
2. The organization's first Business Admin account
3. A unique Business Code

The Business Code is returned to the administrator after registration and is required for future logins.

---

## 4.2 Login

Users authenticate using:

```text
Business Code + Username + Password
```

The username is resolved within the specified organization, allowing the same username to exist in different organizations.

Successful authentication returns:

* JWT access token
* JWT refresh token
* User role
* Business/organization information

---

## 4.3 JWT Configuration

| Token         | Validity |
| ------------- | -------: |
| Access Token  | 12 hours |
| Refresh Token |   7 days |

JWT authentication is implemented using `djangorestframework-simplejwt`.

---

## 4.4 User Roles

| Role           | Code          | Responsibilities                                                                                                                  |
| -------------- | ------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| Super Admin    | `SUPER_ADMIN` | Platform-level role defined in the data model. No organization-tenant login path is exposed in the application.                   |
| Business Admin | `ADMIN`       | Full organization management, including staff, products, inventory, sales, purchases, reports, business profile, and AI modules.  |
| Staff          | `STAFF`       | Day-to-day operations including products, inventory, customers, suppliers, purchases, sales, notifications, and the AI assistant. |

RBAC is enforced through custom Django REST Framework permissions including:

* `IsBusinessAdmin`
* `IsStaff`
* `IsOrganizationMember`

Frontend route guards additionally restrict administrator-only modules such as:

* Reports
* AI
* AI Insights
* Staff
* Business Profile

---

# 5. Product and Category Management

## 5.1 Categories

Categories provide a way to organize products.

Category names are unique within each organization.

## 5.2 Products

Products contain information including:

* Product name
* SKU
* Barcode
* Description
* Buying price
* Selling price
* Product image
* Active/inactive status
* Category

Products can be searched using:

* Name
* SKU
* Barcode
* Category

Products with remaining inventory cannot be deleted, protecting historical stock information.

---

# 6. Inventory Management

INVENTO provides centralized inventory tracking for all products.

## 6.1 Inventory Records

Each inventory record maintains:

* Current quantity
* Minimum stock threshold
* Maximum stock threshold
* Automatic stock status

Possible stock statuses include:

* **In Stock**
* **Low Stock**
* **Out of Stock**

---

## 6.2 Stock Adjustments

Authorized users can perform signed stock adjustments.

The system:

1. Locks the relevant inventory row.
2. Applies the requested quantity adjustment.
3. Prevents negative inventory.
4. Creates an `ADJUSTMENT` stock movement.
5. Records the acting user.

---

## 6.3 Stock Movement History

All important inventory changes are recorded.

Movement types include:

* `IN`
* `OUT`
* `ADJUSTMENT`

Each movement records information such as:

* Quantity
* Remarks
* Acting user
* Related transaction

This provides an audit trail for inventory changes.

---

## 6.4 Automatic Inventory Updates

Inventory is automatically updated when:

* A purchase is completed → stock increases
* A sale is completed → stock decreases
* A purchase is deleted → stock is restored
* A sale is deleted → stock is restored
* A stock adjustment is performed → stock is adjusted

---

## 6.5 Stock Notifications

The system automatically generates notifications when products:

* Reach their low-stock threshold
* Become out of stock

---

# 7. Purchase Management

Purchases represent goods received from suppliers.

A purchase contains:

* Supplier
* Invoice number
* Purchase date
* One or more purchase items
* Unit cost
* Computed invoice total

## 7.1 Purchase Workflow

The standard UI records purchases as **Completed**.

When a purchase is completed:

1. Purchase information is saved.
2. Purchase items are recorded.
3. Inventory quantities are increased.
4. An `IN` stock movement is created.
5. A purchase notification is generated.

There is no pending or receipt-draft workflow exposed through the normal UI.

## 7.2 Purchase Deletion

Deleting a purchase or purchase line item reverses the associated inventory change so that stock totals remain consistent.

---

# 8. Sales Management

Sales are represented as one-time transactions through the POS workflow.

A sale includes:

* Customer
* Invoice number
* Sale date
* One or more sale items
* Automatically calculated transaction total

A customer may either be:

* A registered customer
* A Walk-in Customer

## 8.1 Sales Workflow

When a sale is created:

1. Customer information is selected.
2. Invoice information is entered.
3. Sale items are added.
4. Stock availability is checked.
5. Inventory is deducted.
6. The transaction total is calculated.
7. An `OUT` stock movement is generated.
8. A sale notification is created.
9. Low-stock/out-of-stock notifications are generated when required.

Inventory checks are performed within a database transaction to prevent overselling.

Normal UI sales are recorded as **PAID**, with the amount paid equal to the invoice total.

There is no external payment-gateway integration. The system records transaction amounts only.

## 8.2 Sale Deletion

Deleting a sale or sale item restores the corresponding inventory quantity.

---

# 9. Customer Management

Customers contain:

* Name
* Email
* Phone
* Address
* Loyalty points

Customer phone numbers are unique within an organization.

Customers can be searched and associated with sales.

Sales can also be recorded against a **Walk-in Customer** without creating a registered customer profile.

---

# 10. Supplier Management

Supplier profiles contain:

* Supplier name
* Contact person
* Phone
* Email
* Address

Supplier phone numbers are unique within an organization.

Suppliers are directly associated with purchases, allowing the system to maintain purchase history and supplier spending information.

---

# 11. Staff Management

Business Administrators can create and manage Staff accounts through:

```text
/api/accounts/staff/
```

Staff accounts:

* Belong to the administrator's organization
* Are assigned the `STAFF` role
* Are verified immediately
* Use Business Code + username + password for login

Staff members can access only the modules permitted by their role.

---

# 12. Notifications

INVENTO provides an organization-scoped notification feed.

Notification types include:

| Notification Type | Description                                        |
| ----------------- | -------------------------------------------------- |
| Sale              | Generated after a sale                             |
| Purchase          | Generated after a purchase                         |
| Low Stock         | Generated when stock reaches the minimum threshold |
| Out of Stock      | Generated when inventory reaches zero              |
| System            | General system notifications                       |
| AI Recommendation | Generated AI-based recommendations                 |

Notifications can be marked as read within the application.

---

# 13. Reports

INVENTO provides multiple reporting capabilities.

## 13.1 Sales Report

Provides a date-filterable breakdown containing information such as:

* Invoice
* Customer
* Amount
* Amount paid
* Remaining balance

## 13.2 Purchase Report

Provides a date-filterable breakdown of:

* Purchase invoices
* Suppliers
* Amounts
* Purchase status

## 13.3 Low-Stock Audit

Displays products that are:

* At or below their minimum stock level
* Currently low-stock or out-of-stock

## 13.4 Saved Custom Reports

Business Administrators can create and save reports for:

* Sales
* Purchases
* Inventory
* Customers

Saved reports contain:

* Title
* Description
* Captured report rows

Administrators can later view or delete saved reports.

---

# 14. Dashboard and Analytics

## 14.1 Executive Dashboard

The Executive Dashboard provides a summary of business operations.

### Key Metrics

* Total Revenue
* Total Expenses
* Active Products
* Low/Out-of-Stock Products
* Customer Count
* Supplier Count

## 14.2 Date Filtering

Dashboard metrics can be filtered using:

```text
from_date
to_date
```

## 14.3 Sales vs Purchases

The dashboard provides a comparison between:

* Sales
* Purchases

It includes:

* Total amount
* Transaction count
* Date range
* Visualization

## 14.4 Recent Activity

The dashboard also provides:

* Recent sales
* Recent purchases
* Low-stock alerts

---

# 15. AI-Powered Features

AI functionality is implemented directly within the Django backend through the `ai` application.

There is no separate AI microservice.

The AI provider is **Groq**, accessed through the official Python SDK.

Default model:

```text
llama-3.3-70b-versatile
```

The model can be configured through:

```text
GROQ_MODEL
```

All AI endpoints are tenant-scoped.

---

## 15.1 AI Dashboard

The AI Dashboard combines:

* Demand forecasts
* Reorder recommendations
* AI-generated insights
* Sales metrics
* Low-stock information
* Inventory analysis

---

## 15.2 Business Intelligence

The Business Intelligence module provides:

### Business Overview

* Overall business metrics
* Dashboard statistics

### Sales Intelligence

* Sales summary
* Revenue trends
* Growth compared with previous periods
* Top-selling products

### Inventory Intelligence

* Low-stock products
* Out-of-stock products

### Purchase Intelligence

* Purchase spending
* Top suppliers

### Attention Items

Important business conditions requiring attention.

The reporting window can be controlled using parameters such as:

```text
days
period
bucket
start_date
end_date
```

---

# 16. AI Inventory Summary

The Inventory Summary provides a concise, human-readable analysis of the organization's inventory.

It includes:

* Overall inventory condition
* Inventory population
* Stock health
* Observations
* Recommended actions

This summary is generated from actual tenant inventory data.

---

# 17. Demand Forecasting

INVENTO provides demand forecasting based on historical sales data.

The forecasting system uses:

**scikit-learn `RandomForestRegressor`**

Products with fewer than three sales records are skipped because insufficient historical data is available.

---

# 18. Forecast Details

The Forecast Details module provides weekly predictions for the next four weeks.

It uses:

* Twelve weeks of historical data
* Least-squares linear trend
* Recent-weighted base rate
* Trend-adjusted weekly average

Products without sufficient historical data return an explicit:

```text
insufficient_data
```

result rather than generating an unreliable prediction.

---

# 19. AI Recommendations

The recommendation system calculates restocking suggestions using:

* Current inventory
* Minimum stock thresholds
* Forecasted demand

The system identifies products that may require restocking.

---

# 20. AI Insights

AI Insights generate human-readable business observations such as:

* Best-selling product
* Low-stock products
* Highest expected demand
* Total units sold

Generated insights can be persisted as `AIInsight` records.

The generation process is idempotent, preventing duplicate insights from repeated generation.

Administrators can manage saved insights through the AI Insights page.

---

# 21. AI Inventory Assistant

The AI Inventory Assistant is available to authenticated:

* Business Administrators
* Staff users

The assistant provides a natural-language interface for querying business data.

Users can ask questions about:

* Products
* Inventory
* Stock movements
* Sales
* Purchases
* Customers
* Suppliers
* Categories
* Business performance

It supports date-aware questions such as:

* Today
* This week
* This month
* Last 30 days
* Custom date ranges

### Example Questions

> Which products are running low?

> Which products should I restock?

> How are my sales performing?

> How much revenue did I generate recently?

> Who are my top customers?

> Summarize my current inventory.

> What is my best-selling product this month?

All monetary values are expressed in Nepalese Rupees, for example:

```text
Rs. 2,500.00
```

---

# 22. AI Security

The AI assistant does not have direct database access.

Instead, it uses controlled, tenant-scoped backend tools.

The request flow is:

```text
User
  ↓
AI Assistant
  ↓
Django AI Service
  ↓
Tenant-Scoped Tools
  ↓
Organization Data
```

Every tool operates using the authenticated user's organization.

The Groq API key is stored only in the server-side environment configuration:

```text
GROQ_API_KEY
```

It is never exposed to the frontend.

---

# 23. System Architecture

The high-level architecture of INVENTO is:

```text
                    ┌─────────────────────────────┐
                    │          Users              │
                    │ Business Admin / Staff      │
                    └──────────────┬──────────────┘
                                   │
                                   ▼
                    ┌─────────────────────────────┐
                    │      React 19 + Vite        │
                    │        Frontend              │
                    │ React Router + Axios         │
                    └──────────────┬──────────────┘
                                   │
                              JSON / REST
                                   │
                                   ▼
                    ┌─────────────────────────────┐
                    │ Django 6 + Django REST      │
                    │         Framework            │
                    └──────────────┬──────────────┘
                                   │
              ┌────────────────────┼────────────────────┐
              │                    │                    │
              ▼                    ▼                    ▼
       ┌────────────┐      ┌───────────────┐    ┌──────────────┐
       │ Accounts   │      │    Tenant     │    │ Application  │
       │ & RBAC     │      │   Isolation   │    │   Modules    │
       └────────────┘      └───────────────┘    └──────────────┘
                                                     │
                       ┌─────────────────────────────┼─────────────┐
                       │                             │             │
                       ▼                             ▼             ▼
                 Inventory                      Sales/Purchases   AI
                 Customers                      Suppliers         Reports
                 Notifications                  Business          Dashboard
                       │
                       └─────────────────┬────────────────────────┘
                                         │
                                         ▼
                              ┌─────────────────────┐
                              │     PostgreSQL      │
                              │ Tenant-Scoped Data  │
                              └─────────────────────┘
```

Tenant isolation is implemented at the backend/application-data layer through:

* `TenantModel`
* `TenantModelViewSet`
* `TenantScopedSerializerMixin`

No separate AI microservice is used.

---

# 24. Technology Stack

## 24.1 Frontend

| Technology     | Purpose                           |
| -------------- | --------------------------------- |
| React 19       | User interface                    |
| Vite 8         | Build tool and development server |
| React Router 7 | Client-side routing               |
| Axios          | HTTP/API communication            |
| Recharts       | Charts and analytics              |
| Lucide React   | Icons                             |
| oxlint         | Frontend linting                  |

## 24.2 Backend

| Technology                 | Purpose                           |
| -------------------------- | --------------------------------- |
| Django 6.0                 | Backend framework                 |
| Django REST Framework 3.17 | REST API                          |
| django-filter              | Filtering, searching and ordering |
| django-cors-headers        | CORS management                   |
| Simple JWT                 | JWT authentication                |
| psycopg2-binary            | PostgreSQL database driver        |

## 24.3 Database

```text
PostgreSQL
```

## 24.4 AI and Machine Learning

| Technology            | Purpose                    |
| --------------------- | -------------------------- |
| Groq SDK              | LLM-powered AI assistant   |
| Llama 3.3 70B         | AI language model          |
| scikit-learn          | Demand forecasting         |
| RandomForestRegressor | Forecasting model          |
| pandas                | Data processing            |
| NumPy                 | Numerical processing       |
| joblib                | Machine-learning utilities |

## 24.5 Development Tools

* Python
* Node.js
* Git
* GitHub
* python-dotenv / python-decouple
* Pillow
* Vite
* oxlint

---

# 25. Project Structure

```text
project/
├── backend/
│   ├── accounts/
│   │   └── Custom User, registration, login, staff and RBAC
│   │
│   ├── ai/
│   │   └── AI services and endpoints
│   │       └── services/
│   │           ├── forecasting
│   │           ├── forecast_detail
│   │           ├── recommendation
│   │           ├── insights
│   │           ├── dashboard
│   │           ├── business intelligence
│   │           ├── inventory_summary
│   │           ├── chatbot
│   │           └── tenant-scoped AI tools
│   │
│   ├── business/
│   │   └── Business profile
│   │
│   ├── config/
│   │   └── Django configuration, URLs and WSGI/ASGI
│   │
│   ├── core/
│   │   └── Organization, TenantModel, mixins and utilities
│   │
│   ├── customers/
│   ├── inventory/
│   ├── notifications/
│   ├── purchases/
│   ├── reports/
│   ├── sales/
│   ├── suppliers/
│   ├── requirements.txt
│   └── manage.py
│
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   ├── components/
│   │   ├── context/
│   │   ├── pages/
│   │   ├── services/
│   │   ├── utils/
│   │   ├── App.jsx
│   │   └── main.jsx
│   │
│   ├── public/
│   ├── package.json
│   └── vite.config.js
│
└── README.md
```

---

# 26. Installation and Setup

## 26.1 Prerequisites

The following software is required:

* Python 3.12+
* Node.js 20+
* PostgreSQL
* Git

---

## 26.2 Clone Repository

```bash
git clone https://github.com/B-chand/minor_project.git
cd minor_project
```

---

## 26.3 Backend Setup

```bash
cd backend
python -m venv .venv
```

### Windows

```powershell
.venv\Scripts\activate
```

### Linux/macOS

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## 26.4 Environment Configuration

Create a `.env` file inside the `backend/` directory:

```env
SECRET_KEY=your-django-secret-key
DEBUG=True

DB_NAME=project_db
DB_USER=postgres
DB_PASSWORD=your-db-password
DB_HOST=localhost
DB_PORT=5432

GROQ_API_KEY=your-groq-api-key
GROQ_MODEL=llama-3.3-70b-versatile
```

Additional supported configuration variables include:

```text
ALLOWED_HOSTS
CORS_ALLOW_ALL_ORIGINS
CORS_ALLOWED_ORIGINS
CSRF_TRUSTED_ORIGINS
GROQ_MAX_TOOL_ROUNDS
GROQ_TIMEOUT_SECONDS
LOG_LEVEL
```

**Never commit the `.env` file or API keys to version control.**

---

## 26.5 Database Migration

```bash
python manage.py migrate
```

---

## 26.6 Demo Data

Optional demo data can be generated using:

```bash
python manage.py seed_demo_data
```

The command is idempotent and does not delete existing real data.

---

## 26.7 Start Backend

```bash
python manage.py runserver
```

---

## 26.8 Frontend Setup

Open a second terminal:

```bash
cd frontend
npm install
npm run dev
```

The Vite development server runs at:

```text
http://localhost:5173
```

---

# 27. First Login

To start using INVENTO:

1. Open the frontend.
2. Navigate to **Register**.
3. Create a new organization.
4. Create the first Business Admin account.
5. Save the generated Business Code.
6. Navigate to the login page.
7. Enter:

   * Business Code
   * Username
   * Password
8. After authentication, configure the organization.
9. Add Staff members if required.
10. Add products and categories.
11. Add suppliers and customers.
12. Begin recording purchases and sales.

---

# 28. Security Design

INVENTO implements several security mechanisms.

### Authentication

JWT authentication is required for protected APIs.

### Authorization

Role-based permissions restrict access to administrative functionality.

### Tenant Isolation

Every tenant-owned record is associated with an organization, and all API queries are scoped to the authenticated user's organization.

### Organization Identity

Organization identity is always derived from the authenticated user.

Client-provided organization identifiers are not trusted.

### Password Security

Passwords are securely hashed using Django's built-in password management system.

### Inventory Integrity

Database transactions and row-level locking are used to:

* Prevent negative inventory
* Prevent overselling
* Maintain stock consistency

### AI Security

The Groq API key is stored exclusively on the backend and is never exposed to the frontend.

AI tools can access only data belonging to the authenticated user's organization.

---

# 29. License

This project is developed for **academic purposes** as a Computer Engineering project.

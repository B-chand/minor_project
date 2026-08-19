     # Invento:Smart Multi-Tenant Inventory Management Solution

     ![Project Status](https://img.shields.io/badge/status-active-brightgreen)
     ![Frontend](https://img.shields.io/badge/frontend-React%2019%20%7C%20Vite-blue)
     ![Backend](https://img.shields.io/badge/backend-Django%206%20%7C%20DRF-green)
     ![Database](https://img.shields.io/badge/database-PostgreSQL-blueviolet)
     ![AI](https://img.shields.io/badge/AI-Groq%20%7C%20Scikit--learn-red)

     **INVENTO** is a SaaS-style, AI-powered inventory and business management platform. The repository lives at <https://github.com/B-chand/minor_project>.

     ---

     ## 📌 Overview

     INVENTO is a **multi-tenant inventory management solution**: multiple independent organizations run on the *same* application instance while each organization's data stays completely isolated. An organization registering for the platform is provisioned as its own **tenant** and is assigned a unique **Business Code** (e.g. `B1`, `B2`) used at login.

     Within a tenant, the platform covers the full day-to-day business surface:

     - **Products, categories and inventory** with stock movement history
     - **Suppliers and purchases** that restock inventory
     - **Customers and sales** that automatically deduct inventory
     - **Staff management** with role-based access
     - **Notifications**, **reports**, and a business **dashboard**
     - **AI-powered** forecasting, recommendations, insights and a chat assistant

     Data isolation is enforced at the database/query level: every tenant-owned record carries an `organization` foreign key, and every API query is scoped to the requesting user's organization. Tenant identity is always derived from the authenticated user's account — it is never accepted from the client.

     ---

     ## 🎯 Project Objectives

     - **Multi-tenant architecture** — one application serving many organizations
     - **Secure authentication** — JWT-based login using *Business Code + username + password*
     - **Role-based access control (RBAC)** — distinct Business Admin and Staff capabilities
     - **Inventory management** — stock levels, thresholds, adjustments and full movement history
     - **Sales and purchase management** — transaction recording with automatic stock updates
     - **Reporting and analytics** — dashboard metrics, transaction reports and saved reports
     - **AI-assisted business intelligence** — demand forecasts, restock recommendations, insights and an AI assistant
     - **Tenant data isolation** — strict organization-level scoping on every API and query

     ---

     ## ✨ Key Features

     ### 🏢 Multi-Tenant Architecture

     Every tenant is an `Organization` with its own UUID, profile details, logo and unique Business Code. All business data belongs to a tenant via the shared `TenantModel` base (an `organization` foreign key on every entity).

     Isolation is enforced in three layers:

     1. **`TenantModelViewSet`** (backend) automatically filters every queryset by `request.user.organization` and stamps new records with the user's organization on create.
     2. **`TenantScopedSerializerMixin`** narrows every writable foreign-key field to the user's own tenant, so a client can never reference another organization's records.
     3. The organization is **always** taken from the authenticated user; any `organization` parameter supplied by the client is ignored or rejected.

     A user belongs to exactly one organization and can never switch tenants. A user with no organization sees no tenant data at all.

     ### 🔐 Authentication & RBAC

     - **Registration** opens a new organization and its first **Business Admin** account in one step. The server generates the Business Code and returns it once so the admin can save it for future logins.
     - **Login** (`/api/token/`) requires the Business Code, username and password. The username is looked up *within that organization only*, so the same username may exist in different tenants without conflict. Successful login returns JWT `access`/`refresh` tokens and the user's role and business details.
     - **JWT sessions** use `djangorestframework-simplejwt`; access tokens are valid for 12 hours and refresh tokens for 7 days.

     Roles defined in the system:

     | Role | Code | Responsibilities |
     | --- | --- | --- |
     | Super Admin | `SUPER_ADMIN` | Platform-level role defined in the data model (no organization-tenant login path in the app) |
     | Business Admin | `ADMIN` | Full organization management: staff, products, inventory, sales, purchases, reports, business profile and all AI modules |
     | Staff | `STAFF` | Day-to-day operations: products, inventory, customers, suppliers, purchases, sales, notifications and the AI assistant |

     RBAC is enforced with custom DRF permissions (`IsBusinessAdmin`, `IsStaff`, `IsOrganizationMember`) and route-level role guards in the frontend (Reports, AI, AI Insights, Staff and Business pages are admin-only).

     ### 📦 Product & Category Management

     - **Categories** — grouped product classification, unique per tenant.
     - **Products** — name, SKU, barcode, description, buying/selling prices, image and active status; searchable by name, SKU, barcode or category.
     - Products with remaining inventory cannot be deleted, protecting stock history.

     ### 📊 Inventory Management

     - **Inventory records** — current quantity plus minimum/maximum stock thresholds per product, with an automatic `stock_status` (In Stock / Low Stock / Out of Stock).
     - **Stock adjustments** — a signed quantity adjustment endpoint that locks the row, prevents negative stock, and records an `ADJUSTMENT` movement for the audit trail.
     - **Stock movement history** — every IN, OUT and ADJUSTMENT is logged with quantity, remarks and the acting user, so purchases, sales and adjustments form a complete audit trail.
     - **Automatic updates** — stock increases on purchases and decreases on sales.
     - **Stock alerts** — low-stock and out-of-stock notifications fire automatically.

     ### 🛒 Purchase Management

     Purchases record goods received from suppliers and increase inventory.

     - Create a purchase header (supplier, invoice number, date) and add one or more line items.
     - Each item is saved with its unit cost; the invoice total is computed automatically.
     - **Completed workflow**: the standard UI records every purchase as **Completed**, and the ordered quantities are added to stock immediately — there is no pending/receipt-draft flow exposed in the normal UI.
     - A `StockMovement (IN)` and a purchase notification are generated automatically.
     - Deleting a purchase (or a line item) reverses the stock change so totals stay consistent.

     ### 💰 Sales Management

     Sales are recorded as simple, one-time transactions at the POS:

     - A sale is **one transaction** — pick a customer (or leave it as a *Walk-in Customer*), set the invoice number and date, and add line items.
     - **Inventory is deducted the moment the sale is created** (with stock checked inside a transaction to prevent overselling).
     - The **sale total is a single transaction amount** computed automatically from the line items.
     - The normal UI represents completed sales as **PAID** — a sale order is completed and the amount paid equals the invoice total in one step.
     - Each completed sale creates an `OUT` stock movement and a sale notification, plus low/out-of-stock alerts when thresholds are crossed.
     - Deleting a sale (or a line item) restores the stock.

     There is **no payment-gateway integration**; the platform records in-app transaction amounts only.

     ### 👥 Customer Management

     - Customer profiles (name, email, phone, address) plus **loyalty points**.
     - Phone is unique *within* each organization.
     - Searchable, and automatically integrated with sales (a sale may reference a registered customer or be recorded as a walk-in).

     ### 🏭 Supplier Management

     - Supplier profiles with contact person, phone, email and address.
     - Phone is unique per organization.
     - Suppliers link directly to purchases, enabling spend tracking and purchase history per supplier.

     ### 👨‍💼 Staff/User Management

     - Business Admins can create and manage **Staff** users (`/api/accounts/staff/`).
     - Staff accounts are created under the admin's organization with the `STAFF` role and are verified immediately.
     - Staff members log in with their business code + username + password, exactly like admins, and access their permitted modules.

     ### 🔔 Notifications

     - Organization-scoped notification feed with types: **Sale**, **Purchase**, **Low Stock**, **Out of Stock**, **System** and **AI Recommendation**.
     - Notifications are generated automatically by sales, purchases, stock adjustments and stock-level events, and can be marked as read within the app.

     ### 📑 Reports

     - **Sales report** — date-filterable breakdown of invoices, customers, amounts, amounts paid and remaining balance.
     - **Purchase report** — date-filterable breakdown of purchase invoices, suppliers, amounts and status.
     - **Low stock audit** — products at or below their minimum stock level with current quantities and status.
     - **Saved custom reports** — Business Admins can generate, snapshot and save reports (Sales, Purchase, Inventory, Customer) with a title, description and captured rows, then re-view or delete them later.
     - Dashboard analytics endpoints shared with the Executive Dashboard.

     ### 📈 Dashboard & Analytics

     - **Executive Dashboard** with key metric cards: Total Revenue (Sales), Total Expenses (Purchases), Active Products, and Low / Out of Stock count.
     - **Date-range filtering** — the dashboard metrics can be filtered by `from_date` / `to_date`.
     - **Sales vs Purchases** comparison chart with per-metric summaries (total amount, transaction count, date range).
     - **Network entities** — customer and supplier counts.
     - **Low-stock alerts** widget and **recent Sales/Purchases** tables.

     ---

     ## 🤖 AI-Powered Features

     AI in INVENTO is implemented **inside the Django backend** (the `ai` application) rather than as a separate microservice. The AI provider used is **Groq**, via the official `groq` Python SDK, with the default model **`openai/gpt-oss-120b`** (configured with `GROQ_MODEL`). All AI endpoints are tenant-scoped — the organization always comes from the authenticated user.

     Implemented AI features:

     - **AI Dashboard** — combines demand forecasts, reorder recommendations, generated insights and summary metrics (total sales, low-stock product count) in one endpoint.
     - **Business Intelligence** — a read-only aggregation of business overview, dashboard metrics, sales intelligence (summary, revenue trend, growth vs previous period, top products), inventory intelligence (low/out-of-stock), purchase intelligence (spend, top suppliers) and attention items, with optional reporting-window filters (`days`, `period`, `bucket`, `start_date`/`end_date`).
     - **Inventory Summary** — a concise, rule-based, human-readable summary of the tenant's inventory (overall condition, population, stock health, observations and recommended actions), built purely from real tenant data.
     - **Demand Forecasting** — a per-product demand forecast built with **scikit-learn's `RandomForestRegressor`** from actual sale history (products with fewer than three sales are skipped).
     - **Forecast Details** — per-product weekly forecasting for the next **4 weeks** using a 12-week history and a transparent **trend-adjusted weekly average** method (least-squares linear trend + recent-weighted base rate). Products without enough history return an explicit `insufficient_data` result instead of a fabricated prediction.
     - **Recommendations** — smart reorder suggestions computed from current stock, minimum thresholds and the forecasted demand.
     - **AI Insights** — human-readable insight statements (best seller, low stock, highest expected demand, total units sold) that can be generated and **persisted** as `AIInsight` records (idempotently — repeated generation never duplicates), then managed through the AI Insights page.
     - **AI Inventory Assistant / Chatbot** — a natural-language assistant (see below).

     No API keys are stored or exposed anywhere in the application; the `GROQ_API_KEY` lives only in the server-side `.env` file and is never sent to the browser.

     ---

     ## 💬 AI Assistant

     The **AI Inventory Assistant** (available to every authenticated tenant user, Staff and Business Admin) answers natural-language questions about the organization's business using controlled, tenant-scoped tool calling against the Groq model. The assistant can read data only through the backend's curated tools — it has no direct database access, and every tool is scoped to the authenticated user's organization.

     It supports questions about products, inventory, stock movements, sales, purchases, customers, suppliers, categories, and overall business performance, including date-window awareness (today, this week, this month, last 30 days, custom dates).

     Realistic example questions:

     > Which products are running low?

     > Which products should I restock?

     > How are my sales performing?

     > How much revenue did I generate recently?

     > Who are my top customers?

     > Summarize my current inventory.

     > What is my best-selling product this month?

     All monetary answers are expressed in Nepalese Rupees (e.g. `Rs. 2,500.00`).

     ---

     ## 📊 Dashboard & Analytics

     The **Executive Dashboard** summarizes the tenant's business:

     - **Metric cards** — total revenue (sales), total expenses (purchases), active products, low/out-of-stock count.
     - **Date filtering** — a `from_date`/`to_date` range filter (with validation) applied to the dashboard metrics.
     - **Sales vs Purchases** — a bar-chart comparison plus per-segment totals and transaction counts.
     - **Network entities** — total customers and suppliers.
     - **Low stock alerts** and **recent sales / recent purchases** widgets with quick links to the relevant modules.

     The separate **AI Business Dashboard** adds the AI layer: net profit, sales revenue, stock value, low-stock count, AI inventory summary with recommended actions, business highlights (top product/customer/supplier), stock health, attention items, sales activity with period/bucket controls, revenue trend charts, period-over-period growth, best sellers, low/out-of-stock lists, supplier spend, demand forecasts, reorder recommendations and AI insights.

     ---

     ## 🏗️ System Architecture

     ```
                         Users (Business Admin / Staff)
                                        │
                                        ▼
                         React 19 + Vite Frontend
                              (react-router, axios)
                                        │
                                        ▼
                    Axios  ── JSON ──  REST API (JWT auth)
                                        │
                                        ▼
                    Django 6 + Django REST Framework
                                        │
               ┌────────────────────┼────────────────────┐
               ▼                    ▼                    ▼
          Custom User / RBAC     Tenant Isolation      Application Modules
          (accounts)            (core.TenantModel,     Accounts · Business
                              TenantModelViewSet,   · Inventory
                              TenantScopedSerializer) · Customers ·
                                                       Suppliers ·
                                                       Purchases · Sales ·
                                                       Reports · Notifications
                                                       · AI (forecast, BI,
                                                            insights, chatbot)
               └────────────────────┼────────────────────┘
                                        ▼
                                   PostgreSQL
                              (tenant-scoped data)
     ```

     Tenant isolation lives at the **backend/application-data layer**: the `core` application base classes scope every query and write to the authenticated user's organization before data ever reaches the database. No separate AI microservice exists — the AI features are Django views/services inside the `ai` application.

     ---

     ## 🛠️ Technology Stack

     ### Frontend

     - React 19 (`react`, `react-dom`)
     - Vite 8 build tool and dev server (`@vitejs/plugin-react`)
     - React Router 7 for routing
     - Axios for HTTP/API calls
     - Recharts for charts and analytics visualizations
     - Lucide React for icons
     - oxlint for linting

     ### Backend

     - Django 6.0 (`Django==6.0.7`)
     - Django REST Framework 3.17
     - django-filter (search, filtering and ordering)
     - django-cors-headers (cross-origin API access)
     - djangorestframework-simplejwt (JWT authentication)
     - psycopg2-binary (PostgreSQL driver)

     ### Database

     - PostgreSQL

     ### AI / Machine Learning

     - **Groq** (`groq` SDK) — LLM-backed chat assistant (GPT-OSS-120B)
     - scikit-learn — demand forecasting (`RandomForestRegressor`)
     - pandas and numpy — data manipulation for forecasting
     - joblib — sklearn utilities

     ### Authentication

     - JWT via `djangorestframework-simplejwt` (12-hour access, 7-day refresh tokens)
     - Custom Business-Code + username + password login flow
     - Role-based access control (`SUPER_ADMIN` / `ADMIN` / `STAFF`)

     ### Development Tools

     - python-dotenv / python-decouple — environment configuration
     - Pillow — image handling (product photos, organization logos)
     - `seed_demo_data` Django management command — repeatable demo data seeding
     - Vite dev server + oxlint — frontend development tooling

     ---

     ## 📂 Project Structure

     ```
     project/
     ├── backend/
     │   ├── accounts/          # Custom User, registration, login, staff, RBAC
     │   ├── ai/                # AI services & endpoints
     │   │   └── services/      #   forecasting, forecast_detail, recommendation,
     │   │                      #   insights, dashboard, bi, inventory_summary,
     │   │                      #   chatbot, tools (tenant-scoped AI tools)
     │   ├── business/          # Business profile (type, PAN/VAT, currency)
     │   ├── config/            # Django settings, root urls, wsgi/asgi
     │   ├── core/              # Organization (tenant), TenantModel, mixins,
     │   │                      #   BaseModel + seed_demo_data command
     │   ├── customers/         # Customers
     │   ├── inventory/         # Categories, Products, Inventory, Stock movements
     │   ├── notifications/     # Sales/purchase/stock notifications
     │   ├── purchases/         # Purchases and purchase items
     │   ├── reports/           # Saved reports + dashboard/sales/purchase/low-stock APIs
     │   ├── sales/             # Sales and sale items
     │   ├── suppliers/         # Suppliers
     │   ├── requirements.txt   # Backend Python dependencies
     │   └── manage.py
     │
     ├── frontend/
     │   ├── src/
     │   │   ├── api/           # Axios client and typed API modules
     │   │   ├── components/    # Reusable UI components (layout, common, ai)
     │   │   ├── context/       # Auth + notification providers
     │   │   ├── pages/         # Dashboard, Products, Inventory, Sales, Purchases,
     │   │   │                  #   Customers, Suppliers, Reports, AI, AI Insights,
     │   │   │                  #   AI Assistant (chat), Staff, Business, Notifications…
     │   │   ├── services/      # aiService, chatbotService
     │   │   ├── utils/         # Formatters and helpers
     │   │   ├── App.jsx        # Routes & role guards
     │   │   └── main.jsx
     │   ├── public/
     │   ├── package.json
     │   └── vite.config.js
     │
     └── README.md
     ```

     ---

     ## 🚀 Installation & Setup

     ### Prerequisites

     - **Python 3.12+** (required by Django 6.0)
     - **Node.js 20+** (required by Vite 8)
     - **PostgreSQL** (running locally, e.g. on `localhost:5432`)
     - Git

     ### Clone

     ```bash
     git clone https://github.com/B-chand/minor_project.git
     cd minor_project
     ```

     ### Backend Setup

     ```bash
     cd backend
     python -m venv .venv
     ```

     Activate the virtual environment:

     Linux/Mac:

     ```bash
     source .venv/bin/activate
     ```

     Windows:

     ```powershell
     .venv\Scripts\activate
     ```

     Install dependencies:

     ```bash
     pip install -r requirements.txt
     ```

     Create a `.env` file in the `backend/` directory (a template of the variables below; `.env` is gitignored — never commit secrets):

     ```
     SECRET_KEY=your-django-secret-key
     DEBUG=True

     DB_NAME=project_db
     DB_USER=postgres
     DB_PASSWORD=your-db-password
     DB_HOST=localhost
     DB_PORT=5432

# Groq AI (optional — required for the AI chat assistant)
GROQ_API_KEY=your-groq-api-key
GROQ_MODEL=openai/gpt-oss-120b
     ```

     Additional optional variables supported by `config/settings.py`: `ALLOWED_HOSTS`, `CORS_ALLOW_ALL_ORIGINS`, `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS`, `GROQ_MAX_TOOL_ROUNDS`, `GROQ_TIMEOUT_SECONDS`, `LOG_LEVEL`.

     Apply migrations:

     ```bash
     python manage.py migrate
     ```

     *Optional* — seed every existing organization with realistic demo data (categories, products, suppliers, customers, purchases, sales, stock movements, notifications and AI insights). The command is idempotent and never deletes real data:

     ```bash
     python manage.py seed_demo_data
     ```

     Start the backend server:

     ```bash
     python manage.py runserver
     ```

     ### Frontend Setup

     In a second terminal:

     ```bash
     cd frontend
     npm install
     npm run dev
     ```

     The Vite dev server runs at `http://localhost:5173` (this origin is pre-configured for CORS).

     ### First login

     1. Open the frontend and go to **Register**.
     2. Create the organization and the first Business Admin account.
     3. Note the generated **Business Code**.
     4. Log in with the **Business Code + username + password**.
     5. As an admin, add staff, products/categories, inventory, suppliers and customers, then start recording purchases and sales.

     ---

     ## 🔒 Security Design

     - JWT-based authentication on every protected API
     - Role-based access control for admin-only modules
     - **Tenant-aware data scoping** on every queryset and foreign-key validation
     - Organization identity always derived from the authenticated user (client-supplied tenant values are never trusted)
     - Passwords hashed via Django's built-in password management
     - Server-side stock integrity checks (row locks, no negative stock, no overselling)
     - Groq AI key stored only in server-side environment config and never exposed to clients

     ---

     ## 📄 License

     This project is developed for academic purposes (Computer Engineering minor project).
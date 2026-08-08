import pandas as pd

from sklearn.ensemble import RandomForestRegressor

from sales.models import SaleItem


def forecast_demand(organization=None):

    predictions = []

    product_ids = (
        SaleItem.objects.filter(
            sale__organization=organization
        )
        .values_list(
            "product_id",
            flat=True,
        )
        .distinct()
    )

    for product_id in product_ids:

        sales = (
            SaleItem.objects.filter(
                product_id=product_id,
                sale__organization=organization,
            )
            .select_related(
                "sale",
                "product",
            )
        )

        if sales.count() < 3:
            continue

        data = []

        for item in sales:
            data.append(
                {
                    "date": item.sale.sale_date,
                    "quantity": item.quantity,
                }
            )

        df = pd.DataFrame(data)

        df = (
            df.groupby("date")["quantity"]
            .sum()
            .reset_index()
        )

        df["day"] = range(1, len(df) + 1)

        X = df[["day"]]
        y = df["quantity"]

        model = RandomForestRegressor(
            n_estimators=100,
            random_state=42,
        )

        model.fit(X, y)

        prediction = model.predict(
            [[len(df) + 1]]
        )[0]

        predictions.append(
            {
                "product_id": product_id,
                "product_name": sales.first().product.name,
                "predicted_quantity": max(
                    0,
                    round(prediction),
                ),
            }
        )

    return predictions
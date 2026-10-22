"""Load the supplied snapshot and keep all dashboard aggregations consistent."""

from pathlib import Path

import pandas as pd

DATA_PATH = Path(__file__).with_name("superstore.csv.gz")
SOURCE_URL = "https://www.kaggle.com/datasets/fatihilhan/global-superstore-dataset"
ALL_YEARS = "All years"
ALL_MARKETS = "All markets"


def load_data(path: Path = DATA_PATH) -> pd.DataFrame:
    data = pd.read_csv(path)
    required = {"Order.Date", "Market", "Sub.Category", "Sales", "Profit", "Row.ID"}
    missing = required.difference(data.columns)
    if missing:
        raise ValueError(f"Required columns are missing: {', '.join(sorted(missing))}")
    data["Order.Date"] = pd.to_datetime(data["Order.Date"], errors="raise")
    for column in ("Sales", "Profit"):
        data[column] = pd.to_numeric(data[column], errors="raise")
    if data[list(required)].isna().any().any():
        raise ValueError("A required dashboard field contains missing values.")
    data["Order year"] = data["Order.Date"].dt.year
    return data


def filter_data(data: pd.DataFrame, year=ALL_YEARS, market=ALL_MARKETS) -> pd.DataFrame:
    mask = pd.Series(True, index=data.index)
    if year != ALL_YEARS:
        mask &= data["Order year"].eq(int(year))
    if market != ALL_MARKETS:
        mask &= data["Market"].eq(market)
    return data.loc[mask].copy()


def calculate_metrics(data: pd.DataFrame) -> tuple[float, float, float | None]:
    sales = float(data["Sales"].sum())
    profit = float(data["Profit"].sum())
    margin = profit / sales if sales > 0 else None
    return sales, profit, margin


def monthly_summary(data: pd.DataFrame) -> pd.DataFrame:
    if data.empty:
        return pd.DataFrame(columns=["Month", "Sales", "Profit"])
    summary = data.groupby(pd.Grouper(key="Order.Date", freq="MS"))[
        ["Sales", "Profit"]
    ].sum(min_count=1)
    # Keep absent months missing: do not invent zero sales or profit.
    summary.index.name = "Month"
    return summary.reset_index()


def subcategory_summary(data: pd.DataFrame) -> pd.DataFrame:
    summary = data.groupby("Sub.Category", as_index=False)[["Sales", "Profit"]].sum()
    summary["Margin"] = summary["Profit"].div(summary["Sales"].where(summary["Sales"] > 0))
    # Vega interprets dots in field names as nested-object access.
    return summary.sort_values("Profit", ascending=True).rename(columns={"Sub.Category": "Subcategory"})


def latest_complete_month(data: pd.DataFrame) -> pd.Timestamp | None:
    if data.empty:
        return None
    end = data["Order.Date"].max().normalize()
    month = end.to_period("M")
    if end != month.end_time.normalize():
        month -= 1
    if month < data["Order.Date"].min().to_period("M"):
        return None
    return month.to_timestamp()

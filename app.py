"""A focused sales and profitability dashboard for Yule Liang."""

import altair as alt
import pandas as pd
import streamlit as st

from dashboard_data import (
    ALL_MARKETS,
    ALL_MONTHS,
    ALL_YEARS,
    SOURCE_URL,
    calculate_metrics,
    daily_summary,
    filter_data,
    latest_complete_month,
    load_data,
    month_is_complete,
    monthly_summary,
    subcategory_summary,
)

st.set_page_config(page_title="Superstore | Yule Liang", layout="wide")
st.markdown(
    """
    <style>
    .block-container {max-width: 1280px; padding-top: 3.5rem; padding-bottom: 2rem;}
    h1 {letter-spacing: -0.035em;}
    [data-testid="stMetric"] {
        background: #ffffff; border: 1px solid #dde5df;
        border-radius: 12px; padding: 18px 20px;
    }
    [data-testid="stMetricValue"] {font-variant-numeric: tabular-nums;}
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner=False)
def get_data():
    return load_data()


try:
    df = get_data()
except (OSError, ValueError) as error:
    st.error(f"The sales snapshot could not be loaded: {error}")
    st.stop()

with st.sidebar:
    st.header("Review scope")
    year = st.selectbox(
        "Year", [ALL_YEARS, *sorted(df["Order year"].unique().tolist())], key="year"
    )
    market = st.selectbox(
        "Market", [ALL_MARKETS, *sorted(df["Market"].unique())], key="market"
    )
    year_data = filter_data(df, year)
    month_options = [
        ALL_MONTHS,
        *sorted(year_data["Order.Date"].dt.to_period("M").astype(str).unique()),
    ]
    # A different year must not retain an invisible month from the previous year.
    if st.session_state.get("month", ALL_MONTHS) not in month_options:
        st.session_state["month"] = ALL_MONTHS
    month = st.selectbox(
        "Month", month_options, key="month",
        format_func=lambda value: (
            value if value == ALL_MONTHS else f"{pd.Timestamp(value):%b %Y}"
        ),
    )
    st.caption("Choose a month to align its review, metrics and product breakdown.")
    st.divider()
    st.caption("Prepared by Yule Liang")
    st.caption("Weekly review for the Global Sales Director.")
    st.markdown(f"[Dataset on Kaggle]({SOURCE_URL})")

st.caption("GLOBAL SUPERSTORE / SALES REVIEW")
st.title("Sales & profitability — Yule Liang")
st.write(
    "For the Global Sales Director: identify markets and product groups "
    "that need a profitability review before changing sales or discount plans."
)
period = (
    f"{df['Order.Date'].min():%d %b %Y} – {df['Order.Date'].max():%d %b %Y}"
)
st.caption(
    f"Data: {period}, Kaggle snapshot. Intended production refresh: nightly. "
    "Director review: every Monday. This demonstration does not receive live orders."
)

selected = filter_data(df, year, market, month)
if selected.empty:
    st.info(
        "No sales records match this selection. Review status is unavailable, "
        "not a confirmed zero-profit result. Choose another year, market or month."
    )
    st.stop()

st.caption(
    f"CURRENT SCOPE: {year} / {market} / {month} / {len(selected):,} order-line records. "
    "The three metrics and both charts use exactly this selection."
)
single_month = month != ALL_MONTHS
if single_month:
    chosen_period = pd.Period(month, freq="M")
    if month_is_complete(df, month):
        st.caption(
            f"{chosen_period.to_timestamp():%b %Y}: full calendar month in the historical "
            "snapshot; not a verified accounting close."
        )
    else:
        observed_start = max(df["Order.Date"].min(), chosen_period.start_time)
        observed_end = min(df["Order.Date"].max(), chosen_period.end_time)
        status = (
            "Preliminary month-to-date"
            if observed_start.normalize() == chosen_period.start_time.normalize()
            else "Preliminary partial month"
        )
        st.warning(
            f"{status}: {observed_start:%d %b %Y} – {observed_end:%d %b %Y}. "
            "Do not compare these totals directly with a full month. "
            "A negative result prompts an early check, not the completed-month trigger."
        )
sales, profit, margin = calculate_metrics(selected)
col_sales, col_profit, col_margin = st.columns(3)
col_sales.metric("Total Sales", f"${sales:,.2f}")
col_profit.metric("Total Profit", f"${profit:,.2f}")
col_margin.metric("Profit Margin", f"{margin:.2%}" if margin is not None else "N/A")

# A market's last transaction is not its coverage end: a quiet final day does
# not make that market's month incomplete. Use the snapshot's calendar coverage.
coverage = filter_data(df, year, ALL_MARKETS)
if single_month:
    review_month = pd.Timestamp(month) if month_is_complete(df, month) else None
else:
    review_month = latest_complete_month(coverage)
if review_month is not None:
    recent = selected.loc[
        selected["Order.Date"].dt.to_period("M") == review_month.to_period("M")
    ]
    losses = recent.groupby("Market")["Profit"].sum()
    losses = losses.loc[losses < 0]
    if not losses.empty:
        loss_description = "; ".join(
            f"{name}: \\${value:,.2f}" for name, value in losses.items()
        )
        st.warning(
            f"Completed-month review trigger in {review_month:%b %Y}: {loss_description}. "
            "Ask the regional team to investigate loss-making subcategories "
            "and their discount terms before the next promotion."
        )
    elif not recent.empty:
        st.info(
            f"{review_month:%b %Y}: no selected market had negative total profit. "
            "Check the subcategory chart for losses hidden within profitable markets."
        )
    else:
        st.info(
            f"{review_month:%b %Y}: no transactions are recorded for this market. "
            "Its review status is unavailable, not a confirmed zero-profit result."
        )
    if not single_month:
        st.caption(
            f"This review checks {review_month:%b %Y} only; the metrics and charts above/below "
            "still cover the broader selected period. Inspect this month, then choose a "
            "flagged market, to trace its losses to product groups."
        )

        def inspect_review_month():
            st.session_state["month"] = f"{review_month:%Y-%m}"

        st.button("Inspect review month", on_click=inspect_review_month)
elif single_month:
    preliminary_losses = selected.groupby("Market")["Profit"].sum()
    preliminary_losses = preliminary_losses.loc[preliminary_losses < 0]
    if not preliminary_losses.empty:
        st.warning(
            "Preliminary loss signal: "
            + "; ".join(f"{name}: \\${value:,.2f}" for name, value in preliminary_losses.items())
            + ". Ask the regional team to check product mix, pricing, discounts and costs; "
            "the month has not met the full-calendar coverage rule."
        )
    else:
        st.info("Preliminary review only: no completed-month decision is available for this selection.")
else:
    st.info("No complete calendar month is available for a formal review in this scope.")

trend = daily_summary(selected) if single_month else monthly_summary(selected)
date_field = "Date" if single_month else "Month"
date_format = "%d %b" if single_month else "%b %y"
products = subcategory_summary(selected)
left, right = st.columns([1.15, 1], gap="large")

with left:
    st.subheader("How did performance change?")
    st.caption(
        ("Daily totals within the selected month." if single_month else "Monthly totals.")
        + " The panels have separate dollar scales."
    )
    panels = []
    for field, label, color in (
        ("Sales", "Sales ($)", "#0f766e"),
        ("Profit", "Profit ($)", "#355c8c"),
    ):
        chart = (
            alt.Chart(trend)
            .mark_line(point=True, color=color, strokeWidth=2.5)
            .encode(
                x=alt.X(f"{date_field}:T", title=None, axis=alt.Axis(format=date_format, tickCount=6)),
                y=alt.Y(f"{field}:Q", title=label, scale=alt.Scale(zero=True)),
                tooltip=[
                    alt.Tooltip(f"{date_field}:T", title=date_field, format="%d %b %Y" if single_month else "%b %Y"),
                    alt.Tooltip(f"{field}:Q", title=field, format="$,.2f"),
                ],
            )
            .properties(height=135)
        )
        zero = alt.Chart(pd.DataFrame({"zero": [0]})).mark_rule(
            color="#a7b5b0", strokeDash=[3, 3]
        ).encode(y="zero:Q")
        panels.append(chart + zero)
    trend_chart = (
        alt.vconcat(*panels, spacing=25)
        .resolve_scale(y="independent")
        .configure_view(stroke=None)
        .configure_axis(gridColor="#e4e9e5", labelColor="#50615b", titleColor="#50615b")
    )
    st.altair_chart(trend_chart, width="stretch", key="monthly_trend")
    st.caption(
        "Look for sales growth without comparable profit growth. "
        "A gap has no recorded transactions; it is not a confirmed zero. "
        "Compare equivalent periods and consider seasonality before changing a promotion."
    )

with right:
    st.subheader("Which product groups need attention?")
    st.caption("Subcategory profit, lowest first. Red bars indicate losses.")
    product_chart = (
        alt.Chart(products)
        .mark_bar(cornerRadiusEnd=3)
        .encode(
            x=alt.X("Profit:Q", title="Total profit ($)", axis=alt.Axis(format="~s")),
            y=alt.Y(
                "Subcategory:N",
                title=None,
                sort=alt.SortField(field="Profit", order="ascending"),
                axis=alt.Axis(labelOverlap=False, labelLimit=120),
            ),
            color=alt.condition(alt.datum.Profit < 0, alt.value("#bc4b43"), alt.value("#0f766e")),
            tooltip=[
                alt.Tooltip("Subcategory:N", title="Subcategory"),
                alt.Tooltip("Sales:Q", title="Sales", format="$,.2f"),
                alt.Tooltip("Profit:Q", title="Profit", format="$,.2f"),
                alt.Tooltip("Margin:Q", title="Profit margin", format=".2%"),
            ],
        )
        .properties(height=370)
    )
    zero_line = alt.Chart(pd.DataFrame({"zero": [0]})).mark_rule(color="#82978d").encode(x="zero:Q")
    st.altair_chart(
        (product_chart + zero_line).configure_view(stroke=None),
        width="stretch",
        key="subcategory_profit",
    )
    losing = products.loc[products["Profit"] < 0]
    if not losing.empty:
        st.caption(
            "Loss-making subcategories in this scope: "
            + "; ".join(
                f"{row['Subcategory']} (\\${row['Profit']:,.2f})"
                for _, row in losing.iterrows()
            )
            + "."
        )
    else:
        st.caption("No subcategory has negative total profit in this scope.")

st.divider()
st.caption(
    "Profit margin = sum(Profit) / sum(Sales), not the average of row margins. "
    "Profit is the supplied field; shipping cost is not subtracted again. "
    "Dollar amounts follow the dataset convention and are not independently audited."
)
with st.expander("Data notes and business assumptions"):
    st.markdown(
        """
        - One row is an order line, not a whole order. Negative-profit lines are retained.
        - The source has whole-dollar Sales values, including one zero-sales line;
          no lost precision is reconstructed. A zero-total-sales scope has no defined margin.
        - This is an educational retail scenario, not independently verified company data.
          The uploader does not establish real-company provenance or a complete profit definition.
        - Proposed workflow: check month-to-date results each Monday for early issues.
          Investigate negative market profit formally after the month has full calendar
          coverage. An explicitly selected complete month is reviewed directly;
          the overview checks the latest complete month in the selected year range.
        - Coverage is inferred from the full snapshot's date range, never the last
          transaction of a selected market. It is not a verified accounting close.
          Production use would require a reliable source-coverage timestamp.
        - This snapshot ends in December 2014. No current-month data are invented,
          and there is no automatic feed, same-elapsed-period comparison or causal model.
        - Discounts and losses may be associated. This dashboard does not establish
          that changing a discount will cause a particular profit improvement.
        - An alert can prompt a review; the charts provide the context for that review.
        """
    )

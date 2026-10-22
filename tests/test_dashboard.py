"""Check aggregation, filter consistency, and Streamlit rendering with real data."""

import math
import json
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pyarrow as pa
import streamlit as st
from streamlit.testing.v1 import AppTest

from dashboard_data import (
    ALL_MONTHS, ALL_YEARS, calculate_metrics, daily_summary, filter_data,
    latest_complete_month, load_data, month_is_complete, monthly_summary,
    subcategory_summary,
)

ROOT = Path(__file__).resolve().parents[1]


class DashboardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.df = load_data()

    def test_source_totals(self):
        sales, profit, margin = calculate_metrics(self.df)
        self.assertEqual(len(self.df), 51290)
        self.assertEqual(sales, 12642905)
        self.assertAlmostEqual(profit, 1467457.29128, places=6)
        self.assertAlmostEqual(margin, profit / sales)

    def test_filters_and_monthly_reconciliation(self):
        subset = filter_data(self.df, 2014, "EMEA")
        expected = self.df.loc[
            self.df["Order.Date"].dt.year.eq(2014) & self.df["Market"].eq("EMEA")
        ]
        pd.testing.assert_frame_equal(subset, expected)
        monthly = monthly_summary(subset)
        self.assertAlmostEqual(monthly["Sales"].sum(), subset["Sales"].sum())
        self.assertAlmostEqual(monthly["Profit"].sum(), subset["Profit"].sum())

    def test_zero_sales_and_missing_month(self):
        zero = self.df.loc[self.df["Sales"].eq(0)]
        self.assertIsNone(calculate_metrics(zero)[2])
        sample = self.df.iloc[:2].copy()
        sample["Order.Date"] = pd.to_datetime(["2014-01-01", "2014-03-01"])
        february = monthly_summary(sample).iloc[1]
        self.assertTrue(math.isnan(february["Sales"]))
        self.assertTrue(math.isnan(february["Profit"]))

    def test_every_month_market_reconciles(self):
        # Independently filter original dates, not the helper being tested.
        for period in pd.period_range("2011-01", "2014-12", freq="M"):
            self.assertTrue(month_is_complete(self.df, period))
            for market in ["All markets", *sorted(self.df["Market"].unique())]:
                with self.subTest(month=str(period), market=market):
                    expected = self.df.loc[
                        self.df["Order.Date"].ge(period.start_time)
                        & self.df["Order.Date"].le(period.end_time)
                    ]
                    if market != "All markets":
                        expected = expected.loc[expected["Market"].eq(market)]
                    actual = filter_data(self.df, period.year, market, str(period))
                    pd.testing.assert_frame_equal(actual, expected)
                    for summary in (daily_summary(actual), subcategory_summary(actual)):
                        for field in ("Sales", "Profit"):
                            self.assertAlmostEqual(summary[field].sum(), expected[field].sum())

    def test_calendar_coverage_and_daily_gaps(self):
        self.assertEqual(latest_complete_month(self.df), pd.Timestamp("2014-12-01"))
        partial = self.df.loc[self.df["Order.Date"].le("2014-12-15")]
        self.assertFalse(month_is_complete(partial, "2014-12"))
        self.assertTrue(month_is_complete(partial, "2014-11"))
        self.assertEqual(latest_complete_month(partial), pd.Timestamp("2014-11-01"))
        self.assertFalse(month_is_complete(self.df.iloc[:0], "2014-12"))
        starts_late = self.df.loc[self.df["Order.Date"].ge("2014-12-15")]
        self.assertFalse(month_is_complete(starts_late, "2014-12"))
        self.assertIsNone(latest_complete_month(starts_late))
        sample = self.df.iloc[:2].copy()
        sample["Order.Date"] = pd.to_datetime(["2014-01-01", "2014-01-03"])
        self.assertTrue(math.isnan(daily_summary(sample).iloc[1]["Sales"]))

    def test_app_and_interactive_filter(self):
        app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()
        self.assertEqual(len(app.exception), 0)
        self.assertIn("Yule Liang", app.title[0].value)
        self.assertEqual([m.value for m in app.metric],
                         ["$12,642,905.00", "$1,467,457.29", "11.61%"])
        self.assertEqual(len(app.get("vega_lite_chart")), 2)
        before = [m.value for m in app.metric]
        app.selectbox(key="year").select(2014)
        app.selectbox(key="market").select("EMEA").run()
        self.assertEqual(len(app.exception), 0)
        sales, profit, margin = calculate_metrics(filter_data(self.df, 2014, "EMEA"))
        self.assertEqual([m.value for m in app.metric],
                         [f"${sales:,.2f}", f"${profit:,.2f}", f"{margin:.2%}"])
        self.assertNotEqual(before, [m.value for m in app.metric])
        charts = app.get("vega_lite_chart")
        self.assertEqual(len(charts), 2)
        # Inspect the actual tables delivered to both charts, not just the widgets.
        for chart in charts:
            frames = [
                pa.ipc.open_stream(dataset.data.data).read_all().to_pandas()
                for dataset in chart.proto.datasets
            ]
            chart_data = next(frame for frame in frames if "Sales" in frame.columns)
            self.assertAlmostEqual(float(chart_data["Sales"].sum()), sales)
            self.assertAlmostEqual(float(chart_data["Profit"].sum()), profit)
            spec = json.loads(chart.proto.spec)
            if "Subcategory" in chart_data.columns:
                self.assertEqual(spec["layer"][0]["encoding"]["y"]["field"], "Subcategory")
                self.assertEqual(chart_data["Subcategory"].nunique(), 17)
        app.selectbox(key="market").select("Canada").run()
        self.assertEqual(len(app.exception), 0)
        self.assertTrue(any("Dec 2014" in item.value for item in app.info))

    def assert_scope_charts(self, app, expected):
        self.assertEqual(len(app.exception), 0)
        sales, profit, margin = calculate_metrics(expected)
        self.assertEqual([m.value for m in app.metric],
                         [f"${sales:,.2f}", f"${profit:,.2f}",
                          f"{margin:.2%}" if margin is not None else "N/A"])
        charts = app.get("vega_lite_chart")
        self.assertEqual(len(charts), 2)
        for chart in charts:
            frames = [pa.ipc.open_stream(d.data.data).read_all().to_pandas()
                      for d in chart.proto.datasets]
            chart_data = next(frame for frame in frames if "Sales" in frame.columns)
            self.assertAlmostEqual(chart_data["Sales"].sum(), sales)
            self.assertAlmostEqual(chart_data["Profit"].sum(), profit)

    def test_month_drilldown_and_year_reset(self):
        app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()
        app.selectbox(key="year").select(2014)
        app.selectbox(key="market").select("EMEA").run()
        app.button[0].click().run()
        self.assertEqual(app.selectbox(key="month").value, "2014-12")
        expected = filter_data(self.df, 2014, "EMEA", "2014-12")
        self.assert_scope_charts(app, expected)
        self.assertTrue(any("Daily totals" in item.value for item in app.caption))
        self.assertTrue(any("Dec 2014" in item.value for item in [*app.info, *app.warning]))
        # Selecting an older month must review that month, not December.
        app.selectbox(key="month").select("2014-01").run()
        self.assert_scope_charts(app, filter_data(self.df, 2014, "EMEA", "2014-01"))
        self.assertTrue(any("Jan 2014" in item.value for item in [*app.info, *app.warning]))
        app.selectbox(key="year").select(2013).run()
        self.assertEqual(app.selectbox(key="month").value, ALL_MONTHS)
        self.assert_scope_charts(app, filter_data(self.df, 2013, "EMEA"))
        app.selectbox(key="year").select(ALL_YEARS).run()
        app.selectbox(key="month").select("2011-02").run()
        self.assert_scope_charts(app, filter_data(self.df, ALL_YEARS, "EMEA", "2011-02"))

    def test_partial_month_app_labels_and_no_formal_trigger(self):
        partial = self.df.loc[self.df["Order.Date"].le("2014-12-15")].copy()
        partial["Profit"] = -partial["Profit"].abs()
        st.cache_data.clear()
        try:
            with patch("dashboard_data.load_data", return_value=partial):
                app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()
                app.selectbox(key="year").select(2014).run()
                app.selectbox(key="market").select("EMEA").run()
                app.selectbox(key="month").select("2014-12").run()
                self.assert_scope_charts(app, filter_data(partial, 2014, "EMEA", "2014-12"))
                warnings = " ".join(item.value for item in app.warning)
                self.assertIn("Preliminary month-to-date", warnings)
                self.assertIn("15 Dec 2014", warnings)
                self.assertIn("Preliminary loss signal", warnings)
                self.assertNotIn("Completed-month review trigger", warnings)
        finally:
            st.cache_data.clear()

    def test_empty_selection_is_not_zero_profit(self):
        sparse = self.df.loc[
            ~(self.df["Market"].eq("Canada")
              & self.df["Order.Date"].dt.to_period("M").eq(pd.Period("2014-12")))
        ].copy()
        st.cache_data.clear()
        try:
            with patch("dashboard_data.load_data", return_value=sparse):
                app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()
                app.selectbox(key="market").select("Canada").run()
                app.selectbox(key="month").select("2014-12").run()
                self.assertEqual(len(app.exception), 0)
                self.assertEqual(len(app.metric), 0)
                self.assertTrue(any("not a confirmed zero" in item.value for item in app.info))
        finally:
            st.cache_data.clear()


if __name__ == "__main__":
    unittest.main()

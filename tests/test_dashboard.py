"""Check aggregation, filter consistency, and Streamlit rendering with real data."""

import math
import json
import unittest
from pathlib import Path

import pandas as pd
import pyarrow as pa
from streamlit.testing.v1 import AppTest

from dashboard_data import calculate_metrics, filter_data, load_data, monthly_summary

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


if __name__ == "__main__":
    unittest.main()

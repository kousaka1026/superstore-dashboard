# Global Superstore Sales & Profitability

**Author / team: Yule Liang**  
BANA409, Assignment 4, Part 1

[Open the deployed dashboard](https://superstore-dashboard-asqbnzzkxe8o343yy4nzsn.streamlit.app/) ·
[GitHub repository](https://github.com/kousaka1026/superstore-dashboard)

I designed this dashboard for a **Global Sales Director** to identify markets and
product groups that need a profitability review before changing promotion plans.
It is a historical demonstration, not a live sales system.

![Dashboard preview with all years and markets selected](docs/dashboard-preview.png)

## Step 1 — Dataset and intended user

- **Source:** [Global Superstore Dataset on Kaggle, uploaded by Fatih İlhan](https://www.kaggle.com/datasets/fatihilhan/global-superstore-dataset).
- **Period and size:** January 1, 2011–December 31, 2014; 51,290 rows, 27 original columns,
  7 markets and 147 countries. The original single CSV is about 15.1 MiB, below the
  exercise's approximate 25 MB limit. The repository includes the same file in
  lossless gzip form, without sampling or removing records.
- **Row meaning:** one product line within an order. There are 25,035 distinct
  `Order.ID` values, so counting rows would overstate the number of orders.
- **Provenance:** the uploader describes converting a text file to CSV with R and
  links to an earlier Kaggle version. The page does not verify a real company as
  the source. I treat it as an educational, fictional retail scenario.
  [Tableau describes the Superstore sample family as fictitious](https://help.tableau.com/current/guides/get-started-tutorial/en-us/get-started-tutorial-connect.htm),
  but that does not establish the exact lineage of this processed CSV.
- **License:** the [Kaggle metadata](https://www.kaggle.com/api/v1/datasets/view/fatihilhan/global-superstore-dataset)
  lists MIT. The dataset is attributed to its source.

I chose the Global Sales Director because this role can coordinate regional teams
and review promotion plans across markets. Customer service and warehouse staff
need more operational detail than this page provides. This role and workflow are
design assumptions, not findings from an interview with an actual company.

## Step 2 — Why a dashboard is needed

**Use and decision.** The director reviews the page every Monday before the sales
meeting. During a month, the purpose is to spot preliminary losses and ask for an
early check. After the month ends, the director decides which markets and product
groups need a formal review before approving the next promotion. High sales alone
are not a sufficient reason to continue a promotion.

> If the Global Sales Director sees negative total profit for a market in a complete
> month, they will ask the regional manager to investigate the loss-making
> subcategories, pricing, discount terms and costs before approving the next promotion.

A negative month-to-date result prompts an early check, not the same completed-month
decision. The director should not stop a promotion based only on this chart: the
dataset does not identify the cause of a loss.

**Without the dashboard.** The assumed alternative is exporting orders, filtering
them in a spreadsheet, rebuilding pivot tables, calculating margins and sharing a
static report. Repeating those steps can produce mismatched periods, an incorrect
average of percentages, or losses hidden by profitable products. No time study or
company cost data are available, so I do not claim a measured number of hours or
dollars saved. The business risk is spending analyst time on repeated preparation
and delaying investigation while an unprofitable promotion continues.

**Why not just email, a report or an alert?** The director needs to change the market
and period, then inspect the product groups behind the result. A dashboard makes
those follow-up questions interactive with consistent calculations. An email or
report can summarize the meeting, and an alert can flag a loss, but neither alone
provides this interactive investigation.

## Step 3 — Metrics, charts and design choices

The executed [analysis notebook](analysis.ipynb) checks data quality, distributions,
time coverage and profitability by market, category and discount group.

### Three headline metrics

| Metric | Calculation within the selected scope | Why it matters |
| --- | --- | --- |
| Total Sales | `sum(Sales)` | Establishes sales scale, not profitability. |
| Total Profit | `sum(Profit)` | Shows the dollar contribution or loss. |
| Profit Margin | `sum(Profit) / sum(Sales)` | Distinguishes high sales from efficient earnings. |

Across the full snapshot, these are **$12,642,905.00**, **$1,467,457.29** and **11.61%**.
Margin is calculated from totals, not averaged across rows. A zero-sales denominator
displays N/A.

### Two supporting charts

1. **Sales and profit over time**, in two panels with separate labeled dollar scales.
   The overview shows monthly totals. Selecting a specific month changes the same
   chart to daily totals so it remains useful for investigating that month.
2. **Subcategory profit**, ranked from lowest to highest with loss-making bars in red.
   Tooltips include sales and margin to distinguish low contribution from low efficiency.

These choices follow the EDA: Furniture has $4,110,884 in sales but about 6.94% margin,
compared with 13.99% for Technology. Tables lose $64,083.39 across the snapshot.
EMEA has about 5.45% margin. Sales-only charts would obscure these profitability issues.

### Filters and investigation workflow

**Year, Market and Month** define the review scope. Month options include the year
(for example, Dec 2014), so selecting December never silently combines four years.
Changing Year resets an incompatible Month selection. The three metrics and both
charts always use exactly the same records.

The default overview shows the full snapshot and checks the latest complete month
within the chosen year range. That review message names its own month explicitly;
it is not a statement about the full-period KPI total. **Inspect review month**
narrows the metrics and both charts to that month. Selecting a flagged market then
shows its loss-making subcategories for the same period. When a specific complete
month is selected, the review checks that month instead of silently checking a newer one.

The [layout](docs/layout.md) places purpose and dates first, then KPIs, the review
message and the charts. The numbers establish scale, the trend shows timing and
the product ranking identifies where to investigate.

### Two deliberate exclusions

- **Customer names and customer rankings:** these support account managers, not
  the director's market and product-group review, and add unnecessary detail.
- **Country/city map:** market selection and profit bars answer the decision more
  directly. Geographic area is not a measure of business importance.

### Safeguards against misleading conclusions

- There are no missing cells, duplicate rows or repeated `Row.ID` values in this
  file, but that does not verify its business accuracy. All original rows are retained.
- Negative profit occurs on 12,544 order lines (24.46%), not necessarily that many
  distinct orders. Outliers and losses are not removed.
- The supplied Sales values are whole dollars. One zero-sales line has -$1.11
  profit and remains in totals. Lost source precision is not reconstructed.
- Profit is the supplied field, not verified net income. Shipping cost is not
  subtracted again because its relationship to Profit is undocumented. Currency
  labels follow the dataset convention, without verified exchange-rate treatment.
- Missing days or months stay missing, rather than becoming confirmed zeros.
  An empty selection has unavailable review status, not a zero-profit result.
- An incomplete month is labeled preliminary with its available date range.
  Month-to-date totals are not directly compared with full-month totals. No automated
  same-elapsed-period comparison is implemented. Seasonal effects and product mix
  must be considered before interpreting a change.
- Associations between discounts and losses do not establish causation.

## Step 4 — Refresh cadence and action

| Item | Proposed production policy | Reason |
| --- | --- | --- |
| Refresh | Nightly after the transaction batch | Adds new orders and corrections before the next review; real-time updates are unnecessary. |
| Weekly review | Every Monday, inspect the current month-to-date figures | Identify emerging losses and request an early check while the month is still open. |
| Formal trigger | A market's complete-month reported profit is below $0 | Investigate that month's losing subcategories, prices, discounts and costs before the next promotion. |

Nightly refresh serves the changing **month-to-date** view, not just the completed-month
trigger. In production, the current month would be labeled preliminary until verified
source coverage reaches month end. A week of stale data could omit a week's new orders
and cause the meeting to miss an emerging loss. Even completed months may change after
late postings or corrections. No specific monetary impact is measurable from this file.

The $0 threshold is a proposed management rule, not an observed corporate policy or
a threshold learned from the data. A positive market total does not clear every
subcategory: the breakdown can still reveal losses inside a profitable market.

**What the demonstration actually does:** it reads the committed 2011–2014 CSV.
There is **no automatic production feed or current-month data**. Calendar coverage
is inferred from the full snapshot's date range, not a selected market's last sale;
it is not proof that accounting has closed or every transaction has arrived. All
48 historical months have full calendar coverage, so none is presented as current
month-to-date data. The partial-month logic applies if a future replacement snapshot
ends mid-month. A real deployment would need a verified source-coverage timestamp.
Refreshing Streamlit's cache does not generate new transactions.

## Step 5 — Run and verify

The project was initialized with `uv init` and uses Python 3.14.

```bash
uv sync
uv run streamlit run app.py
uv run python -m unittest discover -s tests -v
```

The public application is deployed from this repository's `main` branch, entrypoint
`app.py`, using Yule Liang's Streamlit account. [Verification notes](docs/verification.md)
describe the checks. For Canvas, the app and repository links are in the first
Markdown cell of `phone-trade-in.ipynb`; the remaining notebook contains Part 2.

## Assignment references

- [In-class exercise and design questions](https://bana409.harrywang.me/docs/lectures/data-app/in-class-group-exercise)
- [Assignment 4 and individual submission requirements](https://bana409.harrywang.me/docs/assignments/assignment-4-linear-regression-sgd-and-random-forest)

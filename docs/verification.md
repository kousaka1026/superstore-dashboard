# Verification

The application was checked locally with Python 3.14.7 using the versions in `uv.lock`.

- The executed `analysis.ipynb` contains six sequentially executed code cells and no error outputs.
- Nine automated checks pass, covering source totals, year/market/month filters,
  daily and monthly reconciliation, missing periods, zero-sales margins, calendar
  coverage and Streamlit interactions. All 48 months are checked across all seven
  markets plus the all-market scope (384 combinations).
- Full-snapshot indicators: sales $12,642,905.00; profit $1,467,457.29; margin 11.61%.
- After selecting 2014 and EMEA: sales $301,702.00; profit $22,600.32; margin 7.49%.
  The tables delivered to both charts reconcile to the same filtered totals.
- After drilling into December 2014 / EMEA: sales $40,016.00; profit $2,537.29;
  margin 6.34%. The trend switches to daily totals and both chart tables still
  reconcile to the selected month. December 2013 / EMEA produces a formal loss
  trigger with -$500.71 profit, and the button opens the matching month.
- Changing Year resets an incompatible Month choice to All months. An explicit
  older month is reviewed directly rather than silently reviewing the latest month.
- A separate test fixture truncates the snapshot at December 15, 2014 and makes
  its profits negative. The app labels December preliminary month-to-date, shows
  an early loss signal, and does not issue a completed-month trigger. The source
  file is not modified. Empty-market/month and late-starting-month fixtures also pass.
- A fresh headless Microsoft Edge session rendered both charts and the Tables
  subcategory label, and reported no browser JavaScript errors.
- The viewport was also checked at 390 pixels wide; the document did not overflow horizontally.
- Dollar amounts in review and loss captions are escaped so Markdown does not
  interpret pairs of dollar signs as mathematical notation.
- Gzip decompression reproduces the original 15,844,267-byte CSV exactly.

The application has been deployed at
[the owner's public Streamlit URL](https://superstore-dashboard-asqbnzzkxe8o343yy4nzsn.streamlit.app/).
The revised month-filter workflow was verified locally in a fresh headless Edge
session before publishing. The README preview shows the revised overview.

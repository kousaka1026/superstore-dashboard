# Verification

The application was checked locally with Python 3.14.7 using the versions in `uv.lock`.

- The executed `analysis.ipynb` contains six sequentially executed code cells and no error outputs.
- Four automated checks pass: full-source totals, filtering and monthly reconciliation,
  zero-sales/missing-month behavior, and Streamlit rendering with reactive chart data.
- Full-snapshot indicators: sales $12,642,905.00; profit $1,467,457.29; margin 11.61%.
- After selecting 2014 and EMEA: sales $301,702.00; profit $22,600.32; margin 7.49%.
  The tables delivered to both charts reconcile to the same filtered totals.
- A fresh headless Microsoft Edge session rendered both charts and the Tables
  subcategory label, and reported no browser JavaScript errors.
- The viewport was also checked at 390 pixels wide; the document did not overflow horizontally.
- Gzip decompression reproduces the original 15,844,267-byte CSV exactly.

These are local verification results. They do not claim that Streamlit Community Cloud
deployment has already occurred; the public app needs to be deployed from the owner's
own account and checked there as described in the README.

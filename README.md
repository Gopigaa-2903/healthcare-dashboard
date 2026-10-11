# CityCare Analytics (Streamlit)

Starts **empty (all KPIs = 0)**. Upload your files and every page fills in.

## Run
```bash
pip install -r requirements.txt
streamlit run app.py
```

## How it works
1. Open **Data Hub** (or the upload box on the home page) and drop files:
   `patients`, `doctors`, `appointments`, `treatments`, `billing` — `.csv` or `.xlsx`
   (one Excel file with 5 sheets also works). Table is auto-detected from file/sheet name or columns.
2. Data goes into an in-memory SQLite DB; all numbers come from SQL (joins, CTEs, window functions) in `queries.py`.
3. "Load sample data" button uses the `Dataset/` folder.

## Pages
Command Center (KPIs, auto-insights, click-to-filter charts, heatmap, Sankey) · Appointments (double-booking check) ·
Doctor Scorecards · Patient 360 · Revenue (forecast, ageing) · SQL Lab · Data Hub

## Files
`app.py` navigation + global filters · `store.py` upload → SQL · `queries.py` all SQL + forecast + insights ·
`pages.py` UI · `ui.py` theme

# StockSense AI – Smart Inventory Analysis & Seasonal Demand Forecasting

Flask + MySQL + pandas/scikit-learn + Chart.js. Inventory, expiry alerts, selling strategy,
reorder recommendations, product sales entry, and ML sales forecasting from your CSV dataset.

## Project structure
```
stocksense/
├── run.py                  <- start the app
├── requirements.txt
├── .env.example            <- copy to .env and add your MySQL password
├── backend/                <- Flask app (routes/, services/, db.py, config.py)
├── database/               <- schema.sql, init_db.py, seed_data.py (sample inventory)
├── dataset/loader.py       <- reads + merges sales.csv / features.csv / stores.csv
├── ml/                     <- features.py, train.py, forecast.py
├── data/                   <- PUT YOUR CSV FILES HERE
├── models/                 <- trained model is saved here (created by training)
└── frontend/               <- templates/index.html + static/css + static/js
```

## Run it – step by step

**Step 1 – Install the tools (one time)**
- Python 3.10 or newer: https://www.python.org/downloads/ (Windows: tick "Add Python to PATH")
- MySQL Server 8.x: https://dev.mysql.org/downloads/mysql/ (or XAMPP). Remember the `root` password you set.

**Step 2 – Open a terminal inside the `stocksense` folder**
- Windows: open the folder, click the address bar, type `cmd`, press Enter.
- Mac/Linux: `cd path/to/stocksense`

**Step 3 – Create a virtual environment and install packages**
```
# Windows
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# Mac / Linux
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**Step 4 – Check your CSV files are in `data/`**
`sales.csv` and `features.csv` are required. `stores.csv` is optional (it was not uploaded; the app
works without it and uses it automatically if you add it). The grocery CSV is only used to create sample
inventory products.

**Step 5 – Tell the app your MySQL password**
Copy `.env.example` to `.env` (Windows: `copy .env.example .env`, Mac/Linux: `cp .env.example .env`),
open `.env` in Notepad/any editor and set `MYSQL_PASSWORD=` to your real password.

**Step 6 – Create the database, tables and sample data**
```
python -m database.init_db
```
You should see: `Database tables are ready.` and `Added 60 sample products ...`.
(To wipe everything and start again: `python -m database.init_db --reset`.)

**Step 7 – Train the forecasting model (about 15–60 seconds)**
```
python -m ml.train
```
It prints the progress and saves the model into `models/`. (You can also click
**Sales Forecasting → Train / retrain model** inside the app instead.)

**Step 8 – Start the app**
```
python run.py
```

**Step 9 – Open the browser**  →  http://127.0.0.1:5000
Stop the server with `Ctrl + C`. Next time you only need: activate venv (Step 3) → `python run.py`.

## What to try first
1. **Dashboard** – cards, charts, low-stock, expiring items, seasonal insights.
2. **Expiry Alerts** – filter by category/period; read the strategy cards (each action has a reason).
3. **Sales** – record a sale; open **Inventory** and see the stock go down. Use the undo button to reverse it.
4. **Sales Forecasting** – pick a store/department/date range; tabs for forecast, trends, seasonal analysis, model accuracy.
5. **Reorder Recommendations** – see which method (sales-based or basic) was used for each product.
6. **Reports** – download CSV or PDF. **Settings** – change lead time etc.; remove sample data when you add your own products.

## How the calculations work (all explainable)
- **Expiry status:** Expired (past date) · Urgent (≤7 days) · Expiring Soon (8–30 days). Only products with stock > 0 are alerted.
- **Units at risk** = stock − (daily sales × days left). Daily sales come from your recorded sales (last 30 days, needs sales on ≥3 days).
  If there is no history, a **labeled assumption** is used: daily sales = minimum stock ÷ 14 (changeable in Settings).
- **Discounts:** 10% / 20% / 30% / 50% by days left, capped at the product's margin so you don't sell below cost
  (except in the last 3 days, where it says so explicitly). BOGO, bundle, campaign, donate, FEFO and "hold reorder" are rule-based, each with a reason.
- **Reorder (sales-based):** reorder point = daily sales × lead time + minimum stock; quantity covers lead time + cover days, capped by shelf life.
  **Reorder (basic, no history):** reorder when stock ≤ minimum; refill to 2× minimum.
- **Forecast model:** trained on `sales.csv` + `features.csv` (merged on store + date). Time-based test on the last 26 weeks; compared with two
  baselines; the best model is re-fit on all history. Only information known in advance is used (store, department, calendar, holiday timing).

## Important limitations (the app says these on screen too)
- The CSV data is **store/department weekly sales** – it is **not** used to predict individual products.
- Per store-department-week predictions are noisy (R² ≈ 0.5); weekly totals across stores are accurate (MAPE ≈ 2%). Weather/CPI/markdown columns added no accuracy.
- The dataset has **US holidays/seasons only** (Black Friday, Labor Day…). No Indian festivals. The Summer/Monsoon/Festive/Winter view is a labeled assumption.
- Future holiday weeks are inferred from past timing. Currency is not specified in the dataset, so forecast numbers are unit-less.
- The grocery CSV's own dates are inconsistent (about half the rows expire before they were received), so sample dates are generated relative to today.
- Charts and icons load from a CDN, so the browser needs internet access.

## Troubleshooting
| Problem | Fix |
|---|---|
| `Access denied for user 'root'` | Wrong password in `.env` (Step 5). |
| `Can't connect to MySQL server` | Start MySQL (Windows: Services → MySQL80 → Start; XAMPP: start MySQL). |
| `ModuleNotFoundError` | Activate the venv (Step 3) and run `pip install -r requirements.txt`. |
| `Missing file: sales.csv` | Put the CSVs in the `data/` folder (exact names). |
| Port 5000 busy (Mac) | Change `port=5000` in `run.py` to 5001. |
| Forecast page says "No model trained yet" | Run Step 7 or click **Train / retrain model**. |

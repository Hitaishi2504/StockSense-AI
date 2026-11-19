"""Dataset processing: read sales.csv + features.csv (+ stores.csv if present) and merge them.

This data is store-and-department level WEEKLY sales. It has no product names,
product quantities or expiry dates, so it is never used for product-level forecasts.
"""
from pathlib import Path

import pandas as pd


class DatasetError(Exception):
    pass


SALES_COLS = {"store_id", "department", "date", "weekly_sales", "is_holiday"}
FEATURE_COLS = {"store_id", "date", "temperature", "fuel_price", "markdown_1", "markdown_2",
                "markdown_3", "markdown_4", "markdown_5", "cpi", "unemployment",
                "is_holiday", "holiday_name", "season"}
EXOG_COLS = ["temperature", "fuel_price", "markdown_1", "markdown_2", "markdown_3",
             "markdown_4", "markdown_5", "cpi", "unemployment"]


def _read(path: Path, required: set, parse_dates=("date",)):
    if not path.exists():
        raise DatasetError(f"Missing file: {path.name}. Put it in the 'data' folder.")
    df = pd.read_csv(path, keep_default_na=True)
    df.columns = [c.strip().lower() for c in df.columns]
    missing = required - set(df.columns)
    if missing:
        raise DatasetError(f"{path.name} is missing columns: {sorted(missing)}")
    for c in parse_dates:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce")
    return df


def load_merged(data_dir):
    """Return (merged_dataframe, report_dict). Raises DatasetError with a clear message."""
    data_dir = Path(data_dir)
    sales = _read(data_dir / "sales.csv", SALES_COLS)
    feats = _read(data_dir / "features.csv", FEATURE_COLS)
    report = {"files_used": ["sales.csv", "features.csv"], "warnings": []}

    bad_dates = int(sales["date"].isna().sum())
    sales = sales.dropna(subset=["date", "weekly_sales"])
    if bad_dates:
        report["warnings"].append(f"Dropped {bad_dates} sales rows with unreadable dates.")
    dup = int(sales.duplicated(["store_id", "department", "date"]).sum())
    if dup:
        sales = sales.drop_duplicates(["store_id", "department", "date"], keep="last")
        report["warnings"].append(f"Removed {dup} duplicate store/department/date rows.")
    fdup = int(feats.duplicated(["store_id", "date"]).sum())
    if fdup:
        feats = feats.drop_duplicates(["store_id", "date"], keep="last")
        report["warnings"].append(f"Removed {fdup} duplicate store/date rows from features.csv.")

    # is_holiday exists in both files -> keep sales.csv's version, check they agree.
    feats = feats.rename(columns={"is_holiday": "is_holiday_feat"})
    df = sales.merge(feats, on=["store_id", "date"], how="left", validate="m:1")
    unmatched = int(df["season"].isna().sum())
    if unmatched:
        report["warnings"].append(f"{unmatched} sales rows had no matching features row (store+date).")
    disagree = int((df["is_holiday"] != df["is_holiday_feat"]).sum())
    if disagree:
        report["warnings"].append(f"{disagree} rows disagree on is_holiday between files (sales.csv used).")
    df = df.drop(columns=["is_holiday_feat"])

    stores_path = data_dir / "stores.csv"
    if stores_path.exists():
        stores = _read(stores_path, {"store_id"}, parse_dates=())
        stores = stores.drop_duplicates("store_id")
        df = df.merge(stores, on="store_id", how="left")
        report["files_used"].append("stores.csv")
    else:
        report["warnings"].append(
            "stores.csv was not found - store type/size is not used. Everything else works without it.")

    df["holiday_name"] = df["holiday_name"].fillna("None")
    df["season"] = df["season"].fillna("Unknown")
    df["is_holiday"] = df["is_holiday"].astype(int)
    df["store_id"] = df["store_id"].astype(int)
    df["department"] = df["department"].astype(int)
    df = df.sort_values(["store_id", "department", "date"]).reset_index(drop=True)

    if df.empty:
        raise DatasetError("No usable rows after merging the CSV files.")
    report.update({
        "rows": int(len(df)),
        "stores": int(df["store_id"].nunique()),
        "departments": int(df["department"].nunique()),
        "date_min": df["date"].min().date().isoformat(),
        "date_max": df["date"].max().date().isoformat(),
        "weeks": int(df["date"].nunique()),
    })
    return df, report

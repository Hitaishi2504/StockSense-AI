"""Feature engineering. Only features that are KNOWN IN ADVANCE are used for the
production model (store, department, calendar, holiday timing, season). Temperature,
CPI, markdowns etc. are not known for future weeks, so they are only used in an
'ablation' experiment to show whether they would have helped."""
import numpy as np
import pandas as pd

CAL_FEATURES = ["store_id", "department", "week_of_year", "month", "quarter",
                "season_code", "is_holiday", "holiday_code", "sd_mean"]
CATEGORICAL = ["store_id", "department"]


def build_reference(df: pd.DataFrame) -> dict:
    """Learn calendar facts from history: month->season, holiday names, holiday timing."""
    month_season = (df.groupby(df["date"].dt.month)["season"]
                    .agg(lambda s: s.mode().iat[0]).to_dict())
    seasons = sorted(df["season"].unique())
    holidays = ["None"] + sorted(n for n in df["holiday_name"].unique() if n != "None")
    h = df[df["is_holiday"] == 1].drop_duplicates("date")
    timing = sorted({(int(d.dayofyear), n) for d, n in zip(h["date"], h["holiday_name"]) if n != "None"})
    return {"month_season": {int(k): v for k, v in month_season.items()},
            "seasons": seasons, "holidays": holidays, "holiday_timing": timing}


def infer_holiday(date: pd.Timestamp, timing, tol=2):
    """For FUTURE weeks: a week is flagged as a holiday week if it falls within `tol`
    days (day-of-year) of a holiday week seen in the historical data."""
    doy = date.dayofyear
    best, name = 999, "None"
    for d, n in timing:
        diff = min(abs(doy - d), 365 - abs(doy - d))
        if diff < best:
            best, name = diff, n
    return (1, name) if best <= tol else (0, "None")


def add_calendar(df: pd.DataFrame, ref: dict, infer_holidays=False) -> pd.DataFrame:
    df = df.copy()
    df["week_of_year"] = df["date"].dt.isocalendar().week.astype(int)
    df["month"] = df["date"].dt.month
    df["quarter"] = df["date"].dt.quarter
    if infer_holidays:
        uniq = {d: infer_holiday(d, ref["holiday_timing"]) for d in df["date"].unique()}
        df["is_holiday"] = [uniq[d][0] for d in df["date"]]
        df["holiday_name"] = [uniq[d][1] for d in df["date"]]
        df["season"] = df["month"].map(ref["month_season"])
    df["season_code"] = df["season"].map({s: i for i, s in enumerate(ref["seasons"])}).fillna(-1).astype(int)
    df["holiday_code"] = df["holiday_name"].map({h: i for i, h in enumerate(ref["holidays"])}).fillna(0).astype(int)
    return df


def metrics(y, p) -> dict:
    y, p = np.asarray(y, float), np.asarray(p, float)
    err = y - p
    mask = y != 0
    ss_res, ss_tot = float((err ** 2).sum()), float(((y - y.mean()) ** 2).sum())
    return {
        "mae": float(np.abs(err).mean()),
        "rmse": float(np.sqrt((err ** 2).mean())),
        "mape": float(np.abs(err[mask] / y[mask]).mean() * 100) if mask.any() else None,
        "wape": float(np.abs(err).sum() / np.abs(y).sum() * 100) if np.abs(y).sum() else None,
        "r2": float(1 - ss_res / ss_tot) if ss_tot else None,
    }

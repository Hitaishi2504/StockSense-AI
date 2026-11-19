"""Train + evaluate the forecasting model on the real CSV data.

Evaluation is a TIME-BASED holdout: the last N weeks are never seen during training
(no random shuffling, which would leak the future into the past)."""
import json
import time
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.inspection import permutation_importance

from dataset.loader import EXOG_COLS, load_merged
from .features import CAL_FEATURES, CATEGORICAL, add_calendar, build_reference, metrics

TEST_WEEKS = 26


def _hgb(features):
    cats = [c for c in CATEGORICAL if c in features]
    return HistGradientBoostingRegressor(max_iter=300, learning_rate=0.06, max_leaf_nodes=31,
                                         min_samples_leaf=40, categorical_features=cats or None,
                                         random_state=42)


def _rf():
    return RandomForestRegressor(n_estimators=120, min_samples_leaf=30, max_features=0.7,
                                 n_jobs=-1, random_state=42)


def _both_levels(test, pred):
    """Metrics per store-department-week, and for the weekly grand total."""
    row = metrics(test["weekly_sales"], pred)
    tmp = test[["date", "weekly_sales"]].assign(pred=pred).groupby("date").sum()
    return {"row_level": row, "weekly_total": metrics(tmp["weekly_sales"], tmp["pred"])}


def train(data_dir, model_dir, test_weeks=TEST_WEEKS, log=print):
    t0 = time.time()
    model_dir = Path(model_dir)
    model_dir.mkdir(parents=True, exist_ok=True)

    log("Loading and merging CSV files...")
    df, report = load_merged(data_dir)
    if report["weeks"] < test_weeks + 52:
        raise ValueError(f"Need at least {test_weeks + 52} weeks of history; found {report['weeks']}.")

    ref = build_reference(df)
    df = add_calendar(df, ref)
    dates = sorted(df["date"].unique())
    cutoff = dates[-test_weeks]
    train_df, test_df = df[df["date"] < cutoff].copy(), df[df["date"] >= cutoff].copy()

    # store+department average level, learned from TRAINING rows only
    sd = train_df.groupby(["store_id", "department"])["weekly_sales"].mean().rename("sd_mean")
    train_df = train_df.join(sd, on=["store_id", "department"])
    test_df = test_df.join(sd, on=["store_id", "department"])
    test_df["sd_mean"] = test_df["sd_mean"].fillna(train_df["weekly_sales"].mean())

    results = {}
    log(f"Train: {len(train_df):,} rows | Test (last {test_weeks} weeks): {len(test_df):,} rows")

    # --- baselines (so the ML model has something honest to beat) ---
    results["Baseline: store+dept average"] = _both_levels(test_df, test_df["sd_mean"].values)
    ly = df.set_index(["store_id", "department", "date"])["weekly_sales"]
    keys = list(zip(test_df["store_id"], test_df["department"], test_df["date"] - pd.Timedelta(days=364)))
    last_year = ly.reindex(keys).values
    ok = ~np.isnan(last_year)
    results["Baseline: same week last year"] = _both_levels(test_df[ok], last_year[ok])

    # --- ML candidates ---
    fitted, preds = {}, {}
    for name, builder in (("HistGradientBoosting", lambda: _hgb(CAL_FEATURES)), ("RandomForest", _rf)):
        log(f"Training {name}...")
        m = builder().fit(train_df[CAL_FEATURES], train_df["weekly_sales"])
        p = m.predict(test_df[CAL_FEATURES])
        fitted[name], preds[name] = m, p
        results[name] = _both_levels(test_df, p)

    best = min(fitted, key=lambda n: results[n]["row_level"]["mae"])
    log(f"Best model on the holdout: {best}")

    # --- ablation: would weather/CPI/markdowns have helped? (they are unknown for the future) ---
    log("Running feature ablation (weather / CPI / markdown features)...")
    ex_feats = CAL_FEATURES + EXOG_COLS
    m_ex = _hgb(ex_feats).fit(train_df[ex_feats], train_df["weekly_sales"])
    ablation = {"calendar_only": results["HistGradientBoosting"]["row_level"],
                "calendar_plus_external": metrics(test_df["weekly_sales"], m_ex.predict(test_df[ex_feats]))}
    corr = df[["weekly_sales"] + EXOG_COLS].corr()["weekly_sales"].drop("weekly_sales").round(3).to_dict()

    # --- permutation importance on the holdout sample ---
    samp = test_df.sample(min(6000, len(test_df)), random_state=1)
    pi = permutation_importance(fitted[best], samp[CAL_FEATURES], samp["weekly_sales"],
                                n_repeats=3, random_state=1, scoring="neg_mean_absolute_error")
    importance = sorted(({"feature": f, "importance": float(v)} for f, v in zip(CAL_FEATURES, pi.importances_mean)),
                        key=lambda x: -x["importance"])

    holdout = test_df[["store_id", "department", "date"]].assign(
        actual=test_df["weekly_sales"].values, predicted=preds[best])
    holdout.to_csv(model_dir / "holdout_predictions.csv", index=False)

    # --- refit the chosen model on ALL history for real future forecasts ---
    log("Refitting the best model on all history...")
    sd_all = df.groupby(["store_id", "department"])["weekly_sales"].mean().rename("sd_mean")
    full = df.join(sd_all, on=["store_id", "department"])
    final = (_hgb(CAL_FEATURES) if best == "HistGradientBoosting" else _rf()).fit(
        full[CAL_FEATURES], full["weekly_sales"])

    meta = {
        "trained_at": datetime.now().isoformat(timespec="seconds"),
        "model_name": best, "features": CAL_FEATURES,
        "train_rows": int(len(train_df)), "test_rows": int(len(test_df)),
        "test_weeks": test_weeks,
        "train_period": [str(train_df["date"].min().date()), str(train_df["date"].max().date())],
        "test_period": [str(test_df["date"].min().date()), str(test_df["date"].max().date())],
        "last_data_date": str(df["date"].max().date()),
        "results": results, "ablation": ablation, "correlations": corr,
        "importance": importance, "dataset_report": report,
        "seconds": round(time.time() - t0, 1),
    }
    joblib.dump({"model": final, "ref": ref, "sd_mean": sd_all.to_dict(), "meta": meta},
                model_dir / "sales_model.joblib")
    (model_dir / "model_report.json").write_text(json.dumps(meta, indent=2))
    log(f"Done in {meta['seconds']}s.")
    return meta


if __name__ == "__main__":
    from backend.config import Config
    train(Config.DATA_DIR, Config.MODEL_DIR)

import json
import traceback
from datetime import datetime

from flask import Blueprint, jsonify, request

from dataset.loader import DatasetError
from ml import forecast as fc
from ml.train import train as train_model

from .. import db
from ..config import Config
from ..utils import err

bp = Blueprint("forecast", __name__, url_prefix="/api/forecast")


def _wrap(fn):
    try:
        return jsonify(fn())
    except DatasetError as e:
        return err(str(e), 422, code="dataset")
    except FileNotFoundError as e:
        return err(str(e), 409, code="no_model")


@bp.get("/meta")
def meta():
    return _wrap(lambda: fc.meta(Config.DATA_DIR, Config.MODEL_DIR))


@bp.post("/train")
def train():
    try:
        res = train_model(Config.DATA_DIR, Config.MODEL_DIR, log=lambda m: None)
    except DatasetError as e:
        return err(str(e), 422, code="dataset")
    except ValueError as e:
        return err(str(e), 422)
    best = res["results"][res["model_name"]]
    db.execute("INSERT INTO model_runs (trained_at, model_name, train_rows, test_rows, mae, rmse, mape, r2, notes) "
               "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
               (datetime.now(), res["model_name"], res["train_rows"], res["test_rows"],
                best["row_level"]["mae"], best["row_level"]["rmse"], best["row_level"]["mape"],
                best["row_level"]["r2"], json.dumps({"weekly_total": best["weekly_total"]})))
    return jsonify({"message": f"Model trained in {res['seconds']}s. Best: {res['model_name']}.",
                    "model": fc._public_model_info(res)})


@bp.get("/series")
def series():
    a = request.args
    weeks = max(1, min(int(a.get("weeks", 12)), 26))
    return _wrap(lambda: fc.series(Config.DATA_DIR, Config.MODEL_DIR, a.get("store", "all"),
                                   a.get("department", "all"), a.get("start"), a.get("end"), weeks))


@bp.get("/analysis")
def analysis():
    a = request.args
    return _wrap(lambda: fc.analysis(Config.DATA_DIR, a.get("store", "all"), a.get("department", "all"),
                                     a.get("start"), a.get("end")))

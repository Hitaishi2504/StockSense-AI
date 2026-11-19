"""Central configuration. Values come from the .env file (see .env.example)."""
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class Config:
    # "mysql" is the real target. "sqlite" exists ONLY for automated tests.
    DB_BACKEND = os.getenv("DB_BACKEND", "mysql").lower()
    MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
    MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
    MYSQL_USER = os.getenv("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
    MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "stocksense")
    SQLITE_PATH = os.getenv("SQLITE_PATH", str(BASE_DIR / "stocksense_test.db"))

    DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))
    MODEL_DIR = Path(os.getenv("MODEL_DIR", BASE_DIR / "models"))
    JSON_SORT_KEYS = False

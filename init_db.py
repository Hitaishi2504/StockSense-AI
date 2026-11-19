"""Create the MySQL database + tables, then add sample inventory data.

Usage (from the project root):
    python -m database.init_db            # create tables + sample data (only if empty)
    python -m database.init_db --reset    # DROP all tables and start fresh
    python -m database.init_db --no-sample
"""
import re
import sys
from pathlib import Path

from backend import create_app, db
from backend.config import Config
from database.seed_data import seed

SCHEMA = Path(__file__).with_name("schema.sql")
TABLES = ["sales", "products", "suppliers", "app_settings", "model_runs"]


def _create_mysql_database():
    import pymysql
    conn = pymysql.connect(host=Config.MYSQL_HOST, port=Config.MYSQL_PORT, user=Config.MYSQL_USER,
                           password=Config.MYSQL_PASSWORD, charset="utf8mb4")
    with conn.cursor() as cur:
        cur.execute(f"CREATE DATABASE IF NOT EXISTS `{Config.MYSQL_DATABASE}` CHARACTER SET utf8mb4")
    conn.commit()
    conn.close()


def _schema_sql():
    text = SCHEMA.read_text()
    # drop the CREATE DATABASE / USE lines: the database is created separately above
    text = re.sub(r"(?im)^\s*(CREATE DATABASE|USE)\b[^;]*;", "", text)
    if db.IS_SQLITE:  # only used by automated tests
        text = text.replace("INT AUTO_INCREMENT PRIMARY KEY", "INTEGER PRIMARY KEY AUTOINCREMENT")
    return text


def main(argv):
    reset, sample = "--reset" in argv, "--no-sample" not in argv
    if not db.IS_SQLITE:
        try:
            _create_mysql_database()
        except Exception as e:
            print("\nCould not connect to MySQL:", e)
            print("Check that MySQL is running and that the values in your .env file are correct.")
            return 1
    app = create_app()
    with app.app_context():
        if reset:
            conn = db.get_conn()
            cur = conn.cursor()
            if not db.IS_SQLITE:
                cur.execute("SET FOREIGN_KEY_CHECKS = 0")
            for t in TABLES:
                cur.execute(f"DROP TABLE IF EXISTS {t}")
            if not db.IS_SQLITE:
                cur.execute("SET FOREIGN_KEY_CHECKS = 1")
            conn.commit()
            print("Dropped existing tables.")
        db.run_script(_schema_sql())
        print("Database tables are ready.")
        if sample:
            print(seed(force=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

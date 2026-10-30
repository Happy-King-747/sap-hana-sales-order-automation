"""
Sales Order Automation Agent
Watches a local folder for CSV files, loads them into SAP HANA Cloud
(SALES_ORDERS table), prints a summary report, and archives the file.
"""
import csv
import os
import shutil
import time

from dotenv import load_dotenv
from hdbcli import dbapi

load_dotenv()

WATCH = os.environ["WATCH_FOLDER"]
DONE = os.path.join(WATCH, "processed")
FAILED = os.path.join(WATCH, "failed")
REQUIRED = ["ORDER_ID", "CUSTOMER_ID", "ORDER_DATE", "NET_AMOUNT", "CURRENCY"]

os.makedirs(DONE, exist_ok=True)
os.makedirs(FAILED, exist_ok=True)


def connect():
    return dbapi.connect(
        address=os.environ["HANA_HOST"],
        port=443,
        user=os.environ["HANA_USER"],
        password=os.environ["HANA_PASSWORD"],
        encrypt=True,
    )


def read_csv(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        missing = [c for c in REQUIRED if c not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"Missing columns: {missing}")
        return [
            (r["ORDER_ID"], r["CUSTOMER_ID"], r["ORDER_DATE"],
             float(r["NET_AMOUNT"]), r["CURRENCY"])
            for r in reader
        ]


def load_rows(conn, rows):
    cur = conn.cursor()
    # Delete-then-insert so re-loading the same file never creates duplicates
    for r in rows:
        cur.execute("DELETE FROM SALES_ORDERS WHERE ORDER_ID = ?", (r[0],))
    cur.executemany("INSERT INTO SALES_ORDERS VALUES (?,?,?,?,?)", rows)
    conn.commit()


def report(conn):
    cur = conn.cursor()
    print("  Total sales by currency:")
    cur.execute(
        "SELECT CURRENCY, SUM(NET_AMOUNT) FROM SALES_ORDERS GROUP BY CURRENCY"
    )
    for currency, total in cur.fetchall():
        print(f"    {currency}: {total:,.2f}")
    print("  Orders per customer:")
    cur.execute(
        "SELECT CUSTOMER_ID, COUNT(*) FROM SALES_ORDERS "
        "GROUP BY CUSTOMER_ID ORDER BY 2 DESC"
    )
    for customer, n in cur.fetchall():
        print(f"    {customer}: {n}")


def process(name):
    path = os.path.join(WATCH, name)
    try:
        rows = read_csv(path)
        conn = connect()
        load_rows(conn, rows)
        print(f"[OK] {name}: loaded {len(rows)} rows")
        report(conn)
        conn.close()
        shutil.move(path, os.path.join(DONE, name))
    except Exception as e:
        print(f"[FAILED] {name}: {e}")
        shutil.move(path, os.path.join(FAILED, name))


if __name__ == "__main__":
    print(f"Watching {WATCH} (Ctrl+C to stop)")
    try:
        while True:
            for name in os.listdir(WATCH):
                if name.lower().endswith(".csv"):
                    process(name)
            time.sleep(10)
    except KeyboardInterrupt:
        print("\nAgent stopped.")

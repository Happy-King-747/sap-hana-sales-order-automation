"""
Ask questions about SALES_ORDERS in plain English.

Flow: question -> SQL (keyword demo now, LLM later) -> safety check -> HANA -> answer.
Only read-only queries on SALES_ORDERS are ever executed.
"""
import os
import re

ALLOWED_TABLE = "SALES_ORDERS"
FORBIDDEN = [
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE",
    "GRANT", "REVOKE", "MERGE", "CALL", "EXEC", "UPSERT", "REPLACE", "INTO",
]
MAX_ROWS = 100


# ---------- 1. Safety checker (used no matter who writes the SQL) ----------
def validate_sql(sql: str) -> str:
    """Return a safe version of the SQL, or raise ValueError."""
    sql = sql.strip().rstrip(";").strip()
    if not sql:
        raise ValueError("Empty query")
    if "--" in sql or "/*" in sql:
        raise ValueError("Comments are not allowed")
    if ";" in sql:
        raise ValueError("Only one statement is allowed")
    if not re.match(r"(?is)^select\b", sql):
        raise ValueError("Only SELECT queries are allowed")
    for word in FORBIDDEN:
        if re.search(rf"(?i)\b{word}\b", sql):
            raise ValueError(f"Forbidden keyword: {word}")
    # every table after FROM / JOIN must be SALES_ORDERS
    tables = re.findall(r"(?i)\b(?:from|join)\s+([\w\".]+)", sql)
    if not tables:
        raise ValueError("No table found")
    my_schema = os.environ.get("HANA_USER", "DBADMIN").upper()
    for t in tables:
        parts = t.replace('"', "").upper().split(".")
        if parts[-1] != ALLOWED_TABLE or (len(parts) == 2 and parts[0] != my_schema) or len(parts) > 2:
            raise ValueError(f"Table not allowed: {t}")
    if not re.search(r"(?i)\blimit\s+\d+\s*$", sql):
        sql += f" LIMIT {MAX_ROWS}"
    return sql


# ---------- 2. Question -> SQL ----------
def demo_question_to_sql(question: str) -> str:
    """Keyword matcher used until an LLM key is available."""
    q = question.lower()
    cust = re.search(r"\bc\d{3}\b", q)
    if cust and ("total" in q or "sales" in q or "spent" in q or "amount" in q):
        return ("SELECT CUSTOMER_ID, SUM(NET_AMOUNT) AS TOTAL, CURRENCY FROM SALES_ORDERS "
                f"WHERE CUSTOMER_ID = '{cust.group().upper()}' GROUP BY CUSTOMER_ID, CURRENCY")
    if cust:
        return f"SELECT * FROM SALES_ORDERS WHERE CUSTOMER_ID = '{cust.group().upper()}'"
    if "currency" in q:
        return "SELECT CURRENCY, SUM(NET_AMOUNT) AS TOTAL FROM SALES_ORDERS GROUP BY CURRENCY"
    if "per customer" in q or "each customer" in q or "by customer" in q:
        return ("SELECT CUSTOMER_ID, COUNT(*) AS ORDERS FROM SALES_ORDERS "
                "GROUP BY CUSTOMER_ID ORDER BY ORDERS DESC")
    if "largest" in q or "biggest" in q or "highest" in q:
        return "SELECT * FROM SALES_ORDERS ORDER BY NET_AMOUNT DESC LIMIT 1"
    if "how many" in q or "count" in q:
        return "SELECT COUNT(*) AS ORDER_COUNT FROM SALES_ORDERS"
    if "all" in q or "list" in q or "show" in q:
        return "SELECT * FROM SALES_ORDERS ORDER BY ORDER_ID"
    raise ValueError("Demo mode doesn't understand that question yet")


def llm_question_to_sql(question: str) -> str:
    """Part 2: call an LLM here once you have an API key."""
    raise NotImplementedError("LLM not connected yet")


def question_to_sql(question: str) -> str:
    if os.environ.get("LLM_PROVIDER"):
        return llm_question_to_sql(question)
    return demo_question_to_sql(question)


# ---------- 3. Run on HANA ----------
def run_query(sql: str):
    from dotenv import load_dotenv
    from hdbcli import dbapi
    load_dotenv()
    conn = dbapi.connect(
        address=os.environ["HANA_HOST"], port=443,
        user=os.environ["HANA_USER"], password=os.environ["HANA_PASSWORD"],
        encrypt=True,
    )
    try:
        cur = conn.cursor()
        cur.execute(sql)
        cols = [d[0] for d in cur.description]
        return cols, cur.fetchall()
    finally:
        conn.close()


def show(cols, rows):
    if not rows:
        print("  (no rows)")
        return
    widths = [max(len(str(c)), *(len(str(r[i])) for r in rows)) for i, c in enumerate(cols)]
    print("  " + " | ".join(str(c).ljust(w) for c, w in zip(cols, widths)))
    print("  " + "-+-".join("-" * w for w in widths))
    for r in rows:
        print("  " + " | ".join(str(v).ljust(w) for v, w in zip(r, widths)))


if __name__ == "__main__":
    print("Ask about your sales orders (type 'exit' to quit).")
    print("Examples: total sales by currency | orders per customer | total for C001")
    while True:
        question = input("\nQuestion> ").strip()
        if question.lower() in ("exit", "quit"):
            break
        if not question:
            continue
        try:
            sql = validate_sql(question_to_sql(question))
            print("  SQL:", sql)
            show(*run_query(sql))
        except Exception as e:
            print("  Could not answer:", e)

# Sales Order Automation (SAP BTP + HANA Cloud + Python)

A small data pipeline that loads sales order files from a local folder into SAP HANA Cloud
(on SAP BTP) and lets you query the data with SQL or plain-English questions.

## Flow
```
Local folder (CSV) -> Python agent -> SAP HANA Cloud table (SALES_ORDERS) -> SQL reports
                                                   ^
Plain-English question -> SQL -> safety check -------+
```

## Components
| File | Purpose |
|---|---|
| `agent.py` | Watches the `incoming` folder, validates CSVs, loads rows into HANA, prints summaries, archives files |
| `ask_agent.py` | Question interface: question -> SQL -> safety check -> HANA -> result table |
| `test_connection.py` | Checks the HANA connection settings |
| `sample_data/` | Example CSV files |

## Features
- Detects new CSV files automatically (checks every 10 seconds)
- Validates required columns before loading
- Idempotent loads: re-loading an order replaces it instead of creating a duplicate
- Moves files to `processed/` on success and `failed/` on error
- Query interface restricted to read-only `SELECT` statements on one approved table
  (blocks multiple statements, comments, DML/DDL keywords, and other tables or schemas)
- Credentials stored in `.env`, excluded from Git

## Tech
SAP BTP (trial), SAP HANA Cloud, SQL, Python 3.11, hdbcli, python-dotenv, VS Code

## Setup
1. Create the table in SAP HANA Database Explorer:
   ```sql
   CREATE TABLE SALES_ORDERS (
     ORDER_ID    NVARCHAR(10) PRIMARY KEY,
     CUSTOMER_ID NVARCHAR(10),
     ORDER_DATE  DATE,
     NET_AMOUNT  DECIMAL(15,2),
     CURRENCY    NVARCHAR(5)
   );
   ```
2. In HANA Cloud Central, allow connections from your IP (Manage Configuration -> Connections).
3. Install libraries: `python -m pip install -r requirements.txt`
4. Copy `.env.example` to `.env` and fill in your host (without `:443`), user and password.
   Keep `WATCH_FOLDER=incoming`.

## Run
**Load files**
```
python agent.py
copy sample_data\sales_orders.csv incoming\
```
**Ask questions** (in a separate run)
```
python ask_agent.py
Question> total sales by currency
Question> orders per customer
Question> total for C001
Question> how many orders
```

## Sample result
Two sample files (8 unique orders, one order repeated across files) produce:
- USD 5,550.00 | EUR 3,910.50 | INR 1,051.00
- Orders per customer: C001 = 3, C002 = 2, C003 = 2, C004 = 1

## Security notes
- No credentials in code or Git; use `.env`.
- The query layer runs only validated read-only SQL on `SALES_ORDERS`.
- Use a dedicated database user with limited rights instead of DBADMIN in production.

## Roadmap
- Connect an LLM so any question is converted into SQL (the safety checker stays in place)
- Support more tables and a scheduled run

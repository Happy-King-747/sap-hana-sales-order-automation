"""Tries a few connection settings and reports which one works."""
import os
from dotenv import load_dotenv
from hdbcli import dbapi

load_dotenv()

variants = {
    "A: encrypt only": dict(encrypt=True),
    "B: openssl provider": dict(encrypt=True, sslCryptoProvider="openssl"),
    "C: mscrypto provider": dict(encrypt=True, sslCryptoProvider="mscrypto"),
    "D: no certificate check (testing only)": dict(encrypt=True, sslValidateCertificate=False),
}

for label, extra in variants.items():
    try:
        conn = dbapi.connect(
            address=os.environ["HANA_HOST"], port=443,
            user=os.environ["HANA_USER"], password=os.environ["HANA_PASSWORD"],
            **extra,
        )
        cur = conn.cursor()
        cur.execute("SELECT CURRENT_USER FROM DUMMY")
        print(f"[WORKS] {label} -> logged in as {cur.fetchone()[0]}")
        conn.close()
    except Exception as e:
        print(f"[fails] {label} -> {str(e)[:110]}")

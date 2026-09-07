"""
Copy data from Snowflake (source) to Postgres (target).

- Credentials/config are read from .streamlit/secrets.toml:
    * Source (Snowflake) keys are the ones prefixed with `sf_` (sf_account, sf_user, ...).
    * Target (Postgres) keys are the ones prefixed with `postgres_` (postgres_host, ...).
    * Target schema is read from `postgres_schema` if present, otherwise defaults to "ganesh_schema".
- Tables are created in Postgres (if missing) with a SERIAL id column.
- Rows are copied WITHOUT the source id column, inserted in ascending source-id order so the
  new SERIAL ids come out in the same relative order as the Snowflake data.
- After loading each table, the Postgres sequence backing the id column is reset to
  MAX(id), so any new record inserted afterwards automatically gets the next sequence value.
- Every run does a fresh full copy: each target table is truncated before reloading, so
  reruns never duplicate or lose data. Pass --no-truncate to append instead.

Usage:
    python migrate_snowflake_to_postgres.py [--tables events,expenses] [--no-truncate]
"""
import argparse
import os
import sys
import tomllib

import psycopg2
import psycopg2.extras
import snowflake.connector

SECRETS_PATH = os.path.join(os.path.dirname(__file__), ".streamlit", "secrets.toml")
DEFAULT_POSTGRES_SCHEMA = "ganesh_schema"

# Table definitions: target Postgres DDL (schema-qualified via {schema} placeholder),
# ordered column list to copy (excludes id), and source ORDER BY column.
TABLES = {
    "notification_emails": {
        "columns": ["email"],
        "ddl": """
            CREATE TABLE IF NOT EXISTS {schema}.notification_emails (
                id SERIAL PRIMARY KEY,
                email TEXT NOT NULL UNIQUE
            )
        """,
    },
    "payment_details": {
        "columns": ["name", "amount", "date", "comments", "payment_type", "recieved_zelle_acc_name"],
        "ddl": """
            CREATE TABLE IF NOT EXISTS {schema}.payment_details (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                amount NUMERIC(10,2) NOT NULL,
                date DATE NOT NULL,
                comments TEXT,
                payment_type TEXT,
                recieved_zelle_acc_name TEXT
            )
        """,
    },
    "committee_members": {
        "columns": ["name", "apartment", "recieve_cash_enable", "zelle_enable"],
        "ddl": """
            CREATE TABLE IF NOT EXISTS {schema}.committee_members (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                apartment TEXT,
                recieve_cash_enable BOOLEAN NOT NULL DEFAULT FALSE,
                zelle_enable BOOLEAN NOT NULL DEFAULT FALSE
            )
        """,
    },
    "transfers": {
        "columns": ["name", "phone", "email"],
        "ddl": """
            CREATE TABLE IF NOT EXISTS {schema}.transfers (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                phone TEXT,
                email TEXT
            )
        """,
    },
    "sponsorship_items": {
        "columns": ["item", "amount", "sponsor_limit", "image_blob", "image_filename"],
        "ddl": """
            CREATE TABLE IF NOT EXISTS {schema}.sponsorship_items (
                id SERIAL PRIMARY KEY,
                item TEXT UNIQUE NOT NULL,
                amount NUMERIC NOT NULL,
                sponsor_limit INTEGER NOT NULL,
                image_blob BYTEA,
                image_filename TEXT
            )
        """,
    },
    "sponsors": {
        "columns": ["name", "email", "mobile", "apartment", "sponsorship", "donation", "gothram", "submitted_at"],
        "ddl": """
            CREATE TABLE IF NOT EXISTS {schema}.sponsors (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT,
                mobile TEXT,
                apartment TEXT NOT NULL,
                sponsorship TEXT,
                donation NUMERIC DEFAULT 0,
                gothram TEXT,
                submitted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """,
    },
    "events": {
        "columns": ["title", "event_date", "event_time", "link", "description"],
        "ddl": """
            CREATE TABLE IF NOT EXISTS {schema}.events (
                id SERIAL PRIMARY KEY,
                title TEXT NOT NULL,
                event_date DATE,
                event_time TIME,
                link TEXT,
                description TEXT
            )
        """,
    },
    "expenses": {
        "columns": ["category", "sub_category", "amount", "date", "spent_by", "comments",
                     "receipt_path", "receipt_blob", "status", "created_at"],
        "ddl": """
            CREATE TABLE IF NOT EXISTS {schema}.expenses (
                id SERIAL PRIMARY KEY,
                category TEXT NOT NULL,
                sub_category TEXT NOT NULL,
                amount NUMERIC(10,2) NOT NULL,
                date DATE NOT NULL,
                spent_by TEXT NOT NULL,
                comments TEXT,
                receipt_path TEXT,
                receipt_blob BYTEA,
                status VARCHAR(10) DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """,
    },
    "prasad_seva": {
        "columns": ["seva_type", "names", "item_name", "num_people", "apartment", "seva_date",
                     "pooja_time", "created_by", "created_at", "status"],
        "ddl": """
            CREATE TABLE IF NOT EXISTS {schema}.prasad_seva (
                id SERIAL PRIMARY KEY,
                seva_type VARCHAR(20),
                names TEXT,
                item_name VARCHAR(100),
                num_people INT,
                apartment VARCHAR(20),
                seva_date DATE,
                pooja_time VARCHAR(20),
                created_by VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status VARCHAR(10) DEFAULT 'active'
            )
        """,
    },
    "laddu_winners": {
        "columns": ["laddu_number", "winner_name", "amount"],
        "ddl": """
            CREATE TABLE IF NOT EXISTS {schema}.laddu_winners (
                id SERIAL PRIMARY KEY,
                laddu_number INTEGER NOT NULL,
                winner_name VARCHAR(255) NOT NULL,
                amount INTEGER NOT NULL
            )
        """,
    },
    "settlements": {
        "columns": ["name", "amount", "sent_by", "comments"],
        "ddl": """
            CREATE TABLE IF NOT EXISTS {schema}.settlements (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                amount NUMERIC(10,2) NOT NULL,
                sent_by VARCHAR(255) NOT NULL,
                comments TEXT
            )
        """,
    },
}


def load_secrets():
    with open(SECRETS_PATH, "rb") as f:
        return tomllib.load(f)


def get_snowflake_connection(secrets):
    return snowflake.connector.connect(
        user=secrets["sf_user"],
        password=secrets["sf_password"],
        account=secrets["sf_account"],
        warehouse=secrets["sf_warehouse"],
        database=secrets["sf_database"],
        schema=secrets["sf_schema"],
        role=secrets["sf_role"],
    )


def get_postgres_connection(secrets):
    return psycopg2.connect(
        host=secrets["postgres_host"],
        port=secrets["postgres_port"],
        dbname=secrets["postgres_dbname"],
        user=secrets["postgres_user"],
        password=secrets["postgres_password"],
    )


def create_target_table(pg_cur, schema, table, ddl_template):
    pg_cur.execute(ddl_template.format(schema=schema))


def fetch_source_rows(sf_cur, table, columns):
    col_list = ", ".join(columns)
    sf_cur.execute(f"SELECT {col_list} FROM {table.upper()} ORDER BY ID ASC")
    return sf_cur.fetchall()


def copy_table(sf_cur, pg_cur, schema, table, config, truncate):
    columns = config["columns"]
    create_target_table(pg_cur, schema, table, config["ddl"])

    if truncate:
        pg_cur.execute(f"TRUNCATE TABLE {schema}.{table} RESTART IDENTITY CASCADE")

    sf_cur.execute(f"SELECT COUNT(*) FROM {table.upper()}")
    source_count = sf_cur.fetchone()[0]

    rows = fetch_source_rows(sf_cur, table, columns)
    if not rows:
        print(f"  {table}: no source rows found, skipping insert")
    else:
        col_list = ", ".join(columns)
        placeholders = ", ".join(["%s"] * len(columns))
        insert_sql = f"INSERT INTO {schema}.{table} ({col_list}) VALUES ({placeholders})"
        psycopg2.extras.execute_batch(pg_cur, insert_sql, rows, page_size=500)
        print(f"  {table}: inserted {len(rows)} row(s)")

    # Keep the sequence in sync so the next manually-inserted row continues correctly.
    pg_cur.execute(
        f"SELECT setval(pg_get_serial_sequence('{schema}.{table}', 'id'), "
        f"COALESCE((SELECT MAX(id) FROM {schema}.{table}), 1), "
        f"(SELECT COUNT(*) FROM {schema}.{table}) > 0)"
    )

    pg_cur.execute(f"SELECT COUNT(*) FROM {schema}.{table}")
    target_count = pg_cur.fetchone()[0]
    return source_count, target_count


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tables", help="Comma separated list of tables to migrate (default: all)")
    parser.add_argument("--no-truncate", dest="truncate", action="store_false",
                         help="Append instead of truncating each target table first (default: fresh full copy)")
    parser.set_defaults(truncate=True)
    args = parser.parse_args()

    secrets = load_secrets()
    schema = secrets.get("postgres_schema", DEFAULT_POSTGRES_SCHEMA)

    tables_to_copy = TABLES
    if args.tables:
        requested = [t.strip() for t in args.tables.split(",") if t.strip()]
        unknown = [t for t in requested if t not in TABLES]
        if unknown:
            print(f"Unknown table(s): {', '.join(unknown)}", file=sys.stderr)
            sys.exit(1)
        tables_to_copy = {t: TABLES[t] for t in requested}

    sf_conn = get_snowflake_connection(secrets)
    pg_conn = get_postgres_connection(secrets)
    try:
        sf_cur = sf_conn.cursor()
        pg_cur = pg_conn.cursor()
        pg_cur.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")

        counts = {}
        for table, config in tables_to_copy.items():
            print(f"Copying {table} -> {schema}.{table} ...")
            try:
                source_count, target_count = copy_table(sf_cur, pg_cur, schema, table, config, args.truncate)
                pg_conn.commit()
                counts[table] = (source_count, target_count)
            except Exception:
                pg_conn.rollback()
                print(f"  {table}: FAILED, rolled back this table's changes", file=sys.stderr)
                raise

        print("\nValidation (source Snowflake count vs target Postgres count):")
        mismatches = []
        for table, (source_count, target_count) in counts.items():
            status = "OK" if source_count == target_count else "MISMATCH"
            if status == "MISMATCH":
                mismatches.append(table)
            print(f"  {table:<20} source={source_count:<8} target={target_count:<8} {status}")

        if mismatches:
            print(f"\nMigration completed with count mismatches in: {', '.join(mismatches)}", file=sys.stderr)
            sys.exit(1)

        print("\nMigration completed successfully, all row counts match.")
    finally:
        sf_conn.close()
        pg_conn.close()


if __name__ == "__main__":
    main()

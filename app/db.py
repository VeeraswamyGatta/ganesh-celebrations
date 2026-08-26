
import psycopg2
import streamlit as st
import snowflake.connector

# ---------- DB Connection ----------
def _create_connection():
    db_type = st.secrets.get("db_type", "postgres").lower()
    if db_type == "postgres":
        return psycopg2.connect(
            host=st.secrets["postgres_host"],
            port=st.secrets["postgres_port"],
            dbname=st.secrets["postgres_dbname"],
            user=st.secrets["postgres_user"],
            password=st.secrets["postgres_password"]
        )
    elif db_type == "snowflake":
        return snowflake.connector.connect(
            user=st.secrets["sf_user"],
            password=st.secrets["sf_password"],
            account=st.secrets["sf_account"],
            warehouse=st.secrets["sf_warehouse"],
            database=st.secrets["sf_database"],
            schema=st.secrets["sf_schema"],
            role=st.secrets["sf_role"]
        )
    else:
        raise ValueError(f"Unsupported db_type: {db_type}")


@st.cache_resource(show_spinner=False)
def _get_cached_connection():
    return _create_connection()


def _is_connection_alive(conn):
    # Snowflake/psycopg2 connections can go stale after long inactivity,
    # so probe with a cheap query rather than trusting the object's state.
    try:
        db_type = st.secrets.get("db_type", "postgres").lower()
        if db_type == "snowflake" and conn.is_closed():
            return False
        if db_type == "postgres" and conn.closed:
            return False
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.close()
        return True
    except Exception:
        return False


def get_connection():
    conn = _get_cached_connection()
    if not _is_connection_alive(conn):
        _get_cached_connection.clear()
        conn = _get_cached_connection()
    return conn


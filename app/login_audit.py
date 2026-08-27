import uuid

import streamlit as st

from .db import get_connection


def ensure_login_audit_table(connection):
    cursor = connection.cursor()
    if st.secrets.get("db_type", "postgres").lower() == "snowflake":
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_login_audit (
                id INTEGER AUTOINCREMENT START 1 INCREMENT 1,
                session_id VARCHAR NOT NULL,
                user_role VARCHAR NOT NULL,
                username VARCHAR NOT NULL,
                ip_address VARCHAR,
                user_agent VARCHAR,
                login_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
                last_activity_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
                logout_at TIMESTAMP_NTZ,
                PRIMARY KEY (id)
            )
        """)
    else:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_login_audit (
                id SERIAL PRIMARY KEY,
                session_id TEXT NOT NULL,
                user_role TEXT NOT NULL,
                username TEXT NOT NULL,
                ip_address TEXT,
                user_agent TEXT,
                login_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_activity_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                logout_at TIMESTAMP
            )
        """)
    connection.commit()


def _client_details():
    headers = getattr(st.context, "headers", {})
    forwarded_for = headers.get("x-forwarded-for", "")
    ip_address = forwarded_for.split(",")[0].strip() or headers.get("x-real-ip", "")
    return ip_address, headers.get("user-agent", "")


def start_login_audit(user_role, username):
    connection = get_connection()
    ensure_login_audit_table(connection)
    session_id = str(uuid.uuid4())
    ip_address, user_agent = _client_details()
    cursor = connection.cursor()
    cursor.execute(
        """
        INSERT INTO user_login_audit (session_id, user_role, username, ip_address, user_agent)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (session_id, user_role, username, ip_address, user_agent),
    )
    connection.commit()
    return session_id


def touch_login_audit(session_id):
    if not session_id:
        return
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        "UPDATE user_login_audit SET last_activity_at=CURRENT_TIMESTAMP() WHERE session_id=%s AND logout_at IS NULL",
        (session_id,),
    )
    connection.commit()


def end_login_audit(session_id):
    if not session_id:
        return
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        """
        UPDATE user_login_audit
        SET logout_at=CURRENT_TIMESTAMP(), last_activity_at=CURRENT_TIMESTAMP()
        WHERE session_id=%s AND logout_at IS NULL
        """,
        (session_id,),
    )
    connection.commit()


def get_today_visit_count():
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT user_role, COUNT(*)
        FROM user_login_audit
        WHERE login_at >= CURRENT_DATE
        GROUP BY user_role
        """
    )
    visit_counts = {role: count for role, count in cursor.fetchall()}
    admin_visits = visit_counts.get("Admin", 0)
    user_visits = visit_counts.get("User", 0)
    return admin_visits, user_visits, admin_visits + user_visits
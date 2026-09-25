from .db import get_connection


def get_notification_emails(cursor=None):
    if cursor is not None:
        cursor.execute("ALTER TABLE committee_members ADD COLUMN IF NOT EXISTS email TEXT")
        cursor.execute(
            "ALTER TABLE committee_members ADD COLUMN IF NOT EXISTS "
            "email_notification_enabled BOOLEAN NOT NULL DEFAULT FALSE"
        )
        cursor.execute("ALTER TABLE committee_members ALTER COLUMN email_notification_enabled SET DEFAULT FALSE")
        cursor.execute(
            "SELECT email FROM committee_members "
            "WHERE email IS NOT NULL AND email != '' "
            "AND email_notification_enabled = TRUE ORDER BY email"
        )
        return list(dict.fromkeys(row[0].strip() for row in cursor.fetchall() if row[0] and row[0].strip()))

    conn = get_connection()
    with conn.cursor() as connection_cursor:
        connection_cursor.execute("ALTER TABLE committee_members ADD COLUMN IF NOT EXISTS email TEXT")
        connection_cursor.execute(
            "ALTER TABLE committee_members ADD COLUMN IF NOT EXISTS "
            "email_notification_enabled BOOLEAN NOT NULL DEFAULT FALSE"
        )
        connection_cursor.execute(
            "ALTER TABLE committee_members ALTER COLUMN email_notification_enabled SET DEFAULT FALSE"
        )
        connection_cursor.execute(
            "SELECT email FROM committee_members "
            "WHERE email IS NOT NULL AND email != '' "
            "AND email_notification_enabled = TRUE ORDER BY email"
        )
        return list(dict.fromkeys(
            row[0].strip() for row in connection_cursor.fetchall() if row[0] and row[0].strip()
        ))

# src/storage/database.py
import sqlite3
import os
import datetime
from src.utils.config import ROOT_DIR  # Import root directory to locate the data folder

DB_DIR = os.path.join(ROOT_DIR, "data")
DB_PATH = os.path.join(DB_DIR, "assistant.db")

# Ensure the data directory exists
os.makedirs(DB_DIR, exist_ok=True)


def get_db_connection():
    """Establishes a connection to the SQLite database."""
    try:
        conn = sqlite3.connect(DB_PATH)
        # Return rows as dictionary-like objects
        conn.row_factory = sqlite3.Row
        print(f"[*] Database connection established to {DB_PATH}")
        return conn
    except sqlite3.Error as e:
        print(f"[!] Database connection error: {e}")
        return None


def initialize_database():
    """Creates the necessary tables if they don't exist."""
    conn = get_db_connection()
    if not conn:
        return

    try:
        cursor = conn.cursor()
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS emails (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id TEXT UNIQUE NOT NULL,
            thread_id TEXT NOT NULL,
            sender TEXT,
            recipient TEXT,
            subject TEXT,
            body_plain TEXT,
            body_html TEXT,
            received_at TIMESTAMP,
            stored_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            processed BOOLEAN DEFAULT FALSE
        );
        """
        )
        # Optional: Add indexes for faster lookups later
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_message_id ON emails (message_id);"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_thread_id ON emails (thread_id);"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_processed ON emails (processed);"
        )

        conn.commit()
        print("[*] Database initialized successfully (tables created if needed).")
    except sqlite3.Error as e:
        print(f"[!] Database initialization error: {e}")
    finally:
        if conn:
            conn.close()


def message_exists(message_id):
    """Checks if an email with the given message_id already exists in the database."""
    conn = get_db_connection()
    if not conn:
        return False  # Assume it doesn't exist if DB connection fails

    exists = False
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM emails WHERE message_id = ?", (message_id,))
        result = cursor.fetchone()
        if result:
            exists = True
    except sqlite3.Error as e:
        print(f"[!] Error checking message existence for {message_id}: {e}")
    finally:
        if conn:
            conn.close()
    return exists


def store_email(email_data):
    """Stores the parsed email data into the database."""
    # Ensure required fields are present
    required_fields = [
        "message_id",
        "thread_id",
        "sender",
        "recipient",
        "subject",
        "body_plain",
        "received_at",
    ]
    if not all(field in email_data for field in required_fields):
        print(
            f"[!] Skipping email storage: Missing required fields in email_data for message {email_data.get('message_id')}"
        )
        return False

    conn = get_db_connection()
    if not conn:
        return False

    sql = """
    INSERT INTO emails (message_id, thread_id, sender, recipient, subject, body_plain, body_html, received_at, processed)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    try:
        cursor = conn.cursor()
        cursor.execute(
            sql,
            (
                email_data["message_id"],
                email_data["thread_id"],
                email_data["sender"],
                email_data["recipient"],
                email_data["subject"],
                email_data.get("body_plain", ""),  # Provide default empty string
                email_data.get("body_html"),  # Can be None
                email_data["received_at"],  # Should be datetime object or ISO string
                False,  # Default processed to False
            ),
        )
        conn.commit()
        print(f"[*] Stored email with Message-ID: {email_data['message_id']}")
        return True
    except sqlite3.IntegrityError:
        # This likely means the message_id already exists (UNIQUE constraint)
        print(
            f"[*] Email with Message-ID {email_data['message_id']} already exists. Skipping."
        )
        return False  # Indicate not stored (because it was a duplicate)
    except sqlite3.Error as e:
        print(f"[!] Error storing email {email_data['message_id']}: {e}")
        conn.rollback()  # Rollback changes on error
        return False
    finally:
        if conn:
            conn.close()


# --- Functions for Day 3+ (can be added now or later) ---


def get_unprocessed_emails():
    """Retrieves all emails marked as unprocessed."""
    conn = get_db_connection()
    if not conn:
        return []

    emails = []
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM emails WHERE processed = FALSE ORDER BY received_at ASC"
        )
        rows = cursor.fetchall()
        # Convert rows to dictionaries for easier handling
        emails = [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"[!] Error fetching unprocessed emails: {e}")
    finally:
        if conn:
            conn.close()
    print(f"[*] Found {len(emails)} unprocessed emails in DB.")
    return emails


def mark_email_processed(message_id):
    """Marks a specific email as processed in the database."""
    conn = get_db_connection()
    if not conn:
        return False

    sql = "UPDATE emails SET processed = TRUE WHERE message_id = ?"
    try:
        cursor = conn.cursor()
        cursor.execute(sql, (message_id,))
        conn.commit()
        # Check if any row was actually updated
        if cursor.rowcount > 0:
            print(f"[*] Marked email {message_id} as processed.")
            return True
        else:
            print(
                f"[*] Could not mark email {message_id} as processed (not found or already processed?)."
            )
            return False
    except sqlite3.Error as e:
        print(f"[!] Error marking email {message_id} as processed: {e}")
        conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

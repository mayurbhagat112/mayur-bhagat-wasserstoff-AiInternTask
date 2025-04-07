# src/utils/config.py
import os

# ... (paths remain the same) ...
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CREDENTIALS_DIR = os.path.join(ROOT_DIR, "credentials")
CREDENTIALS_FILE = os.path.join(CREDENTIALS_DIR, "credentials.json")
TOKEN_FILE = os.path.join(CREDENTIALS_DIR, "token.json")
os.makedirs(CREDENTIALS_DIR, exist_ok=True)

# --- MODIFIED SCOPES ---
# Add the calendar scope (read/write for creating events)
# Keep existing Gmail scopes. Add gmail.send later if needed for sending replies.
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar.events",  # Add this scope
    # Add later if sending replies: 'https://www.googleapis.com/auth/gmail.send'
]
# --- END MODIFIED SCOPES ---

print(f"[*] Using Credentials file: {CREDENTIALS_FILE}")
print(f"[*] Using Token file: {TOKEN_FILE}")
print(f"[*] Requesting Scopes: {SCOPES}")  # Print scopes for verification

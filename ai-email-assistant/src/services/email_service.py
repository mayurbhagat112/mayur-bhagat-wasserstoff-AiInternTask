# src/services/email_service.py
import os.path
import pickle
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Import config variables and parsing helpers
from src.utils.config import SCOPES, CREDENTIALS_FILE, TOKEN_FILE
from src.utils.parsing import get_header_value, parse_email_body, parse_date_string

# Import database functions
from src.storage.database import message_exists, store_email  # Add imports


# get_gmail_service function remains the same as Day 1...
# ... (keep the existing get_gmail_service function here) ...
def get_gmail_service():
    """
    Authenticates with the Gmail API using OAuth 2.0 and returns a service object.
    Handles token storage and refresh.
    """
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first time.
    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE, "rb") as token:
                creds = pickle.load(token)
        except (pickle.UnpicklingError, EOFError, FileNotFoundError) as e:
            print(f"[!] Error loading token file: {e}. Re-authenticating.")
            creds = None  # Force re-authentication
            if os.path.exists(TOKEN_FILE):
                os.remove(TOKEN_FILE)  # Remove corrupted token file

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                print("[*] Refreshing access token...")
                creds.refresh(Request())
            except Exception as e:
                print(f"[!] Failed to refresh token: {e}. Need to re-authenticate.")
                if os.path.exists(TOKEN_FILE):
                    os.remove(TOKEN_FILE)  # Remove invalid token file
                creds = None  # Force re-authentication flow
        else:
            print("[*] No valid credentials found. Starting authentication flow...")
            if not os.path.exists(CREDENTIALS_FILE):
                print(f"[!] ERROR: Credentials file not found at {CREDENTIALS_FILE}")
                print(
                    "[!] Please download credentials.json from Google Cloud Console and place it there."
                )
                return None

            try:
                flow = InstalledAppFlow.from_client_secrets_file(
                    CREDENTIALS_FILE, SCOPES
                )
                # port=0 finds a random available port
                creds = flow.run_local_server(port=0)
                print("[*] Authentication successful!")
            except Exception as e:
                print(f"[!] Error during authentication flow: {e}")
                return None

        # Save the credentials for the next run
        try:
            with open(TOKEN_FILE, "wb") as token:
                pickle.dump(creds, token)
            print(f"[*] Credentials saved to {TOKEN_FILE}")
        except Exception as e:
            print(f"[!] Error saving token file: {e}")

    try:
        service = build("gmail", "v1", credentials=creds)
        print("[*] Gmail service object created successfully.")
        return service
    except HttpError as error:
        print(f"[!] An error occurred while building the service: {error}")
        # If the error is related to revoked credentials, suggest deleting token.json
        if "invalid_grant" in str(error).lower():
            print(
                "[!] Hint: The token might be invalid or revoked. Try deleting 'credentials/token.json' and re-running."
            )
        return None
    except Exception as e:
        print(f"[!] An unexpected error occurred while building the service: {e}")
        return None


# --- Modified fetch function ---
def fetch_and_store_unread_emails(service, max_results=10):
    """
    Fetches recent unread emails, parses them, and stores new ones in the database.
    """
    if not service:
        print("[!] Cannot fetch emails: Service object is not available.")
        return 0  # Return count of newly stored emails

    stored_count = 0
    try:
        results = (
            service.users()
            .messages()
            .list(userId="me", q="is:unread in:inbox", maxResults=max_results)
            .execute()
        )

        messages_info = results.get("messages", [])

        if not messages_info:
            print("[*] No new unread messages found in the inbox.")
            return 0
        else:
            print(
                f"[*] Found {len(messages_info)} unread message candidates. Fetching details..."
            )
            for msg_info in messages_info:
                msg_id = msg_info["id"]

                # Check if we already stored this message to avoid redundant API calls/processing
                if message_exists(msg_id):
                    print(f"[*] Message {msg_id} already exists in DB. Skipping.")
                    continue  # Skip to the next message

                print(f"[*] Fetching full details for Message-ID: {msg_id}...")
                # Get the FULL message content now
                message = (
                    service.users()
                    .messages()
                    .get(
                        userId="me",
                        id=msg_id,
                        format="full",  # Request full details including body and parts
                    )
                    .execute()
                )

                payload = message.get("payload", {})
                headers = payload.get("headers", [])

                # Parse essential details
                subject = get_header_value(headers, "Subject")
                sender = get_header_value(headers, "From")
                recipient = get_header_value(headers, "To")  # Or 'Delivered-To'
                date_str = get_header_value(headers, "Date")

                received_at_dt = parse_date_string(date_str)
                # Use current time if date parsing fails? Or skip? Let's skip for now.
                if not received_at_dt:
                    print(
                        f"[!] Could not parse date for Message-ID {msg_id}. Skipping storage."
                    )
                    continue

                # Parse body
                body_content = parse_email_body(payload)
                plain_body = body_content.get("plain")
                html_body = body_content.get("html")

                # Get threadId
                thread_id = message.get("threadId")

                # Prepare data dictionary for storage
                email_data = {
                    "message_id": msg_id,
                    "thread_id": thread_id,
                    "sender": sender,
                    "recipient": recipient,
                    "subject": subject,
                    "body_plain": plain_body,
                    "body_html": html_body,
                    "received_at": received_at_dt,  # Store as datetime object or ISO string
                }

                # Store the email data in the database
                if store_email(email_data):
                    stored_count += 1

                # Optional: Mark email as read in Gmail after processing?
                # Be careful with this - maybe do it only after successful analysis/action later
                # service.users().messages().modify(userId='me', id=msg_id, body={'removeLabelIds': ['UNREAD']}).execute()
                # print(f"[*] Marked email {msg_id} as read in Gmail.")

            print(f"[*] Finished processing batch. Newly stored emails: {stored_count}")
            return stored_count

    except HttpError as error:
        print(f"[!] An error occurred while fetching/processing emails: {error}")
        if error.resp.status == 403:
            print(
                "[!] Hint: Ensure the Gmail API is enabled and permissions were granted."
            )
        return stored_count  # Return count stored so far
    except Exception as e:
        print(f"[!] An unexpected error occurred during fetching/storing: {e}")
        return stored_count  # Return count stored so far


# src/services/email_service.py OR src/services/google_auth_service.py
# ... (keep imports: os, pickle, Request, InstalledAppFlow, build, HttpError) ...


def get_google_api_service(api_name, api_version):
    """
    Authenticates using OAuth 2.0 and returns a Google API service object.
    Handles token storage and refresh for the requested SCOPES.
    """
    creds = None
    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE, "rb") as token:
                creds = pickle.load(token)
        except Exception as e:
            print(f"[!] Error loading token file: {e}. Re-authenticating.")
            if os.path.exists(TOKEN_FILE):
                os.remove(TOKEN_FILE)
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                print("[*] Refreshing access token...")
                creds.refresh(Request())
            except Exception as e:
                print(f"[!] Failed to refresh token: {e}. Deleting token file.")
                if os.path.exists(TOKEN_FILE):
                    os.remove(TOKEN_FILE)
                creds = None  # Force re-auth
        else:
            print(
                "[*] No valid credentials found or scopes changed. Starting auth flow..."
            )
            if not os.path.exists(CREDENTIALS_FILE):
                print(f"[!] ERROR: Credentials file not found at {CREDENTIALS_FILE}")
                return None
            try:
                # Use SCOPES from config.py
                flow = InstalledAppFlow.from_client_secrets_file(
                    CREDENTIALS_FILE, SCOPES
                )
                creds = flow.run_local_server(port=0)
                print("[*] Authentication successful!")
            except Exception as e:
                print(f"[!] Error during authentication flow: {e}")
                return None
        try:
            with open(TOKEN_FILE, "wb") as token:
                pickle.dump(creds, token)
            print(f"[*] Credentials saved to {TOKEN_FILE}")
        except Exception as e:
            print(f"[!] Error saving token file: {e}")

    try:
        service = build(api_name, api_version, credentials=creds)
        print(
            f"[*] Google API service '{api_name} v{api_version}' created successfully."
        )
        return service
    except HttpError as error:
        print(f"[!] An error occurred building the {api_name} service: {error}")
        if (
            "invalid_grant" in str(error).lower()
            or "invalid permissions" in str(error).lower()
        ):
            print(
                f"[!] Hint: Token might be invalid/revoked or scopes insufficient. Try deleting '{TOKEN_FILE}' and re-running."
            )
        return None
    except Exception as e:
        print(f"[!] An unexpected error occurred building the {api_name} service: {e}")
        return None


# Keep email-specific functions below if this file is email_service.py
# Or move them if you created google_auth_service.py
# ... fetch_and_store_unread_emails etc ...
# Make sure fetch_and_store_unread_emails now calls:
# gmail_service = get_google_api_service('gmail', 'v1')
# instead of get_gmail_service()


# If you kept this in email_service.py, add a simple wrapper for backwards compatibility or update main.py
def get_gmail_service():
    return get_google_api_service("gmail", "v1")


# ... (rest of email_service.py) ...

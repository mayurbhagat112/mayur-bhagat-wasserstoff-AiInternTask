# src/utils/parsing.py
import base64
from email.utils import parsedate_to_datetime
import datetime
from bs4 import (
    BeautifulSoup,
)  # For potential HTML cleaning later, not strictly needed for extraction
from dateutil.parser import parse as dateutil_parse
import datetime


def get_header_value(headers, name):
    """
    Finds the value of a specific header from the list of headers.
    Gmail header names are case-insensitive in practice.
    """
    if not headers:
        return None
    for header in headers:
        # Case-insensitive comparison for header name
        if header.get("name", "").lower() == name.lower():
            return header.get("value")
    return None


def parse_email_body(message_payload):
    """
    Parses the body content (plain text and HTML) from a Gmail message payload.
    Handles multipart messages and base64 decoding.
    """
    plain_body = None
    html_body = None

    mime_type = message_payload.get("mimeType", "")
    parts = message_payload.get("parts", [])
    body_data = message_payload.get("body", {}).get("data")

    if "text/plain" in mime_type and body_data:
        plain_body = base64.urlsafe_b64decode(body_data).decode(
            "utf-8", errors="replace"
        )
    elif "text/html" in mime_type and body_data:
        html_body = base64.urlsafe_b64decode(body_data).decode(
            "utf-8", errors="replace"
        )
    elif "multipart" in mime_type and parts:
        for part in parts:
            # Recursively parse parts
            part_bodies = parse_email_body(part)
            # Prioritize plain text if found
            if part_bodies.get("plain") and not plain_body:
                plain_body = part_bodies["plain"]
            if part_bodies.get("html") and not html_body:
                html_body = part_bodies["html"]
            # If we found plain text in a multipart/alternative, stop looking in this branch
            if "multipart/alternative" in mime_type and plain_body:
                break

    # If we only found HTML, we might want to generate a basic plain text version
    # For now, we just return what we found. Can add HTML-to-text conversion later if needed.

    return {"plain": plain_body, "html": html_body}


def parse_date_string(date_string):
    """
    Parses a date string (like from email headers) into a timezone-aware datetime object.
    Returns None if parsing fails.
    """
    if not date_string:
        return None
    try:
        # parsedate_to_datetime handles various standard email date formats
        dt = parsedate_to_datetime(date_string)
        # If the datetime object is naive, assume UTC? Or try to infer?
        # For simplicity now, let's make it timezone-aware assuming it might be naive
        # A more robust solution might involve pytz if timezone info is present in the string
        if dt and dt.tzinfo is None:
            # This just attaches UTC, doesn't convert. Gmail usually provides TZ offset.
            # dt = dt.replace(tzinfo=datetime.timezone.utc)
            pass  # parsedate_to_datetime usually handles TZ offset correctly if present
        return dt
    except Exception as e:
        print(f"[!] Could not parse date string '{date_string}': {e}")
        return None


# src/utils/parsing.py
# ... (keep existing get_header_value, parse_email_body, parse_date_string) ...
# Install dateutil: pip install python-dateutil


def parse_extracted_datetime(date_str, time_str):
    """
    Attempts to parse date and time strings (potentially extracted by LLM)
    into a datetime object. Returns None on failure.
    Handles combined date/time strings as well.
    """
    if not date_str and not time_str:
        return None

    try:
        # Combine if both exist, otherwise try parsing individually
        # dateutil.parser is quite flexible
        if date_str and time_str:
            full_str = f"{date_str} {time_str}"
        elif date_str:
            full_str = date_str
        else:  # Only time_str exists (less likely to be useful alone)
            print(
                f"[!] Only time string '{time_str}' found, cannot reliably parse without date."
            )
            return None  # Or try parsing time_str assuming today? Risky.

        print(f"[*] Attempting to parse datetime string: '{full_str}'")
        # fuzzy=True might help with slightly malformed strings, but use carefully
        dt = dateutil_parse(full_str, fuzzy=False)
        print(f"[*] Parsed datetime object: {dt}")
        return dt
    except ValueError as e:
        print(f"[!] Could not parse datetime string '{full_str}': {e}")
        return None
    except Exception as e:  # Catch other potential errors
        print(f"[!] Unexpected error parsing datetime '{full_str}': {e}")
        return None

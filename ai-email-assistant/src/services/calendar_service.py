# src/services/calendar_service.py
from googleapiclient.errors import HttpError
import datetime
import pytz  # For timezone handling: pip install pytz

# Import the generic service getter
from src.services.email_service import (
    get_google_api_service,
)  # Adjust import path if you made google_auth_service.py


# --- Helper Function for Time Formatting ---
def format_datetime_for_google_api(dt_obj):
    """Converts a datetime object to the RFC3339 format Google Calendar API expects."""
    if not isinstance(dt_obj, datetime.datetime):
        return None  # Or raise error

    # If the datetime is naive, assume local timezone (adjust if needed!)
    # We need pytz for robust timezone handling.
    # Let's use the current location provided (India Standard Time)
    local_tz = pytz.timezone("Asia/Kolkata")
    if dt_obj.tzinfo is None or dt_obj.tzinfo.utcoffset(dt_obj) is None:
        print(f"[*] Datetime object is naive. Assuming timezone: {local_tz.zone}")
        dt_obj = local_tz.localize(dt_obj)
    else:
        # Convert to local timezone if it's different, just to be sure
        dt_obj = dt_obj.astimezone(local_tz)

    return dt_obj.isoformat()  # isoformat() generates RFC3339 compatible string


# --- Main Calendar Function ---
def create_calendar_event(
    summary, start_datetime, end_datetime, attendees=None, description=""
):
    """
    Creates an event on the user's primary Google Calendar.
    start_datetime and end_datetime should be datetime objects.
    attendees should be a list of email addresses.
    """
    service = get_google_api_service("calendar", "v3")
    if not service:
        print("[!] Cannot create calendar event: Calendar service not available.")
        return None

    # Format datetimes for the API
    start_time_str = format_datetime_for_google_api(start_datetime)
    end_time_str = format_datetime_for_google_api(end_datetime)

    if not start_time_str or not end_time_str:
        print("[!] Invalid start or end datetime object provided.")
        return None

    event = {
        "summary": summary,
        "description": description,
        "start": {
            "dateTime": start_time_str,
            # 'timeZone': 'Asia/Kolkata', # Included in RFC3339 string
        },
        "end": {
            "dateTime": end_time_str,
            # 'timeZone': 'Asia/Kolkata',
        },
        # 'attendees': [{'email': email} for email in attendees] if attendees else [],
        # Add attendees later if needed, requires more permissions potentially
        "reminders": {  # Optional: Add default reminders
            "useDefault": True,
        },
    }

    try:
        print(
            f"[*] Creating calendar event: '{summary}' from {start_time_str} to {end_time_str}"
        )
        created_event = (
            service.events()
            .insert(calendarId="primary", body=event)  # Use the primary calendar
            .execute()
        )
        print(f"[*] Event created successfully! Link: {created_event.get('htmlLink')}")
        return created_event  # Return the created event object
    except HttpError as error:
        print(f"[!] An error occurred creating calendar event: {error}")
        # TODO: Handle specific errors like 409 Conflict (time slot busy?)
        return None
    except Exception as e:
        print(f"[!] An unexpected error occurred creating event: {e}")
        return None


# Example Usage (for testing - requires manual datetime objects)
if __name__ == "__main__":
    print("\n--- Testing Calendar Event Creation ---")
    # IMPORTANT: Replace with actual datetime objects for testing
    now = datetime.datetime.now()
    start_test_time = now + datetime.timedelta(
        days=1, hours=2
    )  # Event tomorrow at current time + 2 hours
    end_test_time = start_test_time + datetime.timedelta(hours=1)  # 1 hour duration

    test_summary = "AI Assistant Test Event"
    test_description = "This event was created automatically by the AI Email Assistant."

    # Make sure you've authenticated with calendar scope before running this test
    # Delete token.json if needed
    create_calendar_event(
        test_summary, start_test_time, end_test_time, description=test_description
    )
    print("------------------------------------")

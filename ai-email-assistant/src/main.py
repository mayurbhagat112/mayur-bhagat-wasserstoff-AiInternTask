# src/main.py
import time
import datetime  # Import datetime
from dotenv import load_dotenv

load_dotenv()

# --- Service Imports ---
from src.services.email_service import (
    get_google_api_service,
    fetch_and_store_unread_emails,
)  # Use generic getter
from src.storage.database import (
    initialize_database,
    get_unprocessed_emails,
    mark_email_processed,
)
from src.services.llm_service import (
    analyze_email_content,
    draft_reply,
)  # Add draft_reply
from src.services.web_search_service import search_web
from src.services.slack_service import send_slack_message
from src.services.calendar_service import (
    create_calendar_event,
)  # Import calendar function

# --- Util Imports ---
from src.utils.parsing import parse_extracted_datetime  # Import datetime parser


# --- Helper Function for Confirmation ---
def confirm_action(prompt_message):
    """Asks the user for confirmation before proceeding."""
    while True:
        response = input(f"{prompt_message} Proceed? (y/n): ").lower().strip()
        if response == "y":
            return True
        elif response == "n":
            print("[*] Action cancelled by user.")
            return False
        else:
            print("Please enter 'y' or 'n'.")


# --- Main Assistant Function ---
def run_assistant():
    print(
        "--- Starting AI Email Assistant (Day 6: Debugging Confirmations) ---"
    )  # Updated title

    # 1. Initialize DB
    print("\n[*] Initializing database...")
    initialize_database()

    # 2. Authenticate
    print("\n[*] Authenticating with Google APIs...")
    gmail_service = get_google_api_service("gmail", "v1")
    if not gmail_service:
        print("[!] Failed to get Google API access. Exiting.")
        return

    # 3. Fetch/Store Emails
    print("\n[*] Fetching unread emails and storing new ones...")
    fetch_and_store_unread_emails(gmail_service, max_results=10)

    # --- LLM Processing & Actions ---
    print("\n[*] Checking for unprocessed emails in the database...")
    unprocessed_emails = get_unprocessed_emails()

    if not unprocessed_emails:
        print("[*] No unprocessed emails found.")
    else:
        print(f"[*] Found {len(unprocessed_emails)} emails for processing.")
        for email in unprocessed_emails:
            print("-" * 30)
            msg_id = email["message_id"]
            print(f"[*] Processing Email - Message-ID: {msg_id}")
            subject = email.get("subject", "")
            body = email.get("body_plain", "")
            sender = email.get("sender", "Unknown Sender")
            print(f"  Subject: {subject}")

            analysis_result = None
            drafted_reply_text = None  # Initialize draft reply
            reply_context = "Email processed."  # Default context

            if not subject and not body:
                print("  [!] Skipping LLM analysis: Both subject and body are empty.")
            else:
                analysis_result = analyze_email_content(subject, body)

            if analysis_result:
                intent = analysis_result.get("intent", "Unknown")
                meeting_details = analysis_result.get("meeting_details")
                print(f"  LLM Intent: {intent}")  # Print initial intent

                # --- SAFETY FILTER for Meeting Requests ---
                if intent == "Meeting Request":
                    # Added/refined keywords
                    promo_keywords = [
                        "unsubscribe",
                        "discount",
                        "sale",
                        "offer",
                        "limited time",
                        "coupon",
                        "save now",
                        "shop now",
                        "view deal",
                        "last call",
                        "percent off",
                        "% off",
                        "expires",
                        "promotion",
                        "clearance",
                    ]
                    meeting_keywords = [
                        "meet",
                        "schedule",
                        "call ",
                        "zoom",
                        "available",
                        "appointment",
                        "calendar",
                        "discuss",
                        "talk",
                        "catch up",
                        "sync up",
                        "proposal",
                        "next steps",
                    ]
                    email_text_lower = (
                        subject.lower() + " " + (body.lower() if body else "")
                    )
                    is_likely_promo = any(
                        keyword in email_text_lower for keyword in promo_keywords
                    )
                    has_meeting_cues = any(
                        keyword in email_text_lower for keyword in meeting_keywords
                    )

                    if is_likely_promo or not has_meeting_cues:
                        print(
                            f"  [!] Overriding LLM Intent '{intent}' based on keywords. Likely not a real meeting request."
                        )
                        intent = "Information Sharing"  # Re-classify
                        meeting_details = None  # Ensure no action taken
                # --- END SAFETY FILTER ---

                # --- DEBUG: Print intent *after* potential override by filter ---
                print(f"DEBUG: Intent *after* safety filter is: '{intent}'")

                # --- Action based on Intent (using potentially overridden intent) ---

                # ** Meeting Request Handling **
                if intent == "Meeting Request" and meeting_details:
                    print(
                        f"  Action: Attempting to schedule meeting based on extracted details..."
                    )
                    cal_summary = meeting_details.get("event_summary", subject)
                    date_str = meeting_details.get("date")
                    time_str = meeting_details.get("time")
                    duration_min = meeting_details.get("duration_minutes", 60)

                    start_dt = parse_extracted_datetime(date_str, time_str)

                    if start_dt:
                        try:
                            duration_min = int(duration_min)
                            end_dt = start_dt + datetime.timedelta(minutes=duration_min)

                            # --- DEBUG PRINT before Calendar confirmation ---
                            print(
                                f"DEBUG: About to ask for Calendar confirmation for '{cal_summary}'."
                            )
                            # --- CONFIRMATION for Calendar ---
                            confirm_prompt = (
                                f"[*] About to create calendar event: '{cal_summary}'\n"
                                f"    Start: {start_dt.strftime('%Y-%m-%d %I:%M %p %Z')}\n"
                                f"    End:   {end_dt.strftime('%Y-%m-%d %I:%M %p %Z')}"
                            )
                            if confirm_action(confirm_prompt):
                                created_event = create_calendar_event(
                                    cal_summary, start_dt, end_dt
                                )
                                if created_event:
                                    event_link = created_event.get(
                                        "htmlLink", "Link unavailable"
                                    )
                                    event_start_str = start_dt.strftime(
                                        "%Y-%m-%d %I:%M %p %Z"
                                    )
                                    reply_context = f"Meeting scheduled successfully: '{cal_summary}' on {event_start_str}. Event link: {event_link}"
                                else:
                                    reply_context = f"Attempted to schedule meeting '{cal_summary}', but failed to create the calendar event (API error or conflict)."
                            else:
                                reply_context = "Meeting scheduling cancelled by user."
                            # --- END CONFIRMATION ---
                        except ValueError:
                            reply_context = f"Could not schedule meeting: Invalid duration '{duration_min}'."
                        except Exception as e:
                            reply_context = (
                                f"Could not schedule meeting: Unexpected error ({e})."
                            )
                    else:
                        reply_context = f"Meeting requested, but could not parse date/time ('{date_str}' '{time_str}') from email details."

                    # Draft reply based on scheduling outcome
                    drafted_reply_text = draft_reply(subject, sender, reply_context)

                # ** Question Handling **
                elif intent == "Question":
                    print(
                        "  Action: Performing web search based on intent 'Question'..."
                    )
                    search_query = subject if subject else "Inquiry from email"
                    if search_query:
                        search_results_text = search_web(search_query)
                        print("\n--- Web Search Results ---")
                        print(search_results_text)
                        print("-------------------------\n")
                        reply_context = f"Regarding your question about '{subject}', here are some search results:\n\n{search_results_text}"
                        drafted_reply_text = draft_reply(subject, sender, reply_context)
                    else:
                        print(
                            "  [!] Could not determine a suitable query for web search."
                        )
                        reply_context = f"Could not perform web search for your question '{subject}'."

                # ** Slack Notification for Important **
                important_intents = ["Action Required"]
                # --- DEBUG PRINT before Slack condition check ---
                print(
                    f"DEBUG: Checking if intent '{intent.lower()}' is in important list: {[i.lower() for i in important_intents]}"
                )
                if intent.lower() in [
                    i.lower() for i in important_intents
                ]:  # Case-insensitive check
                    # --- DEBUG PRINT *inside* Slack condition block ---
                    print(
                        f"DEBUG: Condition MET for Slack notification (Intent: '{intent}')."
                    )
                    print(f"DEBUG: About to call confirm_action for Slack.")
                    # --- CONFIRMATION for Slack ---
                    confirm_prompt = f"[*] About to send Slack notification for '{subject}' (Intent: {intent})"
                    if confirm_action(confirm_prompt):
                        print(
                            f"  Action: Sending Slack notification for intent '{intent}'..."
                        )
                        slack_message = (
                            f"🚨 *Important Email Notification* 🚨\n\n"
                            f"*From:* {sender}\n*Subject:* {subject}\n"
                            f"*LLM Intent:* `{intent}`\n"
                            f"(Message ID: {msg_id})"
                        )
                        if send_slack_message(slack_message):
                            reply_context = f"Detected as '{intent}', notified relevant parties via Slack."
                        else:
                            reply_context = f"Detected as '{intent}', but failed to send Slack notification."
                    else:
                        reply_context = f"Detected as '{intent}', Slack notification skipped by user."
                    # --- END CONFIRMATION ---
                else:
                    # --- DEBUG PRINT if Slack condition NOT met ---
                    print(
                        f"DEBUG: Condition NOT MET for Slack notification (Intent: '{intent}')."
                    )

                # --- Print Draft Reply ---
                if drafted_reply_text:
                    print("\n--- Draft Reply ---")
                    print(f"To: {sender}")
                    print(f"Subject: Re: {subject}")
                    print("---")
                    print(drafted_reply_text)
                    print("-------------------\n")

            else:  # LLM Analysis failed
                print("  [!] Skipping actions due to failed LLM analysis.")
                reply_context = (
                    "Email received, but encountered an error during analysis."
                )

            # --- Mark as Processed ---
            if mark_email_processed(msg_id):
                print(f"[*] Successfully marked email {msg_id} as processed.")
            else:
                print(f"[!] Failed to mark email {msg_id} as processed.")

            print("[*] Waiting 1-2 seconds before next email...")
            time.sleep(2)

    print("\n--- Assistant run finished ---")


if __name__ == "__main__":
    run_assistant()

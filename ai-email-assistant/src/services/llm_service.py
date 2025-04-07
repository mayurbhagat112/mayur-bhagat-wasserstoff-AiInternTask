# src/services/llm_service.py
import os
import requests
import time
import json  # Import json for pretty printing the payload
from dotenv import load_dotenv

# Load environment variables (specifically the Hugging Face token)
load_dotenv()

# Configuration
API_URL = "https://api-inference.huggingface.co/models/google/flan-t5-base"
HF_API_TOKEN = os.getenv("HUGGINGFACE_API_TOKEN")

if not HF_API_TOKEN:
    print("[!] Warning: HUGGINGFACE_API_TOKEN not found in environment variables.")


def query_huggingface_api(payload):
    """Sends a payload to the configured Hugging Face Inference API endpoint."""
    if not HF_API_TOKEN:
        print("[!] Cannot query Hugging Face API: Token missing.")
        return None

    headers = {"Authorization": f"Bearer {HF_API_TOKEN}"}

    # --- DEBUG Step 1: Print the exact payload ---
    # Use json.dumps for potentially better formatting, especially of the prompt string
    try:
        print(f"[*] Sending Payload to HF API:\n{json.dumps(payload, indent=2)}")
    except Exception as e:
        print(f"[!] Error formatting payload for printing: {e}")
        print(f"[*] Raw Payload: {payload}")
    # --- End DEBUG Step 1 ---

    try:
        response = requests.post(API_URL, headers=headers, json=payload)

        # Handle specific HTTP errors
        if response.status_code == 429:
            print("[!] Hugging Face API Rate Limit Hit. Waiting and retrying...")
            time.sleep(5)
            response = requests.post(
                API_URL, headers=headers, json=payload
            )  # Simple retry

        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)

        return response.json()

    except requests.exceptions.RequestException as e:
        # Include response text in error if possible, helpful for 400 errors
        error_details = f"{e}"
        if e.response is not None:
            try:
                error_details += f"\nResponse Status: {e.response.status_code}\nResponse Text: {e.response.text}"
            except Exception:
                pass  # Ignore errors trying to get response details
        print(f"[!] Error querying Hugging Face API: {error_details}")

        if (
            response
            and response.status_code == 503
            and "currently loading" in response.text.lower()
        ):
            print("[!] Model is loading on Hugging Face, try again in a moment.")
        return None
    except Exception as e:
        print(f"[!] An unexpected error occurred during API query: {e}")
        return None


# src/services/llm_service.py
# ... (imports: os, requests, time, json, load_dotenv) ...
# ... (API_URL, HF_API_TOKEN, query_huggingface_api remain the same) ...


def analyze_email_content(subject, body, max_body_length=1500):
    """
    Analyzes email content. Determines intent first, then attempts to
    extract meeting details if applicable.
    """
    if not body:
        body = "(No body content)"
    truncated_body = body[:max_body_length]

    # --- Prompt 1: Get Intent First ---
    intent_prompt = f"""Read the following email subject and body. What is the single primary intent? Choose ONLY ONE category from the list: [Meeting Request, Question, Information Sharing, Spam/Unimportant, Action Required, Other]. Respond with only the chosen category name.

    Subject: {subject}

    Body:
    {truncated_body}

    Primary Intent: """

    intent_payload = {
        "inputs": intent_prompt,
        "parameters": {
            "max_new_tokens": 50,
            "temperature": 0.5,
        },  # Short response expected
    }

    print(f"[*] Sending Intent prompt to LLM for subject: '{subject[:50]}...'")
    intent_response_data = query_huggingface_api(intent_payload)
    primary_intent = "Unknown"  # Default

    if (
        intent_response_data
        and isinstance(intent_response_data, list)
        and len(intent_response_data) > 0
    ):
        raw_intent_text = intent_response_data[0].get("generated_text", "").strip()
        print(f"[*] LLM Intent Received (Raw): '{raw_intent_text}'")
        cleaned_intent = raw_intent_text.strip().strip("[]").strip()
        if cleaned_intent:
            primary_intent = cleaned_intent
        print(f"[*] Parsed Intent: {primary_intent}")
    else:
        print("[!] Failed to get valid Intent analysis from LLM.")
        # Return basic analysis if intent fails
        return {
            "raw": "",
            "intent": primary_intent,
            "summary": "N/A",
            "meeting_details": None,
        }

    # --- Prompt 2 (Conditional): Extract Meeting Details if Intent is Meeting Request ---
    meeting_details = None
    if primary_intent == "Meeting Request":
        print(
            f"[*] Intent is '{primary_intent}'. Attempting to extract meeting details..."
        )
        details_prompt = f"""The following email is a meeting request. Extract the key details needed to schedule it. Provide the output ONLY as a JSON object with keys "event_summary", "date", "time", "duration_minutes", and "attendees" (list of potential email addresses mentioned, if any). If a detail cannot be found, use null or an empty string/list.

        Subject: {subject}

        Body:
        {truncated_body}

        JSON Output:
        ```json
        """  # Instruct LLM to output JSON

        details_payload = {
            "inputs": details_prompt,
            # Adjust parameters if needed for JSON generation
            "parameters": {"max_new_tokens": 150, "temperature": 0.3},
        }
        print("[*] Sending Meeting Details Extraction prompt to LLM...")
        details_response_data = query_huggingface_api(details_payload)

        if (
            details_response_data
            and isinstance(details_response_data, list)
            and len(details_response_data) > 0
        ):
            raw_details_text = (
                details_response_data[0].get("generated_text", "").strip()
            )
            print(f"[*] LLM Meeting Details Received (Raw): '{raw_details_text}'")

            # Attempt to parse the JSON from the response
            try:
                # Clean potential markdown ```json ... ``` artifacts
                if raw_details_text.startswith("```json"):
                    raw_details_text = raw_details_text[7:]
                if raw_details_text.endswith("```"):
                    raw_details_text = raw_details_text[:-3]
                raw_details_text = raw_details_text.strip()

                meeting_details = json.loads(raw_details_text)
                print(f"[*] Parsed Meeting Details: {meeting_details}")
                # Basic validation (check if it's a dict)
                if not isinstance(meeting_details, dict):
                    print("[!] LLM output for details was not a valid JSON object.")
                    meeting_details = None  # Reset if not a dictionary

            except json.JSONDecodeError as e:
                print(
                    f"[!] Failed to parse JSON meeting details from LLM response: {e}"
                )
                meeting_details = None  # Failed parsing
            except Exception as e:
                print(f"[!] Unexpected error parsing meeting details: {e}")
                meeting_details = None
        else:
            print("[!] Failed to get valid Meeting Details analysis from LLM.")

    # --- Combine results ---
    # For now, we don't ask for summary if extracting details, add later if needed
    analysis = {
        "raw": (
            raw_intent_text if "raw_intent_text" in locals() else ""
        ),  # Store raw intent text
        "intent": primary_intent,
        "summary": (
            "Not requested in prompt"
            if primary_intent != "Meeting Request"
            else "Details extracted"
        ),
        "meeting_details": meeting_details,  # Add the extracted details (or None)
    }
    return analysis


# --- Add Reply Drafting function ---
def draft_reply(original_subject, original_sender, action_context):
    """
    Uses the LLM to draft a reply based on the original email and the context of actions taken.
    """
    print(f"[*] Drafting reply based on context: '{action_context}'")

    # Simple prompt for reply generation
    reply_prompt = f"""Draft a polite and concise reply email based on the provided context about how an incoming email was handled. Address the original sender.

    Original Email Subject: {original_subject}
    Original Sender: {original_sender}
    Action Taken / Context: {action_context}

    Draft Reply Email Body:
    """

    payload = {
        "inputs": reply_prompt,
        "parameters": {
            "max_new_tokens": 200,
            "temperature": 0.7,
        },  # Allow more creativity
    }

    print("[*] Sending Reply Generation prompt to LLM...")
    response_data = query_huggingface_api(payload)

    if response_data and isinstance(response_data, list) and len(response_data) > 0:
        drafted_reply = response_data[0].get("generated_text", "").strip()
        print(f"[*] LLM Drafted Reply Received:\n---\n{drafted_reply}\n---")
        return drafted_reply
    else:
        print("[!] Failed to get reply draft from LLM.")
        return None

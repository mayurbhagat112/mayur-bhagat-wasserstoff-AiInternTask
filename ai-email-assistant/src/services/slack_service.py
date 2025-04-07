# src/services/slack_service.py
import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
TARGET_SLACK_CHANNEL_ID = os.getenv("TARGET_SLACK_CHANNEL_ID")

# Initialize Slack Client
slack_client = None
if SLACK_BOT_TOKEN:
    try:
        slack_client = WebClient(token=SLACK_BOT_TOKEN)
        # Test authentication (optional but recommended)
        auth_test = slack_client.auth_test()
        if auth_test.get("ok"):
            print(
                f"[*] Slack client initialized successfully for user {auth_test.get('user')} in team {auth_test.get('team')}"
            )
        else:
            print(f"[!] Slack Authentication failed: {auth_test.get('error')}")
            slack_client = None  # Invalidate client if auth fails
    except SlackApiError as e:
        print(f"[!] Error initializing Slack client: {e.response['error']}")
        slack_client = None
else:
    print(
        "[!] Warning: SLACK_BOT_TOKEN not found in environment variables. Slack integration disabled."
    )

if not TARGET_SLACK_CHANNEL_ID:
    print(
        "[!] Warning: TARGET_SLACK_CHANNEL_ID not found in environment variables. Slack messages may fail."
    )


def send_slack_message(message_text):
    """Sends a message to the configured Slack channel."""
    if not slack_client:
        print("[!] Cannot send Slack message: Client not initialized (check token).")
        return False
    if not TARGET_SLACK_CHANNEL_ID:
        print("[!] Cannot send Slack message: Target channel ID missing.")
        return False

    try:
        response = slack_client.chat_postMessage(
            channel=TARGET_SLACK_CHANNEL_ID,
            text=message_text,
            # You can use blocks= for richer formatting later
        )
        if response.get("ok"):
            print(
                f"[*] Message sent successfully to Slack channel {TARGET_SLACK_CHANNEL_ID}"
            )
            return True
        else:
            print(f"[!] Slack API error posting message: {response.get('error')}")
            return False

    except SlackApiError as e:
        print(f"[!] Error sending Slack message: {e.response['error']}")
        return False
    except Exception as e:
        print(f"[!] An unexpected error occurred sending Slack message: {e}")
        return False


# Example usage (for testing)
if __name__ == "__main__":
    if slack_client and TARGET_SLACK_CHANNEL_ID:
        print("\n--- Testing Slack Integration ---")
        test_message = "Hello from the AI Email Assistant! This is a test message."
        send_slack_message(test_message)
        print("-----------------------------")
    else:
        print(
            "\n[*] Skipping Slack test: Client not initialized or Channel ID missing."
        )

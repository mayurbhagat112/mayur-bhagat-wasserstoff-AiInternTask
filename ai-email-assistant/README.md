# AI Personal Email Assistant (Prototype)

## Overview

This project is a prototype for an AI-powered personal email assistant built in Python. It aims to read emails from a Gmail inbox, understand the context using a Large Language Model (LLM), store relevant information, and interact with external tools (Web Search, Slack, Google Calendar) to assist with managing email tasks. The assistant can currently classify email intent, attempt to schedule meetings, send Slack notifications for important emails, perform web searches for questions, and draft replies based on context, incorporating user confirmation steps for key actions.

**Current Status:** Prototype - Core functionality implemented, known limitations exist, particularly around LLM accuracy for intent classification and detail extraction.

## Features

* **Gmail API Integration:** Fetches unread emails from the inbox using OAuth2 authentication.
* **Email Parsing & Storage:** Parses key fields (sender, subject, body, timestamp, message/thread IDs) and stores emails in an SQLite database (`data/assistant.db`).
* **LLM Intent Analysis:** Uses a Hugging Face Inference API model (`google/flan-t5-base`) to determine the primary intent of emails (e.g., Meeting Request, Question, Action Required, etc.).
* **LLM Detail Extraction (Experimental):** Attempts to extract meeting details (summary, date, time, duration) in JSON format if the intent is identified as 'Meeting Request'.
* **Web Search Integration:** Uses `duckduckgo-search` to perform web searches if the email intent is classified as 'Question'.
* **Slack Notification:** Sends notifications to a specified Slack channel/user for emails classified with important intents (e.g., 'Action Required'), after user confirmation.
* **Google Calendar Integration:** Attempts to create events on the user's primary calendar based on details extracted from 'Meeting Request' emails, after user confirmation.
* **Reply Drafting:** Uses the LLM to draft contextual replies based on actions taken (e.g., meeting scheduled, web search results) or analysis results. Drafts are printed to the console.
* **Rule-Based Safety Filter:** Overrides incorrect 'Meeting Request' classifications from the LLM for emails that appear promotional or lack meeting cues, preventing unwanted scheduling attempts.
* **User Confirmation:** Prompts the user for confirmation via the command line before performing actions like creating calendar events or sending Slack messages.

## Architecture

![Architecture Diagram](docs/architecture.png)
*(Ensure you have created the `docs` folder and placed your `architecture.png` file inside it)*

**Workflow:**
The script periodically fetches unread emails via the Gmail API using secure OAuth2 authentication. Essential details from new emails are parsed and stored in a local SQLite database. The assistant then retrieves unprocessed emails from the database. For each email, it calls the Hugging Face Inference API with a prompt to determine the primary intent. If the intent is 'Meeting Request', a second LLM call attempts to extract structured details (date, time, etc.) as JSON. Based on the final intent (potentially corrected by a safety filter), the assistant decides on actions: if it's a 'Question', it performs a web search; if it's 'Action Required', it prepares a Slack notification; if it's a valid 'Meeting Request' with extracted details, it prepares a Google Calendar event. Before executing actions like Slack notifications or Calendar event creation, it prompts the user for confirmation (y/n). Finally, based on the outcome of the actions, it can use the LLM again to draft a suitable reply, which is printed to the console. The email is then marked as processed in the database.

## Setup Instructions

### Prerequisites

* Python 3.8+
* Git

### Installation

1.  **Clone the repository:**
    ```bash
    git clone <your-repo-url>
    cd ai-email-assistant
    ```
2.  **Create and activate a virtual environment:**
    ```bash
    # Linux/macOS
    python3 -m venv venv
    source venv/bin/activate

    # Windows
    python -m venv venv
    venv\Scripts\activate
    ```
3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

### API Credentials & Environment Variables

You need to obtain credentials for Google Cloud, Hugging Face, and Slack.

1.  **Google Cloud (Gmail & Calendar):**
    * Go to the [Google Cloud Console](https://console.cloud.google.com/).
    * Create a new project.
    * Enable the **Gmail API** and the **Google Calendar API** in the "Library" section.
    * Go to "Credentials", click "Create Credentials", choose "OAuth client ID".
    * Select "Desktop app" as the application type.
    * Download the JSON credentials file.
    * **Rename** the downloaded file to `credentials.json`.
    * Place this `credentials.json` file inside the `credentials/` folder in your project directory. **Do NOT commit this file to Git.**
    * Configure the OAuth Consent Screen (select "External" user type, provide app name, user support email, developer contact. You don't need to submit for verification for personal use, but you will see an "unverified app" screen during the first authentication).

2.  **Hugging Face:**
    * Create an account at [Hugging Face](https://huggingface.co/).
    * Go to your Settings -> Access Tokens.
    * Create a new token (read permission is sufficient). Copy the token (`hf_...`).

3.  **Slack:**
    * Go to [api.slack.com/apps](https://api.slack.com/apps) and create a new app "From scratch". Choose your workspace.
    * Navigate to "OAuth & Permissions".
    * Scroll down to "Scopes" -> "Bot Token Scopes". Add the `chat:write` scope.
    * Install the app to your workspace (button at the top).
    * Copy the **Bot User OAuth Token** (it starts with `xoxb-...`).
    * Find the **Channel ID** for the channel or user you want notifications sent to. For public channels, you can find it in the channel details in Slack (often starts with `C`). For DMs, it might start with `D`.

4.  **Create `.env` File:**
    * In the project root directory (`ai-email-assistant/`), create a file named `.env`.
    * Copy the contents of `.env.example` into `.env`.
    * Fill in your actual credentials obtained above:
        ```dotenv
        # .env
        HUGGINGFACE_API_TOKEN=hf_YOUR_HUGGINGFACE_TOKEN_HERE
        SLACK_BOT_TOKEN=xoxb-YOUR_SLACK_BOT_TOKEN_HERE
        TARGET_SLACK_CHANNEL_ID=YOUR_SLACK_CHANNEL_ID_HERE
        ```
    * **Ensure `.env` is listed in your `.gitignore` file!**

## How to Run

1.  Make sure your virtual environment is activated.
2.  Navigate to the project root directory (`ai-email-assistant/`) in your terminal.
3.  Run the main script:
    ```bash
    python -m src.main
    ```
4.  **First Run:** Your web browser will open, asking you to log in to your Google account and grant permission for the application to access Gmail and Calendar. You may see an "unverified app" warning – click "Advanced" and "Proceed" if you trust the source (your own application). After authorization, a `token.json` file will be created in the `credentials/` folder to store access/refresh tokens for future runs.

The assistant will then fetch emails, process them, and potentially ask for confirmation before taking actions like sending Slack messages or creating calendar events. Drafted replies will be printed to the console.

## AI Coding Assistant Usage *(Optional)*

*(Add a brief summary here if you used tools like GitHub Copilot, Cursor, ChatGPT, etc., and how they helped. e.g., "GitHub Copilot was used to help generate boilerplate code for API requests and suggest error handling patterns.")*

## Limitations

* **LLM Accuracy:** The `flan-t5-base` model used via the Inference API has limitations in accurately classifying intent for all email types and frequently fails to extract structured details (like meeting info) reliably or follow JSON formatting instructions precisely.
* **LLM API Reliability:** The free Hugging Face Inference API can experience rate limits, latency, or temporary unavailability (503 errors), especially for less commonly used models.
* **Date/Time Parsing:** Relies on `python-dateutil` and makes basic assumptions about timezones. May fail for complex or ambiguous date/time expressions.
* **No Email Sending:** Drafted replies are only printed to the console; the assistant does not currently send emails.
* **Basic Error Handling:** Error handling covers common cases but could be more comprehensive.
* **No UI:** Interaction is entirely via the command line.

## Future Improvements

* Implement email sending functionality (via Gmail API) with user confirmation.
* Improve LLM prompts significantly or experiment with larger/fine-tuned models (potentially requiring paid APIs or local hosting).
* Use more robust techniques for extracting structured data (e.g., combining LLM hints with dedicated NER/parsing libraries).
* Enhance timezone handling for calendar events.
* Add support for processing attachments.
* Implement a more sophisticated logging framework.
* Develop a simple web UI (e.g., using Flask or Streamlit).
* Add more tool integrations (e.g., Trello, Jira, CRMs).
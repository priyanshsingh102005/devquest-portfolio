import json
import os
import time
from datetime import datetime, timezone
from urllib import error, request as urlrequest

from flask import Flask, jsonify, render_template, request
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "").strip()
DISCORD_USERNAME = os.getenv("DISCORD_WEBHOOK_USERNAME", "DevQuest Contact Bot").strip()
MAX_DISCORD_RETRIES = 3
MAX_SYNC_RETRY_WAIT_SECONDS = 5


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/ping")
def ping():
    return "OK", 200


def send_to_discord(payload):
    """Send message to Discord webhook with rate-limit aware retries."""

    body = json.dumps(payload).encode("utf-8")

    api_request = urlrequest.Request(
        DISCORD_WEBHOOK_URL,
        data=body,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "DevQuestPortfolio/1.0",
        },
        method="POST",
    )

    def parse_retry_after(http_error, error_body):
        values = []

        retry_after_header = http_error.headers.get("Retry-After")
        if retry_after_header:
            try:
                values.append(float(retry_after_header))
            except ValueError:
                pass

        reset_after_header = http_error.headers.get("X-RateLimit-Reset-After")
        if reset_after_header:
            try:
                values.append(float(reset_after_header))
            except ValueError:
                pass

        try:
            body_data = json.loads(error_body)
            retry_after_body = body_data.get("retry_after")
            if retry_after_body is not None:
                values.append(float(retry_after_body))
        except Exception:
            pass

        if not values:
            return 2.0

        retry_after = max(values)

        # Some APIs return milliseconds; convert only when value is clearly ms-scale.
        if retry_after > 1000:
            retry_after = retry_after / 1000.0

        return max(retry_after, 0.25)

    for _ in range(MAX_DISCORD_RETRIES):
        try:
            with urlrequest.urlopen(api_request, timeout=15):
                return True, None

        except error.HTTPError as exc:
            if exc.code != 429:
                return False, f"Discord API ({exc.code})"

            error_body = exc.read().decode("utf-8", errors="ignore")
            retry_after = parse_retry_after(exc, error_body)

            # Avoid long blocking sleeps in a request/response handler.
            if retry_after > MAX_SYNC_RETRY_WAIT_SECONDS:
                return (
                    False,
                    f"RATE_LIMIT: Too many requests right now. Please wait about {int(round(retry_after))} seconds and try again.",
                )

            time.sleep(retry_after)

        except Exception as exc:
            return False, str(exc)

    return False, "RATE_LIMIT: Too many requests right now. Please try again shortly."


@app.route("/contact", methods=["POST"])
def contact():
    payload = request.get_json(silent=True) or {}

    name = (payload.get("name") or "").strip()
    email = (payload.get("email") or "").strip()
    message = (payload.get("message") or "").strip()

    if not name or not email or not message:
        return jsonify({"ok": False, "error": "All fields are required."}), 400

    if not DISCORD_WEBHOOK_URL:
        return jsonify({"ok": False, "error": "Discord webhook not configured."}), 500

    submitted_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    submitted_iso = (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )

    webhook_payload = {
        "username": DISCORD_USERNAME,
        "content": "New portfolio contact submission",
        "embeds": [
            {
                "title": "Contact Form Submission",
                "color": 5814783,
                "fields": [
                    {"name": "Name", "value": name, "inline": True},
                    {"name": "Email", "value": email, "inline": True},
                    {"name": "Message", "value": message[:1024], "inline": False},
                ],
                "timestamp": submitted_iso,
            }
        ],
    }

    success, error_message = send_to_discord(webhook_payload)

    if not success:
        status_code = 429 if (error_message or "").startswith("RATE_LIMIT:") else 502
        safe_error = (error_message or "Message failed.").replace("RATE_LIMIT:", "").strip()
        return jsonify({"ok": False, "error": safe_error}), status_code

    return jsonify(
        {
            "ok": True,
            "meta": {
                "platform": "discord",
                "submitted_at": submitted_at,
                "contact_name": name,
                "contact_email": email,
            },
        }
    ), 200


if __name__ == "__main__":
    app.run(debug=True)

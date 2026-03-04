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


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/ping")
def ping():
    return "OK", 200


def send_to_discord(payload):
    """Send message to Discord webhook with rate limit handling"""

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

    try:
        with urlrequest.urlopen(api_request, timeout=15):
            return True, None

    except error.HTTPError as exc:

        # Handle Discord rate limit
        if exc.code == 429:
            error_body = exc.read().decode("utf-8", errors="ignore")

            try:
                data = json.loads(error_body)
                retry_after = data.get("retry_after", 2000) / 1000
            except Exception:
                retry_after = 2

            time.sleep(retry_after)

            try:
                with urlrequest.urlopen(api_request, timeout=15):
                    return True, None
            except Exception as retry_error:
                return False, str(retry_error)

        return False, f"Discord API ({exc.code})"

    except Exception as exc:
        return False, str(exc)


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
        "content": "📩 New portfolio contact submission",
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
        return jsonify({"ok": False, "error": error_message}), 502

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
import json
import os
from datetime import datetime, timezone
from urllib import error, request as urlrequest

from flask import Flask, jsonify, render_template, request
from dotenv import load_dotenv

app = Flask(__name__)
load_dotenv()


@app.route('/')
def home():
    return render_template('index.html')


@app.route("/ping")
def ping():
    return "OK", 200


@app.route("/contact", methods=["POST"])
def contact():
    payload = request.get_json(silent=True) or {}
    name = (payload.get("name") or "").strip()
    email = (payload.get("email") or "").strip()
    message = (payload.get("message") or "").strip()

    if not name or not email or not message:
        return jsonify({"ok": False, "error": "All fields are required."}), 400

    discord_webhook_url = (os.getenv("DISCORD_WEBHOOK_URL") or "").strip()
    discord_username = (os.getenv("DISCORD_WEBHOOK_USERNAME") or "DevQuest Contact Bot").strip()

    if not discord_webhook_url:
        return jsonify({
            "ok": False,
            "error": "Discord is not configured on server."
        }), 500

    submitted_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    submitted_iso = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    webhook_payload = {
        "username": discord_username,
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

    body = json.dumps(webhook_payload).encode("utf-8")

    api_request = urlrequest.Request(
        discord_webhook_url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "DevQuestPortfolio/1.0 (+Flask Contact Form)",
        },
        method="POST",
    )

    try:
        with urlrequest.urlopen(api_request, timeout=15):
            return jsonify({
                "ok": True,
                "meta": {
                    "platform": "discord",
                    "submitted_at": submitted_at,
                    "contact_name": name,
                    "contact_email": email,
                    "contact_message": message,
                },
            }), 200
    except error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="ignore")
        error_message = error_body or "Unknown error"

        try:
            parsed = json.loads(error_body)
            if isinstance(parsed, dict):
                error_message = parsed.get("message") or error_message
        except Exception:
            pass

        return jsonify({"ok": False, "error": f"Discord API ({exc.code}): {error_message}"}), 502
    except Exception:
        return jsonify({"ok": False, "error": "Failed to send Discord message."}), 502


if __name__ == '__main__':
    app.run(debug=True)

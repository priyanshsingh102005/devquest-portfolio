import json
import os
from datetime import datetime
from urllib import error, request as urlrequest

from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')


@app.route("/contact", methods=["POST"])
def contact():
    payload = request.get_json(silent=True) or {}
    name = (payload.get("name") or "").strip()
    email = (payload.get("email") or "").strip()
    message = (payload.get("message") or "").strip()

    if not name or not email or not message:
        return jsonify({"ok": False, "error": "All fields are required."}), 400

    wa_token = os.getenv("WA_ACCESS_TOKEN")
    wa_phone_number_id = os.getenv("WA_PHONE_NUMBER_ID")
    wa_recipient = os.getenv("WA_RECIPIENT_NUMBER")

    if not wa_token or not wa_phone_number_id or not wa_recipient:
        return jsonify({
            "ok": False,
            "error": "WhatsApp is not configured on server."
        }), 500

    submitted_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    text_body = (
        "New Portfolio Contact\n"
        "--------------------\n"
        f"Name: {name}\n"
        f"Email: {email}\n"
        f"Submitted: {submitted_at}\n\n"
        "Message:\n"
        f"{message}"
    )

    endpoint = f"https://graph.facebook.com/v22.0/{wa_phone_number_id}/messages"
    body = json.dumps({
        "messaging_product": "whatsapp",
        "to": wa_recipient,
        "type": "text",
        "text": {"body": text_body},
    }).encode("utf-8")

    api_request = urlrequest.Request(
        endpoint,
        data=body,
        headers={
            "Authorization": f"Bearer {wa_token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urlrequest.urlopen(api_request, timeout=15) as response:
            response_data = json.loads(response.read().decode("utf-8"))
            return jsonify({"ok": True, "result": response_data}), 200
    except error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="ignore")
        return jsonify({"ok": False, "error": error_body}), 502
    except Exception:
        return jsonify({"ok": False, "error": "Failed to send WhatsApp message."}), 502

if __name__ == '__main__':
    app.run(debug=True)

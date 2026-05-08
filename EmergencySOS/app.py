from flask import Flask, request, jsonify
from flask_cors import CORS
from urllib.parse import quote

app = Flask(__name__)
CORS(app)

@app.route("/send_sos", methods=["POST"])
def send_sos():
    data = request.json
    location = data["location"]

    phone = "91XXXXXXXXXX"  # must be exact format

    message = quote(f"🚨 EMERGENCY ALERT! Location: {location}")

    whatsapp_link = f"https://wa.me/{phone}?text={message}"

    print("DEBUG LINK:", whatsapp_link)  # IMPORTANT for testing

    return jsonify({"whatsapp_link": whatsapp_link})

if __name__ == "__main__":
    app.run(debug=True)

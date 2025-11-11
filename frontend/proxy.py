from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)

# URL zu deinem echten Backend (z. B. FastAPI, Vercel, etc.)
BACKEND_URL = "https://sepj.vercel.app/metrics"

@app.route("/metrics")
def metrics():
    # Parameter aus der Query übernehmen
    start = request.args.get("start")
    end = request.args.get("end")

    if not start or not end:
        return jsonify({"error": "Missing start/end parameters"}), 400

    try:
        # Anfrage an das Backend senden
        resp = requests.get(
            BACKEND_URL,
            params={"start": start, "end": end},
            headers={"Accept": "application/json"},
            timeout=20
        )

        # Inhalt 1:1 weitergeben
        return Response(
            resp.content,
            status=resp.status_code,
            content_type=resp.headers.get("Content-Type", "application/json"),
        )

    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Proxy request failed: {str(e)}"}), 502


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8083)

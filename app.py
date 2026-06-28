import os

from dotenv import load_dotenv
from flask import Flask, jsonify, make_response, render_template, request, send_from_directory

load_dotenv()

app = Flask(__name__)
ASSETS_DIR = os.path.join(app.root_path, "assets")


@app.route("/assets/<path:filename>")
def assets(filename):
    return send_from_directory(ASSETS_DIR, filename)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/process-query", methods=["POST", "OPTIONS"])
def process():
    if request.method == "OPTIONS":
        response = make_response()
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        return response, 204

    try:
        from search import process_query

        data = request.get_json(silent=True)
        if not data:
            raise ValueError("Request body must be JSON.")

        print("Received request:", data)
        result = process_query(data)

        response = jsonify(result)
        response.headers["Access-Control-Allow-Origin"] = "*"
        return response
    except Exception as e:
        print("Error:", str(e))
        response = jsonify({"error": str(e)})
        response.headers["Access-Control-Allow-Origin"] = "*"
        return response, 500


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)

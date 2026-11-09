import os
import socket

from flask import Flask, jsonify

app = Flask(__name__)

# Message affiché sur la page d'accueil : à modifier pendant le workshop
MESSAGE = "Bonjour depuis le pipeline CI/CD de louis !"
# Version injectée au build (SHA du commit en CI, "dev" par défaut)
VERSION = os.getenv("APP_VERSION", "dev")


@app.route("/")
def index():
    # Page "Coco le Singe" (fichier autonome dans static/coco.html)
    response = app.send_static_file("coco.html")
    response.headers["X-App-Version"] = VERSION[:7]
    response.headers["X-Container"] = socket.gethostname()
    return response


@app.route("/health")
def health():
    return jsonify(status="ok", version=VERSION)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

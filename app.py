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
    # Vidéo plein écran : lecture auto, sans son, en boucle, sans contrôles
    return f"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{MESSAGE}</title>
<style>
  html, body {{ margin: 0; height: 100%; overflow: hidden; background: #000; }}
  video {{
    position: fixed; inset: 0;
    width: 100vw; height: 100vh; height: 100dvh;
    object-fit: cover; pointer-events: none;
  }}
</style>
</head>
<body>
<!-- Version : {VERSION[:7]} | Conteneur : {socket.gethostname()} -->
<video src="/static/gorille.mp4" autoplay muted loop playsinline disablepictureinpicture></video>
</body>
</html>"""


@app.route("/health")
def health():
    return jsonify(status="ok", version=VERSION)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

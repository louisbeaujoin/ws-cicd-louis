import os
import socket

import psycopg
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


@app.route("/gateau")
def gateau():
    # Jeu original "La pâtisserie de Coco" (fichier autonome dans static/gateau.html)
    return app.send_static_file("gateau.html")


@app.route("/health")
def health():
    return jsonify(status="ok", version=VERSION)


@app.route("/db")
def db():
    """Teste la connexion au serveur PostgreSQL (paramètres lus dans l'environnement)."""
    cfg = {k: os.getenv(k) for k in ("DB_HOST", "DB_NAME", "DB_USER", "DB_PASSWORD")}
    missing = [k for k, v in cfg.items() if not v]
    if missing:
        return jsonify(status="erreur", detail="Variables manquantes : " + ", ".join(missing)), 500
    try:
        with psycopg.connect(
            host=cfg["DB_HOST"], dbname=cfg["DB_NAME"], user=cfg["DB_USER"],
            password=cfg["DB_PASSWORD"], sslmode="require", connect_timeout=5,
        ) as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT current_database(), current_user, version(), now(),"
                " inet_server_addr()::text,"
                " (SELECT count(*) FROM information_schema.tables"
                "  WHERE table_schema NOT IN ('pg_catalog', 'information_schema'))"
            )
            base, user, version, heure, ip, nb_tables = cur.fetchone()
    except Exception as exc:  # pas de mot de passe dans le message renvoyé
        return jsonify(status="erreur", host=cfg["DB_HOST"], detail=type(exc).__name__ + " : " + str(exc).split("\n")[0]), 500
    return jsonify(
        status="ok",
        serveur=cfg["DB_HOST"],
        base=base,
        utilisateur=user,
        postgres=version.split(",")[0],
        heure_serveur=heure.isoformat(),
        tables_utilisateur=nb_tables,
        conteneur=socket.gethostname(),
        version_app=VERSION[:7],
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

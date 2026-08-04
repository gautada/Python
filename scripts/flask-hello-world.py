"""
flask-hello-world.py - Minimal Flask smoke test.

Purpose:
    Confirms that a WSGI app can be served out of this image. Not part of
    the base image's own dependencies -- Flask is not installed here (this
    image ships no pip and no app-specific packages by design).

Requires:
    flask (not bundled in this image)

Usage:
    uv run --with flask ~/scripts/flask-hello-world.py
    # then browse http://localhost:8080/

    or, with flask already available on PATH:
    flask --app flask-hello-world run
    python -m flask --app flask-hello-world run
"""

from flask import Flask

app = Flask(__name__)


@app.route("/")
def hello_world():
    return "<p>Hello, World!</p>"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port="8080")

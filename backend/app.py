# backend/app.py
# ─────────────────────────────────────────────────────────────────────────────
# SafeHer — Flask entry point.
# Registers both blueprints, enables CORS, loads env vars.
#
# Run: python app.py
# Server starts at http://localhost:5000
# ─────────────────────────────────────────────────────────────────────────────

import os
from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv

# Load .env from project root (one level up from backend/)
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

# ── Import blueprints ─────────────────────────────────────────────────────────
# risk_grid.py loads the model at import time, so these two imports
# trigger model load before the first request ever arrives.
from routes_heatmap   import heatmap_bp
from routes_saferoute import saferoute_bp

# ─────────────────────────────────────────────────────────────────────────────

def create_app() -> Flask:
    app = Flask(__name__)

    # Allow requests from the React dev server (port 3000)
    # and any production origin — tighten this in prod if needed
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # Register blueprints
    app.register_blueprint(heatmap_bp)
    app.register_blueprint(saferoute_bp)

    # ── Health check ──────────────────────────────────────────────────────────
    @app.route("/api/health", methods=["GET"])
    def health():
        return {"status": "ok", "service": "SafeHer API"}, 200

    return app


# ─────────────────────────────────────────────────────────────────────────────

app = create_app()

if __name__ == "__main__":
    debug = os.environ.get("FLASK_ENV", "production") == "development"
    port  = int(os.environ.get("PORT", 5000))

    print(f"\n{'─'*52}")
    print(f"  SafeHer API starting on http://localhost:{port}")
    print(f"  Debug mode : {debug}")
    print(f"  Endpoints  : /api/heatmap  |  /api/safe-route")
    print(f"{'─'*52}\n")

    app.run(host="0.0.0.0", port=port, debug=debug)
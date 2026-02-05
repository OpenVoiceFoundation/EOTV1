from flask import Flask, request, jsonify, render_template
import sqlite3
import hashlib
import hmac
from datetime import datetime
import os

app = Flask(__name__)

DB_FILE = "receiver_data.db"
SECRET_KEY = b"eot2026et67567"


# -----------------------------
# DATABASE INIT
# -----------------------------
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS ingestion (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            trap_id TEXT NOT NULL,
            trap_type TEXT NOT NULL,
            gps TEXT NOT NULL,
            egg_count INTEGER NOT NULL,
            barangay TEXT,
            sha256_valid INTEGER NOT NULL
        )
    """)

    conn.commit()
    conn.close()


init_db()


# -----------------------------
# FRONTEND
# -----------------------------
@app.route("/")
def index():
    return render_template("receiver.html")


# -----------------------------
# SUBMISSION ENDPOINT
# -----------------------------
@app.route("/api/submit", methods=["POST"])
def submit_data():
    try:
        data = request.get_json(force=True)

        trap_id = data.get("trap_id", "").strip()
        trap_type = data.get("trap_type", "").strip()
        gps = data.get("gps", "").strip()  # expects "lat,long"
        egg_count = int(data.get("egg_count", 0))
        barangay = data.get("barangay", "").strip()
        client_hash = data.get("sha256", "").strip()

        if not trap_id or not trap_type or not gps:
            return jsonify({"success": False, "error": "trap_id, trap_type, and gps are required"}), 400

        # HMAC validation
        payload_str = f"{trap_id}{trap_type}{gps}{egg_count}".encode()
        server_hash = hmac.new(SECRET_KEY, payload_str, hashlib.sha256).hexdigest()
        valid = (server_hash == client_hash)

        # Insert into DB
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO ingestion (timestamp, trap_id, trap_type, gps, egg_count, barangay, sha256_valid)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.utcnow().isoformat(),
            trap_id,
            trap_type,
            gps,
            egg_count,
            barangay,
            1 if valid else 0
        ))
        conn.commit()
        conn.close()

        return jsonify({"success": True, "sha256_valid": valid})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


# -----------------------------
# FETCH DATA FOR DASHBOARD
# -----------------------------
@app.route("/api/ingestion")
def get_ingestion_data():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
        SELECT timestamp, trap_id, trap_type, gps, egg_count, barangay, sha256_valid
        FROM ingestion
        ORDER BY id DESC
        LIMIT 200
    """)

    rows = cur.fetchall()
    conn.close()

    entries = []
    for r in rows:
        entries.append({
            "timestamp": r["timestamp"],
            "trap_id": r["trap_id"],
            "trap_type": r["trap_type"],
            "gps": r["gps"],
            "egg_count": r["egg_count"],
            "barangay": r["barangay"] or "",
            "sha256_valid": bool(r["sha256_valid"]),
        })

    return jsonify(entries)


# -----------------------------
# HEALTH CHECK
# -----------------------------
@app.route("/api/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    # debug=False for production
    app.run(host="0.0.0.0", port=5000, debug=True)

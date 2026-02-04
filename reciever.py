from flask import Flask, request, jsonify, render_template
import csv, os, hashlib, hmac
from datetime import datetime

app = Flask(__name__)
CSV_FILE = "receiver_data.csv"

# --- Shared secret key (must match scanner) ---
SECRET_KEY = b"eot2026et67567"  # <-- Change this if you want

# --- Ensure CSV exists ---
if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, "w", newline="") as f:
        csv.writer(f).writerow(
            [
                "timestamp",
                "trap_id",
                "trap_type",
                "gps",
                "egg_count",
                "barangay",
                "sha256_valid",
            ]
        )


# --- Serve Dashboard ---
@app.route("/")
def index():
    return render_template("receiver.html")


# --- Scanner Submission Endpoint ---
@app.route("/api/submit", methods=["POST"])
def submit_data():
    try:
        data = request.json
        trap_id = data.get("trap_id")
        trap_type = data.get("trap_type")
        gps = data.get("gps")
        egg_count = int(data.get("egg_count", 0))
        barangay = data.get("barangay", "")

        # --- Compute HMAC-SHA256 for verification ---
        payload_str = f"{trap_id}{trap_type}{gps}{egg_count}".encode()
        sha256_hash = hmac.new(SECRET_KEY, payload_str, hashlib.sha256).hexdigest()
        valid = sha256_hash == data.get("sha256")

        # --- Save to CSV ---
        with open(CSV_FILE, "a", newline="") as f:
            csv.writer(f).writerow(
                [datetime.utcnow(), trap_id, trap_type, gps, egg_count, barangay, valid]
            )

        return jsonify({"success": True, "sha256_valid": valid})

    except Exception as e:
        return jsonify({"error": str(e)}), 400


# --- Provide Dashboard Data ---
@app.route("/api/ingestion")
def get_ingestion_data():
    entries = []
    if os.path.exists(CSV_FILE):
        with open(CSV_FILE, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                entries.append(
                    {
                        "timestamp": row["timestamp"],
                        "trap_id": row["trap_id"],
                        "trap_type": row["trap_type"],
                        "gps": row["gps"],
                        "egg_count": int(row["egg_count"]),
                        "barangay": row.get("barangay", ""),
                        "sha256_valid": row["sha256_valid"] == "True",
                    }
                )
    return jsonify(entries)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

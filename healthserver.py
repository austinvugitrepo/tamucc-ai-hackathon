from flask import Flask, request, jsonify, make_response
import mariadb
from openai import OpenAI

app = Flask(__name__)

# ===== CONFIG =====
DB_CONFIG = {
    "user": "webuser",
    "password": "REMOVED_PASSWORD",
    "host": "localhost",
    "database": "Hospital"
}



# ===== CORS HELPER =====
def add_cors(resp):
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return resp

# ===== PRE-FLIGHT =====
@app.route("/api/advice", methods=["OPTIONS"])
def advice_options():
    return add_cors(make_response("", 204))

# ===== POST ROUTE =====
@app.route("/api/advice", methods=["POST"])
def advice():
    data = request.get_json()
    if not data:
        return add_cors(make_response(jsonify({"error": "No input provided"}), 400))

    symptoms = data.get("symptoms", "").strip() or "General patient condition"
    severity = data.get("severity", "critical").lower()

    # ===== FETCH HOSPITALS =====
    recommendations = []
    try:
        conn = mariadb.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT name, eta, tags FROM hospitals")
        hospitals = cursor.fetchall()

        for h in hospitals:
            recommendations.append({
                "name": h["name"],
                "eta": h.get("eta", "N/A"),
                "tags": [t.strip() for t in h["tags"].split(",")] if h.get("tags") else []
            })

        print(f"[DEBUG] Loaded {len(recommendations)} hospitals from DB")

    except Exception as e:
        print("[DEBUG] DB error:", e)
    finally:
        try:
            conn.close()
        except:
            pass

    if not recommendations:
        recommendations = [{"name": "Fallback Hospital", "eta": "N/A", "tags": ["General"]}]
        print("[DEBUG] Using fallback hospital recommendations")

    # ===== GPT-4 PROMPT =====
    prompt = (
        "You are a hospital recommendation assistant.\n"
        "Select the most suitable hospital from the list below based on the patient's symptoms, "
        "matching relevant tags (specialties, services), and also consider ETA (shorter is better if equally matched).\n\n"
        f"Patient symptoms: {symptoms}\n"
        f"Severity: {severity}\n\n"
        "Hospitals:\n" +
        "\n".join(f"- {r['name']} ({r['eta']}) | Tags: {', '.join(r['tags'])}" for r in recommendations) +
        "\n\nRespond with a short explanation of which hospital is best and why, mentioning ETA and relevant tags."
    )

    print("[DEBUG] Sending prompt to GPT-4:\n", prompt)

    # ===== GPT-4 CALL =====
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_completion_tokens=200,
            temperature=0.7
        )
        ai_message = response.choices[0].message.content.strip()
        print("[DEBUG] GPT-4 reply:", ai_message)

    except Exception as e:
        print("[DEBUG] OpenAI error:", e)
        ai_message = "AI unavailable. Showing hospital recommendations only."

    # ===== RETURN JSON =====
    return add_cors(jsonify({
        "message": ai_message,
        "recommendations": recommendations
    }))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050, debug=True)

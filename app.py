from flask import Flask, render_template, request, jsonify
import threading
import rex

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")


# ---------------- API ENDPOINTS ----------------

@app.route("/api/status")
def status():
    return jsonify({
        "silent": rex.state.silent,
        "focus": rex.state.focus,
        "ai": rex.state.ai,
        "speaking": rex.state.speaking,
        "mic": rex.state.voice_running
    })



@app.route("/api/command", methods=["POST"])
def send_command():
    data = request.json
    command = data.get("command", "")

    if command:
        rex.command_queue.put(command)
        return jsonify({"success": True})

    return jsonify({"success": False})


@app.route("/api/silent", methods=["POST"])
def toggle_silent():
    return jsonify({"silent": rex.toggle_silent()})


@app.route("/api/focus", methods=["POST"])
def start_focus():
    rex.start_focus(25)
    return jsonify({"focus": True})



# ---------------- START REX ----------------

# explicit control
@app.route("/api/rex/start", methods=["POST"])
def start_rex_api():
    threading.Thread(target=rex.main, daemon=True).start()
    return jsonify({"status": "started"})



@app.route("/api/mic/start", methods=["POST"])
def start_mic():
    result = rex.start_voice()
    return jsonify({"status": result})


@app.route("/api/mic/stop", methods=["POST"])
def stop_mic():
    result = rex.stop_voice()
    return jsonify({"status": result})



if __name__ == "__main__":
    # Start the command worker to handle tasks
    threading.Thread(target=rex.command_worker, daemon=True).start()
    # Start the speech worker to handle speaking
    threading.Thread(target=rex.speech_worker, daemon=True).start()
    # Start the Flask web server
    app.run(debug=True, port=5000)
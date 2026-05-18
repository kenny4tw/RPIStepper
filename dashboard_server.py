import json
import threading
import time
from pathlib import Path

from flask import Flask, jsonify, render_template, request

from stepper_controller import StepperController

BASE_DIR = Path(__file__).resolve().parent
COMMAND_FILE = BASE_DIR / "command.json"

app = Flask(__name__)
controller = StepperController()
controller_lock = threading.Lock()
last_command_id = None


def execute_command(payload):
    command = str(payload.get("command", "")).strip().lower()
    if not command:
        return {"ok": False, "error": "Missing command"}, 400

    with controller_lock:
        try:
            if command == "move_forward":
                steps = int(payload.get("steps", 100))
                controller.move_forward(steps)
            elif command == "move_backward":
                steps = int(payload.get("steps", 100))
                controller.move_backward(steps)
            elif command == "home":
                max_steps = int(payload.get("max_steps", 2000))
                controller.home(max_steps=max_steps)
            elif command == "stop":
                controller.stop()
            elif command == "set_speed":
                rpm = int(payload.get("rpm", 60))
                controller.set_speed(rpm)
            elif command == "set_style":
                style = str(payload.get("style", "INTERLEAVE"))
                controller.set_style(style)
            else:
                return {"ok": False, "error": f"Unknown command: {command}"}, 400
        except Exception as exc:
            return {"ok": False, "error": str(exc)}, 500

        return {"ok": True, "command": command, "status": controller.get_status()}, 200


def watch_command_file():
    global last_command_id
    while True:
        try:
            if COMMAND_FILE.exists():
                payload = json.loads(COMMAND_FILE.read_text(encoding="utf-8"))
                if isinstance(payload, dict):
                    cmd_id = payload.get("id")
                    if cmd_id is not None and cmd_id != last_command_id:
                        last_command_id = cmd_id
                        result, code = execute_command(payload)
                        if code == 200:
                            print(f"[JSON] Executed command id={cmd_id}: {payload.get('command')}")
                        else:
                            print(f"[JSON] Failed command id={cmd_id}: {result}")
        except Exception as exc:
            print(f"[JSON] Watcher error: {exc}")

        time.sleep(0.5)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/status", methods=["GET"])
def api_status():
    with controller_lock:
        return jsonify(controller.get_status())


@app.route("/api/command", methods=["POST"])
def api_command():
    payload = request.get_json(silent=True) or {}
    result, code = execute_command(payload)
    return jsonify(result), code


@app.route("/api/command-file", methods=["GET"])
def api_command_file():
    if not COMMAND_FILE.exists():
        return jsonify({"exists": False, "path": str(COMMAND_FILE)})
    return jsonify(
        {
            "exists": True,
            "path": str(COMMAND_FILE),
            "content": COMMAND_FILE.read_text(encoding="utf-8"),
        }
    )


def ensure_default_command_file():
    if not COMMAND_FILE.exists():
        template = {
            "id": 1,
            "command": "move_forward",
            "steps": 200,
        }
        COMMAND_FILE.write_text(json.dumps(template, indent=2), encoding="utf-8")


if __name__ == "__main__":
    ensure_default_command_file()
    watcher = threading.Thread(target=watch_command_file, daemon=True)
    watcher.start()
    app.run(host="0.0.0.0", port=5055, debug=False)

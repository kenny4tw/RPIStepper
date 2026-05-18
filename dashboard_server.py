import json
import os
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

from flask import Flask, jsonify, render_template, request

from stepper_controller import StepperController

BASE_DIR = Path(__file__).resolve().parent
COMMAND_FILE = BASE_DIR / "command.json"
RADAR_DASHBOARD_URL = os.getenv("RADAR_DASHBOARD_URL", "http://127.0.0.1:5060")
OPTA_DASHBOARD_URL = os.getenv("OPTA_DASHBOARD_URL", "http://127.0.0.1:5070")
STEPPER_REMOTE_URL = os.getenv("STEPPER_REMOTE_URL", "").strip().rstrip("/")

app = Flask(__name__)
controller = None
controller_error = None
controller_lock = threading.Lock()
mode_lock = threading.Lock()
last_command_id = None
remote_json_enabled = False


def get_controller():
    global controller, controller_error
    if controller is not None:
        return controller, None
    if controller_error is not None:
        return None, controller_error


def has_remote_stepper():
    return bool(STEPPER_REMOTE_URL)


def remote_stepper_request(path, payload=None):
    if not has_remote_stepper():
        return None, 503, "Remote stepper URL not configured"

    url = f"{STEPPER_REMOTE_URL}{path}"
    body = None
    headers = {}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url=url, data=body, headers=headers, method="POST" if body else "GET")
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = resp.read().decode("utf-8")
            return json.loads(data), resp.status, None
    except urllib.error.HTTPError as exc:
        try:
            data = exc.read().decode("utf-8")
            parsed = json.loads(data)
        except Exception:
            parsed = {"ok": False, "error": data if "data" in locals() else str(exc)}
        return parsed, exc.code, None
    except Exception as exc:
        return None, 503, str(exc)

    try:
        controller = StepperController()
        return controller, None
    except Exception as exc:
        controller_error = str(exc)
        print(f"[STEPPER] Hardware unavailable: {controller_error}")
        return None, controller_error


def execute_command(payload, source="ui"):
    global remote_json_enabled
    command = str(payload.get("command", "")).strip().lower()
    if not command:
        return {"ok": False, "error": "Missing command"}, 400

    if source in {"json", "remote"}:
        with mode_lock:
            if not remote_json_enabled:
                return {
                    "ok": False,
                    "error": "Remote JSON control is disabled in dashboard switch",
                }, 403

    if has_remote_stepper():
        result, code, err = remote_stepper_request("/api/command", payload)
        if err:
            return {"ok": False, "error": f"Remote stepper request failed: {err}"}, 503
        return result, code

    with controller_lock:
        ctrl, ctrl_error = get_controller()
        if ctrl is None:
            return {
                "ok": False,
                "error": f"Stepper hardware unavailable: {ctrl_error}",
            }, 503

        try:
            if command == "move_forward":
                steps = int(payload.get("steps", 100))
                ctrl.move_forward(steps)
            elif command == "move_backward":
                steps = int(payload.get("steps", 100))
                ctrl.move_backward(steps)
            elif command == "home":
                max_steps = int(payload.get("max_steps", 2000))
                ctrl.home(max_steps=max_steps)
            elif command == "stop":
                ctrl.stop()
            elif command == "set_speed":
                rpm = int(payload.get("rpm", 60))
                ctrl.set_speed(rpm)
            elif command == "set_style":
                style = str(payload.get("style", "INTERLEAVE"))
                ctrl.set_style(style)
            else:
                return {"ok": False, "error": f"Unknown command: {command}"}, 400
        except Exception as exc:
            return {"ok": False, "error": str(exc)}, 500

        return {
            "ok": True,
            "command": command,
            "source": source,
            "status": ctrl.get_status(),
        }, 200


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
                        result, code = execute_command(payload, source="json")
                        if code == 200:
                            print(f"[JSON] Executed command id={cmd_id}: {payload.get('command')}")
                        else:
                            print(f"[JSON] Failed command id={cmd_id}: {result}")
        except Exception as exc:
            print(f"[JSON] Watcher error: {exc}")

        time.sleep(0.5)


@app.route("/")
def hub():
    return render_template("hub.html")


@app.route("/stepper")
def index():
    return render_template("index.html")


@app.route("/radarsensor")
def radarsensor_dashboard():
    return render_template("embed.html", title="RadarSensor Dashboard", upstream_url=RADAR_DASHBOARD_URL)


@app.route("/opta")
def opta_dashboard():
    return render_template("embed.html", title="Arduino Opta Dashboard", upstream_url=OPTA_DASHBOARD_URL)


@app.route("/api/status", methods=["GET"])
@app.route("/stepper/api/status", methods=["GET"])
def api_status():
    with mode_lock:
        remote_enabled = remote_json_enabled

    if has_remote_stepper():
        result, code, err = remote_stepper_request("/api/status")
        if err:
            status = {
                "available": False,
                "error": f"Remote stepper request failed: {err}",
                "position": 0,
                "limit_switch_1": False,
                "limit_switch_2": False,
                "moving": False,
                "speed_rpm": 0,
                "style": "INTERLEAVE",
                "backend": "remote",
            }
            status["remote_json_enabled"] = remote_enabled
            return jsonify(status)

        if isinstance(result, dict):
            result["backend"] = "remote"
            result["remote_json_enabled"] = remote_enabled
            return jsonify(result), code

    with controller_lock:
        ctrl, ctrl_error = get_controller()
        if ctrl is None:
            status = {
                "available": False,
                "error": ctrl_error,
                "position": 0,
                "limit_switch_1": False,
                "limit_switch_2": False,
                "moving": False,
                "speed_rpm": 0,
                "style": "INTERLEAVE",
                "backend": "local",
            }
        else:
            status = ctrl.get_status()
            status["available"] = True
            status["backend"] = "local"
    status["remote_json_enabled"] = remote_enabled
    return jsonify(status)


@app.route("/api/command", methods=["POST"])
@app.route("/stepper/api/command", methods=["POST"])
def api_command():
    payload = request.get_json(silent=True) or {}
    result, code = execute_command(payload, source="ui")
    return jsonify(result), code


@app.route("/api/remote-command", methods=["POST"])
@app.route("/stepper/api/remote-command", methods=["POST"])
def api_remote_command():
    payload = request.get_json(silent=True) or {}
    result, code = execute_command(payload, source="remote")
    return jsonify(result), code


@app.route("/api/remote-mode", methods=["GET", "POST"])
@app.route("/stepper/api/remote-mode", methods=["GET", "POST"])
def api_remote_mode():
    global remote_json_enabled
    if request.method == "GET":
        with mode_lock:
            return jsonify({"remote_json_enabled": remote_json_enabled})

    payload = request.get_json(silent=True) or {}
    enabled = bool(payload.get("enabled", False))
    with mode_lock:
        remote_json_enabled = enabled
        return jsonify({"ok": True, "remote_json_enabled": remote_json_enabled})


@app.route("/api/command-file", methods=["GET"])
@app.route("/stepper/api/command-file", methods=["GET"])
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

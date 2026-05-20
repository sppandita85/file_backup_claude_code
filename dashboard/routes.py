import subprocess
import sys
from pathlib import Path

from flask import Flask, jsonify, render_template, request

from deep_translator import GoogleTranslator

from mover import db


def register_routes(app: Flask, config):
    def get_conn():
        return db.get_connection(config.expanded_db_path())

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/api/stats")
    def stats():
        conn = get_conn()
        try:
            return jsonify(db.get_summary_stats(conn))
        finally:
            conn.close()

    @app.route("/api/history")
    def history():
        days = int(request.args.get("days", 30))
        conn = get_conn()
        try:
            return jsonify(db.get_recent_moves(conn, days=days))
        finally:
            conn.close()

    @app.route("/api/chart/by-type")
    def chart_by_type():
        conn = get_conn()
        try:
            return jsonify(db.get_stats_by_type(conn))
        finally:
            conn.close()

    @app.route("/api/chart/daily")
    def chart_daily():
        conn = get_conn()
        try:
            return jsonify(db.get_daily_totals(conn))
        finally:
            conn.close()

    @app.route("/api/runs")
    def runs():
        conn = get_conn()
        try:
            return jsonify(db.get_run_history(conn))
        finally:
            conn.close()

    @app.route("/api/config")
    def config_view():
        return jsonify({
            "source_dir": config.source_dir,
            "onedrive_folder": config.onedrive_folder,
            "schedule_hour": config.schedule_hour,
            "schedule_minute": config.schedule_minute,
            "min_age_minutes": config.min_age_minutes,
            "exclude_extensions": config.exclude_extensions,
            "dashboard_port": config.dashboard_port,
        })

    @app.route("/translator")
    def translator():
        return render_template("translator.html")

    @app.route("/api/translate", methods=["POST"])
    def api_translate():
        data = request.get_json(silent=True) or {}
        text = (data.get("text") or "").strip()
        if not text:
            return jsonify({"error": "Please enter a sentence to translate."}), 400
        try:
            translation = GoogleTranslator(source="en", target="de").translate(text)
            return jsonify({"translation": translation or ""})
        except Exception as exc:
            return jsonify({"error": f"Translation failed: {exc}"}), 500

    @app.route("/api/run-now", methods=["POST"])
    def run_now():
        project_dir = Path(__file__).parent.parent
        python = project_dir / ".venv" / "bin" / "python"
        if not python.exists():
            python = Path(sys.executable)
        try:
            result = subprocess.run(
                [str(python), "-m", "mover.mover"],
                cwd=str(project_dir),
                capture_output=True,
                text=True,
                timeout=300,
            )
            return jsonify({
                "success": result.returncode == 0,
                "stdout": result.stdout[-2000:],
                "stderr": result.stderr[-2000:],
            })
        except subprocess.TimeoutExpired:
            return jsonify({"success": False, "error": "Timed out after 5 minutes"}), 500
        except Exception as exc:
            return jsonify({"success": False, "error": str(exc)}), 500

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from flask import Flask
from dashboard.routes import register_routes
from mover import config_loader

app = Flask(__name__, template_folder="templates", static_folder="static")
config = config_loader.load()
register_routes(app, config)

if __name__ == "__main__":
    print(f"Dashboard running at http://localhost:{config.dashboard_port}")
    app.run(host="127.0.0.1", port=config.dashboard_port, debug=False)

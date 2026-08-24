import json

from datetime import datetime
from pathlib import Path


STATE_FILE = Path("dashboard_state.json")


def update_dashboard_state(gesture_name):
    state = {
        "gesture": gesture_name,
        "updated_at": datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    }

    with STATE_FILE.open(
        mode="w",
        encoding="utf-8"
    ) as file:
        json.dump(
            state,
            file,
            indent=4
        )


def create_initial_state():
    if STATE_FILE.exists():
        return

    update_dashboard_state("NO HAND")
import csv
import io
import tempfile
import unittest

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import dashboard


def create_event(
    event_id,
    gesture_name,
    event_time=None,
):
    if event_time is None:
        event_time = datetime(
            2026,
            8,
            24,
            9,
            30,
            tzinfo=timezone.utc,
        )

    return {
        "event_id": event_id,
        "event_time": event_time,
        "gesture_name": gesture_name,
        "open_finger_count": 1,
        "event_source": "CAMERA",
    }


class DashboardRouteTests(unittest.TestCase):
    def setUp(self):
        dashboard.app.config.update(
            TESTING=True,
        )

        self.client = dashboard.app.test_client()

    def test_events_rejects_invalid_gesture(self):
        response = self.client.get(
            "/api/events?gesture=UNKNOWN"
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.get_json()["error"],
            "Invalid gesture filter.",
        )

    def test_events_rejects_invalid_date(self):
        response = self.client.get(
            "/api/events?start_date=24-08-2026"
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.get_json()["error"],
            "Invalid date format.",
        )

    def test_events_rejects_reversed_date_range(self):
        response = self.client.get(
            "/api/events"
            "?start_date=2026-08-25"
            "&end_date=2026-08-24"
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.get_json()["error"],
            "Start date cannot be after end date.",
        )

    @patch(
        "dashboard.get_filtered_gesture_events"
    )
    @patch(
        "dashboard.count_filtered_gesture_events",
        return_value=25,
    )
    def test_events_uses_database_pagination(
        self,
        count_events_mock,
        filtered_events_mock,
    ):
        filtered_events_mock.return_value = [
            create_event(15, "FIST"),
        ]

        response = self.client.get(
            "/api/events"
            "?gesture=FIST"
            "&page=2"
            "&per_page=10"
        )

        self.assertEqual(response.status_code, 200)

        data = response.get_json()

        self.assertEqual(data["count"], 25)
        self.assertEqual(data["page"], 2)
        self.assertEqual(data["per_page"], 10)
        self.assertEqual(data["total_pages"], 3)
        self.assertEqual(len(data["events"]), 1)

        count_events_mock.assert_called_once_with(
            gesture_name="FIST",
            start_date=None,
            end_date=None,
        )

        filtered_events_mock.assert_called_once_with(
            gesture_name="FIST",
            start_date=None,
            end_date=None,
            limit=10,
            offset=10,
        )

    def test_events_rejects_invalid_page_size(self):
        response = self.client.get(
            "/api/events?per_page=101"
        )

        self.assertEqual(response.status_code, 400)

    @patch("dashboard.get_all_gesture_events")
    def test_csv_export_applies_gesture_filter(
        self,
        all_events_mock,
    ):
        all_events_mock.return_value = [
            create_event(1, "OPEN PALM"),
            create_event(2, "FIST"),
            create_event(3, "POINT"),
        ]

        response = self.client.get(
            "/export/csv?gesture=FIST"
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            "gesture_events_filtered.csv",
            response.headers["Content-Disposition"],
        )

        csv_text = response.data.decode("utf-8")
        rows = list(
            csv.reader(io.StringIO(csv_text))
        )

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[1][2], "FIST")

    def test_dashboard_state_returns_default_when_missing(self):
        with tempfile.TemporaryDirectory() as directory:
            missing_state_file = (
                Path(directory) / "missing-state.json"
            )

            with patch.object(
                dashboard,
                "STATE_FILE",
                missing_state_file,
            ):
                response = self.client.get(
                    "/api/dashboard-state"
                )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get_json(),
            {
                "gesture": "NO HAND",
                "updated_at": None,
            },
        )


if __name__ == "__main__":
    unittest.main()
import csv
import io
import json
import os
import sys

from urllib.error import HTTPError, URLError
from urllib.request import urlopen


BASE_URL = os.getenv(
    "DASHBOARD_BASE_URL",
    "http://127.0.0.1:5000",
).rstrip("/")


class SystemTestFailure(Exception):
    pass


def open_url(path):
    return urlopen(
        f"{BASE_URL}{path}",
        timeout=5,
    )


def get_json(path):
    with open_url(path) as response:
        if response.status != 200:
            raise SystemTestFailure(
                f"{path} returned HTTP {response.status}."
            )

        return json.loads(
            response.read().decode("utf-8")
        )


def require_fields(data, fields, endpoint):
    missing_fields = [
        field
        for field in fields
        if field not in data
    ]

    if missing_fields:
        raise SystemTestFailure(
            f"{endpoint} is missing fields: "
            + ", ".join(missing_fields)
        )


def test_home_page():
    with open_url("/") as response:
        html = response.read().decode("utf-8")

    if "Gesture Data Dashboard" not in html:
        raise SystemTestFailure(
            "Dashboard title was not found."
        )


def test_dashboard_data():
    endpoint = "/api/dashboard-data"
    data = get_json(endpoint)

    require_fields(
        data,
        [
            "total_events",
            "open_palm_count",
            "fist_count",
            "point_count",
            "daily_trend",
            "hourly_activity",
            "database_connected",
        ],
        endpoint,
    )

    if not isinstance(data["daily_trend"], list):
        raise SystemTestFailure(
            "daily_trend must be a list."
        )

    if len(data["hourly_activity"]) != 24:
        raise SystemTestFailure(
            "hourly_activity must contain 24 hours."
        )


def test_dashboard_state():
    endpoint = "/api/dashboard-state"
    data = get_json(endpoint)

    require_fields(
        data,
        ["gesture", "updated_at"],
        endpoint,
    )


def test_event_pagination():
    endpoint = (
        "/api/events"
        "?gesture=ALL&page=1&per_page=10"
    )

    data = get_json(endpoint)

    require_fields(
        data,
        [
            "events",
            "count",
            "page",
            "per_page",
            "total_pages",
        ],
        endpoint,
    )

    if data["page"] != 1:
        raise SystemTestFailure(
            "The first event page was not returned."
        )

    if data["per_page"] != 10:
        raise SystemTestFailure(
            "per_page was not applied."
        )

    if len(data["events"]) > 10:
        raise SystemTestFailure(
            "The API returned more than 10 events."
        )

    expected_pages = max(
        1,
        (data["count"] + 9) // 10,
    )

    if data["total_pages"] != expected_pages:
        raise SystemTestFailure(
            "total_pages is incorrect."
        )


def test_invalid_filter():
    try:
        open_url("/api/events?gesture=UNKNOWN")

    except HTTPError as error:
        if error.code != 400:
            raise SystemTestFailure(
                "Invalid gesture did not return HTTP 400."
            ) from error

        return

    raise SystemTestFailure(
        "Invalid gesture was accepted by the API."
    )


def test_filtered_csv_export():
    with open_url(
        "/export/csv?gesture=FIST"
    ) as response:
        content_disposition = response.headers.get(
            "Content-Disposition",
            "",
        )

        csv_text = response.read().decode("utf-8")

    if "gesture_events_filtered.csv" not in (
        content_disposition
    ):
        raise SystemTestFailure(
            "Filtered CSV filename is incorrect."
        )

    rows = list(
        csv.DictReader(io.StringIO(csv_text))
    )

    invalid_rows = [
        row
        for row in rows
        if row.get("gesture_name") != "FIST"
    ]

    if invalid_rows:
        raise SystemTestFailure(
            "Filtered CSV contains non-FIST events."
        )


def run_system_tests():
    tests = [
        ("Home page", test_home_page),
        ("Dashboard data API", test_dashboard_data),
        ("Dashboard state API", test_dashboard_state),
        ("Event pagination", test_event_pagination),
        ("Invalid filter handling", test_invalid_filter),
        ("Filtered CSV export", test_filtered_csv_export),
    ]

    failures = []

    print(f"Testing dashboard at {BASE_URL}\n")

    for name, test_function in tests:
        try:
            test_function()
            print(f"[PASS] {name}")

        except Exception as error:
            failures.append((name, error))
            print(f"[FAIL] {name}: {error}")

    print()

    if failures:
        print(
            f"System test failed: "
            f"{len(failures)} check(s) failed."
        )
        return 1

    print(
        f"System test passed: "
        f"{len(tests)} checks completed."
    )
    return 0


if __name__ == "__main__":
    try:
        sys.exit(run_system_tests())

    except (URLError, TimeoutError) as error:
        print(
            "Dashboard could not be reached:",
            error,
        )
        sys.exit(1)
import csv
import json

from collections import Counter
from datetime import datetime, timedelta
from io import StringIO
from pathlib import Path
from zoneinfo import ZoneInfo

import psycopg

from flask import Flask, jsonify, render_template, request, Response

from database import (
    count_filtered_gesture_events,
    get_all_gesture_events,
    get_filtered_gesture_events,
    initialize_database,
)


app = Flask(__name__)

STATE_FILE = Path("dashboard_state.json")
ACCURACY_FILE = Path(
    "gesture_accuracy_results.csv"
)
ISTANBUL_TIMEZONE = ZoneInfo("Europe/Istanbul")

ALLOWED_GESTURES = {
    "ALL",
    "OPEN PALM",
    "FIST",
    "POINT",
}


def format_event_time(event_time):
    if event_time is None:
        return "No data"

    local_event_time = event_time.astimezone(
        ISTANBUL_TIMEZONE
    )

    return local_event_time.strftime(
        "%Y-%m-%d %H:%M:%S"
    )


def get_event_filter_values():
    gesture_name = request.args.get(
        "gesture",
        default="ALL",
        type=str,
    ).strip().upper()

    start_date = request.args.get(
        "start_date",
        default="",
        type=str,
    ).strip()

    end_date = request.args.get(
        "end_date",
        default="",
        type=str,
    ).strip()

    if gesture_name not in ALLOWED_GESTURES:
        return None, "Invalid gesture filter."

    parsed_dates = {}

    for name, value in (
        ("start_date", start_date),
        ("end_date", end_date),
    ):
        if not value:
            parsed_dates[name] = None
            continue

        try:
            parsed_dates[name] = datetime.strptime(
                value,
                "%Y-%m-%d",
            ).date()

        except ValueError:
            return None, "Invalid date format."

    parsed_start_date = parsed_dates[
        "start_date"
    ]

    parsed_end_date = parsed_dates[
        "end_date"
    ]

    if (
        parsed_start_date
        and parsed_end_date
        and parsed_start_date > parsed_end_date
    ):
        return (
            None,
            "Start date cannot be after end date.",
        )

    return {
        "gesture_name": gesture_name,
        "start_date": start_date,
        "end_date": end_date,
        "parsed_start_date": parsed_start_date,
        "parsed_end_date": parsed_end_date,
    }, None

def get_accuracy_data():
    default_data = {
        "overall_accuracy": 0,
        "total_accuracy_samples": 0,
        "open_palm_accuracy": 0,
        "fist_accuracy": 0,
        "point_accuracy": 0,
        "accuracy_data_available": False,
    }

    if not ACCURACY_FILE.exists():
        return default_data

    gesture_totals = {
        "OPEN PALM": {
            "samples": 0,
            "correct": 0,
        },
        "FIST": {
            "samples": 0,
            "correct": 0,
        },
        "POINT": {
            "samples": 0,
            "correct": 0,
        },
    }

    try:
        with ACCURACY_FILE.open(
            mode="r",
            encoding="utf-8",
            newline="",
        ) as file:
            reader = csv.DictReader(file)

            for row in reader:
                gesture_name = row[
                    "expected_gesture"
                ]

                if gesture_name not in gesture_totals:
                    continue

                total_samples = int(
                    row["total_samples"]
                )

                correct_predictions = int(
                    row["correct_predictions"]
                )

                gesture_totals[
                    gesture_name
                ]["samples"] += total_samples

                gesture_totals[
                    gesture_name
                ]["correct"] += (
                    correct_predictions
                )

    except (
        OSError,
        ValueError,
        KeyError,
    ) as error:
        print(
            "Accuracy result file error:",
            error,
        )

        return default_data

    total_samples = sum(
        result["samples"]
        for result in gesture_totals.values()
    )

    total_correct = sum(
        result["correct"]
        for result in gesture_totals.values()
    )

    def calculate_accuracy(gesture_name):
        result = gesture_totals[
            gesture_name
        ]

        if result["samples"] == 0:
            return 0

        return round(
            result["correct"]
            / result["samples"]
            * 100,
            2,
        )

    if total_samples > 0:
        overall_accuracy = round(
            total_correct
            / total_samples
            * 100,
            2,
        )
    else:
        overall_accuracy = 0

    return {
        "overall_accuracy": overall_accuracy,

        "total_accuracy_samples": (
            total_samples
        ),

        "open_palm_accuracy": (
            calculate_accuracy(
                "OPEN PALM"
            )
        ),

        "fist_accuracy": (
            calculate_accuracy(
                "FIST"
            )
        ),

        "point_accuracy": (
            calculate_accuracy(
                "POINT"
            )
        ),

        "accuracy_data_available": (
            total_samples > 0
        ),
    }


def get_dashboard_data():
    try:
        database_events = get_all_gesture_events()
        database_connected = True

    except (psycopg.Error, OSError) as error:
        print(
            "Dashboard database error:",
            error,
        )

        database_events = []
        database_connected = False

    gesture_names = []
    all_events = []
    event_dates = []
    event_date_hours = []

    for event in database_events:
        gesture_name = event["gesture_name"]

        local_event_time = event[
            "event_time"
        ].astimezone(
            ISTANBUL_TIMEZONE
        )

        local_event_date = (
            local_event_time.date()
        )

        local_event_hour = (
            local_event_time.hour
        )

        gesture_names.append(
            gesture_name
        )

        event_dates.append(
            local_event_date
        )

        event_date_hours.append({
            "date": local_event_date,
            "hour": local_event_hour,
        })

        all_events.append({
            "event_id": event["event_id"],

            "event_time": format_event_time(
                event["event_time"]
            ),

            "gesture_name": gesture_name,

            "open_finger_count": (
                event["open_finger_count"]
            ),

            "event_source": (
                event["event_source"]
            ),
        })

    gesture_counts = Counter(
        gesture_names
    )

    total_events = len(
        gesture_names
    )

    open_palm_count = gesture_counts.get(
        "OPEN PALM",
        0,
    )

    fist_count = gesture_counts.get(
        "FIST",
        0,
    )

    point_count = gesture_counts.get(
        "POINT",
        0,
    )

    if total_events > 0:
        open_palm_percentage = round(
            open_palm_count
            / total_events
            * 100,
            1,
        )

        fist_percentage = round(
            fist_count
            / total_events
            * 100,
            1,
        )

        point_percentage = round(
            point_count
            / total_events
            * 100,
            1,
        )

    else:
        open_palm_percentage = 0
        fist_percentage = 0
        point_percentage = 0

    if gesture_counts:
        most_common_gesture = (
            gesture_counts
            .most_common(1)[0][0]
        )

    else:
        most_common_gesture = "No data"

    if all_events:
        last_event_time = all_events[-1][
            "event_time"
        ]

    else:
        last_event_time = "No data"

    recent_events = list(
        reversed(
            all_events[-10:]
        )
    )

    today = datetime.now(
        ISTANBUL_TIMEZONE
    ).date()

    event_date_counts = Counter(
        event_dates
    )

    daily_trend = []

    for day_offset in range(6, -1, -1):
        trend_date = today - timedelta(
            days=day_offset
        )

        daily_trend.append({
            "date": trend_date.isoformat(),

            "label": trend_date.strftime(
                "%d %b"
            ),

            "count": event_date_counts.get(
                trend_date,
                0,
            ),
        })

    today_hour_counts = Counter(
        event["hour"]
        for event in event_date_hours
        if event["date"] == today
    )

    hourly_activity = []

    for hour in range(24):
        hourly_activity.append({
            "hour": hour,
            "label": f"{hour:02d}:00",

            "count": today_hour_counts.get(
                hour,
                0,
            ),
        })

    today_event_count = sum(
        today_hour_counts.values()
    )

    if today_hour_counts:
        busiest_hour_number = max(
            today_hour_counts,
            key=today_hour_counts.get,
        )

        busiest_hour = (
            f"{busiest_hour_number:02d}:00"
        )

    else:
        busiest_hour = "No data"

    accuracy_data = get_accuracy_data()

    return {
        "total_events": total_events,
        "open_palm_count": open_palm_count,
        "fist_count": fist_count,
        "point_count": point_count,

        "open_palm_percentage": (
            open_palm_percentage
        ),

        "fist_percentage": (
            fist_percentage
        ),

        "point_percentage": (
            point_percentage
        ),

        "today_event_count": (
            today_event_count
        ),

        "busiest_hour": busiest_hour,

        "most_common_gesture": (
            most_common_gesture
        ),

        "last_event_time": last_event_time,
        "recent_events": recent_events,
        "daily_trend": daily_trend,
        "hourly_activity": hourly_activity,

        "database_connected": (
            database_connected
        ),

        **accuracy_data,
    }


@app.route("/api/dashboard-state")
def dashboard_state():
    default_state = {
        "gesture": "NO HAND",
        "updated_at": None,
    }

    if not STATE_FILE.exists():
        return jsonify(
            default_state
        )

    try:
        with STATE_FILE.open(
            mode="r",
            encoding="utf-8",
        ) as file:
            state = json.load(file)

        return jsonify(state)

    except (
        json.JSONDecodeError,
        OSError,
    ):
        return jsonify(
            default_state
        )


@app.route("/api/dashboard-data")
def dashboard_data_api():
    return jsonify(
        get_dashboard_data()
    )


@app.route("/api/events")
def filtered_events_api():
    filters, filter_error = get_event_filter_values()

    if filter_error:
        return jsonify({
            "error": filter_error,
        }), 400

    gesture_name = filters["gesture_name"]
    start_date = filters["start_date"]
    end_date = filters["end_date"]

    page = request.args.get(
        "page",
        default=1,
        type=int,
    )

    per_page = request.args.get(
        "per_page",
        default=10,
        type=int,
    )

    if page < 1:
        return jsonify({
            "error": "Page must be at least 1.",
        }), 400

    if per_page < 1 or per_page > 100:
        return jsonify({
            "error":
                "Per-page value must be "
                "between 1 and 100.",
        }), 400

    has_active_filter = (
        gesture_name != "ALL"
        or bool(start_date)
        or bool(end_date)
    )

    try:
        total_count = count_filtered_gesture_events(
            gesture_name=gesture_name,
            start_date=start_date or None,
            end_date=end_date or None,
        )

        total_pages = max(
            1,
            (total_count + per_page - 1)
            // per_page,
        )

        page = min(page, total_pages)
        event_offset = (page - 1) * per_page

        events = get_filtered_gesture_events(
            gesture_name=gesture_name,
            start_date=start_date or None,
            end_date=end_date or None,
            limit=per_page,
            offset=event_offset,
        )

    except (psycopg.Error, OSError) as error:
        print(
            "Filtered events database error:",
            error,
        )

        return jsonify({
            "error":
                "PostgreSQL database "
                "is unavailable.",

            "events": [],
            "count": 0,
        }), 503

    formatted_events = []

    for event in events:
        formatted_events.append({
            "event_id": event["event_id"],

            "event_time": format_event_time(
                event["event_time"]
            ),

            "gesture_name": (
                event["gesture_name"]
            ),

            "open_finger_count": (
                event["open_finger_count"]
            ),

            "event_source": (
                event["event_source"]
            ),
        })

    return jsonify({
        "events": formatted_events,

        "count": total_count,

        "page": page,

        "per_page": per_page,

        "total_pages": total_pages,

        "filter_active": (
            has_active_filter
        ),
    })


@app.route("/export/csv")
def export_csv():
    filters, filter_error = get_event_filter_values()

    if filter_error:
        return Response(
            filter_error,
            status=400,
            mimetype="text/plain",
        )

    gesture_name = filters["gesture_name"]
    parsed_start_date = filters[
        "parsed_start_date"
    ]
    parsed_end_date = filters[
        "parsed_end_date"
    ]

    try:
        events = get_all_gesture_events()

    except (psycopg.Error, OSError) as error:
        print(
            "CSV export database error:",
            error,
        )

        return Response(
            "CSV export could not be completed "
            "because the PostgreSQL database "
            "is unavailable.",
            status=503,
            mimetype="text/plain",
        )

    filtered_events = []

    for event in events:
        event_gesture = event[
            "gesture_name"
        ].strip().upper()

        local_event_date = event[
            "event_time"
        ].astimezone(
            ISTANBUL_TIMEZONE
        ).date()

        gesture_matches = (
            gesture_name == "ALL"
            or event_gesture == gesture_name
        )

        start_date_matches = (
            parsed_start_date is None
            or local_event_date >= parsed_start_date
        )

        end_date_matches = (
            parsed_end_date is None
            or local_event_date <= parsed_end_date
        )

        if (
            gesture_matches
            and start_date_matches
            and end_date_matches
        ):
            filtered_events.append(event)

    output = StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "event_id",
        "event_time",
        "gesture_name",
        "open_finger_count",
        "event_source",
    ])

    for event in filtered_events:
        writer.writerow([
            event["event_id"],

            format_event_time(
                event["event_time"]
            ),

            event["gesture_name"],
            event["open_finger_count"],
            event["event_source"],
        ])

    csv_content = output.getvalue()
    output.close()

    has_active_filter = (
        gesture_name != "ALL"
        or parsed_start_date is not None
        or parsed_end_date is not None
    )

    export_filename = (
        "gesture_events_filtered.csv"
        if has_active_filter
        else "gesture_events_export.csv"
    )

    return Response(
        csv_content,
        mimetype="text/csv",

        headers={
            "Content-Disposition":
                "attachment; filename="
                f"{export_filename}"
        },
    )


@app.route("/")
def home():
    dashboard_data = (
        get_dashboard_data()
    )

    return render_template(
        "dashboard.html",
        data=dashboard_data,
    )


if __name__ == "__main__":
    try:
        initialize_database()

    except (psycopg.Error, OSError) as error:
        print(
            "PostgreSQL could not "
            "be initialized:",
            error,
        )

        print(
            "Dashboard will continue "
            "in offline mode."
        )

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False,
    )
import csv

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from database import get_database_connection


CSV_FILE = Path("gesture_events.csv")
ISTANBUL_TIMEZONE = ZoneInfo("Europe/Istanbul")


def get_open_finger_count(gesture_name):
    finger_counts = {
        "OPEN PALM": 4,
        "FIST": 0,
        "POINT": 1
    }

    return finger_counts.get(gesture_name)


def read_csv_events():
    events = []

    if not CSV_FILE.exists():
        print("gesture_events.csv bulunamadı.")
        return events

    with CSV_FILE.open(
        mode="r",
        newline="",
        encoding="utf-8"
    ) as file:
        reader = csv.DictReader(file)

        for row in reader:
            event_time_text = row.get(
                "event_time",
                ""
            ).strip()

            gesture_name = row.get(
                "gesture_name",
                ""
            ).strip()

            if not event_time_text or not gesture_name:
                continue

            event_time = datetime.strptime(
                event_time_text,
                "%Y-%m-%d %H:%M:%S"
            )

            event_time = event_time.replace(
                tzinfo=ISTANBUL_TIMEZONE
            )

            events.append((
                event_time,
                gesture_name,
                get_open_finger_count(gesture_name),
                "CSV_IMPORT"
            ))

    return events


def migrate_events():
    events = read_csv_events()

    if not events:
        print("Taşınacak kayıt bulunamadı.")
        return

    insert_query = """
        INSERT INTO gesture_events (
            event_time,
            gesture_name,
            open_finger_count,
            event_source
        )
        VALUES (%s, %s, %s, %s);
    """

    with get_database_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                TRUNCATE TABLE gesture_events
                RESTART IDENTITY;
                """
            )

            cursor.executemany(
                insert_query,
                events
            )

    print(
        f"{len(events)} CSV kaydı PostgreSQL'e taşındı."
    )


if __name__ == "__main__":
    migrate_events()
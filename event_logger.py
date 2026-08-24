import psycopg

from database import save_gesture_event


def log_gesture_event(
    gesture_name,
    open_finger_count=None
):
    try:
        database_event_id = save_gesture_event(
            gesture_name,
            open_finger_count
        )

        print(
            "PostgreSQL event saved:",
            database_event_id,
            "-",
            gesture_name
        )

        return database_event_id

    except (psycopg.Error, OSError) as error:
        print(
            "PostgreSQL event could not be saved:",
            error
        )

        return None
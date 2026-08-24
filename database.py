import os

import psycopg

from dotenv import load_dotenv


load_dotenv()


def get_database_connection():
    return psycopg.connect(
        host=os.getenv(
            "POSTGRES_HOST",
            "localhost",
        ),
        port=os.getenv(
            "POSTGRES_PORT",
            "5433",
        ),
        dbname=os.getenv(
            "POSTGRES_DB",
            "gesture_dashboard",
        ),
        user=os.getenv(
            "POSTGRES_USER",
            "gesture_user",
        ),
        password=os.getenv(
            "POSTGRES_PASSWORD",
        ),
        connect_timeout=3,
    )


def initialize_database():
    create_table_query = """
        CREATE TABLE IF NOT EXISTS gesture_events (
            event_id BIGSERIAL PRIMARY KEY,
            event_time TIMESTAMPTZ NOT NULL
                DEFAULT CURRENT_TIMESTAMP,
            gesture_name VARCHAR(30) NOT NULL,
            open_finger_count SMALLINT,
            event_source VARCHAR(30) NOT NULL
                DEFAULT 'CAMERA'
        );
    """

    create_time_index_query = """
        CREATE INDEX IF NOT EXISTS
            idx_gesture_events_event_time
        ON gesture_events (event_time);
    """

    create_gesture_index_query = """
        CREATE INDEX IF NOT EXISTS
            idx_gesture_events_gesture_name
        ON gesture_events (gesture_name);
    """

    with get_database_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(create_table_query)
            cursor.execute(create_time_index_query)
            cursor.execute(create_gesture_index_query)

    print("Database and table are ready.")


def save_gesture_event(
    gesture_name,
    open_finger_count=None,
):
    insert_query = """
        INSERT INTO gesture_events (
            gesture_name,
            open_finger_count
        )
        VALUES (%s, %s)
        RETURNING event_id;
    """

    with get_database_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                insert_query,
                (
                    gesture_name,
                    open_finger_count,
                ),
            )

            event_id = cursor.fetchone()[0]

    return event_id


def rows_to_events(rows):
    events = []

    for row in rows:
        events.append({
            "event_id": row[0],
            "event_time": row[1],
            "gesture_name": row[2],
            "open_finger_count": row[3],
            "event_source": row[4],
        })

    return events


def get_all_gesture_events():
    select_query = """
        SELECT
            event_id,
            event_time,
            gesture_name,
            open_finger_count,
            event_source
        FROM gesture_events
        ORDER BY event_time ASC, event_id ASC;
    """

    with get_database_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(select_query)
            rows = cursor.fetchall()

    return rows_to_events(rows)


def build_event_filter(
    gesture_name=None,
    start_date=None,
    end_date=None,
):
    conditions = []
    parameters = []

    if gesture_name and gesture_name != "ALL":
        conditions.append("gesture_name = %s")
        parameters.append(gesture_name)

    if start_date:
        conditions.append(
            """
            (
                event_time
                AT TIME ZONE 'Europe/Istanbul'
            )::date >= %s::date
            """
        )
        parameters.append(start_date)

    if end_date:
        conditions.append(
            """
            (
                event_time
                AT TIME ZONE 'Europe/Istanbul'
            )::date <= %s::date
            """
        )
        parameters.append(end_date)

    where_clause = ""

    if conditions:
        where_clause = "WHERE " + " AND ".join(
            conditions
        )

    return where_clause, parameters


def count_filtered_gesture_events(
    gesture_name=None,
    start_date=None,
    end_date=None,
):
    where_clause, parameters = build_event_filter(
        gesture_name=gesture_name,
        start_date=start_date,
        end_date=end_date,
    )

    count_query = f"""
        SELECT COUNT(*)
        FROM gesture_events
        {where_clause};
    """

    with get_database_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                count_query,
                tuple(parameters),
            )

            total_count = cursor.fetchone()[0]

    return total_count


def get_filtered_gesture_events(
    gesture_name=None,
    start_date=None,
    end_date=None,
    limit=10,
    offset=0,
):
    if limit < 1:
        raise ValueError("limit must be positive")

    if offset < 0:
        raise ValueError("offset cannot be negative")

    where_clause, parameters = build_event_filter(
        gesture_name=gesture_name,
        start_date=start_date,
        end_date=end_date,
    )

    select_query = f"""
        SELECT
            event_id,
            event_time,
            gesture_name,
            open_finger_count,
            event_source
        FROM gesture_events
        {where_clause}
        ORDER BY event_time DESC, event_id DESC
        LIMIT %s
        OFFSET %s;
    """

    parameters.extend([
        limit,
        offset,
    ])

    with get_database_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                select_query,
                tuple(parameters),
            )

            rows = cursor.fetchall()

    return rows_to_events(rows)


def test_database_connection():
    with get_database_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    current_database(),
                    current_user,
                    version();
                """
            )

            database_name, database_user, version = (
                cursor.fetchone()
            )

    print("Database:", database_name)
    print("User:", database_user)
    print("PostgreSQL:", version)


if __name__ == "__main__":
    initialize_database()
    test_database_connection()
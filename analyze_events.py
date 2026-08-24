import csv

from collections import Counter
from pathlib import Path


CSV_FILE = Path("gesture_events.csv")


if not CSV_FILE.exists():
    print("gesture_events.csv bulunamadı.")
    raise SystemExit


gesture_names = []
event_times = []

with CSV_FILE.open(
    mode="r",
    newline="",
    encoding="utf-8"
) as file:
    reader = csv.DictReader(file)

    for row in reader:
        gesture_names.append(row["gesture_name"])
        event_times.append(row["event_time"])


if not gesture_names:
    print("Henüz kayıtlı hareket bulunmuyor.")
    raise SystemExit


gesture_counts = Counter(gesture_names)

print("\n--- Gesture Event Summary ---")
print("Total events:", len(gesture_names))

for gesture_name, count in gesture_counts.items():
    print(f"{gesture_name}: {count}")

print("\nFirst event:", event_times[0])
print("Last event:", event_times[-1])

most_common_gesture, highest_count = gesture_counts.most_common(1)[0]

print(
    "Most common gesture:",
    most_common_gesture,
    f"({highest_count} events)"
)
import csv

from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt


CSV_FILE = Path("gesture_events.csv")


if not CSV_FILE.exists():
    print("gesture_events.csv bulunamadı.")
    raise SystemExit


gesture_names = []

with CSV_FILE.open(
    mode="r",
    newline="",
    encoding="utf-8"
) as file:
    reader = csv.DictReader(file)

    for row in reader:
        gesture_names.append(row["gesture_name"])


if not gesture_names:
    print("Grafik oluşturmak için kayıt bulunmuyor.")
    raise SystemExit


gesture_counts = Counter(gesture_names)

gestures = list(gesture_counts.keys())
counts = list(gesture_counts.values())

colors = []

for gesture in gestures:
    if gesture == "OPEN PALM":
        colors.append("#22c55e")
    elif gesture == "FIST":
        colors.append("#ef4444")
    else:
        colors.append("#3b82f6")


plt.figure(figsize=(8, 5))

bars = plt.bar(
    gestures,
    counts,
    color=colors
)

plt.title("Gesture Event Analysis")
plt.xlabel("Gesture")
plt.ylabel("Event Count")
plt.grid(
    axis="y",
    linestyle="--",
    alpha=0.3
)

for bar, count in zip(bars, counts):
    plt.text(
        bar.get_x() + bar.get_width() / 2,
        bar.get_height() + 0.05,
        str(count),
        ha="center"
    )

plt.tight_layout()
plt.show()
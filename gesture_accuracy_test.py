import csv
import time

from collections import Counter
from datetime import datetime
from pathlib import Path

import cv2
import mediapipe as mp

from hand_tracking import (
    create_hand_landmarker,
    draw_hand_landmarks,
    open_camera,
    recognize_gesture,
)


RESULT_FILE = Path(
    "gesture_accuracy_results.csv"
)

TARGET_SAMPLE_COUNT = 100

GESTURE_OPTIONS = {
    "1": "OPEN PALM",
    "2": "FIST",
    "3": "POINT",
}


def select_expected_gesture():
    print()
    print("Gesture Accuracy Test")
    print("---------------------")
    print("1 - OPEN PALM")
    print("2 - FIST")
    print("3 - POINT")
    print()

    while True:
        selection = input(
            "Select the gesture to test: "
        ).strip()

        if selection in GESTURE_OPTIONS:
            return GESTURE_OPTIONS[
                selection
            ]

        print(
            "Invalid selection. "
            "Enter 1, 2 or 3."
        )


def save_test_result(
    expected_gesture,
    total_samples,
    correct_predictions,
    accuracy,
    prediction_counts,
):
    file_exists = (
        RESULT_FILE.exists()
    )

    with RESULT_FILE.open(
        mode="a",
        encoding="utf-8",
        newline="",
    ) as file:
        writer = csv.writer(file)

        if not file_exists:
            writer.writerow([
                "test_time",
                "expected_gesture",
                "total_samples",
                "correct_predictions",
                "accuracy_percentage",
                "open_palm_predictions",
                "fist_predictions",
                "point_predictions",
                "other_predictions",
            ])

        writer.writerow([
            datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            ),

            expected_gesture,
            total_samples,
            correct_predictions,
            accuracy,

            prediction_counts.get(
                "OPEN PALM",
                0,
            ),

            prediction_counts.get(
                "FIST",
                0,
            ),

            prediction_counts.get(
                "POINT",
                0,
            ),

            prediction_counts.get(
                "OTHER",
                0,
            ),
        ])


def run_accuracy_test():
    expected_gesture = (
        select_expected_gesture()
    )

    print()
    print(
        "Expected gesture:",
        expected_gesture,
    )

    print(
        "Hold the gesture steadily "
        "in front of the camera."
    )

    print(
        "The test will collect",
        TARGET_SAMPLE_COUNT,
        "samples."
    )

    print(
        "Press Q to cancel the test."
    )

    camera = None
    predictions = []
    last_timestamp_ms = 0

    try:
        camera = open_camera()

        with create_hand_landmarker() as landmarker:
            while (
                len(predictions)
                < TARGET_SAMPLE_COUNT
            ):
                success, frame = camera.read()

                if not success:
                    print(
                        "Camera frame could "
                        "not be read."
                    )

                    break

                frame = cv2.flip(
                    frame,
                    1,
                )

                rgb_frame = cv2.cvtColor(
                    frame,
                    cv2.COLOR_BGR2RGB,
                )

                mp_image = mp.Image(
                    image_format=(
                        mp.ImageFormat.SRGB
                    ),
                    data=rgb_frame,
                )

                current_timestamp_ms = int(
                    time.monotonic()
                    * 1000
                )

                timestamp_ms = max(
                    current_timestamp_ms,
                    last_timestamp_ms + 1,
                )

                last_timestamp_ms = (
                    timestamp_ms
                )

                result = (
                    landmarker.detect_for_video(
                        mp_image,
                        timestamp_ms,
                    )
                )

                predicted_gesture = (
                    "NO HAND"
                )

                if result.hand_landmarks:
                    hand_landmarks = (
                        result.hand_landmarks[0]
                    )

                    draw_hand_landmarks(
                        frame,
                        hand_landmarks,
                    )

                    (
                        predicted_gesture,
                        _
                    ) = recognize_gesture(
                        hand_landmarks
                    )

                    predictions.append(
                        predicted_gesture
                    )

                correct_so_far = (
                    predictions.count(
                        expected_gesture
                    )
                )

                if predictions:
                    current_accuracy = round(
                        correct_so_far
                        / len(predictions)
                        * 100,
                        1,
                    )
                else:
                    current_accuracy = 0

                cv2.putText(
                    frame,
                    (
                        "Expected: "
                        f"{expected_gesture}"
                    ),
                    (30, 45),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.75,
                    (0, 255, 255),
                    2,
                )

                cv2.putText(
                    frame,
                    (
                        "Prediction: "
                        f"{predicted_gesture}"
                    ),
                    (30, 85),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.75,
                    (255, 0, 0),
                    2,
                )

                cv2.putText(
                    frame,
                    (
                        "Samples: "
                        f"{len(predictions)}"
                        f"/{TARGET_SAMPLE_COUNT}"
                    ),
                    (30, 125),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.75,
                    (0, 255, 0),
                    2,
                )

                cv2.putText(
                    frame,
                    (
                        "Accuracy: "
                        f"{current_accuracy}%"
                    ),
                    (30, 165),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.75,
                    (0, 255, 0),
                    2,
                )

                cv2.imshow(
                    "Gesture Accuracy Test",
                    frame,
                )

                pressed_key = (
                    cv2.waitKey(1)
                    & 0xFF
                )

                if pressed_key == ord("q"):
                    print(
                        "Accuracy test cancelled."
                    )

                    return

    except (
        FileNotFoundError,
        RuntimeError,
        ValueError,
        OSError,
    ) as error:
        print(
            "Accuracy test error:",
            error,
        )

        return

    finally:
        if camera is not None:
            camera.release()

        cv2.destroyAllWindows()

    total_samples = len(
        predictions
    )

    if total_samples == 0:
        print(
            "No valid camera samples "
            "were collected."
        )

        return

    correct_predictions = (
        predictions.count(
            expected_gesture
        )
    )

    accuracy = round(
        correct_predictions
        / total_samples
        * 100,
        2,
    )

    prediction_counts = Counter(
        predictions
    )

    save_test_result(
        expected_gesture=expected_gesture,
        total_samples=total_samples,
        correct_predictions=(
            correct_predictions
        ),
        accuracy=accuracy,
        prediction_counts=(
            prediction_counts
        ),
    )

    print()
    print("Test completed.")
    print(
        "Expected gesture:",
        expected_gesture,
    )

    print(
        "Total samples:",
        total_samples,
    )

    print(
        "Correct predictions:",
        correct_predictions,
    )

    print(
        "Accuracy:",
        f"{accuracy}%",
    )

    print(
        "Prediction distribution:",
        dict(prediction_counts),
    )

    print(
        "Result file:",
        RESULT_FILE,
    )


if __name__ == "__main__":
    run_accuracy_test()
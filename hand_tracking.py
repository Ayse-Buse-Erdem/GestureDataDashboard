import time

from collections import deque
from pathlib import Path

import cv2
import mediapipe as mp

from mediapipe.tasks import python
from mediapipe.tasks.python import vision

from dashboard_controller import create_initial_state
from dashboard_controller import update_dashboard_state
from event_logger import log_gesture_event


BASE_DIRECTORY = Path(__file__).resolve().parent

MODEL_PATH = (
    BASE_DIRECTORY
    / "hand_landmarker.task"
)

CAMERA_INDEX = 0

HAND_CONNECTIONS = [
    (0, 1),
    (1, 2),
    (2, 3),
    (3, 4),
    (0, 5),
    (5, 6),
    (6, 7),
    (7, 8),
    (5, 9),
    (9, 10),
    (10, 11),
    (11, 12),
    (9, 13),
    (13, 14),
    (14, 15),
    (15, 16),
    (13, 17),
    (17, 18),
    (18, 19),
    (19, 20),
    (0, 17)
]


def draw_hand_landmarks(
    frame,
    landmarks
):
    height, width, _ = frame.shape
    points = []

    for landmark in landmarks:
        x = int(
            landmark.x * width
        )

        y = int(
            landmark.y * height
        )

        points.append(
            (x, y)
        )

    for start, end in HAND_CONNECTIONS:
        cv2.line(
            frame,
            points[start],
            points[end],
            (0, 255, 0),
            2
        )

    for point in points:
        cv2.circle(
            frame,
            point,
            5,
            (0, 0, 255),
            -1
        )


def recognize_gesture(landmarks):
    fingertip_ids = [
        8,
        12,
        16,
        20
    ]

    middle_joint_ids = [
        6,
        10,
        14,
        18
    ]

    finger_states = []

    for fingertip_id, middle_joint_id in zip(
        fingertip_ids,
        middle_joint_ids
    ):
        fingertip = landmarks[
            fingertip_id
        ]

        middle_joint = landmarks[
            middle_joint_id
        ]

        is_open = (
            fingertip.y
            < middle_joint.y
        )

        finger_states.append(
            is_open
        )

    open_finger_count = finger_states.count(
        True
    )

    if finger_states == [
        True,
        True,
        True,
        True
    ]:
        return (
            "OPEN PALM",
            open_finger_count
        )

    if finger_states == [
        False,
        False,
        False,
        False
    ]:
        return (
            "FIST",
            open_finger_count
        )

    if finger_states == [
        True,
        False,
        False,
        False
    ]:
        return (
            "POINT",
            open_finger_count
        )

    return (
        "OTHER",
        open_finger_count
    )


def create_hand_landmarker():
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            "The MediaPipe model file "
            f"could not be found: {MODEL_PATH}"
        )

    base_options = python.BaseOptions(
        model_asset_path=str(
            MODEL_PATH
        )
    )

    options = vision.HandLandmarkerOptions(
        base_options=base_options,
        running_mode=(
            vision.RunningMode.VIDEO
        ),
        num_hands=1,
        min_hand_detection_confidence=0.7,
        min_hand_presence_confidence=0.7,
        min_tracking_confidence=0.7
    )

    return (
        vision.HandLandmarker
        .create_from_options(options)
    )


def open_camera():
    camera = cv2.VideoCapture(
        CAMERA_INDEX
    )

    if not camera.isOpened():
        camera.release()

        raise RuntimeError(
            "Camera could not be opened. "
            "Check the camera connection and "
            "Windows camera permissions."
        )

    return camera


def run_hand_tracking():
    create_initial_state()

    camera = None

    gesture_history = deque(
        maxlen=10
    )

    stable_gesture = "NO HAND"
    last_logged_gesture = None
    last_dashboard_gesture = "NO HAND"

    failed_frame_count = 0

    try:
        camera = open_camera()

        with create_hand_landmarker() as landmarker:
            print(
                "Gesture detection started."
            )

            print(
                "Press Q to close the camera."
            )

            while True:
                success, frame = camera.read()

                if not success:
                    failed_frame_count += 1

                    print(
                        "Camera frame could not "
                        "be read:",
                        failed_frame_count
                    )

                    if failed_frame_count >= 10:
                        raise RuntimeError(
                            "Camera connection was lost."
                        )

                    continue

                failed_frame_count = 0

                frame = cv2.flip(
                    frame,
                    1
                )

                rgb_frame = cv2.cvtColor(
                    frame,
                    cv2.COLOR_BGR2RGB
                )

                mp_image = mp.Image(
                    image_format=(
                        mp.ImageFormat.SRGB
                    ),
                    data=rgb_frame
                )

                timestamp_ms = int(
                    time.monotonic() * 1000
                )

                result = (
                    landmarker.detect_for_video(
                        mp_image,
                        timestamp_ms
                    )
                )

                gesture_name = "NO HAND"
                open_finger_count = 0

                if result.hand_landmarks:
                    hand_landmarks = (
                        result.hand_landmarks[0]
                    )

                    draw_hand_landmarks(
                        frame,
                        hand_landmarks
                    )

                    (
                        gesture_name,
                        open_finger_count
                    ) = recognize_gesture(
                        hand_landmarks
                    )

                    gesture_history.append(
                        gesture_name
                    )

                    most_common_gesture = max(
                        set(gesture_history),
                        key=gesture_history.count
                    )

                    if (
                        gesture_history.count(
                            most_common_gesture
                        )
                        >= 7
                    ):
                        stable_gesture = (
                            most_common_gesture
                        )

                    if (
                        stable_gesture
                        in [
                            "OPEN PALM",
                            "FIST",
                            "POINT"
                        ]
                        and stable_gesture
                        != last_logged_gesture
                    ):
                        log_gesture_event(
                            stable_gesture,
                            open_finger_count
                        )

                        update_dashboard_state(
                            stable_gesture
                        )

                        last_dashboard_gesture = (
                            stable_gesture
                        )

                        last_logged_gesture = (
                            stable_gesture
                        )

                else:
                    gesture_history.clear()

                    stable_gesture = "NO HAND"
                    last_logged_gesture = None

                    if (
                        last_dashboard_gesture
                        != "NO HAND"
                    ):
                        update_dashboard_state(
                            "NO HAND"
                        )

                        last_dashboard_gesture = (
                            "NO HAND"
                        )

                cv2.putText(
                    frame,
                    f"Current: {gesture_name}",
                    (30, 50),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (255, 0, 0),
                    2
                )

                cv2.putText(
                    frame,
                    f"Stable: {stable_gesture}",
                    (30, 90),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (0, 150, 255),
                    2
                )

                cv2.putText(
                    frame,
                    (
                        "Open fingers: "
                        f"{open_finger_count}"
                    ),
                    (30, 130),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (255, 0, 0),
                    2
                )

                cv2.imshow(
                    "Gesture Detection",
                    frame
                )

                pressed_key = (
                    cv2.waitKey(1)
                    & 0xFF
                )

                if pressed_key == ord("q"):
                    print(
                        "Gesture detection stopped."
                    )

                    break

    except FileNotFoundError as error:
        print(
            "Model file error:",
            error
        )

    except RuntimeError as error:
        print(
            "Camera error:",
            error
        )

    except (
        ValueError,
        OSError
    ) as error:
        print(
            "Gesture detection error:",
            error
        )

    finally:
        if camera is not None:
            camera.release()

        cv2.destroyAllWindows()


if __name__ == "__main__":
    run_hand_tracking()
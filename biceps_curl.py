import cv2
import mediapipe as mp
import numpy as np

EXTENDED_ANGLE = 150   # arm is down
CURLED_ANGLE = 50      # arm is up
MIN_VIS = 0.3


class BicepsCurlAPI:

    def __init__(self):
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
            model_complexity=1,
        )
        self.reset()

    def __del__(self):
        self.pose.close()

    def reset(self):
        self.rep_count = 0
        self.stage = "DOWN"
        self.frame_count = 0

    # ------------------------------------------------------------------
    @staticmethod
    def calculate_angle(a, b, c):
        a, b, c = np.array(a), np.array(b), np.array(c)
        radians = (
            np.arctan2(c[1] - b[1], c[0] - b[0])
            - np.arctan2(a[1] - b[1], a[0] - b[0])
        )
        angle = np.abs(np.degrees(radians))
        return 360 - angle if angle > 180 else angle

    # ------------------------------------------------------------------
    def analyze_frame(self, image_bytes: bytes) -> dict:

        # decode
        np_arr = np.frombuffer(image_bytes, np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if frame is None:
            return {"error": "Invalid frame"}

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.pose.process(rgb)

        if not results.pose_landmarks:
            return {"error": "No pose detected"}

        landmarks = results.pose_landmarks.landmark
        self.frame_count += 1
        mp_lm = self.mp_pose.PoseLandmark

        # visibility guard
        key_indices = [
            mp_lm.LEFT_SHOULDER.value, mp_lm.LEFT_ELBOW.value, mp_lm.LEFT_WRIST.value,
            mp_lm.RIGHT_SHOULDER.value, mp_lm.RIGHT_ELBOW.value, mp_lm.RIGHT_WRIST.value,
        ]
        low_vis = [i for i in key_indices if landmarks[i].visibility < MIN_VIS]
        if low_vis:
            return {
                "reps": self.rep_count,
                "stage": self.stage,
                "left_angle": None,
                "right_angle": None,
                "feedback": ["Move into frame"],
                "frame": self.frame_count,
            }

        # landmarks
        def p(i):
            return [landmarks[i].x, landmarks[i].y]

        left_angle = self.calculate_angle(
            p(mp_lm.LEFT_SHOULDER.value),
            p(mp_lm.LEFT_ELBOW.value),
            p(mp_lm.LEFT_WRIST.value),
        )
        right_angle = self.calculate_angle(
            p(mp_lm.RIGHT_SHOULDER.value),
            p(mp_lm.RIGHT_ELBOW.value),
            p(mp_lm.RIGHT_WRIST.value),
        )

        # counting logic — use the most-curled arm so either arm triggers the count
        best_angle = min(left_angle, right_angle)

        if best_angle > EXTENDED_ANGLE:
            if self.stage == "UP":  # coming down -> count rep
                self.rep_count += 1
            self.stage = "DOWN"
        elif best_angle < CURLED_ANGLE:
            self.stage = "UP"

        # feedback
        feedback = []
        if self.stage == "DOWN":
            feedback.append("Curl up!")
        elif self.stage == "UP":
            feedback.append("Lower down!")

        return {
            "reps": self.rep_count,
            "stage": self.stage,
            "left_angle": round(left_angle),
            "right_angle": round(right_angle),
            "feedback": feedback,
            "frame": self.frame_count,
        }

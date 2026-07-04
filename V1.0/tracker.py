import os
import time
import math
import logging

import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import pyautogui

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


class HandTrackerError(Exception):
    print(Exception)


class HandTracker:

    PINCH_THRESHOLD = 0.04
    THUMB_CURL_THRESHOLD = 0.05
    FRAME_WIDTH = 640
    FRAME_HEIGHT = 480
    MIN_HAND_DETECTION_CONFIDENCE = 0.6
    MIN_HAND_PRESENCE_CONFIDENCE = 0.6
    MODEL_FILENAME = "hand_landmarker.task"

    def __init__(self, smoothingFactor: float = 0.2, cameraIndex: int = 0,
                 altF4Enabled: bool = True, showCameraWindow: bool = True):
        
        pyautogui.FAILSAFE = False
        pyautogui.PAUSE = 0
        pyautogui.MINIMUM_DURATION = 0

        self.camera_index: int = cameraIndex
        self.smoothing_factor: float = smoothingFactor
        self.altF4_is_blocked: bool = altF4Enabled
        self.ShowCameraWindow: bool = showCameraWindow

        self.screen_width, self.screen_height = pyautogui.size()

        self.prev_mouse_x, self.prev_mouse_y = None, None

        self.latest_hands_data = []
        self.latest_handedness_data = []

        self.is_listening = False
        self.mouse_mode_active = False

        self._trigger_flags = {
            "left_index": False,
            "left_middle": False,
            "left_ring": False,
            "right_index": False,
            "right_middle": False,
            "right_ring": False,
            "right_pinky": False,
        }
        self.toggle_lock = False
        self.mouse_is_down = False

        self.IsRunning: bool = True

    def get_distance(self, p1, p2) -> float:
        """Berechnet den euklidischen Abstand im 3D-Raum zwischen zwei Landmarks."""
        return math.sqrt((p1.x - p2.x) ** 2 + (p1.y - p2.y) ** 2 + (p1.z - p2.z) ** 2)

    def _trigger_once(self, flag_name: str, distance: float, action) -> bool:
        """
        Fuehrt `action` genau einmal aus, solange der Pinch aktiv gehalten wird
        (Debounce), statt bei jedem Frame neu auszuloesen.
        Gibt True zurueck, wenn die Geste in diesem Frame aktiv ist.
        """
        active = distance < self.PINCH_THRESHOLD
        if active:
            if not self._trigger_flags[flag_name]:
                self._trigger_flags[flag_name] = True
                action()
        else:
            self._trigger_flags[flag_name] = False
        return active

    def _reset_all_triggers(self):
        for key in self._trigger_flags:
            self._trigger_flags[key] = False

    def _on_result(self, result: vision.HandLandmarkerResult, output_image: mp.Image, timestamp_ms: int):
        if result.hand_landmarks and result.handedness:
            self.latest_hands_data = result.hand_landmarks
            self.latest_handedness_data = [h[0].category_name for h in result.handedness]
        else:
            self.latest_hands_data = []
            self.latest_handedness_data = []

    def _build_detector(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        model_path = os.path.join(script_dir, self.MODEL_FILENAME)

        if not os.path.isfile(model_path):
            raise HandTrackerError(
                f"Modell-Datei nicht gefunden: {model_path}. "
                f"Bitte '{self.MODEL_FILENAME}' neben main.py ablegen."
            )

        base_options = python.BaseOptions(model_asset_path=model_path)
        options = vision.HandLandmarkerOptions(
            base_options=base_options,
            num_hands=2,
            running_mode=vision.RunningMode.LIVE_STREAM,
            min_hand_detection_confidence=self.MIN_HAND_DETECTION_CONFIDENCE,
            min_hand_presence_confidence=self.MIN_HAND_PRESENCE_CONFIDENCE,
            result_callback=self._on_result,
        )
        return vision.HandLandmarker.create_from_options(options)

    def _open_camera(self):
        cap = cv2.VideoCapture(self.camera_index)
        if not cap.isOpened():
            raise HandTrackerError(f"Kamera mit Index {self.camera_index} konnte nicht geoeffnet werden.")
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.FRAME_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.FRAME_HEIGHT)
        return cap

    def start(self):
        try:
            detector_cm = self._build_detector()
        except HandTrackerError as e:
            logger.error(str(e))
            self.IsRunning = False
            return

        try:
            with detector_cm as detector:
                try:
                    cap = self._open_camera()
                except HandTrackerError as e:
                    logger.error(str(e))
                    self.IsRunning = False
                    return

                logger.info(
                    "Hand-Tracker gestartet (Kamera %s). Standardmaessig STUMM.",
                    self.camera_index,
                )

                try:
                    while cap.isOpened() and self.IsRunning:
                        success, frame = cap.read()
                        if not success:
                            logger.warning("Konnte kein Kamerabild lesen, breche Loop ab.")
                            break

                        frame = self._process_frame(frame, detector)

                        if self.ShowCameraWindow:
                            cv2.imshow("Aktivierungs-Shortcut Manager", frame)
                        if cv2.waitKey(1) & 0xFF == ord('q'):
                            self.IsRunning = False
                finally:
                    cap.release()
                    cv2.destroyAllWindows()
        except Exception:
            logger.exception("Unerwarteter Fehler im Hand-Tracker-Loop.")
            self.IsRunning = False

    def _process_frame(self, frame, detector):
        frame = cv2.flip(frame, 1)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

        timestamp = int(time.time() * 1000)
        detector.detect_async(mp_image, timestamp)

        current_hands = list(self.latest_hands_data)
        current_sides = list(self.latest_handedness_data)

        any_hand_doing_toggle = False
        right_index_pinch_active_this_frame = False

        for hand, side in zip(current_hands, current_sides):
            if self.is_listening and self.mouse_mode_active and side == "Left":
                thumb_tip, index_tip = hand[4], hand[8]
                if self.get_distance(thumb_tip, index_tip) < self.PINCH_THRESHOLD:
                    right_index_pinch_active_this_frame = True

        for hand, side in zip(current_hands, current_sides):
            toggled = self._handle_hand(hand, side, right_index_pinch_active_this_frame)
            any_hand_doing_toggle = any_hand_doing_toggle or toggled

        self._handle_drawing_release(right_index_pinch_active_this_frame)

        if not any_hand_doing_toggle:
            self.toggle_lock = False

        if not self.is_listening:
            self._reset_all_triggers()
            self.prev_mouse_x, self.prev_mouse_y = None, None
            if self.mouse_is_down:
                pyautogui.mouseUp()
                self.mouse_is_down = False

        self._draw_overlay(frame)
        return frame

    def _handle_hand(self, hand, side, right_index_pinch_active_this_frame) -> bool:
        thumb_tip, index_tip = hand[4], hand[8]
        middle_tip, ring_tip, pinky_tip = hand[12], hand[16], hand[20]

        index_curled = index_tip.y > hand[6].y
        middle_curled = middle_tip.y > hand[10].y
        ring_curled = ring_tip.y > hand[14].y
        pinky_curled = pinky_tip.y > hand[18].y
        thumb_curled = abs(thumb_tip.x - hand[5].x) < self.THUMB_CURL_THRESHOLD

        did_toggle = False

        # Globaler Aktivierungs-Toggle (nur linke Hand)
        if side == "Left":
            is_toggle_gesture = (not thumb_curled) and index_curled and middle_curled and ring_curled and (not pinky_curled)
            if is_toggle_gesture:
                did_toggle = True
                if not self.toggle_lock:
                    self.is_listening = not self.is_listening
                    self.toggle_lock = True
                    logger.info("Zuhoer-Modus geaendert! Aktiv: %s", self.is_listening)

        if not self.is_listening:
            return did_toggle

        if self.mouse_mode_active:
            self._handle_drawing_mode(side, thumb_tip, index_tip, middle_tip, pinky_tip,
                                       right_index_pinch_active_this_frame)
        else:
            self.prev_mouse_x, self.prev_mouse_y = None, None
            self._handle_shortcut_mode(side, thumb_tip, index_tip, middle_tip, ring_tip)

        return did_toggle

    def _handle_drawing_mode(self, side, thumb_tip, index_tip, middle_tip, pinky_tip,
                              right_index_pinch_active_this_frame):
        if side != "Left":
            return

        if not right_index_pinch_active_this_frame:
            right_pinky_dist = self.get_distance(thumb_tip, pinky_tip)

            def _exit_drawing_mode():
                self.mouse_mode_active = False
                if self.mouse_is_down:
                    pyautogui.mouseUp()
                    self.mouse_is_down = False
                logger.info("Zeichen-Modus DEAKTIVIERT. Zurueck im Normal-Modus.")

            if self._trigger_once("right_pinky", right_pinky_dist, _exit_drawing_mode):
                return
        else:
            self._trigger_flags["right_pinky"] = False

        right_middle_dist = self.get_distance(thumb_tip, middle_tip)
        self._trigger_once("right_middle", right_middle_dist,
                            lambda: (pyautogui.click(), logger.info("Einfacher Klick ausgefuehrt."))[0])

        target_x = int(index_tip.x * self.screen_width)
        target_y = int(index_tip.y * self.screen_height)

        if self.prev_mouse_x is None or self.prev_mouse_y is None:
            self.prev_mouse_x, self.prev_mouse_y = target_x, target_y

        current_mouse_x = int(self.prev_mouse_x + (target_x - self.prev_mouse_x) * self.smoothing_factor)
        current_mouse_y = int(self.prev_mouse_y + (target_y - self.prev_mouse_y) * self.smoothing_factor)

        if right_index_pinch_active_this_frame:
            if not self.mouse_is_down:
                pyautogui.moveTo(current_mouse_x, current_mouse_y)
                pyautogui.mouseDown()
                self.mouse_is_down = True
                logger.info("Zeichnen aktiv (Klick gehalten)...")
            else:
                pyautogui.dragTo(current_mouse_x, current_mouse_y, button='left')
        else:
            pyautogui.moveTo(current_mouse_x, current_mouse_y)

        self.prev_mouse_x, self.prev_mouse_y = current_mouse_x, current_mouse_y

    def _handle_shortcut_mode(self, side, thumb_tip, index_tip, middle_tip, ring_tip):
        if side == "Left":
            left_index_dist = self.get_distance(thumb_tip, index_tip)
            self._trigger_once("left_index", left_index_dist,
                                lambda: pyautogui.hotkey('win', 'ctrl', 'left'))

            left_middle_dist = self.get_distance(thumb_tip, middle_tip)
            self._trigger_once("left_middle", left_middle_dist,
                                lambda: pyautogui.hotkey('win', 'ctrl', 'right'))

            left_ring_dist = self.get_distance(thumb_tip, ring_tip)

            def _activate_drawing_mode():
                self.mouse_mode_active = True
                logger.info("Zeichen-Modus AKTIVIERT. Alle normalen Shortcuts blockiert.")

            self._trigger_once("left_ring", left_ring_dist, _activate_drawing_mode)

        elif side == "Right":
            right_index_dist = self.get_distance(thumb_tip, index_tip)
            if not self.altF4_is_blocked:
                self._trigger_once("right_index", right_index_dist,
                                    lambda: pyautogui.hotkey('alt', 'f4'))
            else:
                self._trigger_flags["right_index"] = False

            right_middle_dist = self.get_distance(thumb_tip, middle_tip)
            self._trigger_once("right_middle", right_middle_dist,
                                lambda: pyautogui.hotkey('win', 'tab'))

            right_ring_dist = self.get_distance(thumb_tip, ring_tip)
            self._trigger_once("right_ring", right_ring_dist,
                                lambda: pyautogui.hotkey('win', 'd'))

    def _handle_drawing_release(self, right_index_pinch_active_this_frame):
        if self.mouse_mode_active and not right_index_pinch_active_this_frame and self.mouse_is_down:
            pyautogui.mouseUp()
            self.mouse_is_down = False
            logger.info("Zeichnen beendet (Klick losgelassen).")

    def _draw_overlay(self, frame):
        if not self.is_listening:
            cv2.putText(frame, "MODUS: STUMM (Gesten gesperrt)", (50, 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        elif self.mouse_mode_active:
            cv2.putText(frame, "MODUS: ZEICHNEN / MAUS (Aktiv)", (50, 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 255), 2)
            if self.mouse_is_down:
                cv2.putText(frame, "MAUS: ZEICHNEN AKTIV", (50, 100),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
        else:
            cv2.putText(frame, "MODUS: NORMAL (Shortcuts Aktiv)", (50, 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)


if __name__ == "__main__":
    tracker = HandTracker()
    tracker.start()

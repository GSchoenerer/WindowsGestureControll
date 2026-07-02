import os
import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import pyautogui
import time
import math

class HandTracker:
    def __init__(self,smoothingFactor=0.2,cameraIndex=1,altF4Enabled=True):
        """
        Initialisiert den HandTracker.
        :param camera_index: Der Index der zu verwendenden Kamera (Standard: 1)
        :param smoothing_factor: Faktor zur Glättung der Mausbewegung gegen Zittern (Standard: 0.2)
        """
        # PyAutoGUI-Sicherheitsnetz deaktivieren
        pyautogui.FAILSAFE = False
        pyautogui.PAUSE = 0
        pyautogui.MINIMUM_DURATION = 0

        # Parameter aus dem Konstruktor
        self.camera_index = cameraIndex
        self.smoothing_factor = smoothingFactor
        self.altF4_is_blocked = altF4Enabled

        # Bildschirmgröße für die Maussteuerung ermitteln
        self.screen_width, self.screen_height = pyautogui.size()

        # FINE-TUNING PARAMETER GEGEN DAS ZITTERN (JITTER)
        self.prev_mouse_x, self.prev_mouse_y = None, None

        # Globale Variablen für den asynchronen Daten-Austausch (Unterstützt beide Hände)
        self.latest_hands_data = []
        self.latest_handedness_data = []

        # Status-Variablen für das System
        self.is_listening = False            # Der globale Aktivierungsmodus (True = aktiv, False = stumm)
        self.mouse_mode_active = False       # Der Zeichen/Mausmodus (True = aktiv, False = Normaler Modus)

        # Sperren (Debounce), um Mehrfachauslösungen bei gehaltenem Pinch zu verhindern
        self.toggle_lock = False
        self.left_index_triggered = False
        self.left_middle_triggered = False
        self.left_ring_triggered = False

        self.right_index_triggered = False
        self.right_middle_triggered = False
        self.right_ring_triggered = False
        self.right_pinky_triggered = False

        # Status für das Halten der linken Maustaste im Zeichenmodus
        self.mouse_is_down = False

        # SetUp variables
        self.altF4_is_blocked = False

        self.IsRunning : bool = True

    # Mathematische Hilfsfunktion: Berechnet den Abstand im 3D-Raum
    def get_distance(self, p1, p2):
        return math.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2 + (p1.z - p2.z)**2)

    # MEDIAPIPE CALLBACK FUNKTION (Verarbeitet mehrere Hände parallel)
    def _print_result(self, result: vision.HandLandmarkerResult, output_image: mp.Image, timestamp_ms: int):
        if result.hand_landmarks and result.handedness:
            self.latest_hands_data = result.hand_landmarks
            self.latest_handedness_data = [h[0].category_name for h in result.handedness]
        else:
            self.latest_hands_data = []
            self.latest_handedness_data = []

    # HAUPTSCHLEIFE STARTEN
    def start(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        model_path = os.path.join(script_dir, "hand_landmarker.task")

        base_options = python.BaseOptions(model_asset_path=model_path)
        options = vision.HandLandmarkerOptions(
            base_options=base_options,
            num_hands=2,                                  # Erkennt linke und rechte Hand parallel
            running_mode=vision.RunningMode.LIVE_STREAM,
            min_hand_detection_confidence=0.6,            # Höhere Grundstabilität beim Finden der Hand
            min_hand_presence_confidence=0.6,             # Verhindert, dass die Hand kurz "verschwindet"
            result_callback=self._print_result
        )

        with vision.HandLandmarker.create_from_options(options) as detector:
            cap = cv2.VideoCapture(self.camera_index)     # Kamera aus Konstruktor-Argument
            
            # PERFORMANCE-BOOST: Auflösung auf 640x480 drosseln für maximale FPS und weniger CPU-Last!
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            
            print(f"Multi-Shortcut & Mouse Manager gestartet (Kamera {self.camera_index}). Standardmäßig STUMM.")

            while cap.isOpened() and self.IsRunning:
                success, frame = cap.read()
                if not success: break

                frame = cv2.flip(frame, 1)
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

                timestamp = int(time.time() * 1000)
                detector.detect_async(mp_image, timestamp)

                # Thread-sichere Schnappschüsse der aktuellen Frame-Daten
                current_hands = list(self.latest_hands_data)
                current_sides = list(self.latest_handedness_data)

                any_hand_doing_toggle = False
                right_index_pinch_active_this_frame = False

                # 1. DURCHGANG: Vorab prüfen, ob der Zeichen-Pinch aktiv ist
                for hand, side in zip(current_hands, current_sides):
                    if self.is_listening and self.mouse_mode_active and side == "Left":
                        thumb_tip = hand[4]
                        index_tip = hand[8]
                        if self.get_distance(thumb_tip, index_tip) < 0.04:
                            right_index_pinch_active_this_frame = True

                # 2. DURCHGANG: Eigentliche Gestenverarbeitung
                for hand, side in zip(current_hands, current_sides):
                    thumb_tip = hand[4]
                    index_tip = hand[8]
                    middle_tip = hand[12]
                    ring_tip = hand[16]
                    pinky_tip = hand[20]

                    # Anatomischer Zustand der Finger (Eingeknickt oder gestreckt)
                    index_curled = index_tip.y > hand[6].y
                    middle_curled = middle_tip.y > hand[10].y
                    ring_curled = ring_tip.y > hand[14].y
                    pinky_curled = pinky_tip.y > hand[18].y
                    thumb_curled = abs(thumb_tip.x - hand[5].x) < 0.05

                    # ==================================================================
                    # GLOBALER AKTIVIERUNGS-TOGGLE (NUR LINKE HAND)
                    # ==================================================================
                    if side == "Left":
                        is_toggle_gesture = (not thumb_curled) and index_curled and middle_curled and ring_curled and (not pinky_curled)
                        
                        if is_toggle_gesture:
                            any_hand_doing_toggle = True
                            if not self.toggle_lock:
                                self.is_listening = not self.is_listening
                                self.toggle_lock = True
                                print(f"[SYSTEM] Zuhör-Modus geändert! Aktiv: {self.is_listening}")

                    # ==================================================================
                    # GESTEN-VERARBEITUNG (NUR AKTIV WENN IS_LISTENING = TRUE)
                    # ==================================================================
                    if self.is_listening:
                        
                        # --------------------------------------------------------------
                        # MODUS A: ZEICHEN / MAUS-MODUS (DRAWING MODE)
                        # --------------------------------------------------------------
                        if self.mouse_mode_active:
                            
                            if side == "Right":
                                pass

                            elif side == "Left":
                                # Geste 1: Pinch Daumen + KLEINER FINGER -> ZURÜCK IN DEN NORMAL MODE
                                if not right_index_pinch_active_this_frame:
                                    right_pinky_dist = self.get_distance(thumb_tip, pinky_tip)
                                    if right_pinky_dist < 0.04:
                                        if not self.right_pinky_triggered:
                                            self.right_pinky_triggered = True
                                            self.mouse_mode_active = False
                                            if self.mouse_is_down:
                                                pyautogui.mouseUp()
                                                self.mouse_is_down = False
                                            print("[SYSTEM] Zeichen-Modus DEAKTIVIERT. Zurück im Normal Mode.")
                                        continue
                                    else:
                                        self.right_pinky_triggered = False
                                else:
                                    self.right_pinky_triggered = False

                                # Geste 2: Pinch Daumen + Mittelfinger -> EINFACHER MAUSKLICK
                                right_middle_dist = self.get_distance(thumb_tip, middle_tip)
                                if right_middle_dist < 0.04:
                                    if not self.right_middle_triggered:
                                        self.right_middle_triggered = True
                                        pyautogui.click()
                                        print("[MAUS] Einfacher Klick ausgeführt.")
                                else:
                                    self.right_middle_triggered = False

                                # Zielkoordinaten berechnen
                                target_x = int(index_tip.x * self.screen_width)
                                target_y = int(index_tip.y * self.screen_height)
                                
                                if self.prev_mouse_x is None or self.prev_mouse_y is None:
                                        self.prev_mouse_x, self.prev_mouse_y = target_x, target_y
                                
                                # Glättung anwenden (Nutzt SMOOTHING_FACTOR aus Konstruktor)
                                current_mouse_x = int(self.prev_mouse_x + (target_x - self.prev_mouse_x) * self.smoothing_factor)
                                current_mouse_y = int(self.prev_mouse_y + (target_y - self.prev_mouse_y) * self.smoothing_factor)
                                
                                # MAUSBEWEGUNG / ZEICHNEN EXEKUTIEREN
                                if right_index_pinch_active_this_frame:
                                    if not self.mouse_is_down:
                                        pyautogui.moveTo(current_mouse_x, current_mouse_y)
                                        pyautogui.mouseDown()
                                        self.mouse_is_down = True
                                        print("[MAUS] Zeichnen aktiv (Klick gehalten)...")
                                    else:
                                        pyautogui.dragTo(current_mouse_x, current_mouse_y, button='left')
                                else:
                                    pyautogui.moveTo(current_mouse_x, current_mouse_y)

                                self.prev_mouse_x, self.prev_mouse_y = current_mouse_x, current_mouse_y

                        # --------------------------------------------------------------
                        # MODUS B: NORMALER SHORTCUT-MODUS
                        # --------------------------------------------------------------
                        else:
                            self.prev_mouse_x, self.prev_mouse_y = None, None
                            
                            if side == "Left":
                                left_index_dist = self.get_distance(thumb_tip, index_tip)
                                if left_index_dist < 0.04:
                                    if not self.left_index_triggered:
                                        self.left_index_triggered = True
                                        pyautogui.hotkey('win', 'ctrl', 'left')
                                else:
                                    self.left_index_triggered = False

                                left_middle_dist = self.get_distance(thumb_tip, middle_tip)
                                if left_middle_dist < 0.04:
                                    if not self.left_middle_triggered:
                                        self.left_middle_triggered = True
                                        pyautogui.hotkey('win', 'ctrl', 'right')
                                else:
                                    self.left_middle_triggered = False

                                left_ring_dist = self.get_distance(thumb_tip, ring_tip)
                                if left_ring_dist < 0.04:
                                    if not self.left_ring_triggered:
                                        self.left_ring_triggered = True
                                        self.mouse_mode_active = True
                                        print("[SYSTEM] Zeichen-Modus AKTIVIERT. Alle normalen Shortcuts blockiert.")
                                else:
                                    self.left_ring_triggered = False

                            elif side == "Right":
                                right_index_dist = self.get_distance(thumb_tip, index_tip)
                                if right_index_dist < 0.04 and not self.altF4_is_blocked:
                                    if not self.right_index_triggered:
                                        self.right_index_triggered = True
                                        pyautogui.hotkey('alt', 'f4')
                                else:
                                    self.right_index_triggered = False

                                right_middle_dist = self.get_distance(thumb_tip, middle_tip)
                                if right_middle_dist < 0.04:
                                    if not self.right_middle_triggered:
                                        self.right_middle_triggered = True
                                        pyautogui.hotkey('win', 'tab')
                                else:
                                    self.right_middle_triggered = False

                                right_ring_dist = self.get_distance(thumb_tip, ring_tip)
                                if right_ring_dist < 0.04:
                                    if not self.right_ring_triggered:
                                        self.right_ring_triggered = True
                                        pyautogui.hotkey('win', 'd')
                                else:
                                    self.right_ring_triggered = False

                # --- UNTERSTÜTZENDE SCHLEIFEN-LOGIK ---
                if self.mouse_mode_active and not right_index_pinch_active_this_frame and self.mouse_is_down:
                    pyautogui.mouseUp()
                    self.mouse_is_down = False
                    print("[MAUS] Zeichnen beendet (Klick losgelassen).")

                if not any_hand_doing_toggle:
                    self.toggle_lock = False

                if not self.is_listening:
                    self.left_index_triggered = False
                    self.left_middle_triggered = False
                    self.left_ring_triggered = False
                    self.right_index_triggered = False
                    self.right_middle_triggered = False
                    self.right_ring_triggered = False
                    self.right_pinky_triggered = False
                    self.prev_mouse_x, self.prev_mouse_y = None, None
                    if self.mouse_is_down:
                        pyautogui.mouseUp()
                        self.mouse_is_down = False

                # --- TEXT-FEEDBACK AUF DEM MONITOR ---
                if not self.is_listening:
                    cv2.putText(frame, "MODUS: STUMM (Gesten gesperrt)", (50, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                else:
                    if self.mouse_mode_active:
                        cv2.putText(frame, "MODUS: ZEICHNEN / MAUS (Aktiv)", (50, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 255), 2)
                        if self.mouse_is_down:
                            cv2.putText(frame, "MAUS: ZEICHNEN AKTIV", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
                    else:
                        cv2.putText(frame, "MODUS: NORMAL (Shortcuts Aktiv)", (50, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

                cv2.imshow("Aktivierungs-Shortcut Manager", frame)

            cap.release()
            cv2.destroyAllWindows()


import os
import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import pyautogui
import time
import math

# PyAutoGUI-Sicherheitsnetz deaktivieren
pyautogui.FAILSAFE = False
# Verzögerungen auf Null setzen für absolut flüssiges Zeichnen in Paint
pyautogui.PAUSE = 0
pyautogui.MINIMUM_DURATION = 0

# Bildschirmgröße für die Maussteuerung ermitteln
screen_width, screen_height = pyautogui.size()

# FINE-TUNING PARAMETER GEGEN DAS ZITTERN (JITTER)
SMOOTHING_FACTOR = 0.20
prev_mouse_x, prev_mouse_y = None, None

# Globale Variablen für den asynchronen Daten-Austausch (Unterstützt beide Hände)
latest_hands_data = []
latest_handedness_data = []

# Status-Variablen für das System
is_listening = False            # Der globale Aktivierungsmodus (True = aktiv, False = stumm)
mouse_mode_active = False       # Der Zeichen/Mausmodus (True = aktiv, False = Normaler Modus)

# Sperren (Debounce), um Mehrfachauslösungen bei gehaltenem Pinch zu verhindern
toggle_lock = False
left_index_triggered = False
left_middle_triggered = False
left_ring_triggered = False

right_index_triggered = False
right_middle_triggered = False
right_ring_triggered = False
right_pinky_triggered = False

# Status für das Halten der linken Maustaste im Zeichenmodus
mouse_is_down = False

# Mathematische Hilfsfunktion: Berechnet den Abstand im 3D-Raum
def get_distance(p1, p2):
    return math.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2 + (p1.z - p2.z)**2)

# ==============================================================================
# MEDIAPIPE CALLBACK FUNKTION (Verarbeitet mehrere Hände parallel)
# ==============================================================================
def print_result(result: vision.HandLandmarkerResult, output_image: mp.Image, timestamp_ms: int):
    global latest_hands_data, latest_handedness_data
    if result.hand_landmarks and result.handedness:
        latest_hands_data = result.hand_landmarks
        latest_handedness_data = [h[0].category_name for h in result.handedness]
    else:
        latest_hands_data = []
        latest_handedness_data = []

# ==============================================================================
# MEDIAPIPE INITIATION (Jetzt optimiert für stabilere Erkennung)
# ==============================================================================
script_dir = os.path.dirname(os.path.abspath(__file__))
model_path = os.path.join(script_dir, "hand_landmarker.task")

base_options = python.BaseOptions(model_asset_path=model_path)
options = vision.HandLandmarkerOptions(
    base_options=base_options,
    num_hands=2,                                  # Erkennt linke und rechte Hand parallel
    running_mode=vision.RunningMode.LIVE_STREAM,
    min_hand_detection_confidence=0.6,            # Höhere Grundstabilität beim Finden der Hand
    min_hand_presence_confidence=0.6,             # Verhindert, dass die Hand kurz "verschwindet"
    result_callback=print_result
)

# ==============================================================================
# HAUPTSCHLEIFE
# ==============================================================================
with vision.HandLandmarker.create_from_options(options) as detector:
    cap = cv2.VideoCapture(1)                     # Deine Kamera auf Index 1
    
    # PERFORMANCE-BOOST: Auflösung auf 640x480 drosseln für maximale FPS und weniger CPU-Last!
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    print("Multi-Shortcut & Mouse Manager gestartet. Standardmäßig STUMM.")

    while cap.isOpened():
        success, frame = cap.read()
        if not success: break

        frame = cv2.flip(frame, 1)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

        timestamp = int(time.time() * 1000)
        detector.detect_async(mp_image, timestamp)

        # Thread-sichere Schnappschüsse der aktuellen Frame-Daten
        current_hands = list(latest_hands_data)
        current_sides = list(latest_handedness_data)

        any_hand_doing_toggle = False
        right_index_pinch_active_this_frame = False

        # 1. DURCHGANG: Vorab prüfen, ob der Zeichen-Pinch aktiv ist
        # Hier nutzen wir nun eine leicht erhöhte Toleranz, damit der Strich nicht abreißt!
        for hand, side in zip(current_hands, current_sides):
            if is_listening and mouse_mode_active and side == "Left":
                thumb_tip = hand[4]
                index_tip = hand[8]
                if get_distance(thumb_tip, index_tip) < 0.04:
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
                    if not toggle_lock:
                        is_listening = not is_listening
                        toggle_lock = True
                        print(f"[SYSTEM] Zuhör-Modus geändert! Aktiv: {is_listening}")

            # ==================================================================
            # GESTEN-VERARBEITUNG (NUR AKTIV WENN IS_LISTENING = TRUE)
            # ==================================================================
            if is_listening:
                
                # --------------------------------------------------------------
                # MODUS A: ZEICHEN / MAUS-MODUS (DRAWING MODE)
                # --------------------------------------------------------------
                if mouse_mode_active:
                    
                    if side == "Right":
                        pass

                    elif side == "Left":
                        # Geste 1: Pinch Daumen + KLEINER FINGER -> ZURÜCK IN DEN NORMAL MODE
                        if not right_index_pinch_active_this_frame:
                            right_pinky_dist = get_distance(thumb_tip, pinky_tip)
                            if right_pinky_dist < 0.04:
                                if not right_pinky_triggered:
                                    right_pinky_triggered = True
                                    mouse_mode_active = False
                                    if mouse_is_down:
                                        pyautogui.mouseUp()
                                        mouse_is_down = False
                                    print("[SYSTEM] Zeichen-Modus DEAKTIVIERT. Zurück im Normal Mode.")
                                continue
                            else:
                                right_pinky_triggered = False
                        else:
                            right_pinky_triggered = False

                        # Geste 2: Pinch Daumen + Mittelfinger -> EINFACHER MAUSKLICK (Bleibt bei 0.04 für Präzision)
                        right_middle_dist = get_distance(thumb_tip, middle_tip)
                        if right_middle_dist < 0.04:
                            if not right_middle_triggered:
                                right_middle_triggered = True
                                pyautogui.click()
                                print("[MAUS] Einfacher Klick ausgeführt.")
                        else:
                            right_middle_triggered = False

                        # Zielkoordinaten berechnen
                        target_x = int(index_tip.x * screen_width)
                        target_y = int(index_tip.y * screen_height)
                        
                        if prev_mouse_x is None or prev_mouse_y is None:
                            prev_mouse_x, prev_mouse_y = target_x, target_y
                        
                        # Glättung anwenden
                        current_mouse_x = int(prev_mouse_x + (target_x - prev_mouse_x) * SMOOTHING_FACTOR)
                        current_mouse_y = int(prev_mouse_y + (target_y - prev_mouse_y) * SMOOTHING_FACTOR)
                        
                        # MAUSBEWEGUNG / ZEICHNEN EXEKUTIEREN
                        if right_index_pinch_active_this_frame:
                            if not mouse_is_down:
                                pyautogui.moveTo(current_mouse_x, current_mouse_y)
                                pyautogui.mouseDown()
                                mouse_is_down = True
                                print("[MAUS] Zeichnen aktiv (Klick gehalten)...")
                            else:
                                pyautogui.dragTo(current_mouse_x, current_mouse_y, button='left')
                        else:
                            pyautogui.moveTo(current_mouse_x, current_mouse_y)

                        prev_mouse_x, prev_mouse_y = current_mouse_x, current_mouse_y

                # --------------------------------------------------------------
                # MODUS B: NORMALER SHORTCUT-MODUS
                # --------------------------------------------------------------
                else:
                    prev_mouse_x, prev_mouse_y = None, None
                    
                    if side == "Left":
                        left_index_dist = get_distance(thumb_tip, index_tip)
                        if left_index_dist < 0.04:
                            if not left_index_triggered:
                                left_index_triggered = True
                                pyautogui.hotkey('win', 'ctrl', 'left')
                        else:
                            left_index_triggered = False

                        left_middle_dist = get_distance(thumb_tip, middle_tip)
                        if left_middle_dist < 0.04:
                            if not left_middle_triggered:
                                left_middle_triggered = True
                                pyautogui.hotkey('win', 'ctrl', 'right')
                        else:
                            left_middle_triggered = False

                        left_ring_dist = get_distance(thumb_tip, ring_tip)
                        if left_ring_dist < 0.04:
                            if not left_ring_triggered:
                                left_ring_triggered = True
                                mouse_mode_active = True
                                print("[SYSTEM] Zeichen-Modus AKTIVIERT. Alle normalen Shortcuts blockiert.")
                        else:
                            left_ring_triggered = False

                    elif side == "Right":
                        right_index_dist = get_distance(thumb_tip, index_tip)
                        if right_index_dist < 0.04:
                            if not right_index_triggered:
                                right_index_triggered = True
                                pyautogui.hotkey('alt', 'f4')
                        else:
                            right_index_triggered = False

                        right_middle_dist = get_distance(thumb_tip, middle_tip)
                        if right_middle_dist < 0.04:
                            if not right_middle_triggered:
                                right_middle_triggered = True
                                pyautogui.hotkey('win', 'tab')
                        else:
                            right_middle_triggered = False

                        right_ring_dist = get_distance(thumb_tip, ring_tip)
                        if right_ring_dist < 0.04:
                            if not right_ring_triggered:
                                right_ring_triggered = True
                                pyautogui.hotkey('win', 'd')
                        else:
                            right_ring_triggered = False

        # --- UNTERSTÜTZENDE SCHLEIFEN-LOGIK ---
        if mouse_mode_active and not right_index_pinch_active_this_frame and mouse_is_down:
            pyautogui.mouseUp()
            mouse_is_down = False
            print("[MAUS] Zeichnen beendet (Klick losgelassen).")

        if not any_hand_doing_toggle:
            toggle_lock = False

        if not is_listening:
            left_index_triggered = False
            left_middle_triggered = False
            left_ring_triggered = False
            right_index_triggered = False
            right_middle_triggered = False
            right_ring_triggered = False
            right_pinky_triggered = False
            prev_mouse_x, prev_mouse_y = None, None
            if mouse_is_down:
                pyautogui.mouseUp()
                mouse_is_down = False

        # --- TEXT-FEEDBACK AUF DEM MONITOR ---
        if not is_listening:
            cv2.putText(frame, "MODUS: STUMM (Gesten gesperrt)", (50, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        else:
            if mouse_mode_active:
                cv2.putText(frame, "MODUS: ZEICHNEN / MAUS (Aktiv)", (50, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 255), 2)
                if mouse_is_down:
                    cv2.putText(frame, "MAUS: ZEICHNEN AKTIV", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
            else:
                cv2.putText(frame, "MODUS: NORMAL (Shortcuts Aktiv)", (50, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        cv2.imshow("Aktivierungs-Shortcut Manager", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'): break

    cap.release()
    cv2.destroyAllWindows()
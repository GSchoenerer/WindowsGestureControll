import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import pyautogui
import time
import math

# PyAutoGUI-Sicherheitsnetz deaktivieren
pyautogui.FAILSAFE = False

# Globale Variablen für den asynchronen Daten-Austausch (Unterstützt jetzt beide Hände)
latest_hands_data = []
latest_handedness_data = []

# Status-Variablen für das System
is_listening = False            # Der globale Modus (True = aktiv, False = stumm)

# Sperren (Debounce), um Mehrfachauslösungen bei gehaltenem Pinch zu verhindern
toggle_lock = False
left_index_triggered = False
left_middle_triggered = False
left_ring_triggered = False

right_index_triggered = False
right_middle_triggered = False
right_ring_triggered = False

# Mathematische Hilfsfunktion: Berechnet den Abstand im 3D-Raum
def get_distance(p1, p2):
    return math.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2 + (p1.z - p2.z)**2)

# Dummy-Funktion für den Zeichenmodus / Mausmodus (Linke Hand, Ringfinger)
def toggle_mouse_drawing_mode():
    print("[Maus-Modus] Geste erkannt! (Hier wird später der Mausmodus aktiviert/deaktiviert)")

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
# MEDIAPIPE INITIATION (num_hands=2 für paralleles Tracking)
# ==============================================================================
model_path = r'C:\Users\schon\PenColorTracking\ObjectTracking\hand_landmarker.task'
base_options = python.BaseOptions(model_asset_path=model_path)
options = vision.HandLandmarkerOptions(
    base_options=base_options,
    num_hands=2,                                  # Erkennt nun linke und rechte Hand gleichzeitig
    running_mode=vision.RunningMode.LIVE_STREAM,
    result_callback=print_result
)

# ==============================================================================
# HAUPTSCHLEIFE
# ==============================================================================
with vision.HandLandmarker.create_from_options(options) as detector:
    cap = cv2.VideoCapture(0)
    print("Gesten-Steuerung aktiv. Standardmäßig STUMM.")

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

        # Flags, um zu prüfen, ob die Toggles/Pinches in dieser Runde noch aktiv sind
        any_hand_doing_toggle = False

        # Schleife über alle im Bild erkannten Hände (bis zu 2)
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
            # 1. MODUS-TOGGLE (NUR LINKE HAND: Daumen & Kleiner Finger gestreckt, andere zu)
            # ==================================================================
            if side == "Left":
                is_toggle_gesture = (not thumb_curled) and index_curled and middle_curled and ring_curled and (not pinky_curled)
                
                if is_toggle_gesture:
                    any_hand_doing_toggle = True
                    if not toggle_lock:
                        is_listening = not is_listening  # Wechselt den Modus (An/Aus)
                        toggle_lock = True
                        print(f"[SYSTEM] Modus geändert! Aktiv: {is_listening}")

            # ==================================================================
            # 2. SHORTCUTS AUSFÜHREN (NUR WENN IS_LISTENING = TRUE)
            # ==================================================================
            if is_listening:
                
                # ------------------- LINKE HAND BEFEHLE -------------------
                if side == "Left":
                    # Pinch Daumen + Zeigefinger -> Win + Strg + Left Arrow
                    left_index_dist = get_distance(thumb_tip, index_tip)
                    if left_index_dist < 0.04:
                        if not left_index_triggered:
                            left_index_triggered = True
                            pyautogui.hotkey('win', 'ctrl', 'left')
                    else:
                        left_index_triggered = False

                    # Pinch Daumen + Mittelfinger -> Win + Strg + Right Arrow
                    left_middle_dist = get_distance(thumb_tip, middle_tip)
                    if left_middle_dist < 0.04:
                        if not left_middle_triggered:
                            left_middle_triggered = True
                            pyautogui.hotkey('win', 'ctrl', 'right')
                    else:
                        left_middle_triggered = False

                    # Pinch Daumen + Ringfinger -> Zeichen/Maus-Modus (Dummy)
                    left_ring_dist = get_distance(thumb_tip, ring_tip)
                    if left_ring_dist < 0.04:
                        if not left_ring_triggered:
                            left_ring_triggered = True
                            toggle_mouse_drawing_mode()
                    else:
                        left_ring_triggered = False

                # ------------------- RECHTE HAND BEFEHLE -------------------
                elif side == "Right":
                    # Pinch Daumen + Zeigefinger -> Alt + F4
                    right_index_dist = get_distance(thumb_tip, index_tip)
                    if right_index_dist < 0.04:
                        if not right_index_triggered:
                            right_index_triggered = True
                            pyautogui.hotkey('alt', 'f4')
                    else:
                        right_index_triggered = False

                    # Pinch Daumen + Mittelfinger -> Win + Tab
                    right_middle_dist = get_distance(thumb_tip, middle_tip)
                    if right_middle_dist < 0.04:
                        if not right_middle_triggered:
                            right_middle_triggered = True
                            pyautogui.hotkey('win', 'tab')
                    else:
                        right_middle_triggered = False

                    # Pinch Daumen + Ringfinger -> Win + D
                    right_ring_dist = get_distance(thumb_tip, ring_tip)
                    if right_ring_dist < 0.04:
                        if not right_ring_triggered:
                            right_ring_triggered = True
                            pyautogui.hotkey('win', 'd')
                    else:
                        right_ring_triggered = False

        # Wenn keine linke Hand mehr die Toggle-Geste macht, schalte die Sperre frei
        if not any_hand_doing_toggle:
            toggle_lock = False

        # Wenn das Programm im stummen Modus ist, setzen wir alle Befehls-Sperren zurück
        if not is_listening:
            left_index_triggered = False
            left_middle_triggered = False
            left_ring_triggered = False
            right_index_triggered = False
            right_middle_triggered = False
            right_ring_triggered = False

        # Visuelles Feedback auf dem Kamerabild platzieren
        if is_listening:
            cv2.putText(frame, "MODUS: ZUHOEREN (Gesten aktiv)", (50, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        else:
            cv2.putText(frame, "MODUS: STUMM (Gesten gesperrt)", (50, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

        # Monitor-Fenster anzeigen
        cv2.imshow("Aktivierungs-Shortcut Manager", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'): break

    cap.release()
    cv2.destroyAllWindows()
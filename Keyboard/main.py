import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import pyautogui
import time
import math

# PyAutoGUI-Sicherheitsnetz deaktivieren
pyautogui.FAILSAFE = False

# Globale Variablen für den asynchronen Daten-Austausch mit der KI
latest_hand_data = None
is_pinched = False
last_active_key = None  # Speichert die Taste, auf der der Finger zuletzt war

# Mathematische Hilfsfunktion: Berechnet den Abstand im 3D-Raum
def get_distance(p1, p2):
    return math.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2 + (p1.z - p2.z)**2)

# ==============================================================================
# TASTATUR-LAYOUT DEFINIEREN
# ==============================================================================
keys_layout = []
rows = [
    ["Q", "W", "E", "R", "T", "Z", "U", "I", "O", "P"],
    ["A", "S", "D", "F", "G", "H", "J", "K", "L", "OE"],
    ["Y", "X", "C", "V", "B", "N", "M", " ", "BACK", "ENTER"]
]

start_y = 0.5  # Die Tastatur beginnt in der unteren Hälfte des Bildes
button_h = 0.12
button_w = 0.08
spacing = 0.015

for row_idx, row in enumerate(rows):
    for col_idx, key in enumerate(row):
        current_w = button_w
        if key in ["BACK", "ENTER"]:
            current_w = button_w * 1.5
        if key == " ":
            current_w = button_w * 2
            
        x = 0.05 + col_idx * (button_w + spacing)
        y = start_y + row_idx * (button_h + spacing)
        keys_layout.append({"key": key, "x": x, "y": y, "w": current_w, "h": button_h})

# ==============================================================================
# MEDIAPIPE CALLBACK FUNCTION
# ==============================================================================
def print_result(result: vision.HandLandmarkerResult, output_image: mp.Image, timestamp_ms: int):
    global latest_hand_data
    if result.hand_landmarks:
        latest_hand_data = result.hand_landmarks[0]
    else:
        latest_hand_data = None

# ==============================================================================
# MEDIAPIPE SETUP
# ==============================================================================
model_path = r'C:\Users\schon\PenColorTracking\ObjectTracking\hand_landmarker.task'
base_options = python.BaseOptions(model_asset_path=model_path)
options = vision.HandLandmarkerOptions(
    base_options=base_options,
    num_hands=1,
    running_mode=vision.RunningMode.LIVE_STREAM,
    result_callback=print_result
)

# ==============================================================================
# MAIN LOOP
# ==============================================================================
with vision.HandLandmarker.create_from_options(options) as detector:
    cap = cv2.VideoCapture(0)
    print("Virtuelles Keyboard aktiv. Öffne ein Textdokument und tippe in die Luft!")

    while cap.isOpened():
        success, frame = cap.read()
        if not success: break

        frame = cv2.flip(frame, 1)
        h_img, w_img, _ = frame.shape
        
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

        timestamp = int(time.time() * 1000)
        detector.detect_async(mp_image, timestamp)

        current_hand = latest_hand_data
        current_hover_key = None  # Die Taste, über der wir aktuell „schweben“

        # --- TASTEN ZEICHNEN ---
        for button in keys_layout:
            x1, y1 = int(button["x"] * w_img), int(button["y"] * h_img)
            x2, y2 = int((button["x"] + button["w"]) * w_img), int((button["y"] + button["h"]) * h_img)
            color = (255, 255, 255)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, button["key"], (x1 + 10, y1 + 35), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        if current_hand is not None:
            thumb_tip = current_hand[4]
            index_tip = current_hand[8]

            # 1. PRÜFEN, ÜBER WELCHER TASTE DER ZEIGEFINGER SCHWEBT
            for button in keys_layout:
                if (button["x"] < index_tip.x < button["x"] + button["w"] and
                    button["y"] < index_tip.y < button["y"] + button["h"]):
                    current_hover_key = button
                    last_active_key = button  # Merkfunktion: Aktualisiere die zuletzt berührte Taste
                    break

            # Wenn der Finger über einer Taste ist, färben wir sie GELB
            if current_hover_key:
                x1, y1 = int(current_hover_key["x"] * w_img), int(current_hover_key["y"] * h_img)
                x2, y2 = int((current_hover_key["x"] + current_hover_key["w"]) * w_img), int((current_hover_key["y"] + current_hover_key["h"]) * h_img)
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 255), -1)
                cv2.putText(frame, current_hover_key["key"], (x1 + 10, y1 + 35), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)

            # 2. PINCH DETEKTION (Daumen + Zeigefinger zusammen)
            pinch_distance = get_distance(thumb_tip, index_tip)

            # Wenn Daumen und Zeigefinger zusammen sind (< 0.04)
            if pinch_distance < 0.04:
                if not is_pinched:
                    is_pinched = True
                    
                    # Hier greift die neue Logik: Drücke die ZULETZT aktive Taste!
                    if last_active_key:
                        key_pressed = last_active_key["key"]
                        
                        # Ausführen des echten Tastendrucks in Windows
                        if key_pressed == "BACK":
                            pyautogui.press("backspace")
                        elif key_pressed == "ENTER":
                            pyautogui.press("enter")
                        elif key_pressed == "OE":
                            pyautogui.write("ö")
                        else:
                            pyautogui.write(key_pressed.lower())
                            
                        # Visuelles Feedback: Die gedrückte Taste blinkt im Bild kurz GRÜN auf
                        kx1, ky1 = int(last_active_key["x"] * w_img), int(last_active_key["y"] * h_img)
                        kx2, ky2 = int((last_active_key["x"] + last_active_key["w"]) * w_img), int((last_active_key["y"] + last_active_key["h"]) * h_img)
                        cv2.rectangle(frame, (kx1, ky1), (kx2, ky2), (0, 255, 0), -1)
                        cv2.putText(frame, key_pressed, (kx1 + 10, ky1 + 35), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
            else:
                is_pinched = False
                # Wenn wir den Pinch wieder öffnen und über KEINER Taste schweben, 
                # löschen wir den Speicher, damit nicht aus Versehen doppelt getippt wird.
                if current_hover_key is None:
                    last_active_key = None

        cv2.imshow("Virtuelle Tastatur", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'): break

    cap.release()
    cv2.destroyAllWindows()
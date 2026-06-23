import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import pyautogui
import time
import math

# ==============================================================================
# CONFIGURATION & INITIALIZATION
# ==============================================================================

# PyAutoGUI-Sicherheitsnetz deaktivieren (verhindert Abstürze bei schnellen Eckenbewegungen)
pyautogui.FAILSAFE = False
SCREEN_WIDTH, SCREEN_HEIGHT = pyautogui.size()

# Variablen für das Glättungs-System (Smoothing) des Cursors
smooth_x, smooth_y = 0, 0
smoothing_factor = 0.20  # Niedriger = smoother beim Zeichnen, Höher = direkter

# Globale Variablen für den asynchronen Daten-Austausch mit der KI
latest_hand_data = None
is_mouse_down = False

# Mathematische Hilfsfunktion: Berechnet den Abstand zwischen zwei Punkten im 3D-Raum
def get_distance(p1, p2):
    return math.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2 + (p1.z - p2.z)**2)

# ==============================================================================
# MEDIAPIPE CALLBACK FUNCTION (Runs in background thread)
# ==============================================================================
def print_result(result: vision.HandLandmarkerResult, output_image: mp.Image, timestamp_ms: int):
    global latest_hand_data
    if result.hand_landmarks:
        # Wir speichern die gesamte Handstruktur (alle 21 Skelett-Punkte)
        latest_hand_data = result.hand_landmarks[0]
    else:
        latest_hand_data = None

# ==============================================================================
# MEDIAPIPE SETUP
# ==============================================================================
# WICHTIG: Absoluter Windows-Pfad zu deiner Model-Datei
model_path = r'C:\Users\schon\PenColorTracking\ObjectTracking\hand_landmarker.task'
base_options = python.BaseOptions(model_asset_path=model_path)

options = vision.HandLandmarkerOptions(
    base_options=base_options,
    num_hands=1,
    running_mode=vision.RunningMode.LIVE_STREAM,  # Zwingend erforderlich für flüssiges Webcam-Streaming
    result_callback=print_result                  # Schickt Ergebnisse asynchron an unsere Funktion oben
)

# ==============================================================================
# MAIN APPLICATION LOOP
# ==============================================================================
with vision.HandLandmarker.create_from_options(options) as detector:
    cap = cv2.VideoCapture(0)
    print("Gesten-Maussteuerung aktiv. Drücke 'q' im Webcam-Fenster zum Beenden.")

    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            print("Webcam-Frame konnte nicht gelesen werden.")
            break

        # Bild horizontal spiegeln, damit die Maus-Steuerung intuitiv ist (wie ein Spiegel)
        frame = cv2.flip(frame, 1)
        
        # Frame von BGR in RGB umwandeln und für MediaPipe verpacken
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

        # Erkennung asynchron starten (erfordert exakten Zeitstempel in Millisekunden)
        timestamp = int(time.time() * 1000)
        detector.detect_async(mp_image, timestamp)

        # THREAD-PROTECTION: Sofortigen lokalen Schnappschuss der Handdaten erstellen.
        # Das verhindert den 'NoneType object is not subscriptable' Absturz, falls 
        # die KI genau während dieser Schleifenrunde im Hintergrund die Hand verliert.
        current_hand = latest_hand_data

        if current_hand is not None:
            # Relevante Fingergelenke aus dem Schnappschuss extrahieren
            wrist = current_hand[0]         # Handgelenk
            thumb_tip = current_hand[4]     # Daumenspitze
            index_tip = current_hand[8]     # Zeigefingerspitze
            middle_tip = current_hand[12]   # Mittelfingerspitze
            ring_tip = current_hand[16]     # Ringfingerspitze
            pinky_tip = current_hand[20]    # Kleinfingerspitze

            # --- 1. CURSOR-STEUERUNG (Maus bewegen) ---
            # Zeigefingerspitze steuert die Position auf dem Bildschirm
            target_x = int(index_tip.x * SCREEN_WIDTH)
            target_y = int(index_tip.y * SCREEN_HEIGHT)
            
            # Exponentielle Glättung gegen biologisches Handzittern
            smooth_x = smooth_x + (target_x - smooth_x) * smoothing_factor
            smooth_y = smooth_y + (target_y - smooth_y) * smoothing_factor
            
            pyautogui.moveTo(int(smooth_x), int(smooth_y))

            # --- 2. GESTEN-BERECHNUNG (Anatomische Logik) ---
            # Geste A: Klick / Pinch (Abstand von Daumenspitze zu Zeigefingerspitze)
            pinch_distance = get_distance(thumb_tip, index_tip)
            
            # Geste B: Faust (Wir prüfen logisch, ob die 4 Finger eingerollt sind)
            # In MediaPipe ist Y=0 oben und Y=1 unten im Bild. 
            # Wenn die Fingerspitze einen GRÖSSEREN Y-Wert hat als das Gelenk darunter, ist der Finger eingeknickt.
            index_curled = index_tip.y > current_hand[6].y
            middle_curled = middle_tip.y > current_hand[10].y
            ring_curled = ring_tip.y > current_hand[14].y
            pinky_curled = pinky_tip.y > current_hand[18].y
            
            # Es gilt nur dann als Faust, wenn alle 4 Finger gleichzeitig eingeknickt sind
            is_fist_detected = index_curled and middle_curled and ring_curled and pinky_curled

            # --- 3. AKTIONEN AUSFÜHREN ---
            if is_fist_detected:
                # Faust erkannt -> Maus gedrückt halten (Zeichnen / Drag & Drop)
                if not is_mouse_down:
                    pyautogui.mouseDown()
                    is_mouse_down = True
                cv2.putText(frame, "GESTE: FAUST (Drag & Hold)", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

            elif pinch_distance < 0.04:
                # Pinch erkannt -> Normaler Einzelklick
                if is_mouse_down:  # Sicherheitsnetz: Falls wir direkt aus einer Faust kommen, erst loslassen
                    pyautogui.mouseUp()
                    is_mouse_down = False
                pyautogui.click()
                cv2.putText(frame, "GESTE: KLICK (Pinch)", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2)
                time.sleep(0.12)  # Kurzer Cooldown gegen ungewollte Doppel-Klicks
                
            else:
                # Keine Aktion / Hand offen -> Nur Cursor bewegen, Maustaste ggf. loslassen
                if is_mouse_down:
                    pyautogui.mouseUp()
                    is_mouse_down = False
                cv2.putText(frame, "Cursor bewegen", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

        # Webcam-Monitor-Fenster anzeigen
        cv2.imshow("MediaPipe Gesture Mouse Control", frame)

        # Beenden, wenn die Taste 'q' gedrückt wird
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
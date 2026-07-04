import os
import threading
import logging

import customtkinter as ctk
import cv2
from pygrabber.dshow_graph import FilterGraph

from tracker import HandTracker

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

ctk.set_appearance_mode("Dark")


class MainWindow(ctk.CTk):

    BUTTON_INACTIVE_COLOR = "#3f4e5f"
    BUTTON_ACTIVE_COLOR = "blue"
    DEFAULT_SMOOTH = 0.25

    def __init__(self):
        super().__init__()

        self.currDir: str = os.path.dirname(os.path.abspath(__file__))
        self.smooth: float = self.DEFAULT_SMOOTH
        self.IsAltF4EnabledCheckVar = ctk.BooleanVar(value=True)
        self.IsAltF4Enabled: bool = True
        self.ShowCameraWindowCheckVar = ctk.BooleanVar(value=True)
        self.cameraDictionarry: dict[str, int] = {}
        self.selectedCameraName = ctk.StringVar()
        self.selectedCamera: int = 0

        self.handTracker: HandTracker | None = None
        self.trackingThread: threading.Thread | None = None

        self.title("SetUp")
        self.geometry("550x140")
        self._set_icon("CTK_TrackerStopped.ico")
        self.rowconfigure(5)
        self.columnconfigure(5)

        self.get_cameras()
        self._build_ui()

    def _set_icon(self, filename: str):
        icon_path = os.path.join(self.currDir, "Icons", filename)
        if os.path.isfile(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception:
                logger.warning("Icon konnte nicht gesetzt werden: %s", icon_path)
        else:
            logger.warning("Icon-Datei nicht gefunden: %s", icon_path)

    def get_cameras(self):
        graph = FilterGraph()
        camera_names = graph.get_input_devices()

        self.cameraDictionarry = {}
        for index, name in enumerate(camera_names):
            cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
            try:
                if cap.isOpened():
                    self.cameraDictionarry[name] = index
            finally:
                cap.release()

        logger.info("Gefundene Kameras: %s", self.cameraDictionarry)

    def translate_camera_name(self, camera_name: str):
        camera_index = self.cameraDictionarry.get(camera_name)
        if camera_index is None:
            logger.warning("Unbekannte Kamera ausgewaehlt: '%s'. Behalte vorherige Auswahl (%s).",
                            camera_name, self.selectedCamera)
            return
        self.selectedCamera = camera_index
        logger.info("Kamera ausgewaehlt: %s (Index %s)", camera_name, camera_index)

    def set_smooth(self, value_smooth):
        self.smooth = value_smooth

    def enable_altf4(self):
        self.IsAltF4Enabled = bool(self.IsAltF4EnabledCheckVar.get())
        logger.info("Alt+F4 aktiviert: %s", self.IsAltF4Enabled)

    def start_tracking(self):
        logger.info("Tracking wird gestartet.")

        self.handTracker = HandTracker(
            smoothingFactor=self.smooth,
            cameraIndex=self.selectedCamera,
            altF4Enabled=self.IsAltF4Enabled,
            showCameraWindow=self.ShowCameraWindowCheckVar.get(),
        )

        self.startButton.configure(fg_color=self.BUTTON_INACTIVE_COLOR, state="disabled")
        self.stopButton.configure(fg_color=self.BUTTON_ACTIVE_COLOR, state="normal")
        self.smoothSlider.configure(state="disabled")
        self.altF4CheckBox.configure(state="disabled")

        self.trackingThread = threading.Thread(target=self.handTracker.start, daemon=True)
        self.trackingThread.start()
        self._set_icon("CTK_TrackerRunning.ico")

    def stop_tracking(self):
        logger.info("Tracking wird gestoppt.")

        self.startButton.configure(fg_color=self.BUTTON_ACTIVE_COLOR, state="normal")
        self.stopButton.configure(fg_color=self.BUTTON_INACTIVE_COLOR, state="disabled")
        self.smoothSlider.configure(state="normal")
        self.altF4CheckBox.configure(state="normal")

        if self.handTracker is not None:
            self.handTracker.IsRunning = False
        else:
            logger.warning("stop_tracking() aufgerufen, aber kein aktiver HandTracker vorhanden.")

        self.handTracker = None
        self._set_icon("CTK_TrackerStopped.ico")

    def _build_ui(self):
        # Smooth Slider
        self.smoothSliderLable = ctk.CTkLabel(master=self, text="Smooth (right=more mouse smooth)")
        self.smoothSliderLable.grid(row=0, column=0, pady=5, padx=5)

        self.smoothSlider = ctk.CTkSlider(master=self, from_=1, to=0.01, command=self.set_smooth)
        self.smoothSlider.set(self.smooth)
        self.smoothSlider.grid(row=1, column=0, pady=5, padx=5)

        # Enable/Disable alt+f4
        self.altF4CheckBox = ctk.CTkCheckBox(master=self, text="Alt+F4 disabled",variable=self.IsAltF4EnabledCheckVar,onvalue=True, offvalue=False,command=self.enable_altf4)
        self.altF4CheckBox.grid(row=2, column=0, pady=5, padx=5)

        # Show Camera Window
        self.showCameraWindowCheckBox = ctk.CTkCheckBox(master=self, text="Show Camera Window",variable=self.ShowCameraWindowCheckVar,onvalue=True, offvalue=False)
        self.showCameraWindowCheckBox.grid(row=2, column=1, pady=5, padx=5)

        # Camera selector
        self.cameraSelect = ctk.CTkComboBox(master=self, values=list(self.cameraDictionarry.keys()),variable=self.selectedCameraName,command=self.translate_camera_name)
        self.cameraSelect.grid(row=1, column=1, pady=5, padx=5)

        # Start/Stop Buttons
        self.startButton = ctk.CTkButton(master=self, text="Start", command=self.start_tracking)
        self.startButton.grid(row=0, column=4, pady=5, padx=5)

        self.stopButton = ctk.CTkButton(master=self, text="Stop", fg_color=self.BUTTON_INACTIVE_COLOR,command=self.stop_tracking)
        self.stopButton.grid(row=1, column=4, padx=5, pady=5)
        self.stopButton.configure(state="disabled")


if __name__ == "__main__":
    mainWindow = MainWindow()
    mainWindow.mainloop()

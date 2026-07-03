import threading
import customtkinter as ctk
from main import HandTracker as HT
import cv2
from pygrabber.dshow_graph import FilterGraph
import os

ctk.set_appearance_mode("Dark")


class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Variables
        self.currDir : str = os.path.dirname(os.path.abspath(__file__))
        self.smooth : float = 0.25
        self.buttonInactiveColorStartStop : str = "#3f4e5f"
        self.IsAltF4EnabledCheckVar = ctk.BooleanVar(value=True)
        self.IsAltF4Enabled : bool = True
        self.cameraListNumbers : list[str] = []
        self.cameraListNames : list[str] = []
        self.cameraDictionarry : dict[str, str] = {}
        self.selectedCameraName = ctk.StringVar()
        self.selectedCamera : int = 0
        self.IsTrackerRunning : bool = False





        self.handTracker = None
        self.title("SetUp")
        self.geometry("450x300")
        self.iconbitmap(os.path.join(self.currDir, "Icons","CTK_TrackerStopped.ico"))
        self.rowconfigure(5)
        self.columnconfigure(5)


        

        def StartHandTracker(start : bool = True):
            if start:
                self.handTracker = HT(smoothingFactor=self.smooth, cameraIndex=self.selectedCamera, altF4Enabled=self.IsAltF4Enabled)
                # self.handTracker.IsRunning = True
                self.handTracker.start()
            else:
                self.handTracker.IsRunning = False
                self.handTracker = None    
        def SetSmooth(valueSmooth):
            self.smooth = valueSmooth
            print(valueSmooth)

        # Blue is wrong find right one
        def StartTracking():
            print("started")
            self.startButton.configure(fg_color=self.buttonInactiveColorStartStop)
            self.stopButton.configure(fg_color="blue")

            self.startButton.configure(state="disabled")
            self.smoothSlider.configure(state="disabled")
            self.stopButton.configure(state="normal")
            self.altF4CheckBox.configure(state="disabled")

            self.trackingThread = threading.Thread(target=StartHandTracker, daemon=True)
            self.trackingThread.start()
            self.iconbitmap(os.path.join(self.currDir, "Icons","CTK_TrackerRunning.ico"))

        def StopTracking():
            print("Stopped")
            self.startButton.configure(fg_color="blue")
            self.stopButton.configure(fg_color=self.buttonInactiveColorStartStop)

            self.smoothSlider.configure(state="normal")
            self.startButton.configure(state="normal")
            self.altF4CheckBox.configure(state="normal")
            self.stopButton.configure(state="disabled")
            StartHandTracker(False)
            self.iconbitmap(os.path.join(self.currDir, "Icons","CTK_TrackerStopped.ico"))


        def EnableAltF4():
            if self.IsAltF4EnabledCheckVar.get() == True:
                self.IsAltF4Enabled = True
                print(self.IsAltF4Enabled)
            elif self.IsAltF4EnabledCheckVar.get() == False:
                self.IsAltF4Enabled = False
                print(self.IsAltF4Enabled)
            print(self.selectedCameraName.get())
        
        def GetCameras(cameraList : list[str]):
            graph = FilterGraph()
            cameraList = graph.get_input_devices()
 
            for index in range(len(cameraList)):
                cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
                if cap.isOpened():
                    self.cameraDictionarry[cameraList[index]] = index
                    cap.release()
                print(self.cameraDictionarry)
        def TranslateCameraName(cameraName : str):
            self.selectedCamera = self.cameraDictionarry.get(cameraName)
            print(self.selectedCamera)
        # Start functions    
        GetCameras(self.cameraListNames)

        

        # Smooth Slider
        self.smoothSliderLable = ctk.CTkLabel(master=self, text="Smooth (right=more mouse smooth)")
        self.smoothSliderLable.grid(row=0,column=0,pady=5,padx=5)

        self.smoothSlider = ctk.CTkSlider(master=self, from_=1, to=0.01, command=SetSmooth)
        self.smoothSlider.set(self.smooth)
        self.smoothSlider.grid(row=1, column=0,pady=5,padx=5)

        # Enable/Disable alt+f4
        self.altF4CheckBox = ctk.CTkCheckBox(master=self,text="Alt+F4 disabled",variable=self.IsAltF4EnabledCheckVar,onvalue=True,offvalue=False,command=EnableAltF4)
        self.altF4CheckBox.grid(row=3,column=0,pady=5,padx=5)

        # Camera selector
        self.cameraSelect = ctk.CTkComboBox(master=self,values=list(self.cameraDictionarry.keys()),variable=self.selectedCameraName,command=TranslateCameraName)
        self.cameraSelect.grid(row=4,column=0,pady=5,padx=5)

        # Start/Stop button for the tracking
        self.startButton = ctk.CTkButton(master=self,text="Start",command=StartTracking)
        self.startButton.grid(row=2,column=3,pady=5,padx=5)

        self.stopButton = ctk.CTkButton(master=self,text="Stop",fg_color=self.buttonInactiveColorStartStop,command=StopTracking)
        self.stopButton.grid(row=3,column=3,padx=5,pady=5)
        self.stopButton.configure(state="disabled")




if __name__ == "__main__":
    mainWindow = MainWindow()
    mainWindow.mainloop()
    

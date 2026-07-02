import customtkinter as ctk
from main import HandTracker as HT


ctk.set_appearance_mode("Dark")


class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("SetUp")
        self.geometry("450x300")

        self.rowconfigure(5)
        self.columnconfigure(5)
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
        
            self.handTracker = HT(smoothingFactor=self.smooth, cameraIndex=1, altF4Enabled=self.IsAltF4Enabled)
            self.handTracker.start()

        def StopTracking():
            print("Stopped")
            self.startButton.configure(fg_color="blue")
            self.stopButton.configure(fg_color=self.buttonInactiveColorStartStop)

            self.smoothSlider.configure(state="normal")
            self.startButton.configure(state="normal")
            self.altF4CheckBox.configure(state="normal")
            self.stopButton.configure(state="disabled")


        def EnableAltF4():
            if self.IsAltF4EnabledCheckVar.get() == True:
                self.IsAltF4Enabled = True
                print(self.IsAltF4Enabled)
            elif self.IsAltF4EnabledCheckVar.get() == False:
                self.IsAltF4Enabled = False
                print(self.IsAltF4Enabled)

        # Variables
        self.smooth : float = 0.25
        self.buttonInactiveColorStartStop : str = "#3f4e5f"
        self.IsAltF4EnabledCheckVar = ctk.BooleanVar(value=True)
        self.IsAltF4Enabled : bool = True



        # Smooth Slider
        self.smoothSliderLable = ctk.CTkLabel(master=self, text="Smooth (right=more mouse smooth)")
        self.smoothSliderLable.grid(row=0,column=0,pady=5,padx=5)

        self.smoothSlider = ctk.CTkSlider(master=self, from_=1, to=0.01, command=SetSmooth)
        self.smoothSlider.set(self.smooth)
        self.smoothSlider.grid(row=1, column=0,pady=5,padx=5)

        # Enable/Disable alt+f4
        self.altF4CheckBox = ctk.CTkCheckBox(master=self,text="Alt+F4 enabled",variable=self.IsAltF4EnabledCheckVar,onvalue=True,offvalue=False,command=EnableAltF4)
        self.altF4CheckBox.grid(row=3,column=0,pady=5,padx=5)












        # Start/Stop button for the tracking
        self.startButton = ctk.CTkButton(master=self,text="Start",command=StartTracking)
        self.startButton.grid(row=2,column=3,pady=5,padx=5)

        self.stopButton = ctk.CTkButton(master=self,text="Stop",fg_color=self.buttonInactiveColorStartStop,command=StopTracking)
        self.stopButton.grid(row=3,column=3,padx=5,pady=5)
        self.stopButton.configure(state="disabled")




if __name__ == "__main__":
    mainWindow = MainWindow()
    mainWindow.mainloop()

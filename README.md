# BE CAREFULL WHILE USING ON IMPORTANT FILES ALT + F4 COMMAND IS VERRY SENSITIVE!!!!!

## Gesture Controll for Windows - under MIT License

### Important notes

- **This Programm uses a camera and MediaPipe to detect hand gestures**
- **The video will not be recorded or saved on your SSD/HD and only used in RAM**
- **Because of the use of a camera a unknowing third party can enter the screen. The full Responsibility is on the user to ensure that the programm doesnt infringe on the right of privacy of third parties**
- **If any DSGvO violations or other legal problems occur through the programm the user bears the sole responsibility for them**


The Gesturedetection is not perfect and depends on lighting and camera position.
As mentioned above the programm can misread gestures so be carefull when using it while important files are open.
The yet to be implemented Drawmode will hevily depend on the fps of your camera as with low fps it can stutter quiet a bit.

### Implemented Gestures

Normal Mode:

    Left Hand:
        
        - Pinch Indexfinger and thumb execute short cut: win + strg + left arrow
        - Pinch Middlefinger and thumb execute short cut: win + strg + right arrow
        - Pinch Ringfinger and thumb activate / deactivate Mouse/drawing mode (not yet implemented can be ignored if needed for clarity add dummy function)
        - Thumb and littlefinger stretched and all other fingers closed: switch the programm into a mode that acepts gesture commands if executed again stop acepting all other gestures but this one to reactivate

    Right Hand:

        - Pich index finger and thumb execute shortcut: alt + f4
        - Pinch Middlefinger and thumb execute shortcut: win + tab
        - Pinch Ringfinger and thumb execute shortcut: win + d

Drawing/Mouse Mode:

    Left Hand:
        
        - No function implemented
        - Possible functions: Pinch fingers for things linke erraser
    
    Right Hand:
        - No function implemented

### Hardware

Created with the following Hardware:

- CPU: Intel Core Ultra 7
- RAM: 32 GB of DDR5 RAM(5600 MT/s)
- GPU: NVIDIA GeForce RTX 5060

Average System Usage:

- CPU: not tested
- RAM: not tested
- GPU: not tested

Camera: for the normal gesture controll 30 fps is enough for the drawing/mouse controll it is laggy on 30 fps so 60 fps is recomended (yet to be tested)

### Tutorials

The main tutorial is going to be the text tutorial as I will try to make all the gestures as distinguishable as possible.
If Video tutorials are created they will be in a folder labeled "VideoTutorials".

### Setup tutorial

The setup is going to be either in a seperate installer or a setp by setp guide and will be found either here (the step by step version) or in a folder labled "installer" (for the installer version) 
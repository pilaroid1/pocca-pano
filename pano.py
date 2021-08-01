"""
    POCCA Pano
"""
import sys
sys.path.append("../")
import time
import configparser
import os
import signal
import uuid

from pocca.display.interface import Interface
from pocca.vision.camera import Camera #Pi Camera Manager
from pocca.vision.effects import Effects # OpenCV Effects
from pocca.vision.convert import Convert # FFMPEG Conversion
from pocca.controls.buttons import Buttons # Joystick / Buttons
from pocca.vision.panorama import Panorama

import pygame


# Detect a CTRL-C abord program interrupt, and gracefully exit the application
def sigint_handler(signal, frame):
    print(TEXT.DEV_STOP)
    going = False
    sys.exit(0)

# Enable abord program interrupt
signal.signal(signal.SIGINT, sigint_handler)

settings = configparser.ConfigParser()
settings.read("/media/usb/pocca.ini")
if settings["APPLICATION"]["lang"] == "fr":
    from pocca.localization.fr import TEXT
else:
    from pocca.localization.en import TEXT
path_images = settings["FOLDERS"]["pictures"]
path_temp = settings["FOLDERS"]["temp"]

print("\033c", end="") # Clear Terminal
print(" ~~~~~~ 📷 POCCA (Panoramique) 📷 ~~~~~~")
print(TEXT.LOCK_WARNING)

interface = Interface(settings)
camera = Camera(settings, TEXT)
effects = Effects()
convert = Convert(TEXT)
buttons = Buttons(TEXT)

pano_images = int(settings["CAMERA"]["pano_images"])
pano_crop = int(settings["CAMERA"]["pano_crop"])
panorama = Panorama(path_images=path_images, path_temp=path_temp, pano_images=pano_images, image_size=(int(settings["CAMERA"]["width"]),int(settings["CAMERA"]["height"])))

interface.start()
camera.start()
camera.clear_temp() # Remove Previous Images

going = True
start_timer = 0
filename = ""
countdown = 0

print(" ~~~~~~~~~~~~")

while going:
    # Viewfinder (Live preview)
    if interface.state == "viewfinder":
        try:
            # Capture frame continously
            for frame in camera.stream.capture_continuous(camera.rawCapture, format='bgr', use_video_port=True):
                # Get array of RGB from images
                frame = frame.array

                frame_resize = camera.resize(frame, (interface.resolution))
                interface.to_screen(frame_resize)
                interface.top_left(interface.state)
                interface.top_right("pano")

                if(countdown > 0):
                    interface.bottom(str(countdown))

                if interface.state == "countdown" :
                    if time.time() > (start_timer + 1):
                        print(TEXT.TIMER + " : " + str(countdown))
                        if countdown > 0:
                            countdown = countdown - 1
                        else:
                            interface.state = "record"
                        start_timer = time.time()

                # If we are in record mode
                if interface.state == "record":
                    if(camera.count() < (panorama.images - 1)):
                        camera.save(frame, path_temp)
                        countdown = 3
                        start_timer = time.time()
                        interface.state = "countdown"
                    else:
                        camera.save(frame, path_temp)
                        # Try to make the timelapse
                        filename = ""
                        interface.image("saving")
                        try:
                            images = ["img0.png","img1.png"]
                            print(TEXT.JOIN_IMAGES + " img0 <--> img1")
                            panorama.join_images(images)
                            if panorama.status == 0 :
                                panorama.crop_images(pano_crop)
                                if pano_images == 4:
                                    panorama.save(path_temp + "/pano1.png")
                                    if panorama.status == 0 :
                                        images = ["img2.png","img3.png"]
                                        print(TEXT.JOIN_IMAGES + " img2 <--> img3")
                                        panorama.join_images(images)
                                        panorama.crop_images(pano_crop)
                                        panorama.save(path_temp + "/pano2.png")
                                        if panorama.status == 0:
                                            images = ["pano1.png","pano2.png"]
                                            print(TEXT.JOIN_IMAGES + " pano1 <--> pano2")
                                            panorama.join_images(images)
                                            panorama.crop_images(pano_crop)
                            if panorama.status == 0:
                                filename = panorama.save(path_temp + "/" "pano" + "_" + str(uuid.uuid4())[:8] + ".png")
                                print(TEXT.PANORAMA_CONVERT_OK)
                            else:
                                print(TEXT.PANORAMA_CONVERT_FAILED + " " + str(panorama.status))
                            interface.state = "preview"
                            break
                        except:
                            raise
                            print(TEXT.PANORAMA_CONVERT_FAILED + " " + str(panorama.status))
                            interface.state = "preview"
                            camera.clear_temp()
                            camera.rawCapture.truncate(0)
                            break

                """
                Buttons
                Check if a button is pressed
                """
                # Check if a button is pressed
                pressed = buttons.check()

                # If the button is pressed
                if pressed == buttons.BTN: # or  web_action == 1:
                    start_timer = time.time()
                    countdown = 3
                    interface.state = "countdown"
                camera.rawCapture.truncate(0)

        # If the video capture failed, crash gracefully
        except Exception as error:
            raise # Add this to check error
            print("❌ ➡️ : " + str(error))
            going = False

    # Preview mode (show timelapse/panorama)
    if interface.state == "preview":
        pressed = buttons.check()
        # If in Panorama, show image
        try:
            interface.load(filename)
        except:
            interface.image("error_pano")
        if pressed != buttons.NOACTION:
            interface.state = "viewfinder"
            camera.rawCapture.truncate(0)

# If we exit the application, we go here
print(TEXT.SHUTDOWN_APP)
camera.stop()
interface.stop()
sys.exit(0)

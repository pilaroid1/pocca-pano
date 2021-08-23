"""
    POCCA Pano
"""
import sys
sys.path.append("/media/usb/apps")
from pocca.display.interface import Interface
from pocca.display.countdown import Countdown
from pocca.vision.camera import Camera #Pi Camera Manager
from pocca.controls.buttons import Buttons # Joystick / Buttons
from pocca.vision.panorama import Panorama
from pocca.utils.app import App # Application Manager (Settings / Secrets / utilities)
import os
import uuid

app = App()
app.clear_terminal()
print(app.TEXT.LOCK_WARNING)
print(" ~~~~~~ 📷 Pilaroid Pano 📷  ~~~~~~")
print(" https://github.com/usini/pocca-pano")

interface = Interface(app.settings, app.system)
countdown = Countdown(app.settings, app.TEXT)
buttons = Buttons(app.TEXT)

camera = Camera(app.settings, app.TEXT, app.camera_resolution)
camera.clear_temp() # Remove Previous Images

pano_images = int(app.settings["APPLICATION"]["pano_images"])
pano_crop = int(app.settings["APPLICATION"]["pano_crop"])
panorama = Panorama(path_images=app.path["images"], path_temp=app.path["temp"], pano_images=pano_images, image_size=app.camera_resolution)
filename = ""

# If we exit the application, we go here
def stop(signal, frame):
    print(app.TEXT.SHUTDOWN_APP)
    app.running = False
app.stop_function(stop)

def run():
    global countdown, filename
    # Viewfinder (Live preview)
    if interface.state == "viewfinder":
        # Capture frame continously

        for frame in camera.stream.capture_continuous(camera.rawCapture, format='bgr', use_video_port=True):
            # Get array of RGB from images
            frame = frame.array

            if not app.running:
                sys.exit(0)

            frame_resize = camera.resize(frame, (interface.resolution))
            interface.to_screen(frame_resize)
            interface.top_left(interface.state)
            interface.top_right("pano")

            if countdown.running():
                if countdown.started:
                    interface.bottom(str(countdown.current()))
                else:
                    interface.state = "record"

            interface.update()

            # If we are in record mode
            if interface.state == "record":
                if(camera.count() < (panorama.images - 1)):
                    camera.save(frame, app.path["temp"]  + "/images")
                    countdown.start()
                    interface.state = "viewfinder"
                else:
                    camera.save(frame, app.path["temp"] + "/images")
                    # Try to make the timelapse
                    filename = ""
                    interface.image("saving")
                    try:
                        images = os.listdir(app.path["temp"] + "/images")
                        print(app.TEXT.JOIN_IMAGES + " img0 <--> img1")
                        interface.image("saving")
                        interface.update()
                        panorama.join_images(images)
                        if panorama.status == 0:
                            filename = panorama.save(app.path["images"] + "/" "pano" + "_" + str(uuid.uuid4())[:8] + ".jpg")
                            camera.save_timestamp(filename)
                            print(app.TEXT.PANORAMA_CONVERT_OK)
                        else:
                            print(app.TEXT.PANORAMA_CONVERT_FAILED + " " + str(panorama.status))
                        interface.state = "preview"
                    except:
                        raise
                        print(app.TEXT.PANORAMA_CONVERT_FAILED + " " + str(panorama.status))
                        interface.state = "preview"
            camera.refresh()
            controls()

def controls():
    """
    Buttons
    Check if a button is pressed
    """
    # Check if a button is pressed
    pressed = buttons.check()

    # If the button is pressed
    if interface.state == "viewfinder":
        if pressed == buttons.BTN: # or  web_action == 1:
            if not countdown.running():
                countdown.start()
            interface.state = "countdown"

    # Preview mode (show timelapse/panorama)
    if interface.state == "preview":
        # If in Panorama, show image
        try:
            interface.load(filename)
        except:
            interface.image("error_pano")
        interface.top_left(interface.state)
        interface.top_right("pano")
        interface.update()
        while interface.state == "preview":
            pressed = buttons.check()
            if pressed != buttons.NOACTION:
                interface.state = "viewfinder"
                camera.clear_temp()
                camera.refresh()
            if not app.running:
                sys.exit(0)

run()


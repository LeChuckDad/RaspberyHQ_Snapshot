# RaspberyHQ_Snapshot
Webinterface for livepicture and snapshot funkction with raspberry pi hq camera

The web interface is started via “python3 app.py”.
The interface can then be accessed via a web browser, e.g. http://Pi-IP:5000/

The web interface has a button for displaying a live image. 
There are 4 input fields available with gain exposure time name (image name with which it is saved) and number of times the photo should be taken. the recording is started with the “record” button. All images are saved as raw. For a quick preview, the image is reduced to 640*480 and saved as jpg

the file is saved in the format date-time-gain-exposure-time-name.raw


follwing packages are needed:

# Flask, OpenCV und andere Python-Pakete installieren
pip install flask opencv-python

# Notwendige System-Tools
sudo apt-get update
sudo apt-get install libcamera-tools dcraw

Software configuration for raspberry hq camera:
"""use the raspberry pi debian "bookworm" version"
sudo nano /boot/firmware/config.txt
dtoverlay=imx477 

#Start RaspberryGQ Snapshot
python app.py
after starting you see the server adress: Running on http://192.168.178.53:5000


if you have a different camera chip, replace imx477 with yours. Look here 
https://www.waveshare.com/wiki/Raspberry_Pi_HQ_Camera

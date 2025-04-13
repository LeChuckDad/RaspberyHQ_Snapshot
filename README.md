# RaspberyHQ_Snapshot
Webinterface for livepicture and snapshot funkction with raspberry pi hq camera

The web interface is started via “python3 app.py”.
The interface can then be accessed via a web browser, e.g. http://Pi-IP:5000/

The web interface has a button for displaying a live image. 
There are 4 input fields available with gain exposure time name (image name with which it is saved) and number of times the photo should be taken. the recording is started with the “record” button. All images are saved as raw. For a quick preview, the image is reduced to 640*480 and saved as jpg

the file is saved in the format date-time-gain-exposure-time-name.raw


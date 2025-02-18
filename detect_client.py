import requests
import time
import json
import sys
import os
import numpy as np
import cv2 as cv
import io
import imutils
from picamera.array import PiRGBArray
from picamera import PiCamera
from flask import Response
from flask import Flask
from flask import render_template
URL = "http://belnek.ddns.net:8001"
from gpiozero import AngularServo
from gpiozero.pins.pigpio import PiGPIOFactory
pigpio_factory = PiGPIOFactory()
pan_max_left = 0
pan_max_right = 180
mid_x = (pan_max_right - pan_max_left)/2
min_x = pan_max_left - mid_x
max_x = pan_max_right - mid_x
import threading
lock = threading.Lock()
app = Flask(__name__)
lastFrame = None
@app.route("/")
def index():
    return render_template("index.html")
try:
    servo =AngularServo(17, initial_angle=-20.0,
                    min_angle=min_x, max_angle=max_x,
                    pin_factory=pigpio_factory)
except(Exception):
    servo.value = None
cam_cx = 256 / 2
big_w = 256

colors = [
    (256,0,0),
    (0,0,120),
    (0,0,0),
    (0,256,0),
    (220,220,0),
    (107,142,35),
    (152,251,152),
    (70,130,180),
    (220,20,60),
    (255,0,0),
    (0,0,142),
    (0,0,70),
    (0,60,100),
    (0,80,100),
    (0,0,230),
    (119,11,32),
    (70,70,70),
    (102,102,156),
    (190,153,153),
]

def get_color(idx):
    return colors[idx % len(colors)]
 

def generate():
    global lastFrame, lock
    
    while True:
        with lock:
            if lastFrame is None:
                continue
            (flag, encodedImage) = cv.imencode(".jpg", lastFrame)
            if not flag:
                continue
        yield(b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' +
              bytearray(encodedImage) + b'\r\n')
        
def request_detect(f):
    try:
        params = dict (file = f)
        resp = requests.post(URL + "/detect", files=params, verify=False)
        if resp.status_code == requests.codes.ok:
            return 0, resp.json()
        return resp.status_code, resp.content
    except:
        return 503, None

def request_detect_draw(f):
    try:
        params = dict (file = f)
        resp = requests.post(URL + "/ddetect", files=params, verify=False)
        if resp.status_code == requests.codes.ok:
            return 0, resp.content
    except:
        return 503, None



def read_file(path):
    with open(path, "rb") as f:
        return f.read()

def to_memfile(content):
    memfile = io.BytesIO()
    memfile.write(content)
    memfile.seek(0)
    return memfile

def detect_file(path):
    with open(path, "rb") as f:
        return request_detect(f)

def detect_draw(path):
    with open(path, "rb") as f:
        return request_detect_draw(f)



def detect_img(img):
    _, img_encoded = cv.imencode('.jpg', img)
    return request_detect(to_memfile(img_encoded))

def detect_draw_img(img):
    _, img_encoded = cv.imencode('.jpg', img)
    return request_detect_draw(to_memfile(img_encoded))


def draw_detection(img, d, draw_text=True):
    if d is None:
        return
    n = 0
    for a in d:
        clr = get_color(n)
        cv.rectangle(img, (a["x"], a["y"]), (a["x"] + a["w"], a["y"] + a["h"]), clr, thickness=2)
        word = a["name"] + "(" + str(int(100. * a["score"])) + "%)" 
        if draw_text:
            cv.putText(img, word, (a["x"] + 5, a["y"] + 25), cv.FONT_HERSHEY_SIMPLEX, 0.5, clr, 1, cv.LINE_AA)
        n += 1

def pan_goto(x):    # Move the pan/tilt to a specific location.
    # convert x and y 0 to 180 deg to -45 to + 45 coordinates
    # required for the gpiozero python servo setup

    # check maximum server limits and change if exceeded
    # These can be less than the maximum permitted
    if x <  -85:
        x = -85
    elif x > 45:
        x = 45

    

    # convert and move pan servo
    
    try:
        servo.angle = x
    except (Exception):
        servo.value = None

    # convert and move tilt servo
     # give the servo's some time to move

    return x
def detect():
    global lastFrame
    t = time.time()
    camera = PiCamera()
    camera.resolution = (256, 256)
    raw = PiRGBArray(camera, size=(256, 256))
    time.sleep(0.1)
    pan_cx = pan_goto(-20.0)
    #err, R = detect_file(sys.argv[1])
    #img = cv.imread(sys.argv[1])
    #err, R = detect_img(img)
    for frame in camera.capture_continuous(raw, format="bgr", use_video_port=True):
    
        image = frame.array
        err, R = detect_img(image)
        t = time.time() - t
        if err == 0:    
            if len(R) > 0:
                r = R[0]
                (fx, fy, fw, fh) = r['x'], r['y'], r['w'], r['h']
                cx = int(fx + fw/2)
                Nav_LR = int((cam_cx - cx) /7 )
                pan_cx = pan_cx + Nav_LR
                pan_cx = pan_goto(pan_cx)
            draw_detection(image, R, True)
            img = cv.resize(image, (512, 512))
            lastFrame = img
            #cv.imshow('frame', img)
           
        else:
            print (err, R)

        if cv.waitKey(1) & 0xFF == ord('q'):
            break
        raw.truncate(0)
@app.route("/video_feed")
def video_feed():
    return Response(generate(),
                    mimetype="multipart/x-mixed-replace; boundary=frame")


if __name__ == "__main__":
    t = threading.Thread(target=detect)
    t.daemon = True
    t.start()
    
    app.run(host="0.0.0.0", port="8000", debug=False, threaded=True, use_reloader=False)
    

 
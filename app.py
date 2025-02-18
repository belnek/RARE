import os
import threading
import datetime
import time
import requests
import logging
import io
import numpy as np
import cv2
import dnn_conf as conf

if not os.path.isdir(conf.LOG_PATH):
    os.makedirs(conf.LOG_PATH)        

log_file = conf.LOG_PATH + "/" + conf.LOG_FILE
logging.basicConfig(filename=log_file,level=logging.DEBUG, format='%(asctime)s.%(msecs)03d %(threadName)s %(levelname)-8s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')


from flask import Flask
from flask import send_file, send_from_directory
from flask import jsonify
from flask import request


import detect_ctrl as ctrl


app = Flask(__name__)


def get_request_file(request):
    if 'file' not in request.files:
        return None

    file = request.files['file']
    input_file = io.BytesIO()
    file.save(input_file)
    return np.fromstring(input_file.getvalue(), dtype=np.uint8)


def send_blob(blob, mime_type):
    out_file = io.BytesIO()
    out_file.write(blob)
    out_file.seek(0)
    return send_file(out_file, mimetype=mime_type)

lastFrame = ""

@app.route('/')
def index():
    return 'DNN REST Service'



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

@app.route('/detect', methods=['POST'])
def detect():
    data = get_request_file(request)
    if data is None:
        "file", requests.codes.bad_request

    rc, ret = ctrl.detect(data)
    #rc1, jpg = ctrl.detect_draw(data)
    #lastFrame = jpg
    #cv2.imshow("frame", jpg)
    if not rc:
        return jsonify({"error" : ret}), requests.codes.bad_request
    return jsonify(ret), requests.codes.ok



@app.route('/ddetect', methods=['POST'])
def detect_draw():
    data = get_request_file(request)
    if data is None:
        "file", requests.codes.bad_request

    rc, jpg = ctrl.detect_draw(data)
    if not rc:
        return ret, requests.codes.bad_request
    return send_blob(jpg, "image/jpeg")





if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8001, debug=True, threaded=False, use_reloader=False)


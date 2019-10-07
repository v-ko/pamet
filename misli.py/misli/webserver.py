#!/usr/bin/python
# -*- coding: utf-8 -*-

import os, subprocess
from datetime import datetime
from flask import Flask, render_template, jsonify, redirect, url_for, request
from datetime import datetime
from datetime import timedelta

app = Flask(__name__)
app.config.from_object(__name__)
computeProcesses = []

#CONFIG VARIABLES
uploadFolder = 'uploads'
CHUNK_SIZE = 30
ESTIMATED_SLOWNESS_FACTOR = 25

if not os.path.exists(uploadFolder):
    os.makedirs(uploadFolder)


@app.route("/")
def index():
    return render_template("index.html")


@app.route('/upload', methods=['POST'])
def upload():
    if request.method == 'POST':
        files = request.files.getlist('files')
        timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S-%f")

        for file in files:
            if file:
                filename = os.path.join(uploadFolder, file.filename.replace(" ","_")+"_"+timestamp)
                file.save(filename)


if __name__ == "__main__":
    app.run(debug=True, port=80, host='0.0.0.0')

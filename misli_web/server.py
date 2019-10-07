#!/usr/bin/python
# -*- coding: utf-8 -*-

import os, subprocess
from datetime import datetime
from flask import Flask, render_template, jsonify, redirect, url_for, request
from datetime import datetime
from datetime import timedelta

# THIS FUCKER IS NOT WORKING. I STARTED PROGRAMMING IT BUT DEEMED IT UNNECESSARY ATM

#Check for the working dir
if not os.getcwd().endswith("bulphonc/s5"):
    print("This script should be run from the bulphonc/s5/ directory (the Kaldi recipe) ")
    exit(-1)

app = Flask(__name__)
app.config.from_object(__name__)

#CONFIG VARIABLES
webNotesFolder = '/sync/misli/web'

if not os.path.exists(uploadFolder):
    os.makedirs(uploadFolder)

@app.route("/")
def index():
    return render_template("index.html")

@app.route('/upload', methods=['POST'])
def upload():
    global computeProcesses

    if request.method == 'POST':
        files = request.files.getlist('files')
        now = datetime.now()
        timestamp = now.strftime("%Y-%m-%d-%H-%M-%S-%f")
        folderName = os.path.join(uploadFolder, timestamp)
        os.mkdir(folderName)

        fileCount = 0
        for file in files:
            if file and allowed_file(file.filename):
                fileCount += 1
                filename = os.path.join(folderName, file.filename)
                file.save(filename)

        if fileCount==0:
            return "No compatible audio files were upleaded"

        subprocess.run(['local/convert_dir_to_wav.py',folderName])
        folderName = os.path.join(folderName, "converted_to_wav")
        #Segment script that splits bigger files into renamed chunks (in the same dir)
        computeProcesses.append( subprocess.Popen(['local/recognize_wav.py','-n', timestamp, folderName]) )
        #Record estimated time left
        with open( os.path.join(folderName,"estimated_time"), "w") as eta:
            numJobs = 16
            if fileCount>numJobs and fileCount<16: numJobs = fileCount
            secondsLeft = ESTIMATED_SLOWNESS_FACTOR*CHUNK_SIZE*numFiles/numJobs
            eta.write( str( datetime.now() + timedelta(seconds=secondsLeft)) )
        return redirect(url_for("result", result_id=timestamp))

@app.route('/<note_file>.html', methods=['GET'])
def result(note_file):
    resultsFilePath = os.path.join("data/uploads/"+result_id, "converted_to_wav/transcriptions.txt")
    etaFilePath = os.path.join("data/uploads/"+result_id, "converted_to_wav/estimated_time")

    if not os.path.exists(resultsFilePath):
        if not os.path.exists(etaFilePath):
            return "Invalid result id (the estimated_time file is missing)."
        else:
            output = "<html><head><title>Computing results</title></head><body><script>setTimeout('location.reload(true);',60000);</script>Estimated time until results are ready: "
            with open(etaFilePath,"r") as eta:
                output += eta.read()
            output+="<br>Refreshing the page every minute automatically</body></html>"
            return output
    else:
        output = "<html><head><title>Ready!</title></head><body>"
        with open(resultsFilePath,"r") as file:
            output += file.read().replace("\n","<br><br>")
            output += "</body></html>"
        return output

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

if __name__ == "__main__":
    app.run(debug=True, port=5000, host='0.0.0.0')

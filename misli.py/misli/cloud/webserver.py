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


# //Export notes as web pages (lambda)
#     connect(ui->actionExport_all_as_web_notes,&QAction::triggered,[&](){
#         QDir webDir(misliLibrary()->folderPath+"/web");
#         if(!webDir.exists()) webDir.mkpath(webDir.absolutePath());

#         QImage img(1000,1000, QImage::Format_ARGB32);//hacky workaround to get the text length adjust
#         QPainter p(&img);

#         QFile jsFile(":/misli_web/static/misli.js"), styleFile(":/misli_web/static/style.css");
#         if(!jsFile.open(QIODevice::ReadOnly)) qDebug("Could not load misli.js resource");
#         if(!styleFile.open(QIODevice::ReadOnly)) qDebug("Could not load misli.js resource");
#         QString jsContents = jsFile.readAll(), styleContents = styleFile.readAll();
#         jsFile.close();
#         styleFile.close();

#         for(NoteFile *nf: misliLibrary()->noteFiles()){
#             QFile file(webDir.absoluteFilePath(nf->name()+".html"));
#             file.open(QIODevice::WriteOnly);
#             QTextStream stream(&file);
#             stream<<"<!DOCTYPE html>\n"
#                     "<html>\n"
#                     "    <head>\n"
#                     "        <style>\n";
#                     //"        <link rel='stylesheet' href='static/style.css'>\n"
#             stream<<styleContents;
#             stream<<"        </style>\n"
#                     "    </head>\n"
#                     "<body style=\"overflow: hidden\">\n"
#                     "\t<canvas id=\"misliCanvas\">Your browser does not support the HTML5 canvas tag.</canvas>\n"
#                     "\t<!-- GENERATED -->\n";
#             for(Note *nt: nf->notes){

#                 if(!nt->tags.contains("for_export_v1")) continue;

#                 nt->checkForDefinitions();
#                 nt->drawNote(p); //hacky workaround to get the text length adjust
#                 stream<<"\t<a";
#                 //Specify link address if the note redirects
#                 if(nt->type==NoteType::webPage){
#                     stream<<" href=\""+nt->addressString+"\"";
#                 }
#                 stream<<" class=\"note\" id=\""<<"n"<<nt->id<<"\" style=\"";
#                 //Specify background color
#                 if(nt->backgroundColor()!=QColor::fromRgbF(0,0,1,0.1)){
#                     stream<<"background-color: rgba("<<nt->backgroundColor().red()<<","<<nt->backgroundColor().green()<<","<<nt->backgroundColor().blue()<<","<<nt->backgroundColor().alphaF()<<");";
#                 }
#                 //Specify text color
#                 if(nt->backgroundColor()!=QColor::fromRgbF(0,0,1,1)){
#                     stream<<"color: rgba("<<nt->textColor().red()<<","<<nt->textColor().green()<<","<<nt->textColor().blue()<<","<<nt->textColor().alphaF()<<");";
#                 }
#                 //Specify border
#                 if( (nt->type==NoteType::redirecting) | (nt->type==NoteType::webPage) ){
#                     stream<<"border: 1px solid rgba("<<nt->textColor().red()<<","<<nt->textColor().green()<<","<<nt->textColor().blue()<<","<<nt->textColor().alphaF()<<");";
#                 }
#                 //Close off
#                 stream<<"\">"<<nt->textForDisplay()<<"</a>\n";
#             }

#             //stream<<"<script type='text/javascript' src='static/misli.js' ></script>\n"
#             stream<<"\n<script>\n";
#             stream<<jsContents;
#             stream<<"\t//GENERATED\n";
#             for(Note *nt: nf->notes){
#                 if(!nt->tags.contains("for_export_v1")) continue;
#                 stream<<"\tnewNote("<<"\"n"<<nt->id<<"\","<<nt->rect().left()<<","<<nt->rect().top()<<","<<nt->rect().width()<<","<<nt->rect().height()<<","<<nt->fontSize<<");\n";
#                 for(Link ln: nt->outlinks){
#                     stream<<"\tnewLink("<<ln.line.x1()<<","<<ln.line.y1()<<","<<ln.line.x2()<<","<<ln.line.y2()<<");\n";
#                 }
#             }

#             stream<<"updateCanvas();"
#                     "</script>\n"
#                     "\n"
#                     "</body>\n"
#                     "</html>";

#             stream.flush();
#             file.close();
#         }
#     });
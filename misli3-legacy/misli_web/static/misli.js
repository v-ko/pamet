
//TODO:
//drag to look around
//scroll to zoom in/out
//update on window change

var canvas = document.getElementById("misliCanvas");
canvas.width = window.innerWidth
canvas.height = window.innerHeight
var context = canvas.getContext("2d");
//ctx.font = "30px Arial";
//ctx.fillText("Hello World",10,50);
var links = [];
var notes = [];
var eyeX = 0;
var eyeY = 0;
var eyeZ = 90;
var pushLeft = false;
var XonPush = 0;
var YonPush = 0;
var eyeXOnPush = 0;
var eyeYOnPush = 0;
var rendering = 0;
var MOVE_SPEED = 3;

function stop(x, min, max){
    if (x<min) {
        x=min;
    }else if (x>max){
        x=max;
    }
    return x;
}
function intersectRect(r1, r2) {
  return !(r2.x > r1.right ||
           r2.right < r1.x ||
           r2.y > r1.bottom ||
           r2.bottom < r1.y);
}
function heightScaleFactor(){
    return 1000/eyeZ;
}

function projectX(x){
    x = x - eyeX;
    return x*heightScaleFactor() + window.innerWidth/2
}
function projectY(y){
    y = y - eyeY;
    return y*heightScaleFactor() + window.innerHeight/2
}
function drawLine(x1,y1,x2,y2){
    context.beginPath();
    context.moveTo(x1+1, y1+1); //Има един пиксел още разлика между канваса и елементите
    context.lineTo(x2, y2);
    context.strokeStyle = "rgb(0,0,255)";
    context.stroke();
}

class Link{
    constructor(){
        this.x1 = 0;
        this.y1 = 0;
        this.x2 = 0;
        this.y2 = 0;
    }
}
class Note{
    constructor(id,x,y,w,h,fontSize){
        this.id = id;
        this.x = x;
        this.y = y;
        this.w = w;
        this.h = h;
        this.bottom = y+h;
        this.right = x+w;
        this.fontSize = fontSize;
    }
}

function newNote(id,x,y,w,h,fontSize){
    var nt = new Note(id,x,y,w,h,fontSize);
    notes.push(nt);
}
function newLink(x1,y1,x2,y2){
    var ln = new Link;
    ln.x1 = x1;
    ln.y1 = y1;
    ln.x2 = x2;
    ln.y2 = y2;
    links.push(ln);
}

function updateCanvas(){
    context.clearRect(0, 0, canvas.width, canvas.height);
    for(var i = 0; i<links.length; i++){
        ln = links[i];
        drawLine(projectX(ln.x1),projectY(ln.y1),projectX(ln.x2),projectY(ln.y2));
    }
    w = canvas.width/heightScaleFactor();
    h = canvas.height/heightScaleFactor();
    x = eyeX - w/2;
    y = eyeY - h/2;
    var windowFrame = new Note(-1, x, y, w, h, 1);

    for(var i = 0; i<notes.length; i++){
        var nt = notes[i];
        var note = document.getElementById(nt.id);
        if(intersectRect(nt, windowFrame)){//
            note.style.visibility = "visible"
            note.style.left = projectX(nt.x)+"px";
            note.style.top = projectY(nt.y)+"px";
            note.style.width = nt.w*heightScaleFactor()+"px";
            note.style.height = nt.h*heightScaleFactor()+"px";
            note.style.fontSize = nt.fontSize*heightScaleFactor()+"px";
            note.style.lineHeight = nt.fontSize*heightScaleFactor()*1.1+"px";
        }else{
            note.style.visibility = "hidden"
        }
    }
}

function canvasOnMouseDownHandler(event){
    if(event.button==0){
        pushLeft = true;
        XonPush = event.clientX;
        YonPush = event.clientY;
        eyeXOnPush = eyeX;
        eyeYOnPush = eyeY;
        updateCanvas();
        event.preventDefault();
    }
}
function canvasOnMouseUpHandler(event){
    if(event.button==0){ //right is 2 !!
        pushLeft = false;
        updateCanvas();
        event.preventDefault();
    }
}
function canvasOnMouseMoveHandler(event){
    if(pushLeft){
        var xrel = event.clientX - XonPush, yrel = event.clientY - YonPush;
        eyeX = eyeXOnPush - xrel*eyeZ/1000; // eyez/1000 is the transform factor practically
        eyeY = eyeYOnPush - yrel*eyeZ/1000;
        updateCanvas();
    }
    event.preventDefault();
}
function canvasMouseWheelHandler(event){
      if (event.ctrlKey) {
        // Your zoom/scale factor
        eyeZ = stop(eyeZ - MOVE_SPEED, 1, 1000);
      } else {
        // Your trackpad X and Y positions
        eyeZ = stop(eyeZ + event.deltaY*MOVE_SPEED/120, 1, 1000);
      }
      updateCanvas();
      event.preventDefault();
      return false
}

canvas.addEventListener("mousedown", canvasOnMouseDownHandler);
canvas.addEventListener("mouseup", canvasOnMouseUpHandler);
canvas.addEventListener("mousemove", canvasOnMouseMoveHandler);
window.addEventListener("wheel", canvasMouseWheelHandler, false);

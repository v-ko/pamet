// Get the root element
var r = document.querySelector(':root');
var map_page = document.getElementById("mapPage");
var pushLeft = false;
var eyeX = 0;
var eyeY = 0;
var viewportHeight = 25
var XonPush = 0;
var YonPush = 0;
var eyeXOnPush = 0;
var eyeYOnPush = 0;
const MOVE_STEP = 5;

function getViewportHeight() {
    var rs = getComputedStyle(r);
    return 20.0 / parseFloat(rs.getPropertyValue('--map-scale'));
}

function heightScaleFactor(){
    return 20.0 / viewportHeight
}

function setViewportHeight(new_val) {
    console.log('Height set to ' + new_val)
    viewportHeight = new_val
    r.style.setProperty('--map-scale', heightScaleFactor());
}

function getViewportPosition() {
    var rs = getComputedStyle(r);
    var x = parseFloat(rs.getPropertyValue('--map-translate-x'));
    var y = parseFloat(rs.getPropertyValue('--map-translate-y'));
    return [x, y];
}

function setViewportPosition(x, y) {
    console.log('Position set to ' + x + ', ' + y)
    eyeX = x
    eyeY = y
    x = x * heightScaleFactor()
    y = y * heightScaleFactor()
    r.style.setProperty('--map-translate-x', (-x) + 'px');
    r.style.setProperty('--map-translate-y', (-y) + 'px');
}

function mouseWheelHandler(event) {
    new_height = getViewportHeight() + MOVE_STEP * event.deltaY / 120
    setViewportHeight(new_height)
}

function mouseDownHandler(event) {
    if (event.button == 0) {
        console.log('Push')
        pushLeft = true;
        XonPush = event.clientX;
        YonPush = event.clientY;
        eyeXOnPush = eyeX;
        eyeYOnPush = eyeY;
        // updateCanvas();
        event.preventDefault();
    }
}
function mouseUpHandler(event) {
    if (event.button == 0) { //right is 2 !!
        console.log('Finishing click')
        pushLeft = false;
        // updateCanvas();
        event.preventDefault();
    }
}
function mouseMoveHandler(event) {
    if (pushLeft) {
        var xrel = event.clientX - XonPush, yrel = event.clientY - YonPush;
        viewport_height = getViewportHeight()
        viewport_pos = getViewportPosition()
        console.log('eye on push: ' + eyeXOnPush + ', ' + eyeYOnPush)
        console.log('delta: ' + xrel + ', ' + yrel)
        eyeX = eyeXOnPush - xrel /heightScaleFactor();
        eyeY = eyeYOnPush - yrel /heightScaleFactor();
        setViewportPosition(eyeX, eyeY)
    }
    event.preventDefault();
}

setViewportHeight(viewportHeight)
setViewportPosition(eyeX, eyeY)

window.addEventListener("wheel", mouseWheelHandler, false);
window.addEventListener("mousedown", mouseDownHandler);
window.addEventListener("mouseup", mouseUpHandler);
window.addEventListener("mousemove", mouseMoveHandler);

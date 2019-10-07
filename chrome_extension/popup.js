/*
 * Real-Time Tab Sync
 *
 * Author: Petko Ditchev
 *
*/

var debuggingMode = true;
/*var port = connectNative('org.sofia.playlistserver');
port.onMessage.addListener(function(msg) {
	console.log("Received" + msg);
});
port.onDisconnect.addListener(function() {
	console.log("Disconnected");
});*/

window.onload = function(){
	chrome.runtime.sendNativeMessage("org.sofia.playlistserver",{text:"messssssg"},function (msg) { console.log(msg); });
};


function debug() {
    if( debuggingMode ){
        chrome.extension.getBackgroundPage().console.log.apply( this, arguments );
    }
}

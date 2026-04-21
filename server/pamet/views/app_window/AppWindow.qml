import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtWebEngine

ApplicationWindow {
    id: root
    width: 800
    height: 600
    visible: true
    title: "Pamet"
    flags: Qt.FramelessWindowHint | Qt.Window
    visibility: Window.Maximized

    // `appState` and `backend` are set via QQmlContext.setContextProperty from Python

    color: palette.window

    property bool _isMax: root.visibility === Window.Maximized
    property int _grip: 5

    // Close window when last tab is closed
    Connections { target: appState ?? null; function onClose_last_tab() { root.close() } }

    // Dynamic window title
    onTitleChanged: {}  // let binding do the work
    Binding {
        target: root
        property: "title"
        value: {
            if (!appState) return "Pamet"
            let idx = appState.currentTabIndex
            if (idx < 0) return "Pamet"
            let t = tabBar.contentChildren[idx]?.text ?? ""
            return t ? "Pamet — " + t : "Pamet"
        }
    }

    // ── Frameless resize edges (in Overlay so coords cover full window) ──
    component ResizeEdge: MouseArea {
        required property int edges
        hoverEnabled: true
        cursorShape: {
            if (root._isMax) return Qt.ArrowCursor
            let e = edges
            let L = Qt.LeftEdge, R = Qt.RightEdge, T = Qt.TopEdge, B = Qt.BottomEdge
            if ((e & L) && (e & T) || (e & R) && (e & B)) return Qt.SizeFDiagCursor
            if ((e & R) && (e & T) || (e & L) && (e & B)) return Qt.SizeBDiagCursor
            if (e & (L | R)) return Qt.SizeHorCursor
            return Qt.SizeVerCursor
        }
        onPressed: function(mouse) {
            if (!root._isMax) root.startSystemResize(edges)
        }
    }
    Item {
        parent: Overlay.overlay
        anchors.fill: parent
        ResizeEdge { edges: Qt.LeftEdge; x: 0; y: _grip; width: _grip; height: root.height - 2 * _grip; z: 100 }
        ResizeEdge { edges: Qt.RightEdge; x: root.width - _grip; y: _grip; width: _grip; height: root.height - 2 * _grip; z: 100 }
        ResizeEdge { edges: Qt.TopEdge; x: _grip; y: 0; width: root.width - 2 * _grip; height: _grip; z: 100 }
        ResizeEdge { edges: Qt.BottomEdge; x: _grip; y: root.height - _grip; width: root.width - 2 * _grip; height: _grip; z: 100 }
        ResizeEdge { edges: Qt.LeftEdge | Qt.TopEdge; x: 0; y: 0; width: _grip; height: _grip; z: 101 }
        ResizeEdge { edges: Qt.RightEdge | Qt.TopEdge; x: root.width - _grip; y: 0; width: _grip; height: _grip; z: 101 }
        ResizeEdge { edges: Qt.LeftEdge | Qt.BottomEdge; x: 0; y: root.height - _grip; width: _grip; height: _grip; z: 101 }
        ResizeEdge { edges: Qt.RightEdge | Qt.BottomEdge; x: root.width - _grip; y: root.height - _grip; width: _grip; height: _grip; z: 101 }

        // Window border when not maximized
        Rectangle {
            anchors.fill: parent; visible: !root._isMax; z: 102
            color: "transparent"; border.width: 1
            border.color: Qt.rgba(palette.text.r, palette.text.g, palette.text.b, 0.15)
        }
    }

    // ── Title bar ───────────────────────────────────────────────────
    header: Rectangle {
        id: titleBar
        height: 42
        color: palette.window

        // Window drag on all empty title bar space
        DragHandler { target: null; onActiveChanged: if (active) root.startSystemMove() }

        // Bottom separator
        Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: palette.mid }

        RowLayout {
            anchors.fill: parent
            anchors.margins: 4
            spacing: 2

            ToolButton {
                Layout.fillHeight: true; Layout.preferredWidth: height
                icon.name: "go-previous"; icon.color: palette.buttonText; focusPolicy: Qt.TabFocus
                enabled: appState ? appState.canGoBack : false
                onClicked: { if (!appState) return; let v = webViewRepeater.itemAt(appState.currentTabIndex); if (v) v.goBack() }
            }
            ToolButton {
                Layout.fillHeight: true; Layout.preferredWidth: height
                icon.name: "media-playlist-shuffle"; icon.color: palette.buttonText; focusPolicy: Qt.TabFocus
                onClicked: { if (backend) backend.toggleShell() }
            }
            ToolButton {
                Layout.fillHeight: true; Layout.preferredWidth: height
                icon.name: "go-next"; icon.color: palette.buttonText; focusPolicy: Qt.TabFocus
                enabled: appState ? appState.canGoForward : false
                onClicked: { if (!appState) return; let v = webViewRepeater.itemAt(appState.currentTabIndex); if (v) v.goForward() }
            }

            TabBar {
                id: tabBar
                Layout.fillWidth: true; Layout.fillHeight: true
                topPadding: 0; bottomPadding: 0
                currentIndex: appState ? appState.currentTabIndex : 0
                onCurrentIndexChanged: { if (backend) backend.switchToTab(currentIndex) }
                background: Item {}

                Repeater {
                    model: appState ? appState.tabModel : null
                    TabButton {
                        id: tabBtn
                        text: model.title || "Untitled"
                        width: Math.min(implicitWidth + 40, 240)
                        anchors.top: parent ? parent.top : undefined
                        anchors.bottom: parent ? parent.bottom : undefined
                        leftPadding: 10; rightPadding: 28
                        font.pixelSize: 14

                        background: Rectangle {
                            anchors.fill: parent
                            radius: 6
                            color: tabBtn.checked ? Qt.rgba(palette.text.r, palette.text.g, palette.text.b, 0.1)
                                 : tabBtn.hovered ? Qt.rgba(palette.text.r, palette.text.g, palette.text.b, 0.06)
                                 : "transparent"
                        }

                        contentItem: Text {
                            text: tabBtn.text
                            color: palette.windowText
                            elide: Text.ElideRight
                            verticalAlignment: Text.AlignVCenter
                            font: tabBtn.font
                        }

                        ToolButton {
                            id: closeBtn
                            implicitHeight: 20; implicitWidth: 20; padding: 0
                            icon.name: "window-close"; icon.color: palette.buttonText
                            anchors.right: parent.right; anchors.rightMargin: 4
                            anchors.verticalCenter: parent.verticalCenter
                            onClicked: backend.closeTab(index)
                            background: Rectangle {
                                radius: 10
                                color: closeBtn.hovered ? Qt.rgba(1, 0, 0, 0.15) : "transparent"
                            }
                        }

                        MouseArea {
                            anchors.fill: parent
                            acceptedButtons: Qt.MiddleButton
                            onClicked: backend.closeTab(index)
                        }
                    }
                }
            }

            // Spacer
            Item { Layout.fillWidth: true; Layout.minimumWidth: 20; Layout.fillHeight: true }

            ToolButton {
                Layout.fillHeight: true; Layout.preferredWidth: height
                icon.name: "window-minimize"; icon.color: palette.buttonText; focusPolicy: Qt.TabFocus
                onClicked: root.showMinimized()
            }
            ToolButton {
                Layout.fillHeight: true; Layout.preferredWidth: height
                icon.name: root._isMax ? "window-restore" : "window-maximize"
                icon.color: palette.buttonText; focusPolicy: Qt.TabFocus
                onClicked: root._isMax ? root.showNormal() : root.showMaximized()
            }
            ToolButton {
                Layout.fillHeight: true; Layout.preferredWidth: height
                icon.name: "window-close"; icon.color: palette.buttonText; focusPolicy: Qt.TabFocus
                onClicked: root.close()
            }
        }
    }

    // ── Shared web engine profile with desktop config injection ────
    WebEngineProfile {
        id: webProfile
        storageName: "pamet-desktop-qml"
        Component.onCompleted: {
            userScripts.collection = [{
                name: "desktopConfig",
                sourceCode: backend.injectionScript,
                injectionPoint: WebEngineScript.DocumentCreation,
                worldId: WebEngineScript.MainWorld
            }]
        }
    }

    // ── Content area ────────────────────────────────────────────────
    SplitView {
        id: contentSplit
        anchors.fill: parent
        orientation: Qt.Vertical

        StackLayout {
            id: webViewStack
            SplitView.fillWidth: true; SplitView.fillHeight: true
            currentIndex: appState ? appState.currentTabIndex : 0
            onCurrentIndexChanged: {
                if (!backend) return
                let v = webViewRepeater.itemAt(currentIndex)
                if (v) backend.updateNavState(v.canGoBack, v.canGoForward)
                else backend.updateNavState(false, false)
                // Rebind dev tools to the newly active tab
                if (devToolsView.visible) {
                    if (v) v.devToolsView = devToolsView
                }
            }

            Repeater {
                id: webViewRepeater
                model: appState ? appState.tabModel : null
                WebEngineView {
                    id: webView
                    url: model.url
                    profile: webProfile

                    onLoadingChanged: function(loadReq) {
                        if (loadReq.status === WebEngineView.LoadSucceededStatus) {
                            if (webViewStack.currentIndex === index)
                                webView.forceActiveFocus()
                        } else if (loadReq.status === WebEngineView.LoadFailedStatus) {
                            console.log("Page load failed: " + loadReq.errorString
                                + " (Maybe the frontend server is not started?)")
                        }
                    }
                    onNavigationRequested: function(request) {
                        let url = request.url.toString()
                        if (request.isMainFrame && !backend.isInternalUrl(url)) {
                            request.reject()
                            backend.openInSystemBrowser(url)
                        }
                    }
                    onNewWindowRequested: function(request) {
                        backend.openTab(request.requestedUrl.toString(), false)
                    }
                    onTitleChanged: backend.updateTabTitle(index, title)
                    onUrlChanged: {
                        backend.updateTabUrl(index, webView.url.toString())
                        if (webViewStack.currentIndex === index)
                            backend.updateNavState(webView.canGoBack, webView.canGoForward)
                    }
                    onJavaScriptConsoleMessage: function(level, message, lineNumber, sourceId) {
                        let tag = level === 0 ? "js:info" : level === 1 ? "js:warn" : "js:error"
                        console.log(tag + ": " + message)
                    }
                }
            }
        }

        // Dev tools inspector panel
        WebEngineView {
            id: devToolsView
            SplitView.fillWidth: true
            SplitView.preferredHeight: contentSplit.height / 3
            visible: false
        }
    }

    // Show/hide dev tools from backend signal
    Connections {
        target: backend ?? null
        function onDevToolsVisibleChanged() {
            let show = backend.devToolsVisible
            if (show) {
                let v = webViewRepeater.itemAt(webViewStack.currentIndex)
                if (v) v.devToolsView = devToolsView
                devToolsView.visible = true
            } else {
                devToolsView.visible = false
            }
        }
    }

    // Responsive dev tools orientation
    onWidthChanged: _updateDevToolsOrientation()
    onHeightChanged: _updateDevToolsOrientation()
    function _updateDevToolsOrientation() {
        if (!devToolsView.visible) return
        let ratio = root.width / (root.height || 1)
        contentSplit.orientation = ratio > 1.3 ? Qt.Horizontal : Qt.Vertical
    }

    // ── Keyboard shortcuts ──────────────────────────────────────────
    Shortcut { sequence: "Ctrl+W"; onActivated: backend.closeCurrentTab() }
    Shortcut { sequence: "Ctrl+Shift+C"; onActivated: backend.toggleDevTools() }
    Shortcut { sequence: "Ctrl+Tab"; onActivated: backend.nextTab() }
    Shortcut { sequence: "Ctrl+Shift+Tab"; onActivated: backend.previousTab() }
    Shortcut { sequence: "Ctrl+T"; onActivated: backend.openNewTab() }
    Shortcut { sequence: "Ctrl+Shift+T"; onActivated: backend.restoreTab() }
    Shortcut {
        sequence: "Alt+Left"
        onActivated: {
            if (!appState) return
            let v = webViewRepeater.itemAt(appState.currentTabIndex)
            if (v && v.canGoBack) v.goBack()
        }
    }
    Shortcut {
        sequence: "Alt+Right"
        onActivated: {
            if (!appState) return
            let v = webViewRepeater.itemAt(appState.currentTabIndex)
            if (v && v.canGoForward) v.goForward()
        }
    }
    Shortcut {
        sequence: "Ctrl+R"
        onActivated: {
            if (!appState) return
            let v = webViewRepeater.itemAt(appState.currentTabIndex)
            if (v) v.reload()
        }
    }
    Shortcut { sequence: "Ctrl+1"; onActivated: backend.switchToTab(0) }
    Shortcut { sequence: "Ctrl+2"; onActivated: backend.switchToTab(1) }
    Shortcut { sequence: "Ctrl+3"; onActivated: backend.switchToTab(2) }
    Shortcut { sequence: "Ctrl+4"; onActivated: backend.switchToTab(3) }
    Shortcut { sequence: "Ctrl+5"; onActivated: backend.switchToTab(4) }
    Shortcut { sequence: "Ctrl+6"; onActivated: backend.switchToTab(5) }
    Shortcut { sequence: "Ctrl+7"; onActivated: backend.switchToTab(6) }
    Shortcut { sequence: "Ctrl+8"; onActivated: backend.switchToTab(7) }
    Shortcut { sequence: "Ctrl+9"; onActivated: backend.switchToTab(8) }
}

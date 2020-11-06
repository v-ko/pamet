import time

from PySide2.QtWidgets import QGraphicsView, QGraphicsScene
from PySide2.QtCore import Qt, QPointF, QObject
from PySide2.QtGui import QTransform

from misli import log
from misli.core import Note
from misli.gui import MOVE_SPEED
from misli.gui.qt.viewport import Viewport
from misli.gui.qt.note_widget_box import NoteWidgetItem


# от map_page-a
# from misli.gui.qt.map_canvas_view import MapCanvasView
# from misli.gui.qt.map_canvas_view import MapCanvasGraphicsScene
        # map_page = MapCanvasView(self)
        # self.ui.tabWidget.addTab(map_page.view, "test tab")


class NoteWidgetItem(QGraphicsProxyWidget):
    def __init__(self, note, parent=None):
        super(NoteWidgetItem, self).__init__()
        self._note = None
        self.widget = None
        self.parent = parent

        self.setNote(note)

    @property
    def note(self):
        return self._note

    def setNote(self, note):
        self._note = note

        plugin_class_name = note._class + 'NoteWidget'
        if plugin_class_name not in noteWidgetPlugins:
            print('No plugin can handle note of type: %s' % note.type)

        NoteWidgetClass = noteWidgetPlugins[plugin_class_name]
        self.setWidget(NoteWidgetClass(note))
        self.setGeometry(note.rect)


class MapCanvasGraphicsScene(QGraphicsScene):
    def __init__(self, parent=None):
        super(MapCanvasGraphicsScene, self).__init__(parent=parent)
        self.setBackgroundBrush(Qt.white)


class MapCanvasGraphicsView(QGraphicsView):
    def __init__(self, scene, parent=None):
        super(MapCanvasGraphicsView, self).__init__(scene, parent=parent)

        # Nested classes
        class Activateable():
            def __init__(self, name):
                self._name = name
                self._isActive = False

            def isActive(self):
                return self._isActive

            def start(self):
                if self._isActive:
                    log.warning('Trying to start %s while it`s active' % self._name)
                    return

                log.info('Starting canvas drag')
                self._isActive = True

            def stop(self):
                if not self._isActive:
                    log.warning('Trying to stop %s while it`s inactive' % self._name)
                    return

                log.info('Stopping canvas drag')
                self._isActive = False

        # Class variables
        self.viewport = Viewport(self)

        self.canvasDrag = Activateable("canvasDrag")
        self.viewportPosOnPress = QPointF()
        self.mousePosOnPress = QPointF()

        # Widget properties config
        pal = self.palette()
        pal.setColor(pal.Window, Qt.white)

        self.setPalette(pal)
        self.setMouseTracking(1)
        self.setFocusPolicy(Qt.ClickFocus)
        self.setAcceptDrops(True)
        self.setAutoFillBackground(True)

    def update_viewport(self):
        scale = self.viewport.heightScaleFactor()
        transform = QTransform()
        center = self.viewport.center

        transform.scale(scale, scale)
        transform.translate(center.x(), center.y())

        self.setTransform(transform)
        self.centerOn(center)

    def mousePressEvent(self, event):
        if event.button() is Qt.LeftButton:

            self.mousePosOnPress = event.pos()
            self.viewportPosOnPress = self.viewport.center
            self.canvasDrag.start()

    def mouseReleaseEvent(self, event):
        if event.button() is Qt.LeftButton:

            if self.canvasDrag.isActive():
                self.canvasDrag.stop()

    def mouseMoveEvent(self, event):

        if self.canvasDrag.isActive():
            delta = QPointF(self.mousePosOnPress - event.pos())
            unprojectedDelta = delta / self.viewport.heightScaleFactor()
            self.viewport.center = self.viewportPosOnPress + unprojectedDelta
            # self.updateNotesDisplay()
            self.update_viewport()

        self.lastMousePosition = event.pos()

    def wheelEvent(self, event):
        global defaultFontSize
        numDegrees = event.delta() / 8
        numSteps = numDegrees / 15

        self.viewport.eyeHeight -= MOVE_SPEED * numSteps
        self.viewport.eyeHeight = max(1, min(self.viewport.eyeHeight, 1000))

        self.update_viewport()
        # //glutPostRedisplay(); artefact, thank you for siteseeing

    # def resizeEvent(self, event):
    #     self.update()


class MapCanvasView(QObject):
    def __init__(self, parent=None):
        super(MapCanvasView, self).__init__(parent=parent)

        self.scene = MapCanvasGraphicsScene(self)
        self.view = MapCanvasGraphicsView(self.scene)

        self._canvas = None
        self.note_boxes = []

        # Self config
        self.setCanvas(None)

    @property
    def canvas(self):
        return self._canvas

    def setCanvas(self, canvas):
        if self._canvas == canvas:
            return

        if not canvas:
            self.view.hide()
            return

        if self.view.isHidden():
            self.view.show()

        self._canvas = canvas

        self.load_note_widgets()
        # for nt in self._canvas.notes:
        #     self.scene.addRect(nt.rect)
        # self.update()

    def load_note_widgets(self):
        load_time = time.time()

        for nt in self._canvas.notes:
            note_widget_item = NoteWidgetItem(
                Note(**nt.__dict__), parent=self)

            self.scene.addItem(note_widget_item)

            if note_widget_item:
                self.note_boxes.append(note_widget_item)

        print('Note load time: %s' % (load_time - time.time()))

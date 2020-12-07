import time

from PySide2.QtWidgets import QWidget, QApplication
from PySide2.QtCore import Qt, QRectF, QSizeF, QPointF, QPoint
from PySide2.QtGui import QPainter, QPicture

from misli import log
from misli.objects import Note
from misli.constants import MOVE_SPEED, MIN_HEIGHT_SCALE, MAX_HEIGHT_SCALE
from misli.gui.map_page.viewport import Viewport
from misli.gui.notes.note_widget_box import NoteWidgetBox


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

        log.warning('Starting canvas drag')
        self._isActive = True

    def stop(self):
        if not self._isActive:
            log.warning('Trying to stop %s while it`s inactive' % self._name)
            return

        log.info('Stopping canvas drag')
        self._isActive = False


class MapPageComponent(QWidget):
    def __init__(self, page=None):
        super(MapPageComponent, self).__init__()

        # Class variables
        self._canvas = None
        self.noteBoxes = []

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

        # Self config
        self.setCanvas(None)

    @property
    def canvas(self):
        return self._canvas

    def setCanvas(self, canvas):
        if self._canvas == canvas:
            return

        if not canvas:
            self.hide()
            return

        if self.isHidden():
            self.show()

        self._canvas = canvas

        self.loadNoteWidgets()
        self.update()

    def loadNoteWidgets(self):
        if self.noteBoxes:
            return

        for nt in self.canvas.notes:
            noteBox = NoteWidgetBox(Note(**nt.__dict__), parent=self)

            if noteBox:
                self.noteBoxes.append(noteBox)

    def controlIsPressed(self):
        return QApplication.keyboardModifiers().testFlag(Qt.ControlModifier)

    def shiftIsPressed(self):
        return QApplication.keyboardModifiers().testFlag(Qt.ShoftModifier)

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
            self.update()

        self.lastMousePosition = event.pos()

    def wheelEvent(self, event):
        numDegrees = event.delta() / 8
        numSteps = numDegrees / 15

        delta = MOVE_SPEED * numSteps
        self.viewport.eyeHeight -= delta
        self.viewport.eyeHeight = max(
            MIN_HEIGHT_SCALE,
            min(self.viewport.eyeHeight, MAX_HEIGHT_SCALE))

        log.info(
            'Wheel event. Delta: %s . Eye height: %s' %
            (delta, self.viewport.eyeHeight))

        self.update()
        # //glutPostRedisplay(); artefact, thank you for siteseeing

    def paintEvent(self, event):
        paintStartTime = time.time()

        painter = QPainter()
        # get font size in pixels via fontmetrics

        painter.begin(self)

        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)

        pen = painter.pen()
        pen.setCosmetic(True)
        painter.setPen(pen)

        scaleFactor = self.viewport.heightScaleFactor()
        translation = QPointF(self.rect().center()) / scaleFactor
        translation -= self.viewport.center

        painter.scale(scaleFactor, scaleFactor)
        painter.translate(translation.x(), translation.y())

        canvasViewport = QRectF()
        canvasViewport.setSize(QSizeF(
            self.width() / self.viewport.heightScaleFactor(),
            self.height() / self.viewport.heightScaleFactor()))
        canvasViewport.moveCenter(
            QPointF(self.viewport.center.x(), self.viewport.center.y()))

        render_time_sum = 0
        play_time_sum = 0

        for nb in self.noteBoxes:
            if not nb.note.rect.intersects(canvasViewport):
                continue

            if nb.widget:
                painter.save()
                painter.translate(nb.note.rect.topLeft())

                # In order to be pixel perfect - relay through QPicture
                # Otherwise QWidget rounds up coordinates.
                # RIP 30 hours of trying other workarounds

                if not nb.qpainter_command_cache:
                    render_start = time.time()
                    nb.qpainter_command_cache = QPicture()
                    nb.widget.render(nb.qpainter_command_cache, QPoint(0, 0))
                    render_time_sum += time.time() - render_start

                play_start = time.time()
                nb.qpainter_command_cache.play(painter)
                play_time_sum += time.time() - play_start

                painter.restore()

        # print('Render time sum: %s ms' % (1000 * render_time_sum))
        # print('Play time sum: %s ms' % (1000 * play_time_sum))

        painter.end()

        print('Paint event latency: %s ms' %
              int(1000 * (time.time() - paintStartTime)))

    def resizeEvent(self, event):
        self.update()

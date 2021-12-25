"""
file: letItSnow.py
info: A PySide2 widget that allows you to add snow to any other widget
"""
import sys
from random import randint
from PySide2 import QtWidgets, QtCore, QtGui


class Snowflake(QtWidgets.QGraphicsItem):
    def __init__(self, diameter=5, startX=0.0):
        # type: (int, float) -> None
        super(Snowflake, self).__init__()
        self.loops = 0
        self.diameter = diameter
        self._startX = startX
        self._startY = -self.diameter * float(randint(1, 20))
        self.speed = float(randint(10, 50)) / 50.0
        self.drift = float(randint(-5, 5)) / 5.0

    @property
    def startX(self):
        return self._startX * self.scene().width()

    @property
    def startY(self):
        return self._startY

    @property
    def startPos(self):
        return QtCore.QPointF(self.startX, self.startY)

    def boundingRect(self):
        penWidth = 1.0
        return QtCore.QRectF(-10 - penWidth / 2, -10 - penWidth / 2, 20 + penWidth, 20 + penWidth)

    def paint(self, painter, option, *args, **kwargs):
        snowColor = QtGui.QColor(200, 200, 200, 255)
        center = QtCore.QPointF(self.pos().x() + self.diameter / 2.0, self.pos().y() + self.diameter / 2.0)
        gradient = QtGui.QRadialGradient()
        gradient.setCenter(center)
        gradient.setCenterRadius(self.diameter / 2)
        gradient.setFocalPoint(center)
        # gradient.setFocalRadius(self.diameter / 10)
        gradient.setColorAt(0, snowColor)
        gradient.setColorAt(1, QtGui.QColor(0, 0, 0, 0))
        snowBrush = QtGui.QBrush(gradient)
        painter.setBrush(snowBrush)
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawEllipse(self.pos().x(), self.pos().y(), self.diameter, self.diameter)

    def advance(self, phase):
        # type: (int) -> None
        if not phase == 1:
            return
        xPos = self.pos().x()
        yPos = self.pos().y()
        if self.loops == 0:
            xPos = self.startX
            yPos = self.startY
            self.loops += 1
        pos = QtCore.QPointF(xPos, yPos)
        pos.setX(pos.x() + self.drift * self.speed)
        pos.setY(pos.y() + 1 * self.speed)
        # Move to top if outside of scene bounds
        # NOTE: mapToScene(pos) != scenePos()
        scenePos = self.mapToScene(self.pos()).y()
        if scenePos >= self.scene().height():
            pos = self.startPos
            self.loops += 1
        self.setPos(pos)


class LetItSnow(QtWidgets.QWidget):
    def __init__(self, snowFlakeCount=100, parent=None):
        # type: (int, QtWidgets.QWidget) -> None
        super(LetItSnow, self).__init__(parent=parent)
        # ATTRIBUTES
        # --------------------
        self.snowFlakeCount = snowFlakeCount
        self.spawnRate = 1  # How many snowFlakes are emitted per frame
        # UI
        # --------------------
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
        self._graphicsScene = QtWidgets.QGraphicsScene()
        self._graphicsScene.setItemIndexMethod(QtWidgets.QGraphicsScene.NoIndex)
        self._graphicsView = QtWidgets.QGraphicsView(self._graphicsScene)
        self._graphicsView.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
        self._graphicsView.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self._graphicsView.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        bgColor = QtGui.QColor(0, 0, 0, 0)
        bgBrush = QtGui.QBrush(bgColor)
        self._graphicsScene.setBackgroundBrush(bgBrush)
        self._graphicsView.setStyleSheet("border: 0px")
        self.setStyleSheet('''QWidget{background: transparent;}''')
        # Assemble
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._graphicsView)
        # EVENTS
        # --------------------
        self.timeline = QtCore.QTimeLine()
        self.timeline.setFrameRange(0, 100)
        self.timeline.setLoopCount(0)
        self.timeline.setEasingCurve(QtCore.QEasingCurve.Linear)
        self.timeline.valueChanged.connect(self._update)

    def showEvent(self, event):
        if self.timeline.state() is not QtCore.QTimeLine.State.Running:
            self.timeline.start()
        self._fitScene()

    def hideEvent(self, event):
        self.timeline.stop()

    def resizeEvent(self, event):
        self._fitScene()

    def paintEvent(self, event):
        parent = self.parent()
        if parent:
            parentSize = parent.size()
            if self.size() != parentSize:
                self.resize(parentSize)

    def _fitScene(self):
        self._graphicsScene.setSceneRect(self.rect())
        self._graphicsView.setResizeAnchor(QtWidgets.QGraphicsView.AnchorViewCenter)

    def _update(self):
        snowFlakes = self._graphicsScene.items(self._graphicsScene.sceneRect())
        if len(snowFlakes) < self.snowFlakeCount:
            diameter = randint(3, 10)
            startX = float(randint(0, int(self.width()))) / self.width()
            snowFlake = Snowflake(diameter=diameter, startX=startX)
            self._graphicsScene.addItem(snowFlake)
        self._graphicsScene.update()
        self._graphicsScene.advance()


if __name__ == "__main__":
    app = QtWidgets.QApplication()
    widget = LetItSnow()
    widget.show()
    sys.exit(app.exec_())

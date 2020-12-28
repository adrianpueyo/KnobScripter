import nuke

try:
    if nuke.NUKE_VERSION_MAJOR < 11:
        from PySide import QtCore, QtGui, QtGui as QtWidgets
        from PySide.QtCore import Qt
    else:
        from PySide2 import QtWidgets, QtGui, QtCore
        from PySide2.QtCore import Qt
except ImportError:
    from Qt import QtCore, QtGui, QtWidgets


class CodeGallery(QtWidgets.QDialog):
    def __init__(self, knobScripter="", _parent=QtWidgets.QApplication.activeWindow()):
        super(CodeGallery, self).__init__()

        self.knobScripter = knobScripter
        self.setWindowTitle("Code Gallery + Snippet Editor")

        self.initUI()
        # self.resize(500,300)

    def initUI(self):
        master_layout = QtWidgets.QVBoxLayout()

        test_label = QtWidgets.QLabel("test")
        master_layout.addWidget(test_label)
        master_layout.addWidget(ToggableGroup(self))

        self.setLayout(master_layout)


# class CodeGalleryPane(CodeGallery)
# def __init__(self, node = "", knob="knobChanged"):
#        super(KnobScripterPane, self).__init__(isPane=True, _parent=QtWidgets.QApplication.activeWindow())
# TODO Pane instead, its own thing
# TODO: Snippets: button to delete snippet, add snippet to script
# TODO: Snippet editor and preferences apply changes (via "Reload Snippets and Settings button or whatever...") on all knobscripters? (by having a set of the active knobscripters and removing them on close)


class ToggableGroup(QtWidgets.QFrame):
    """ QFrame with an arrow, a title area and a toggable content layout. """
    def __init__(self, parent=None):
        super(ToggableGroup, self).__init__(parent)

        self.collapsed = False

        # Widgets and layouts

        self.arrow = Arrow()

        # Layout
        # 1. Top Layout
        # Left (clickable) part, for the title
        self.top_clickable_layout = QtWidgets.QVBoxLayout()
        self.top_clickable_widget = ClickableWidget()
        self.top_clickable_widget.clicked.connect(self.toggleCollapsed)
        self.top_clickable_widget.setLayout(self.top_clickable_layout)

        #temp
        self.top_clickable_layout.addWidget(QtWidgets.QLabel("This is a test..."))

        # Right (non-clickable) part, for buttons or extras
        self.top_right_layout = QtWidgets.QHBoxLayout()

        # Together
        top_layout = QtWidgets.QHBoxLayout()
        top_layout.addWidget(self.top_clickable_widget)
        top_layout.addLayout(self.top_right_layout)

        # 2. Main content area
        self.content_layout = QtWidgets.QVBoxLayout()

        # 3. Vertical layout of 1 and 2
        v_layout = QtWidgets.QVBoxLayout()
        v_layout.addLayout(top_layout)
        v_layout.addLayout(self.content_layout)

        # 4. HLayout of arrow and 3
        master_layout = QtWidgets.QHBoxLayout()
        master_layout.addWidget(self.arrow)
        master_layout.addLayout(v_layout)

        self.setLayout(master_layout)

    def toggleCollapsed(self):
        self.collapsed = not self.collapsed
        self.arrow.setExpanded(not self.arrow.expanded)
        print("Collapsed:"+str(self.collapsed))


class ClickableWidget(QtWidgets.QWidget):
    clicked = QtCore.Signal()
    def __init__(self, parent=None):
        super(ClickableWidget, self).__init__(parent)
        self.setMouseTracking(True)
        self.highlighted = False

    def setHighlighted(self, highlighted=False):
        self.highlighted = highlighted

    def enterEvent(self, event):
        ''' Mouse hovering '''
        self.setHighlighted(True)
        return True

    def leaveEvent(self, event):
        ''' Stopped hovering '''
        self.setHighlighted(False)
        return True

    def mouseReleaseEvent(self, event):
        ''' Emit clicked '''
        if self.highlighted:
            self.clicked.emit()
            pass
        super(ClickableWidget, self).mouseReleaseEvent(event)



class Arrow(QtWidgets.QFrame):
    def __init__(self, expanded=False, parent=None):
        super(Arrow, self).__init__(parent)
        self.setMaximumSize(24, 24)
        self.expanded = expanded

        self._arrow_down = [QtCore.QPointF(7.0, 8.0), QtCore.QPointF(17.0, 8.0), QtCore.QPointF(12.0, 13.0)]
        self._arrow_right = [QtCore.QPointF(8.0, 7.0), QtCore.QPointF(13.0, 12.0), QtCore.QPointF(8.0, 17.0)]
        self._arrowPoly = None
        self.setExpanded(expanded)

    def setExpanded(self, expanded=True):
        if expanded:
            self._arrowPoly = self._arrow_down
        else:
            self._arrowPoly = self._arrow_right

    def paintEvent(self, event):
        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setBrush(QtGui.QColor(192, 192, 192))
        painter.setPen(QtGui.QColor(64, 64, 64))
        painter.drawPolygon(self._arrowPoly)
        painter.end()
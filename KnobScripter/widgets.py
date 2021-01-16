import logging
from collections import OrderedDict
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

from scripteditor import ksscripteditor

class GripWidget(QtWidgets.QFrame):
    def __init__(self, parent=None, inner_widget = None, resize_x=False, resize_y=True):
        super(GripWidget, self).__init__(parent)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(inner_widget)
        layout.setMargin(0)
        self.setLayout(layout)

        cursor = None
        if resize_x and resize_y:
            cursor = Qt.SizeAllCursor
        elif resize_x:
            cursor = Qt.SplitHCursor
        elif resize_y:
            cursor = Qt.SplitVCursor

        self.setCursor(QtGui.QCursor(cursor))

        self.parent = parent
        self.resize_x = resize_x
        self.resize_y = resize_y
        self.parent_min_size = (10, 10)

        self.setMouseTracking(True)
        self.pressed = False
        self.click_pos = None
        self.click_offset = None

    def mousePressEvent(self, e):
        self.click_pos = self.mapToParent(e.pos())
        self.pressed = True
        g = self.parent.geometry()
        self.click_offset = [g.width() - self.click_pos.x(), g.height() - self.click_pos.y()]
        super(GripWidget, self).mousePressEvent(e)

    def mouseReleaseEvent(self, e):
        self.pressed = False
        super(GripWidget, self).mouseReleaseEvent(e)

    def mouseMoveEvent(self, e):
        if self.pressed:
            p = self.mapToParent(e.pos())
            if self.resize_x:
                self.parent.setFixedWidth(max(self.parent_min_size[0], p.x() + self.click_offset[0]))
            if self.resize_y:
                self.parent.setFixedHeight(max(self.parent_min_size[1], p.y() + self.click_offset[1]))

class HLine(QtWidgets.QFrame):
    def __init__(self):
        super(HLine, self).__init__()
        self.setFrameStyle(QtWidgets.QFrame.HLine | QtWidgets.QFrame.Sunken)
        self.setLineWidth(1)
        self.setMidLineWidth(0)
        self.setLayout(None)

class ClickableWidget(QtWidgets.QFrame):
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
        super(ClickableWidget, self).mouseReleaseEvent(event)
        if event.button() == Qt.LeftButton:
            if self.highlighted:
                self.clicked.emit()
                pass

class Arrow(QtWidgets.QFrame):
    def __init__(self, expanded=False, parent=None):
        super(Arrow, self).__init__(parent)
        self.padding = (4,2)
        self.setFixedSize(12+self.padding[0], 12+self.padding[1])

        self.expanded = expanded

        px,py = self.padding
        self._arrow_down = [QtCore.QPointF(0+px, 2.0+py), QtCore.QPointF(10.0+px, 2.0+py), QtCore.QPointF(5.0+px, 7.0+py)]
        self._arrow_right = [QtCore.QPointF(2.0+px, 0.0+py), QtCore.QPointF(7.0+px, 5.0+py), QtCore.QPointF(2.0+px, 10.0+py)]
        self._arrowPoly = None
        self.setExpanded(expanded)

    def setExpanded(self, expanded=True):
        if expanded:
            self._arrowPoly = self._arrow_down
        else:
            self._arrowPoly = self._arrow_right
        self.expanded = expanded

    def paintEvent(self, event):
        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setBrush(QtGui.QColor(192, 192, 192))
        painter.setPen(QtGui.QColor(64, 64, 64))
        painter.drawPolygon(self._arrowPoly)
        painter.end()

class ToggableGroup(QtWidgets.QFrame):
    """ Abstract QFrame with an arrow, a title area and a toggable content layout. """
    def __init__(self, parent=None, title="", collapsed=False):
        super(ToggableGroup, self).__init__(parent)

        self.collapsed = collapsed

        # Widgets and layouts
        self.arrow = Arrow(parent=self)

        # Layout
        # 1. Top Layout
        # Left (clickable) part, for the title
        self.top_clickable_widget = ClickableWidget()
        self.top_clickable_layout = QtWidgets.QHBoxLayout()
        self.top_clickable_layout.setSpacing(6)
        self.top_clickable_widget.setLayout(self.top_clickable_layout)
        #self.top_clickable_widget.setStyleSheet(".ClickableWidget{margin-top: 3px;background:transparent}")
        #self.top_clickable_widget.setStyleSheet("background:#000;float:left;")
        self.top_clickable_widget.clicked.connect(self.toggleCollapsed)


        # Right (non-clickable) part, for buttons or extras
        self.top_right_layout = QtWidgets.QHBoxLayout()

        self.top_clickable_layout.addWidget(self.arrow)
        self.title_label = QtWidgets.QLabel()
        self.title_label.setStyleSheet("line-height:50%;")
        self.title_label.setTextInteractionFlags(Qt.NoTextInteraction)
        self.title_label.setWordWrap(True)

        self.top_clickable_widget.setSizePolicy(QtWidgets.QSizePolicy.Preferred,QtWidgets.QSizePolicy.Preferred)
        self.setTitle(title)
        self.top_clickable_layout.addWidget(self.title_label)
        self.top_clickable_layout.addSpacing(1)
        self.top_clickable_layout.setAlignment(Qt.AlignVCenter)

        # Together
        self.top_layout = QtWidgets.QHBoxLayout()
        self.top_layout.addWidget(self.top_clickable_widget)
        self.top_layout.addLayout(self.top_right_layout)

        # 2. Main content area
        self.content_widget = QtWidgets.QFrame()
        self.content_widget.setObjectName("content-widget")
        self.content_widget.setStyleSheet("#content-widget{margin:6px 0px 5px 24px;}")
        self.content_layout = QtWidgets.QVBoxLayout()
        self.content_widget.setLayout(self.content_layout)
        #self.content_widget.setSizePolicy(QtWidgets.QSizePolicy.Expanding,QtWidgets.QSizePolicy.Expanding)

        # 3. Vertical layout of 1 and 2
        master_layout = QtWidgets.QVBoxLayout()
        master_layout.addLayout(self.top_layout)
        master_layout.addWidget(self.content_widget)

        self.setLayout(master_layout)
        self.setCollapsed(self.collapsed)

        master_layout.setMargin(0)
        self.content_layout.setMargin(0)
        self.content_layout.setSizeConstraint(self.content_layout.SetNoConstraint)
        self.setMinimumHeight(10)
        self.top_clickable_layout.setMargin(0)

    def setTitle(self,text=""):
        self.title_label.setText(text)

    def toggleCollapsed(self):
        self.collapsed = not self.collapsed
        self.setCollapsed(self.collapsed)

    def setCollapsed(self, collapsed=True):
        self.collapsed = collapsed
        self.arrow.setExpanded(not collapsed)
        self.content_widget.setVisible(not collapsed)
        logging.debug("Collapsed:"+str(collapsed))

#TODO THE NEXT ONE:
class ToggableCodeGroup(ToggableGroup):
    """ ToggableGroup adapted for having a code editor """

    def __init__(self, parent=None):
        self.prev_height = None
        super(ToggableCodeGroup, self).__init__(parent=parent)
        self.parent = parent

        # Add content
        self.script_editor = ksscripteditor.KSScriptEditor()
        self.script_editor.setMinimumHeight(20)

        self.content_layout.addWidget(self.script_editor)
        self.content_layout.setSpacing(1)

        self.grip_line = GripWidget(self, inner_widget=HLine())
        self.grip_line.setStyleSheet("GripWidget:hover{border: 1px solid #DDD;}")
        self.grip_line.parent_min_size = (100, 100)
        self.content_layout.addWidget(self.grip_line)

    def setCollapsed(self, collapsed=True):
        if collapsed:
            self.prev_height = self.height()
            self.setMinimumHeight(0)
        else:
            if self.prev_height:
                self.setFixedHeight(self.prev_height)

        super(ToggableCodeGroup, self).setCollapsed(collapsed)


class RadioSelector(QtWidgets.QWidget):
    radio_selected = QtCore.Signal(object)
    def __init__(self, item_list=None, orientation=0, parent=None):
        """
        item_list: list of strings
        orientation = 0 (h) or 1 (v)
        """
        super(RadioSelector, self).__init__(parent)
        self.item_list = item_list
        self.button_list = OrderedDict()
        for item in item_list:
            self.button_list[item] = QtWidgets.QRadioButton(item)


        if orientation == 0:
            self.layout = QtWidgets.QHBoxLayout()
        else:
            self.layout = QtWidgets.QVBoxLayout()

        self.button_group = QtWidgets.QButtonGroup(self)
        for i, btn in enumerate(self.button_list):
            self.button_group.addButton(self.button_list[btn], i)
            self.layout.addWidget(self.button_list[btn])
        self.button_group.buttonClicked.connect(self.button_clicked)

        self.layout.addStretch(1)

        self.setLayout(self.layout)
        self.layout.setMargin(0)

    def button_clicked(self, button):
        self.radio_selected.emit(str(button.text()))

    def set_button(self,text,emit=False):
        text = text.lower()
        item_list_lower = [i.lower() for i in self.item_list]
        if text in item_list_lower:
            btn = self.button_group.button(item_list_lower.index(text))
            btn.setChecked(True)
            if emit:
                self.radio_selected.emit(btn.text())
        else:
            logging.debug("Couldn't set radio button text.")

    def selected_text(self):
        return str(self.button_group.button(self.button_group.checkedId()).text())
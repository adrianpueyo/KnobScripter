import nuke
import logging

try:
    if nuke.NUKE_VERSION_MAJOR < 11:
        from PySide import QtCore, QtGui, QtGui as QtWidgets
        from PySide.QtCore import Qt
    else:
        from PySide2 import QtWidgets, QtGui, QtCore
        from PySide2.QtCore import Qt
except ImportError:
    from Qt import QtCore, QtGui, QtWidgets

from ..scripteditor.ksscripteditor import KSScriptEditor
from ..scripteditor.pythonhighlighter import KSPythonHighlighter

# TODO these panels should be global and not depend on a single knobscripter? they can have it still, but only useful when adding the snippet etc (and it can ask which knobscripter to Pick)
# TODO get the style from somewhere else, not the knobscripter
code_gallery_dict = {
    "blink" : [
        {
            "title": "Kernel skeleton",
            "desc": "Basic code structure for starting a Blink kernel.",
            "cat": ["Base codes"],
            "code": """\nkernel KernelName : ImageComputationKernel<ePixelWise>\n{\n  Image<eRead, eAccessPoint, eEdgeClamped> src;\n  Image<eWrite> dst;\n\n  param:\n\n\n  local:\n\n\n  void init() {\n\n  }\n\n  void process(int2 pos) {\n    dst() = src();\n  }\n};\n""",
        },
        {
            "title": "Process function",
            "desc": "Example template for the main processing function in Blink.",
            "cat":["Base codes"],
            "code": """void process() {\n    // Read the input image\n    SampleType(src) input = src();\n\n    // Isolate the RGB components\n    float3 srcPixel(input.x, input.y, input.z);\n\n    // Calculate luma\n    float luma = srcPixel.x * coefficients.x\n               + srcPixel.y * coefficients.y\n               + srcPixel.z * coefficients.z;\n    // Apply saturation\n    float3 saturatedPixel = (srcPixel - luma) * saturation + luma;\n\n    // Write the result to the output image\n    dst() = float4(saturatedPixel.x, saturatedPixel.y, saturatedPixel.z, input.w);\n  }"""
        },
        {
            "title": "Longer text? what would happen exactly? lets try it like right now yes yes yes yes yes ",
            "desc": "Example template for the main processing function in Blink. this is the same but with a way longer description to see what happens... lets see!!!!.",
            "cat":["Base codes"],
            "code": """void process() {\n    // Read the input image\n    SampleType(src) input = src();\n\n    // Isolate the RGB components\n    float3 srcPixel(input.x, input.y, input.z);\n\n    // Calculate luma\n    float luma = srcPixel.x * coefficients.x\n               + srcPixel.y * coefficients.y\n               + srcPixel.z * coefficients.z;\n    // Apply saturation\n    float3 saturatedPixel = (srcPixel - luma) * saturation + luma;\n\n    // Write the result to the output image\n    dst() = float4(saturatedPixel.x, saturatedPixel.y, saturatedPixel.z, input.w);\n  }"""
        },
    ],
    "python": [
        {
            "title": "print statement",
            "desc": "Simple print statement...",
            "cat": ["Base codes"],
            "code": """print("2")""",
        },
    ],
}



class CodeGalleryWidget(QtWidgets.QWidget):
    def __init__(self, knobScripter="", _parent=QtWidgets.QApplication.activeWindow()):
        super(CodeGalleryWidget, self).__init__(_parent)

        self.knobScripter = knobScripter
        if self.knobScripter:
            self.color_style_python = self.knobScripter.color_style_python
            self.color_style_blink = self.knobScripter.color_style_blink
        else:
            self.color_style_python = "sublime"
            self.color_style_blink = "default"
        self.color_style_python = "sublime"

        self.setWindowTitle("Code Gallery + Snippet Editor")

        self.initUI()
        # self.resize(500,300)

    def initUI(self):
        self.layout = QtWidgets.QVBoxLayout()

        # 1. Filters (language etc)

        # 2. Scroll Area
        # 2.1. Inner scroll content
        self.scroll_content = QtWidgets.QWidget()
        self.scroll_layout = QtWidgets.QVBoxLayout()
        self.scroll_content.setLayout(self.scroll_layout)
        self.scroll_content.setContentsMargins(0,0,8,0)

        self.build_gallery()
        #self.filter_gallery(lang="python")

        # 2.2. External Scroll Area
        self.scroll = QtWidgets.QScrollArea()
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setWidgetResizable(True)
        self.scroll.setWidget(self.scroll_content)

        self.layout.addWidget(self.scroll)

        #temp
        """
        tg = ToggableGroup(self)
        tg.setFrameStyle(QtWidgets.QFrame.Panel | QtWidgets.QFrame.Plain)

        tg.setStyleSheet(".ToggableGroup{border: 1px solid #222;padding:4px;}") #Dot makes it not inherited by sublasses
        """
        self.scroll_layout.setMargin(0)
        #master_layout.setSpacing(0)
        self.scroll_layout.addStretch()

        self.setLayout(self.layout)

    def build_gallery(self):
        for lang in code_gallery_dict.keys():
            tg = ToggableGroup(self)
            tg.setTitle("<big><b>{}</b></big>".format(lang))

            for code in code_gallery_dict[lang]:
                if all(i in code for i in ["title","code"]):
                    cgi = CodeGalleryItem(self)
                    # 1. Title/description
                    title = "<b>{0}</b>".format(code["title"])
                    if "desc" in code:
                        title += "<br><small style='color:#999'>{}</small>".format(code["desc"])
                    cgi.setTitle(title)

                    # 2. Content
                    highlighter = KSPythonHighlighter(cgi.script_editor.document())
                    highlighter.setStyle(self.color_style_python)

                    tg.content_layout.addWidget(cgi)

            self.scroll_layout.insertWidget(-1, tg)

    def filter_code(self, lang=None):
        """ Hide and show the widgets inside the scroll area based on selected parameters."""
        return True


# class CodeGalleryPane(CodeGallery)
# def __init__(self, node = "", knob="knobChanged"):
#        super(KnobScripterPane, self).__init__(isPane=True, _parent=QtWidgets.QApplication.activeWindow())
# TODO Pane instead, its own thing
# TODO: Snippets: button to delete snippet, add snippet to script
# TODO: Snippet editor and preferences apply changes (via "Reload Snippets and Settings button or whatever...") on all knobscripters? (by having a set of the active knobscripters and removing them on close)

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
        top_layout = QtWidgets.QHBoxLayout()
        top_layout.addWidget(self.top_clickable_widget)
        top_layout.addLayout(self.top_right_layout)

        # 2. Main content area
        self.content_widget = QtWidgets.QFrame()
        self.content_widget.setObjectName("content-widget")
        self.content_widget.setStyleSheet("#content-widget{margin:6px 0px 5px 24px;}")
        self.content_layout = QtWidgets.QVBoxLayout()
        self.content_widget.setLayout(self.content_layout)
        #self.content_widget.setSizePolicy(QtWidgets.QSizePolicy.Expanding,QtWidgets.QSizePolicy.Expanding)

        # 3. Vertical layout of 1 and 2
        master_layout = QtWidgets.QVBoxLayout()
        master_layout.addLayout(top_layout)
        master_layout.addWidget(self.content_widget)

        self.setLayout(master_layout)
        self.setCollapsed(self.collapsed)

        master_layout.setMargin(0)
        self.content_layout.setMargin(0)
        self.content_layout.setSizeConstraint(self.content_layout.SetNoConstraint)
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

class CodeGalleryItem(ToggableGroup):
    """ ToggableGroup adapted specifically for a code gallery item. """
    def __init__(self, parent=None):
        self.prev_height = None

        super(CodeGalleryItem, self).__init__(parent=parent)
        self.parent = parent

        # Add buttons
        btn1_text = "Insert code"
        btn1 = QtWidgets.QPushButton(btn1_text)
        btn1.setMaximumWidth(btn1.fontMetrics().boundingRect(btn1_text).width() + 14)

        btn2_text = "Save snippet"
        btn2 = QtWidgets.QPushButton(btn2_text)
        btn2.setMaximumWidth(btn1.fontMetrics().boundingRect(btn2_text).width() + 14)

        self.top_right_layout.addWidget(btn1)
        self.top_right_layout.addWidget(btn2)

        # Add content
        self.script_editor = KSScriptEditor()
        self.script_editor.setMinimumHeight(20)

        #self.setSizePolicy(QtWidgets.QSizePolicy.LineEdit,QtWidgets.QSizePolicy.LineEdit)
        self.script_editor.setStyleSheet('background:#282828;color:#EEE;')  # Main Colors
        #if self.knobScripter:
        #    script_editor_font = self.knobScripter.script_editor_font
        #    script_editor.setFont(script_editor_font)

        self.script_editor.setPlainText("function(2)")

        grip_handle = GripHandle(self)
        self.script_editor.setCornerWidget(grip_handle)

        #temp
        """
        sewidget = QtWidgets.QWidget()

        selayout = QtWidgets.QGridLayout(sewidget)
        sewidget.setLayout(selayout)

        cw = QtWidgets.QSizeGrip(self)
        selayout.addWidget(self.script_editor)
        selayout.addWidget(cw,1,1,1,1,Qt.AlignBottom|Qt.AlignRight)
        """

        #self.content_layout.addWidget(self.script_editor)
        self.content_layout.addWidget(self.script_editor)

        self.grip_line = GripWidget(self, inner_widget=HLine())
        self.grip_line.parent_min_size = (100,100)

        self.content_layout.addWidget(self.grip_line)
    
    def setCollapsed(self, collapsed=True):
        if collapsed:
            self.prev_height = self.height()
            self.setMinimumHeight(0)
        else:
            if self.prev_height:
                self.setFixedHeight(self.prev_height)

        super(CodeGalleryItem, self).setCollapsed(collapsed)

# TODO white lines on splitter line when hovering
# TODO knobscripter font

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
                #self.parent.resize(self.parent.width(), max(self.parent_min_size[1], p.y() + self.click_offset[1]))
                self.parent.setFixedHeight(max(self.parent_min_size[1], p.y() + self.click_offset[1]))


class HLine(QtWidgets.QFrame):
    def __init__(self,parent=None):
        super(HLine, self).__init__(parent)
        self.setFrameStyle(QtWidgets.QFrame.HLine | QtWidgets.QFrame.Sunken)
        self.setLineWidth(1)
        self.setMidLineWidth(0)

class GripHandle(QtWidgets.QPushButton):
    def __init__(self,parent=None, resize_x = False, resize_y = True):
        super(GripHandle, self).__init__(parent)
        self.parent = parent
        self.resize_x = resize_x
        self.resize_y = resize_y
        self.setMouseTracking(True)

        self.click_pos = None
        self.click_offset = None

    def mousePressEvent(self, e):
        self.click_pos = self.mapToParent(e.pos())
        g = self.parent.geometry()
        self.click_offset = [g.width()-self.click_pos.x(),g.height()-self.click_pos.y()]
        super(GripHandle,self).mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if self.isDown():
            p = self.mapToParent(e.pos())
            if self.resize_x:
                self.parent.setFixedWidth(p.x()+self.click_offset[0])
            if self.resize_y:
                self.parent.setFixedHeight(p.y()+self.click_offset[1])

    #TODO implement as horizontal line with scroll arrows instead of a stupid corner


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
        if event.button() == Qt.LeftButton:
            if self.highlighted:
                self.clicked.emit()
                pass
        super(ClickableWidget, self).mouseReleaseEvent(event)


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
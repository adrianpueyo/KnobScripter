import nuke
import logging
from functools import partial
import json
from collections import OrderedDict

try:
    if nuke.NUKE_VERSION_MAJOR < 11:
        from PySide import QtCore, QtGui, QtGui as QtWidgets
        from PySide.QtCore import Qt
    else:
        from PySide2 import QtWidgets, QtGui, QtCore
        from PySide2.QtCore import Qt
except ImportError:
    from Qt import QtCore, QtGui, QtWidgets

from ..scripteditor import ksscripteditor
from ..scripteditor import pythonhighlighter
from ..scripteditor import blinkhighlighter
from .. import utils
import dialogs
import snippets
from .. import config

# TODO Flat is better than nested, bring panels up!
code_gallery_dict = {
    "blink" : [
        {
            "title": "Kernel skeleton",
            "desc": "Basic code structure for starting a Blink kernel.",
            "cat": ["Base codes"],
            "code": """\nkernel KernelName : ImageComputationKernel<ePixelWise>\n{\n  Image<eRead, eAccessPoint, eEdgeClamped> src;\n  Image<eWrite> dst;\n\n  param:\n\n\n  local:\n\n\n  void init() {\n\n  }\n\n  void process(int2 pos) {\n    dst() = src();\n  }\n};\n""",
            "editor_height" : 40,
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
            "cat":["Base codes", "Example"],
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

def clearLayout(layout):
    if layout is not None:
        while layout.count():
            child = layout.takeAt(0)
            if child.widget() is not None:
                child.widget().deleteLater()
            elif child.layout() is not None:
                clearLayout(child.layout())

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
        self.radio_selected.emit(button.text())

    def set_button(self,text):
        text = text.lower()
        item_list_lower = [i.lower() for i in self.item_list]
        if text in item_list_lower:
            btn = self.button_group.button(item_list_lower.index(text))
            btn.setChecked(True)
            self.radio_selected.emit(btn.text())
        else:
            logging.debug("Couldn't set radio button text.")

    def selected_text(self):
        return str(self.button_group.button(self.button_group.checkedId()).text())


class CodeGalleryWidget(QtWidgets.QWidget):
    def __init__(self, knobScripter="", _parent=QtWidgets.QApplication.activeWindow()):
        super(CodeGalleryWidget, self).__init__(_parent)

        self.knobScripter = knobScripter
        self.color_style_python = "sublime"

        self.code_language = "python"

        self.lang_buttons = OrderedDict([
            ("python", QtWidgets.QRadioButton("Python")),
            ("blink", QtWidgets.QRadioButton("Blink")),
            ("all", QtWidgets.QRadioButton("All")),
        ])

        self.setWindowTitle("Code Gallery + Snippet Editor")

        self.initUI()
        # self.resize(500,300)
        self.set_code_language(self.code_language)

    def initUI(self):
        self.layout = QtWidgets.QVBoxLayout()

        # 1. Filters (language etc)
        self.filter_widget = QtWidgets.QFrame()
        #self.filter_widget.setContentsMargins(0,0,0,0)
        filter_layout = QtWidgets.QHBoxLayout()

        code_language_label = QtWidgets.QLabel("Language:")
        filter_layout.addWidget(code_language_label)
        # TODO Compatible with expressions and TCL knobs too!!

        self.lang_button_group = QtWidgets.QButtonGroup(self)
        for btn in self.lang_buttons:
            self.lang_button_group.addButton(self.lang_buttons[btn])
            filter_layout.addWidget(self.lang_buttons[btn])
        self.lang_button_group.buttonClicked.connect(self.lang_btn_pressed)
        filter_layout.addStretch()

        self.reload_button = QtWidgets.QPushButton("Reload")
        self.reload_button.clicked.connect(self.reload)
        filter_layout.setMargin(0)
        #filter_layout.addSpacing(14)
        #self.expand_all_button = QtWidgets.QPushButton("Expand")
        #self.collapse_all_button = QtWidgets.QPushButton("Collapse")
        #filter_layout.addWidget(self.expand_all_button)
        #filter_layout.addWidget(self.collapse_all_button)
        filter_layout.addWidget(self.reload_button)

        self.filter_widget.setLayout(filter_layout)
        self.layout.addWidget(self.filter_widget)
        self.layout.addWidget(HLine())

        # 2. Scroll Area
        # 2.1. Inner scroll content
        self.scroll_content = QtWidgets.QWidget()
        self.scroll_layout = QtWidgets.QVBoxLayout()
        self.scroll_content.setLayout(self.scroll_layout)
        self.scroll_content.setContentsMargins(0,0,8,0)

        self.set_code_language(self.code_language, force_reload=True)
        #self.filter_gallery(lang="python")

        # 2.2. External Scroll Area
        self.scroll = QtWidgets.QScrollArea()
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setWidgetResizable(True)
        self.scroll.setWidget(self.scroll_content)

        self.layout.addWidget(self.scroll)
        #self.layout.setSpacing(0)

        self.scroll.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.MinimumExpanding)

        #temp
        """
        tg = ToggableGroup(self)
        tg.setFrameStyle(QtWidgets.QFrame.Panel | QtWidgets.QFrame.Plain)

        tg.setStyleSheet(".ToggableGroup{border: 1px solid #222;padding:4px;}") #Dot makes it not inherited by sublasses
        """
        self.scroll_layout.setMargin(0)
        #master_layout.setSpacing(0)
        self.scroll_layout.addStretch()
        #self.layout.addStretch()

        #self.layout.setContentsMargins(10,10,0,8)
        self.setLayout(self.layout)

    def lang_btn_pressed(self,button):
        """ Find the code language corresponding to the pressed button and call self.set_code_language with it. """
        if button not in self.lang_buttons.values():
            return False
        self.set_code_language(self.get_button_language(button))

    def get_button_language(self, button):
        """ Return (str) the languaage of the selected button """
        lang = next((l for l in self.lang_buttons if self.lang_buttons[l] == button), None)
        return lang

    def reload(self):
        """ Force a rebuild of the widgets in the current filter status. """
        lang = self.get_button_language(self.lang_button_group.checkedButton())
        self.set_code_language(lang, force_reload=True)

    def set_code_language(self,lang,force_reload=False):
        """ Set the code language, clear the scroll layout and rebuild it as needed. """
        lang = lang.lower()
        if lang not in self.lang_buttons:
            return False
        elif force_reload == False and lang == self.code_language:
            logging.debug("KS: Doing nothing because the language was already selected.")
            return False

        self.lang_buttons[lang].setChecked(True)
        self.code_language = lang
        logging.debug("Setting code language to "+lang)

        # Clear scroll area
        clearLayout(self.scroll_layout)

        # Build widgets as needed
        if lang == "all":
            for lang in code_gallery_dict.keys():
                tg = ToggableGroup(self)
                tg.setTitle("<big><b>{}</b></big>".format(lang.capitalize()))
                self.build_gallery_group(code_gallery_dict[lang], tg.content_layout, lang=lang)
                self.scroll_layout.insertWidget(-1, tg)
                self.scroll_layout.addSpacing(10)
        else:
            self.build_gallery_group(code_gallery_dict[lang], self.scroll_layout, lang=lang)
        self.scroll_layout.addStretch()

    def build_gallery_group(self, code_list, layout, lang="python"):
        """ Given a list of code gallery items, it builds the widgets in the given layout """
        # 1. Get available categories
        categories = []
        for code in code_list:
            for cat in code["cat"]:
                categories.append(cat)
        categories = list(set(categories))

        # 2. Build gallery items
        for cat in categories:
            tg = ToggableGroup(self)
            tg.setTitle("<big><b>{}</b></big>".format(cat))
            for code in code_list:
                if cat in code["cat"]:
                    cgi = self.code_gallery_item(code, lang = lang)
                    tg.content_layout.addWidget(cgi)

            layout.insertWidget(-1, tg)
            layout.addSpacing(4)

    def code_gallery_item(self, code, lang="python"):
        """ Given a code dict, returns the corresponding code gallery widget. """
        if not all(i in code for i in ["title", "code"]):
            return False
        cgi = CodeGalleryItem(self)

        # 1. Title/description
        title = "<b>{0}</b>".format(code["title"])
        if "desc" in code:
            title += "<br><small style='color:#999'>{}</small>".format(code["desc"])
        cgi.setTitle(title)

        cgi.btn_insert_code.clicked.connect(partial(self.insert_code, cgi))
        cgi.btn_save_snippet.clicked.connect(partial(self.save_snippet, cgi))

        # 2. Content
        cgi.script_editor.set_code_language(lang.lower())
        #cgi.script_editor.setFont(config.script_editor_font)
        cgi.script_editor.setPlainText(code["code"])

        if "editor_height" in code:
            cgi.setFixedHeight(cgi.top_layout.sizeHint().height() + 40 + code["editor_height"])
        else:
            cgi.setFixedHeight(cgi.top_layout.sizeHint().height() + 140)

        return cgi

    def insert_code(self, code_gallery_item):
        """ Insert the code contained in code_gallery_item in the knobScripter's texteditmain. """
        ks = None
        utils.relistAllKnobScripterPanes()
        if self.knobScripter in nuke.AllKnobScripters:
            ks = self.knobScripter
        elif len(nuke.AllKnobScripters):
            for widget in nuke.AllKnobScripters:
                if widget.metaObject().className() == 'KnobScripterPane' and widget.isVisible():
                    ks = widget
            if not ks:
                ks = nuke.AllKnobScripters[-1]
        else:
            nuke.message("No KnobScripters found!")
            return False

        code = code_gallery_item.script_editor.toPlainText()
        ks.script_editor.addSnippetText(code)

    def save_snippet(self, code_gallery_item, shortcode = ""):
        """ Save the current code as a snippet (by introducing a shortcode) """
        # while...
        code = code_gallery_item.script_editor.toPlainText()
        lang = code_gallery_item.script_editor.code_language
        asp = snippets.AppendSnippetPanel(self, code, "test", lang=lang)
        asp.show()
        return
        # 1. Ask for the shortcode
        if shortcode =="":
            temp_code = "default"
            while True:
                #TODO move these lines to the snippets appendSnippet function itself
                temp_code, ok = QtWidgets.QInputDialog.getText(self,"Set shortcode text","Set your shortcode text:",text=temp_code)
                if not ok:
                    break
        return


        # 2. Try to save it!
        snippets.append_snippet()

        # 3. Find the ks and refresh it
        #TODO: Snippets should refresh every time the window shows? Maybe not



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

class CodeGalleryItem(ToggableGroup):
    """ ToggableGroup adapted specifically for a code gallery item. """
    def __init__(self, parent=None):
        self.prev_height = None

        super(CodeGalleryItem, self).__init__(parent=parent)
        self.parent = parent

        # Add buttons
        btn1_text = "Insert code"
        self.btn_insert_code = QtWidgets.QPushButton(btn1_text)
        self.btn_insert_code.setMaximumWidth(self.btn_insert_code.fontMetrics().boundingRect(btn1_text).width() + 14)

        btn2_text = "Save snippet"
        self.btn_save_snippet = QtWidgets.QPushButton(btn2_text)
        self.btn_save_snippet.setMaximumWidth(self.btn_save_snippet.fontMetrics().boundingRect(btn2_text).width() + 14)

        self.top_right_layout.addWidget(self.btn_insert_code)
        self.top_right_layout.addWidget(self.btn_save_snippet)

        # Add content
        self.script_editor = ksscripteditor.KSScriptEditor()
        self.script_editor.setMinimumHeight(20)

        #self.setSizePolicy(QtWidgets.QSizePolicy.LineEdit,QtWidgets.QSizePolicy.LineEdit)

        #self.content_layout.addWidget(self.script_editor)
        self.content_layout.addWidget(self.script_editor)
        self.content_layout.setSpacing(1)

        hline = HLine()
        #hline.setStyleSheet("margin:0px;padding:0px;")
        self.grip_line = GripWidget(self, inner_widget=HLine())
        self.grip_line.setStyleSheet("GripWidget:hover{border: 1px solid #DDD;}")
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
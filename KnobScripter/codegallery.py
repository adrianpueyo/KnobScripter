import nuke
import logging
from functools import partial

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
import utils
import snippets
import widgets

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

class CodeGalleryWidget(QtWidgets.QWidget):
    def __init__(self, knob_scripter="", _parent=QtWidgets.QApplication.activeWindow()):
        super(CodeGalleryWidget, self).__init__(_parent)

        self.knob_scripter = knob_scripter
        self.code_language = "python"

        self.initUI()
        # self.resize(500,300)
        self.change_lang(self.code_language)

    def initUI(self):
        self.layout = QtWidgets.QVBoxLayout()

        # 1. Filters (language etc)
        self.filter_widget = QtWidgets.QFrame()
        filter_layout = QtWidgets.QHBoxLayout()
        code_language_label = QtWidgets.QLabel("Language:")
        filter_layout.addWidget(code_language_label)
        # TODO Compatible with expressions and TCL knobs too!!
        self.lang_selector = widgets.RadioSelector(["Python", "Blink", "All"])
        self.lang_selector.radio_selected.connect(self.change_lang)
        filter_layout.addWidget(self.lang_selector)
        filter_layout.addStretch()
        self.reload_button = QtWidgets.QPushButton("Reload")
        self.reload_button.clicked.connect(self.reload)
        filter_layout.setMargin(0)
        filter_layout.addWidget(self.reload_button)

        self.filter_widget.setLayout(filter_layout)
        self.layout.addWidget(self.filter_widget)
        self.layout.addWidget(widgets.HLine())

        # 2. Scroll Area
        # 2.1. Inner scroll content
        self.scroll_content = QtWidgets.QWidget()
        self.scroll_layout = QtWidgets.QVBoxLayout()
        self.scroll_layout.setMargin(0)
        self.scroll_layout.addStretch()
        self.scroll_content.setLayout(self.scroll_layout)
        self.scroll_content.setContentsMargins(0,0,8,0)

        self.change_lang(self.code_language, force_reload=True)

        # 2.2. External Scroll Area
        self.scroll = QtWidgets.QScrollArea()
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setWidgetResizable(True)
        self.scroll.setWidget(self.scroll_content)
        self.scroll.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.MinimumExpanding)

        self.layout.addWidget(self.scroll)

        self.setLayout(self.layout)

    def reload(self):
        """ Force a rebuild of the widgets in the current filter status. """
        lang = self.lang_selector.selected_text()
        self.change_lang(lang, force_reload=True)

    def change_lang(self,lang,force_reload=False):
        """ Set the code language, clear the scroll layout and rebuild it as needed. """
        lang = lang.lower()

        if force_reload == False and lang == self.code_language:
            logging.debug("KS: Doing nothing because the language was already selected.")
            return False

        self.lang_selector.set_button(lang)
        self.code_language = lang
        logging.debug("Setting code language to "+lang)

        # Clear scroll area
        utils.clear_layout(self.scroll_layout)

        # Build widgets as needed
        if lang == "all":
            for lang in code_gallery_dict.keys():
                tg = widgets.ToggableGroup(self)
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
            tg = widgets.ToggableGroup(self)
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
        if self.knob_scripter in nuke.AllKnobScripters:
            ks = self.knob_scripter
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


# class CodeGalleryPane(CodeGallery)
# def __init__(self, node = "", knob="knobChanged"):
#        super(KnobScripterPane, self).__init__(isPane=True, _parent=QtWidgets.QApplication.activeWindow())
# TODO Pane instead, its own thing
# TODO: Snippets: button to delete snippet, add snippet to script
# TODO: Snippet editor and preferences apply changes (via "Reload Snippets and Settings button or whatever...") on all knobscripters? (by having a set of the active knobscripters and removing them on close)


class CodeGalleryItem(widgets.ToggableCodeGroup):
    """ widgets.ToggableGroup adapted specifically for a code gallery item. """

    def __init__(self, parent=None):

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

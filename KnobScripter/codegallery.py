import nuke
import os
import logging
import json
from functools import partial

try:
    if nuke.NUKE_VERSION_MAJOR >= 16:
        from PySide6 import QtCore, QtGui, QtWidgets
        from PySide6.QtCore import Qt

        IS_PYSIDE6 = True
    elif nuke.NUKE_VERSION_MAJOR >= 11:
        from PySide2 import QtWidgets, QtGui, QtCore
        from PySide2.QtCore import Qt

        IS_PYSIDE6 = False
    else:
        from PySide import QtCore, QtGui, QtGui as QtWidgets
        from PySide.QtCore import Qt

        IS_PYSIDE6 = False
except ImportError:
    from Qt import QtCore, QtGui, QtWidgets

    IS_PYSIDE6 = False

from KnobScripter import utils, snippets, widgets, config, content, ksscripteditor

code_gallery_dict = {
    "blink": [
        {
            "title": "Kernel skeleton",
            "desc": "Basic code structure for starting a Blink kernel.",
            "cat": ["Base codes"],
            "code": """\
kernel KernelName : ImageComputationKernel<ePixelWise>
{
  Image<eRead, eAccessPoint, eEdgeClamped> src;
  Image<eWrite> dst;

  param:

  local:

  void init() {

  }

  void process(int2 pos) {
    dst() = src();
  }
};
""",
            "editor_height": 40,
        },
        {
            "title": "Process function",
            "desc": "Example template for the main processing function in Blink.",
            "cat": ["Base codes"],
            "code": """void process() {
    // Read the input image
    SampleType(src) input = src();

    // Isolate the RGB components
    float3 srcPixel(input.x, input.y, input.z);

    // Calculate luma
    float luma = srcPixel.x * coefficients.x
               + srcPixel.y * coefficients.y
               + srcPixel.z * coefficients.z;
    // Apply saturation
    float3 saturatedPixel = (srcPixel - luma) * saturation + luma;

    // Write the result to the output image
    dst() = float4(saturatedPixel.x, saturatedPixel.y, saturatedPixel.z, input.w);
  }"""
        },
        {
            "title": "Longer text? what would happen exactly? lets try it like right now yes yes yes yes yes ",
            "desc": "Example template for the main processing function in Blink. this is the same but with a way longer description to see what happens... lets see!!!!.",
            "cat": ["Base codes", "Example"],
            "code": """void process() {
    // Read the input image
    SampleType(src) input = src();

    // Isolate the RGB components
    float3 srcPixel(input.x, input.y, input.z);

    // Calculate luma
    float luma = srcPixel.x * coefficients.x
               + srcPixel.y * coefficients.y
               + srcPixel.z * coefficients.z;
    // Apply saturation
    float3 saturatedPixel = (srcPixel - luma) * saturation + luma;

    // Write the result to the output image
    dst() = float4(saturatedPixel.x, saturatedPixel.y, saturatedPixel.z, input.w);
  }"""
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


def get_categories(code_dict=None):
    """Return a list of available categories for the specified code_dict (or the default one if not specified)."""
    code_dict = code_dict or load_code_gallery_dict(config.codegallery_user_txt_path)
    categories = []
    for lang in code_dict:
        for code_item in code_dict[lang]:
            if "cat" in code_item:
                cat = code_item["cat"]
                if isinstance(cat, list):
                    categories.extend(cat)
    return list(set(categories))


def load_all_code_gallery_dicts():
    """Return a dictionary containing the code gallery dicts from all different paths."""
    user_dict = config.code_gallery_files
    full_dict = dict()
    for file in config.code_gallery_files + [config.codegallery_user_txt_path]:
        file_dict = load_code_gallery_dict(file)
        logging.debug(f"Loading file: {file}")
        for key in file_dict.keys():
            if key not in full_dict:
                full_dict[key] = []
            for single_code_dict in file_dict[key]:
                full_dict[key].append(single_code_dict)
    logging.debug(f"Combined code gallery dict: {full_dict}")
    return full_dict


def load_code_gallery_dict(path=None):
    """
    Load the codes from the user JSON path as a dict.

    :param path: Path to the JSON file.
    :return: Dictionary of code items.
    """
    if not path:
        path = config.codegallery_user_txt_path
    if not os.path.isfile(path):
        logging.debug(f"Path doesn't exist: {path}")
        return dict()
    else:
        try:
            with open(path, "r", encoding="utf-8") as f:
                code_dict = json.load(f)
                return code_dict
        except Exception as e:
            logging.debug(f"Couldn't open file: {path}.\nLoading empty dict instead. Error: {e}")
            return dict()


def save_code_gallery_dict(code_dict, path=None):
    """Perform a JSON dump of the code gallery into the specified path."""
    if not path:
        path = config.codegallery_user_txt_path
    with open(path, "w", encoding="utf-8") as f:
        json.dump(code_dict, f, sort_keys=True, indent=4)
        content.code_gallery_dict = code_dict


def append_code(code, title=None, desc=None, categories=None, path=None, lang="python"):
    """Load the code gallery file as a dict and append a new code entry."""
    if code == "":
        return False
    path = path or config.codegallery_user_txt_path
    title = title or ""
    desc = desc or ""
    categories = categories or get_categories()
    lang = lang.lower()
    all_codes = load_code_gallery_dict(path)
    if lang not in all_codes:
        all_codes[lang] = []
    single_code_dict = {
        "title": title,
        "desc": desc,
        "cat": categories,
        "code": code
    }
    all_codes[lang].append(single_code_dict)
    save_code_gallery_dict(all_codes, path)


class AppendCodePanel(QtWidgets.QDialog):
    def __init__(self, parent=None, code=None, title=None, desc=None, cat=None, lang="python", path=None):
        super(AppendCodePanel, self).__init__(parent)

        self.lang = lang
        title = title or ""
        desc = desc or ""
        cat = cat or []
        self.path = path or config.codegallery_user_txt_path
        self.existing_code_dict = load_code_gallery_dict(self.path)
        self.existing_categories = get_categories(self.existing_code_dict)

        # Layout
        self.layout = QtWidgets.QVBoxLayout()

        # Code language selector
        self.lang_selector = widgets.RadioSelector(["Python", "Blink", "All"])
        self.lang_selector.radio_selected.connect(self.change_lang)

        # Title
        self.title_lineedit = QtWidgets.QLineEdit(title)
        f = self.title_lineedit.font()
        f.setWeight(QtGui.QFont.Bold)
        self.title_lineedit.setFont(f)

        # Description
        self.description_lineedit = QtWidgets.QLineEdit(desc)

        # Category
        self.category_combobox = QtWidgets.QComboBox()
        self.category_combobox.setEditable(True)
        self.category_combobox.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.category_combobox.addItem("", "")
        for cat in self.existing_categories:
            self.category_combobox.addItem(str(cat), str(cat))

        # Code editor
        self.script_editor = ksscripteditor.KSScriptEditor()
        self.script_editor.setPlainText(code)
        se_policy = self.script_editor.sizePolicy()
        se_policy.setVerticalStretch(1)
        self.script_editor.setSizePolicy(se_policy)

        # Warnings
        self.warnings_label = QtWidgets.QLabel("Please set a code and title.")
        self.warnings_label.setStyleSheet("color: #D65; font-style: italic;")
        self.warnings_label.setWordWrap(True)
        self.warnings_label.mouseReleaseEvent = lambda x: self.warnings_label.hide()

        # Buttons
        self.button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Save | QtWidgets.QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.save_pressed)
        self.button_box.rejected.connect(self.cancel_pressed)

        # Form layout
        self.form = QtWidgets.QFormLayout()
        self.form.addRow("Language: ", self.lang_selector)
        self.form.addRow("Title: ", self.title_lineedit)
        self.form.addRow("Description: ", self.description_lineedit)
        self.form.addRow("Category: ", self.category_combobox)
        self.form.addRow("Code: ", self.script_editor)
        self.form.addRow("", self.warnings_label)
        self.warnings_label.hide()
        self.form.setFieldGrowthPolicy(QtWidgets.QFormLayout.ExpandingFieldsGrow)

        self.layout.addLayout(self.form)
        self.layout.addWidget(self.button_box)
        self.setLayout(self.layout)

        # Init values
        self.setWindowTitle("Add Code to Code Gallery")
        self.lang_selector.set_button(self.lang)
        self.script_editor.set_code_language(self.lang)
        self.title_lineedit.setFocus()
        self.title_lineedit.selectAll()

    def change_lang(self, lang):
        self.script_editor.set_code_language(str(lang.lower()))

    def save_pressed(self):
        title = self.title_lineedit.text()
        description = self.description_lineedit.text()
        categories_str = self.category_combobox.lineEdit().text()
        categories = [c.strip() for c in categories_str.split(",") if c.strip()]
        code = self.script_editor.toPlainText()
        lang = self.lang_selector.selected_text()
        if "" in [code, title]:
            self.warnings_label.show()
            return False
        logging.debug(
            f"Code to be saved \nLang:\n{lang}\nTitle:\n{title}\nDescription:\n{description}\nCategory:\n{categories}\nCode:\n{code}\n------")
        append_code(code, title, description, categories, lang=lang)
        code_gallery_dict = load_code_gallery_dict()
        try:
            content.code_gallery_dict = code_gallery_dict
        except Exception as e:
            logging.debug(e)
        self.accept()

    def cancel_pressed(self):
        if self.script_editor.toPlainText() != "":
            msg = "Do you wish to discard the changes?"
            # Assuming dialogs.ask is defined elsewhere in your codebase.
            if not dialogs.ask(msg, self, default_yes=False):
                return False
        self.reject()


class CodeGalleryWidget(QtWidgets.QWidget):
    def __init__(self, knob_scripter="", _parent=QtWidgets.QApplication.activeWindow(), lang="python"):
        super(CodeGalleryWidget, self).__init__(_parent)

        self.knob_scripter = knob_scripter
        self.code_language = lang

        self.initUI()
        self.change_lang(self.code_language)

    def initUI(self):
        self.layout = QtWidgets.QVBoxLayout()

        # 1. Filters (language etc)
        self.filter_widget = QtWidgets.QFrame()
        filter_layout = QtWidgets.QHBoxLayout()
        code_language_label = QtWidgets.QLabel("Language:")
        filter_layout.addWidget(code_language_label)
        self.lang_selector = widgets.RadioSelector(["Python", "Blink", "All"])
        self.lang_selector.radio_selected.connect(self.change_lang)
        filter_layout.addWidget(self.lang_selector)
        filter_layout.addStretch()
        self.reload_button = QtWidgets.QPushButton("Reload")
        self.reload_button.clicked.connect(self.reload)
        # Replace deprecated setMargin with setContentsMargins
        filter_layout.setContentsMargins(0, 0, 0, 0)
        filter_layout.addWidget(self.reload_button)

        self.filter_widget.setLayout(filter_layout)
        self.layout.addWidget(self.filter_widget)
        self.layout.addWidget(widgets.HLine())

        # 2. Scroll Area
        self.scroll_content = QtWidgets.QWidget()
        self.scroll_layout = QtWidgets.QVBoxLayout()
        # Replace deprecated setMargin with setContentsMargins
        self.scroll_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll_layout.addStretch()
        self.scroll_content.setLayout(self.scroll_layout)
        self.scroll_content.setContentsMargins(0, 0, 8, 0)

        self.change_lang(self.code_language, force_reload=True)

        self.scroll = QtWidgets.QScrollArea()
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setWidgetResizable(True)
        self.scroll.setWidget(self.scroll_content)
        self.scroll.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.MinimumExpanding)

        self.layout.addWidget(self.scroll)

        # 3. Lower buttons
        self.lower_layout = QtWidgets.QHBoxLayout()

        self.add_code_btn = widgets.APToolButton("add_filled")
        self.add_code_btn.setToolTip("Add new code")
        self.add_code_btn.clicked.connect(self.add_code)

        self.v_expand_btn = widgets.APToolButton("v_expand", icon_size=22)
        self.v_expand_btn.setToolTip("Expand all codes")
        self.v_expand_btn.clicked.connect(self.expand_codes)
        self.v_collapse_btn = widgets.APToolButton("v_collapse", icon_size=22)
        self.v_collapse_btn.setToolTip("Collapse all codes")
        self.v_collapse_btn.clicked.connect(self.collapse_codes)

        self.help_btn = widgets.APToolButton("help_filled")
        self.help_btn.setToolTip("Help")
        self.help_btn.clicked.connect(self.show_help)

        self.lower_layout.addWidget(self.add_code_btn)
        self.lower_layout.addSpacing(12)
        self.lower_layout.addWidget(self.v_expand_btn)
        self.lower_layout.addWidget(self.v_collapse_btn)
        self.lower_layout.addStretch()
        self.lower_layout.addWidget(self.help_btn)

        self.layout.addWidget(widgets.HLine())
        self.layout.addLayout(self.lower_layout)

        self.setLayout(self.layout)

    def reload(self):
        """Force a rebuild of the widgets in the current filter status."""
        lang = self.lang_selector.selected_text()
        self.change_lang(lang, force_reload=True)

    def change_lang(self, lang, force_reload=False):
        """Set the code language, clear the scroll layout, and rebuild it as needed."""
        lang = lang.lower()
        if not force_reload and lang == self.code_language:
            logging.debug("KS: Doing nothing because the language was already selected.")
            return False

        self.lang_selector.set_button(lang)
        self.code_language = lang
        logging.debug(f"Setting code language to {lang}")

        # Clear scroll area
        utils.clear_layout(self.scroll_layout)

        code_gallery_dict = load_all_code_gallery_dicts()

        # Build widgets as needed
        if lang == "all":
            for lang_key in code_gallery_dict.keys():
                tg = widgets.ToggableGroup(self)
                tg.setTitle("<big><b>{}</b></big>".format(lang_key.capitalize()))
                self.build_gallery_group(code_gallery_dict[lang_key], tg.content_layout, lang=lang_key)
                self.scroll_layout.insertWidget(-1, tg)
                self.scroll_layout.addSpacing(10)
        elif lang in code_gallery_dict:
            self.build_gallery_group(code_gallery_dict[lang], self.scroll_layout, lang=lang)
        self.scroll_layout.addStretch()

    def build_gallery_group(self, code_list, layout, lang="python"):
        """Given a list of code gallery items, build the widgets in the given layout."""
        # 1. Get available categories
        categories = []
        for code in code_list:
            for cat in code["cat"]:
                categories.append(cat)
        categories = list(set(categories))

        # 2. Build gallery items grouped by category
        for cat in categories:
            tg = widgets.ToggableGroup(self)
            tg.setTitle("<big><b>{}</b></big>".format(cat))
            for code in code_list:
                if cat in code["cat"]:
                    cgi = self.code_gallery_item(code, lang=lang)
                    tg.content_layout.addWidget(cgi)
            layout.insertWidget(-1, tg)
            layout.addSpacing(4)

    def code_gallery_item(self, code, lang="python"):
        """Given a code dict, return the corresponding code gallery widget."""
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
        cgi.script_editor.setPlainText(code["code"])

        if "editor_height" in code:
            cgi.setFixedHeight(cgi.top_layout.sizeHint().height() + 40 + code["editor_height"])
        else:
            cgi.setFixedHeight(cgi.top_layout.sizeHint().height() + 140)

        return cgi

    def add_code(self):
        """Bring up a panel to add a new code to the Code Gallery."""
        codepanel = AppendCodePanel(self, lang=self.code_language)
        codepanel.show()

    def insert_code(self, code_gallery_item):
        """Insert the code from code_gallery_item into the KnobScripter's main text editor."""
        self.knob_scripter = utils.getKnobScripter(self.knob_scripter)
        if self.knob_scripter:
            code = code_gallery_item.script_editor.toPlainText()
            self.knob_scripter.script_editor.addSnippetText(code)

    def save_snippet(self, code_gallery_item, shortcode=""):
        """Save the current code as a snippet by introducing a shortcode."""
        code = code_gallery_item.script_editor.toPlainText()
        lang = code_gallery_item.script_editor.code_language
        asp = snippets.AppendSnippetPanel(self, code, shortcode, lang=lang)
        asp.show()

    def all_code_groups(self):
        """Return a list of all Code Gallery Groups."""
        all_scroll_widgets = (self.scroll_layout.itemAt(i).widget() for i in range(self.scroll_layout.count()))
        gallery_groups = []
        for g in all_scroll_widgets:
            if isinstance(g, widgets.ToggableGroup):
                gallery_groups.append(g)
        return gallery_groups

    def all_codegallery_items(self, code_groups=None):
        """Return a list of all CodeGalleryItems."""
        if not code_groups:
            code_groups = self.all_code_groups()
        codegallery_items = []
        for g in code_groups:
            all_subwidgets = (g.content_layout.itemAt(i).widget() for i in range(g.content_layout.count()))
            for w in all_subwidgets:
                if isinstance(w, CodeGalleryItem):
                    codegallery_items.append(w)
        return codegallery_items

    def expand_codes(self):
        code_groups = self.all_code_groups()
        for w in code_groups + self.all_codegallery_items(code_groups):
            w.setCollapsed(False)

    def collapse_codes(self):
        code_groups = self.all_code_groups()
        for w in code_groups + self.all_codegallery_items(code_groups):
            w.setCollapsed(True)

    def show_help(self):
        # TODO: Create proper help (e.g., link to documentation or a video)
        nuke.message("The Code Gallery is a convenient place for code reference. It allows yourself or your studio "
                     "to have a gallery of useful pieces of code, categorized and accompanied by a title and short "
                     "description. \n\nPlease refer to the docs for more information.")


class CodeGalleryItem(widgets.ToggableCodeGroup):
    """widgets.ToggableGroup adapted specifically for a code gallery item."""

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

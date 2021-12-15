# -*- coding: utf-8 -*-
""" This module provides all the functionality relative to KnobScripter's Snippets.

Main classes:
    * AppendSnippetPanel: Convenient widget to append a snippet to the current dict.
    * SnippetsWidget: Snippet Edit panel, where you can create/delete/edit/save snippets.
    * SnippetsItem: ToggableGroup adapted to editing a specific Snippet.

Main functions:
    * load_snippets_dict: Loads all available snippets as a dictionary.
    * load_all_snippets: Loads snippets recursively. Deprecated.
    * save_snippets_dict: Saves a given dictionary as snippets.
    * append_snippet: Appends a given snippet to the dictionary and saves.

adrianpueyo.com

"""

import nuke
import json
import os
import re
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

from KnobScripter import ksscripteditor, config, dialogs, utils, widgets, content


def load_snippets_dict(path=None):
    """
    Load the snippets from json path as a dict. Return dict()
    if default_snippets == True and no snippets file found, loads default library of snippets.
    """
    if not path:
        path = config.snippets_txt_path
    if not os.path.isfile(path):
        logging.debug("Path doesn't exist: " + path)
        return content.default_snippets
    else:
        try:
            with open(path, "r") as f:
                snippets = json.load(f)
                return snippets
        except:
            logging.debug("Couldn't open file: {}.\nLoading default snippets instead.".format(path))
            return content.default_snippets


def save_snippets_dict(snippets_dict, path=None):
    """ Perform a json dump of the snippets into the path """
    if not path:
        path = config.snippets_txt_path
    with open(path, "w") as f:
        json.dump(snippets_dict, f, sort_keys=True, indent=4)
        content.all_snippets = snippets_dict


def append_snippet(code, shortcode="", path=None, lang=None):
    """ Load the snippets file as a dict and append a snippet """
    if code == "":
        return False
    if not path:
        path = config.snippets_txt_path
    if not lang:
        lang = "python"
    lang = lang.lower()
    all_snippets = load_snippets_dict(path)
    if shortcode == "":
        return False
    if lang not in all_snippets:
        all_snippets[lang] = []
    all_snippets[lang].append([shortcode, code])
    save_snippets_dict(all_snippets, path)


class AppendSnippetPanel(QtWidgets.QDialog):
    def __init__(self, parent=None, code=None, shortcode=None, path=None, lang="python"):
        super(AppendSnippetPanel, self).__init__(parent)

        self.lang = lang
        shortcode = shortcode or ""
        self.path = path or config.snippets_txt_path
        self.existing_snippets = load_snippets_dict(self.path)
        if not self.existing_snippets:
            return
        self.existing_shortcodes = self.existing_snippets.keys()

        # Layout
        self.layout = QtWidgets.QVBoxLayout()

        # Code language
        self.lang_selector = widgets.RadioSelector(["Python", "Blink", "All"])

        self.lang_selector.radio_selected.connect(self.change_lang)

        # Shortcode
        self.shortcode_lineedit = QtWidgets.QLineEdit(shortcode)
        f = self.shortcode_lineedit.font()
        f.setWeight(QtGui.QFont.Bold)
        self.shortcode_lineedit.setFont(f)

        # Code
        self.script_editor = ksscripteditor.KSScriptEditor()

        # self.script_editor.set_code_language(lang)
        self.script_editor.setPlainText(code)
        se_policy = self.script_editor.sizePolicy()
        se_policy.setVerticalStretch(1)
        self.script_editor.setSizePolicy(se_policy)

        # Warnings
        self.warnings_label = QtWidgets.QLabel("Please set a code and a shortcode.")
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
        self.form.addRow("Shortcode: ", self.shortcode_lineedit)
        self.form.addRow("Code: ", self.script_editor)
        self.form.addRow("", self.warnings_label)
        self.warnings_label.hide()
        self.form.setFieldGrowthPolicy(QtWidgets.QFormLayout.ExpandingFieldsGrow)

        self.layout.addLayout(self.form)
        self.layout.addWidget(self.button_box)
        self.setLayout(self.layout)

        # Init values
        self.setWindowTitle("Add Snippet")
        self.lang_selector.set_button(self.lang)
        self.script_editor.set_code_language(self.lang)
        self.shortcode_lineedit.setFocus()
        self.shortcode_lineedit.selectAll()

    def change_lang(self, lang):
        self.script_editor.set_code_language(str(lang.lower()))

    def save_pressed(self):
        shortcode = self.shortcode_lineedit.text()
        code = self.script_editor.toPlainText()
        lang = self.lang_selector.selected_text()
        if code == "" or shortcode == "":
            self.warnings_label.show()
            return False
        if shortcode in self.existing_shortcodes:
            msg = "A snippet with the given code already exists. Do you wish to overwrite it?"
            if not dialogs.ask(msg, self, default_yes=False):
                return False
        logging.debug(
            "Snippet to be saved \nLang:\n{0}\nShortcode:\n{1}\nCode:\n{2}\n------".format(lang, shortcode, code))
        append_snippet(code, shortcode, lang=lang)
        all_snippets = load_snippets_dict()
        try:
            content.all_snippets = all_snippets
        except Exception as e:
            logging.debug(e)
        self.accept()

    def cancel_pressed(self):
        if self.script_editor.toPlainText() != "":
            msg = "Do you wish to discard the changes?"
            if not dialogs.ask(msg, self, default_yes=False):
                return False
        self.reject()


class SnippetsWidget(QtWidgets.QWidget):
    """ Widget containing snippet editors, lang selector and other functionality. """

    def __init__(self, knob_scripter="", _parent=QtWidgets.QApplication.activeWindow()):
        super(SnippetsWidget, self).__init__(_parent)
        self.knob_scripter = knob_scripter
        self.code_language = "python"
        self.snippets_built = False

        self.initUI()
        self.build_snippets(lang=self.code_language)

    def initUI(self):
        self.layout = QtWidgets.QVBoxLayout()

        # 1. Filters (language etc)
        self.filter_widget = QtWidgets.QFrame()
        filter_layout = QtWidgets.QHBoxLayout()
        code_language_label = QtWidgets.QLabel("Language:")
        filter_layout.addWidget(code_language_label)
        # TODO Compatible with expressions and TCL knobs too
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
        self.scroll_content.setContentsMargins(0, 0, 8, 0)

        # 2.2. External Scroll Area
        self.scroll = QtWidgets.QScrollArea()
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setWidgetResizable(True)
        self.scroll.setWidget(self.scroll_content)
        self.scroll.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.MinimumExpanding)

        self.layout.addWidget(self.scroll)

        # 3. Lower buttons
        self.lower_layout = QtWidgets.QHBoxLayout()

        self.add_snippet_btn = widgets.KSToolButton("add_filled")
        self.add_snippet_btn.setToolTip("Add new snippet")
        self.add_snippet_btn.clicked.connect(self.add_snippet)

        self.sort_az_btn = widgets.KSToolButton("sort_az", icon_size=22)
        self.sort_az_btn.setToolTip("Sort snippets A-Z")
        self.sort_az_btn.clicked.connect(self.sort_snippets)
        self.sort_za_btn = widgets.KSToolButton("sort_za", icon_size=22)
        self.sort_za_btn.setToolTip("Sort snippets Z-A")
        self.sort_za_btn.clicked.connect(lambda: self.sort_snippets(reverse=True))
        self.v_expand_btn = widgets.KSToolButton("v_expand", icon_size=22)
        self.v_expand_btn.setToolTip("Expand all snippets")
        self.v_expand_btn.clicked.connect(self.expand_snippets)
        self.v_collapse_btn = widgets.KSToolButton("v_collapse", icon_size=22)
        self.v_collapse_btn.setToolTip("Collapse all snippets")
        self.v_collapse_btn.clicked.connect(self.collapse_snippets)
        self.save_snippets_btn = widgets.KSToolButton("save_all")
        self.save_snippets_btn.setToolTip("Save all snippets")
        self.save_snippets_btn.clicked.connect(self.save_all_snippets)
        self.snippets_help_btn = widgets.KSToolButton("help_filled")
        self.snippets_help_btn.setToolTip("Help")
        self.snippets_help_btn.clicked.connect(self.snippets_help)

        self.lower_layout.addWidget(self.add_snippet_btn)
        self.lower_layout.addSpacing(12)
        self.lower_layout.addWidget(self.sort_az_btn)
        self.lower_layout.addWidget(self.sort_za_btn)
        self.lower_layout.addSpacing(12)
        self.lower_layout.addWidget(self.v_expand_btn)
        self.lower_layout.addWidget(self.v_collapse_btn)
        self.lower_layout.addStretch()
        self.lower_layout.addWidget(self.save_snippets_btn)
        self.lower_layout.addWidget(self.snippets_help_btn)

        self.layout.addWidget(widgets.HLine())
        self.layout.addLayout(self.lower_layout)

        self.setLayout(self.layout)

    def reload(self):
        """ Force a rebuild of the widgets in the current filter status. """
        self.build_snippets()

    def build_snippets(self, lang=None):
        lang = lang or self.code_language
        lang = lang.lower()
        self.code_language = lang

        # Clear scroll area
        utils.clear_layout(self.scroll_layout)
        snippets_dict = load_snippets_dict()
        # Build widgets as needed
        for language in snippets_dict:
            # print("language: "+language)
            for snippet in snippets_dict[language]:
                if isinstance(snippet, list):
                    self.add_snippet(snippet[0], snippet[1], lang=str(language))
        self.scroll_layout.addStretch()
        self.change_lang(self.code_language)
        self.snippets_built = True

    def change_lang(self, lang, force_reload=True):
        """ Set the code language, clear the scroll layout and rebuild it as needed. """
        lang = str(lang).lower()

        if force_reload == False and lang == self.code_language:
            logging.debug("KS: Doing nothing because the language was already selected.")
            return False

        self.lang_selector.set_button(lang)
        self.code_language = lang
        logging.debug("Setting code language to " + lang)

        for snippets_item in self.all_snippets_items():
            snippets_item.setHidden(snippets_item.lang != self.code_language)
        return

    def all_snippets_items(self):
        """ Return a list of all SnippetItems. """
        all_widgets = (self.scroll_layout.itemAt(i).widget() for i in range(self.scroll_layout.count()))
        snippets_items = []
        for w in all_widgets:
            if isinstance(w, SnippetsItem):
                snippets_items.append(w)
        return snippets_items

    def add_snippet(self, key=None, code=None, lang=None):
        """ Create a new snippet field and focus on it. """
        key = key or ""
        code = code or ""
        lang = lang or self.code_language
        snippets_item = SnippetsItem(key, code, lang, self)
        snippets_item.btn_insert.clicked.connect(partial(self.insert_code, snippets_item))
        snippets_item.btn_duplicate.clicked.connect(partial(self.duplicate_snippet, snippets_item))
        snippets_item.btn_delete.clicked.connect(partial(self.delete_snippet, snippets_item))
        # snippets_item.setTitle("Key:")
        self.scroll_layout.insertWidget(0, snippets_item)
        snippets_item.key_lineedit.setFocus()

    def insert_code(self, snippet_item):
        """ Insert the code contained in snippet_item in the knobScripter's texteditmain. """
        self.knob_scripter = utils.getKnobScripter(self.knob_scripter)
        if self.knob_scripter:
            code = snippet_item.script_editor.toPlainText()
            self.knob_scripter.script_editor.addSnippetText(code)

    def duplicate_snippet(self, snippet_item):
        self.add_snippet(snippet_item.key_lineedit.text(), snippet_item.script_editor.toPlainText(), self.code_language)

    @staticmethod
    def delete_snippet(snippet_item):
        snippet_item.deleteLater()

    def sort_snippets(self, reverse=False):
        def code_key(snippets_item):
            return snippets_item.key_lineedit.text()

        snippets_items = sorted(self.all_snippets_items(), key=code_key, reverse=reverse)

        for w in reversed(snippets_items):
            self.scroll_layout.removeWidget(w)
            self.scroll_layout.insertWidget(0, w)

    def expand_snippets(self):
        for w in self.all_snippets_items():
            w.setCollapsed(False)

    def collapse_snippets(self):
        for w in self.all_snippets_items():
            w.setCollapsed(True)

    def save_all_snippets(self):
        # 1. Build snippet dict
        snippet_dict = {}
        for snippets_item in self.all_snippets_items():
            lang = snippets_item.lang
            key = snippets_item.key_lineedit.text()
            code = snippets_item.script_editor.toPlainText()
            if lang not in snippet_dict:
                snippet_dict[lang] = []
            if "" not in [key, code]:
                snippet_dict[lang].append([key, code])
        # 2. Notify...
        msg = "Are you sure you want to save all snippets?\nAny snippets deleted will be lost."
        if dialogs.ask(msg):
            # 3. Save!
            save_snippets_dict(snippet_dict)

    @staticmethod
    def snippets_help():
        # TODO make proper help... link to pdf or video?
        nuke.message("Snippets are a convenient way to save pieces of code you need to use over and over. "
                     "By setting a code and shortcode, every time you write the shortcode on the script editor and "
                     "press tab, the full code will be added. it also includes other convenient features. "
                     "Please refer to the docs for more information.")


class SnippetsItem(widgets.ToggableCodeGroup):
    """ widgets.ToggableGroup adapted specifically for a snippet item. """

    def __init__(self, key="", code="", lang="python", parent=None):
        super(SnippetsItem, self).__init__(parent=parent)
        self.parent = parent
        self.lang = lang

        self.title_label.setParent(None)

        # Add QLineEdit
        self.key_lineedit = QtWidgets.QLineEdit()
        self.key_lineedit.setMinimumWidth(20)
        self.key_lineedit.setStyleSheet("background:#222222;")
        f = self.key_lineedit.font()
        f.setWeight(QtGui.QFont.Bold)
        self.key_lineedit.setFont(f)
        self.key_lineedit.setText(str(key))
        self.top_clickable_layout.addWidget(self.key_lineedit)

        # Add buttons
        self.btn_insert = widgets.KSToolButton("download")
        self.btn_insert.setToolTip("Insert code into KnobScripter editor")
        self.btn_duplicate = widgets.KSToolButton("duplicate")
        self.btn_duplicate.setToolTip("Duplicate snippet")
        self.btn_delete = widgets.KSToolButton("delete")
        self.btn_delete.setToolTip("Delete snippet")

        self.top_right_layout.addWidget(self.btn_insert)
        self.top_right_layout.addWidget(self.btn_duplicate)
        self.top_right_layout.addWidget(self.btn_delete)

        # Set code
        self.script_editor.set_code_language(lang.lower())
        self.script_editor.setPlainText(str(code))

        lines = self.script_editor.document().blockCount()
        lineheight = self.script_editor.fontMetrics().height()

        self.setFixedHeight(80 + lineheight * min(lines - 1, 4))
        self.grip_line.parent_min_size = (100, 80)

        self.setTabOrder(self.key_lineedit, self.script_editor)

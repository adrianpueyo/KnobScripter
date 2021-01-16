import nuke
import json
import os
import re
import logging

import widgets

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
import config
import dialogs
import codegallery
import utils

def loadSnippetsDict(path=None):
    ''' Load the snippets from json path as a dict. Return dict() '''
    if not path:
        path = config.snippets_txt_path
    if not os.path.isfile(path):
        logging.debug("Path doesn't exist: "+path)
        return {}
    else:
        with open(path, "r") as f:
            snippets = json.load(f)
            return snippets

def loadAllSnippets(path="", max_depth=5, depth=0):
    '''
    Load prefs recursive. When maximum recursion depth, ignores paths.
    '''
    max_depth = max_depth
    cur_depth = depth
    if path == "":
        path = config.snippets_txt_path
    if not os.path.isfile(path):
        return {}
    else:
        loaded_snippets = {}
        with open(path, "r") as f:
            file = json.load(f)
            for i, (key, val) in enumerate(file.items()):
                if re.match(r"\[custom-path-[0-9]+]$", key):
                    if cur_depth < max_depth:
                        new_dict = self.loadAllSnippets(path=val, max_depth=max_depth, depth=cur_depth + 1)
                        loaded_snippets.update(new_dict)
                else:
                    loaded_snippets[key] = val
            return loaded_snippets

def saveSnippets(snippets_dict, path=None):
    ''' Perform a json dump of the snippets into the path '''
    if not path:
        path = config.snippets_txt_path
    with open(path, "w") as f:
        json.dump(snippets_dict, f, sort_keys=True, indent=4)

def append_snippet(code, shortcode="", path=None, lang = None):
    ''' Load the snippets file as a dict and append a snippet '''
    # TODO Add Language functionality... so snippets should be changed completely...
    if code == "":
        return False
    if not path:
        path = config.snippets_txt_path
    all_snippets = loadSnippetsDict(path)
    if shortcode == "":
        return False
    all_snippets[shortcode] = code
    saveSnippets(all_snippets, path)

class AppendSnippetPanel(QtWidgets.QDialog):
    def __init__(self, parent=None, code=None, shortcode=None, path = None, lang="python"):
        super(AppendSnippetPanel, self).__init__(parent)

        self.lang = lang
        shortcode = shortcode or ""
        self.path = path or config.snippets_txt_path
        self.existing_snippets = loadSnippetsDict(self.path)
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

        #self.script_editor.set_code_language(lang)
        self.script_editor.setPlainText(code)
        se_policy = self.script_editor.sizePolicy()
        se_policy.setVerticalStretch(1)
        self.script_editor.setSizePolicy(se_policy)

        # Warnings
        self.warnings_label = QtWidgets.QLabel("Please set a code and a shortcode.")
        self.warnings_label.setStyleSheet("color: #D65; font-style: italic;")
        self.warnings_label.setWordWrap(True)
        self.warnings_label.mouseReleaseEvent = lambda x:self.warnings_label.hide()

        # Buttons
        self.button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Save | QtWidgets.QDialogButtonBox.Cancel)
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
            if dialogs.ask(msg, self, default_yes=False) == False:
                return False
        logging.debug("Snippet to be saved \nLang:\n{0}\nShortcode:\n{1}\nCode:\n{2}\n------".format(lang, shortcode, code))
        append_snippet(code,shortcode,lang=lang)
        all_snippets = loadAllSnippets(max_depth=5)
        for ks in nuke.AllKnobScripters:
            try:
                ks.snippets = all_snippets
            except Exception as e:
                pass
        self.accept()

    def cancel_pressed(self):
        if self.script_editor.toPlainText() != "":
            msg = "Do you wish to discard the changes?"
            if not dialogs.ask(msg, self, default_yes=False):
                return False
        self.reject()


#TODO remove stupid buttons and add reload button, sae as code gallery.

class SnippetsWidget(QtWidgets.QWidget):
    """ Widget containing snippet editors, lang selector and other functionality. """
    # TODO Load default snippets should appear if not already loaded, or everything empty.
    def __init__(self, knob_scripter="", _parent=QtWidgets.QApplication.activeWindow()):
        super(SnippetsWidget, self).__init__(_parent)
        self.knob_scripter = knob_scripter
        self.code_language = "python"

        self.initUI()
        self.change_lang(self.code_language)

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
        # MAKE THIS AS NEEDED!
        """
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
        """




class SnippetsPanel(QtWidgets.QDialog):
    def __init__(self, knob_scripter="", _parent=QtWidgets.QApplication.activeWindow()):
        super(SnippetsPanel, self).__init__(_parent)
        # TODO delete buttons on the snippets! and categories per code languages (meaning dynamically show/hide widgets on request)

        self.knob_scripter = knob_scripter

        # self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)
        self.setWindowTitle("Snippet editor")

        self.snippets_dict = loadSnippetsDict(path=config.snippets_txt_path)

        self.initUI()
        self.resize(500, 300)

    def initUI(self):
        self.layout = QtWidgets.QVBoxLayout()

        # First Area (Titles)
        title_layout = QtWidgets.QHBoxLayout()
        shortcuts_label = QtWidgets.QLabel("Shortcut")
        code_label = QtWidgets.QLabel("Code snippet")
        title_layout.addWidget(shortcuts_label, stretch=1)
        title_layout.addWidget(code_label, stretch=2)
        self.layout.addLayout(title_layout)

        # Main Scroll area
        self.scroll_content = QtWidgets.QWidget()
        self.scroll_layout = QtWidgets.QVBoxLayout()

        self.buildSnippetWidgets()

        self.scroll_content.setLayout(self.scroll_layout)

        # Scroll Area Properties
        self.scroll = QtWidgets.QScrollArea()
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setWidgetResizable(True)
        self.scroll.setWidget(self.scroll_content)

        self.layout.addWidget(self.scroll)

        # File knob test
        # self.filePath_lineEdit = SnippetFilePath(self)
        # self.filePath_lineEdit
        # self.layout.addWidget(self.filePath_lineEdit)

        # Lower buttons
        self.bottom_layout = QtWidgets.QHBoxLayout()

        self.add_btn = QtWidgets.QPushButton("Add snippet")
        self.add_btn.setToolTip("Create empty fields for an extra snippet.")
        self.add_btn.clicked.connect(self.addSnippet)
        self.bottom_layout.addWidget(self.add_btn)

        self.addPath_btn = QtWidgets.QPushButton("Add custom path")
        self.addPath_btn.setToolTip("Add a custom path to an external snippets .txt file.")
        self.addPath_btn.clicked.connect(self.addCustomPath)
        self.bottom_layout.addWidget(self.addPath_btn)

        self.bottom_layout.addStretch()

        self.save_btn = QtWidgets.QPushButton('OK')
        self.save_btn.setToolTip("Save the snippets into a json file and close the panel.")
        self.save_btn.clicked.connect(self.okPressed)
        self.bottom_layout.addWidget(self.save_btn)

        self.cancel_btn = QtWidgets.QPushButton("Cancel")
        self.cancel_btn.setToolTip("Cancel any new snippets or modifications.")
        self.cancel_btn.clicked.connect(self.close)
        self.bottom_layout.addWidget(self.cancel_btn)

        self.apply_btn = QtWidgets.QPushButton('Apply')
        self.apply_btn.setToolTip("Save the snippets into a json file.")
        self.apply_btn.setShortcut('Ctrl+S')
        self.apply_btn.clicked.connect(self.applySnippets)
        self.bottom_layout.addWidget(self.apply_btn)

        self.help_btn = QtWidgets.QPushButton('Help')
        self.help_btn.setShortcut('F1')
        self.help_btn.clicked.connect(self.showHelp)
        self.bottom_layout.addWidget(self.help_btn)

        self.layout.addLayout(self.bottom_layout)

        self.setLayout(self.layout)

    def reload(self):
        '''
        Clears everything without saving and redoes the widgets etc.
        Only to be called if the panel isn't shown meaning it's closed.
        '''
        for i in reversed(range(self.scroll_layout.count())):
            self.scroll_layout.itemAt(i).widget().deleteLater()

        self.snippets_dict = loadSnippetsDict(path=config.snippets_txt_path)

        self.buildSnippetWidgets()

    def buildSnippetWidgets(self):
        for i, (key, val) in enumerate(self.snippets_dict.items()):
            if re.match(r"\[custom-path-[0-9]+]$", key):
                file_edit = SnippetFilePath(val)
                self.scroll_layout.insertWidget(-1, file_edit)
            else:
                snippet_edit = SnippetEdit(key, val, parent=self)
                self.scroll_layout.insertWidget(-1, snippet_edit)

    def getSnippetsAsDict(self):
        dic = {}
        num_snippets = self.scroll_layout.count()
        path_i = 1
        for s in range(num_snippets):
            se = self.scroll_layout.itemAt(s).widget()
            if se.__class__.__name__ == "SnippetEdit":
                key = se.shortcut_editor.text()
                val = se.script_editor.toPlainText()
                if key != "":
                    dic[key] = val
            else:
                path = se.filepath_lineEdit.text()
                if path != "":
                    dic["[custom-path-{}]".format(str(path_i))] = path
                    path_i += 1
        return dic

    def applySnippets(self):
        saveSnippets(self.getSnippetsAsDict())
        self.knob_scripter.snippets = loadAllSnippets(max_depth=5)

    def okPressed(self):
        self.applySnippets()
        self.accept()

    def addSnippet(self, key="", val=""):
        se = SnippetEdit(key, val, parent=self)
        self.scroll_layout.insertWidget(0, se)
        self.show()
        self.scroll.verticalScrollBar().setValue(0)
        return se

    def addCustomPath(self, path=""):
        cpe = SnippetFilePath(path)
        self.scroll_layout.insertWidget(0, cpe)
        self.show()
        cpe.browseSnippets()
        return cpe

    def showHelp(self):
        ''' Create a new snippet, auto-completed with the help '''
        help_key = "help"
        help_val = """Snippets are a convenient way to have code blocks that you can call through a shortcut.\n\n1. Simply write a shortcut on the text input field on the left. You can see this one is set to "help".\n\n2. Then, write a code or whatever in this script editor. You can include $$ as the placeholder for where you'll want the mouse cursor to appear.\nYou can instead write $$someText$$ to have someText selected.\nOr even $anythingHere$ to have a panel ask you what to put in $anythingHere$, and once you type it substitute it everywhere it finds that keyword.\n\n3. Finally, click OK or Apply to save the snippets. On the main script editor, you'll be able to call any snippet by writing the shortcut (in this example: help) and pressing the Tab key.\n\nIn order to remove a snippet, simply leave the shortcut and contents blank, and save the snippets."""
        help_se = self.addSnippet(help_key, help_val)
        help_se.script_editor.resize(160, 160)


class SnippetEdit(QtWidgets.QWidget):
    ''' Simple widget containing two fields, for the snippet shortcut and content '''
    def __init__(self, key="", val="", parent=None):
        super(SnippetEdit, self).__init__(parent)

        self.knob_scripter = parent.knob_scripter
        self.layout = QtWidgets.QHBoxLayout()

        self.shortcut_editor = QtWidgets.QLineEdit(self)
        f = self.shortcut_editor.font()
        f.setWeight(QtGui.QFont.Bold)
        self.shortcut_editor.setFont(f)
        self.shortcut_editor.setText(str(key))
        # self.script_editor = QtWidgets.QTextEdit(self)
        self.script_editor = ksscripteditor.KSScriptEditor()
        self.script_editor.setMinimumHeight(100)
        self.script_editor.set_code_language("python")
        self.script_editor.resize(90, 90)
        self.script_editor.setPlainText(str(val))
        self.layout.addWidget(self.shortcut_editor, stretch=1, alignment=Qt.AlignTop)
        self.layout.addWidget(self.script_editor, stretch=2)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.setLayout(self.layout)

        # TODO: Base gallery of snippets that can be imported or something. Or button to Import Defaults, when empty...


class SnippetFilePath(QtWidgets.QWidget):
    ''' Simple widget containing a filepath lineEdit and a button to open the file browser '''

    def __init__(self, path="", parent=None):
        super(SnippetFilePath, self).__init__(parent)

        self.layout = QtWidgets.QHBoxLayout()

        self.custompath_label = QtWidgets.QLabel(self)
        self.custompath_label.setText("Custom path: ")

        self.filepath_lineEdit = QtWidgets.QLineEdit(self)
        self.filepath_lineEdit.setText(str(path))
        # self.script_editor = QtWidgets.QTextEdit(self)
        self.filepath_lineEdit.setStyleSheet('background:#282828;color:#EEE;')  # Main Colors
        self.filepath_lineEdit.setFont(config.script_editor_font)

        self.file_button = QtWidgets.QPushButton(self)
        self.file_button.setText("Browse...")
        self.file_button.clicked.connect(self.browseSnippets)

        self.layout.addWidget(self.custompath_label)
        self.layout.addWidget(self.filepath_lineEdit)
        self.layout.addWidget(self.file_button)
        self.layout.setContentsMargins(0, 10, 0, 10)

        self.setLayout(self.layout)

    def browseSnippets(self):
        ''' Opens file panel for ...snippets.txt '''
        browseLocation = nuke.getFilename('Select snippets file', '*.txt')

        if not browseLocation:
            return

        self.filepath_lineEdit.setText(browseLocation)
        return

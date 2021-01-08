import nuke
import json
import os
import re

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
from .. import config
import dialogs

def loadSnippetsDict(path=None):
    ''' Load the snippets from json path as a dict. Return dict() '''
    if not path:
        path = config.snippets_txt_path
    if not os.path.isfile(path):
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


def appendSnippet(shortcode, code, path=None, check=True):
    ''' Load the snippets file as a dict and append a snippet '''
    if shortcode == "" or code == "":
        return False
    all_snippets = loadSnippetsDict(path)
    if shortcode in all_snippets and check:
        if not dialogs.ask("Shortcode {0} already in use. Do you wish to overwrite it?".format(shortcode)):
            return False
    all_snippets[shortcode] = code
    saveSnippets(all_snippets, path)


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
        self.knob_scripter.snippets = self.knob_scripter.loadSnippets(maxDepth=5)
        self.knob_scripter.loadSnippets()

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


class AddSingleSnippet(QtWidgets.QDialog):
    def __init__(self, knob_scripter="", parent=None):
        super(AddSingleSnippet, self).__init__(parent)
        layout = QtWidgets.QVBoxLayout()

        snippet_edit = SnippetEdit("","",parent)

        self.setLayout(layout)


class SnippetEdit(QtWidgets.QWidget):
    ''' Simple widget containing two fields, for the snippet shortcut and content '''

    def __init__(self, key="", val="", parent=None):
        super(SnippetEdit, self).__init__(parent)

        self.knob_scripter = parent.knob_scripter
        self.color_scheme = self.knob_scripter.color_scheme
        self.layout = QtWidgets.QHBoxLayout()

        self.shortcut_editor = QtWidgets.QLineEdit(self)
        f = self.shortcut_editor.font()
        f.setWeight(QtGui.QFont.Bold)
        self.shortcut_editor.setFont(f)
        self.shortcut_editor.setText(str(key))
        # self.script_editor = QtWidgets.QTextEdit(self)
        self.script_editor = ksscripteditor.KSScriptEditor()
        self.script_editor.setMinimumHeight(100)
        self.script_editor.setStyleSheet('background:#282828;color:#EEE;')  # Main Colors
        self.highlighter = pythonhighlighter.KSPythonHighlighter(self.script_editor.document())
        self.highlighter.setStyle(self.knob_scripter.color_scheme)
        self.script_editor_font = self.knob_scripter.script_editor_font
        self.script_editor.setFont(self.script_editor_font)
        self.script_editor.resize(90, 90)
        self.script_editor.setPlainText(str(val))
        self.layout.addWidget(self.shortcut_editor, stretch=1, alignment=Qt.AlignTop)
        self.layout.addWidget(self.script_editor, stretch=2)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.setLayout(self.layout)


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
        self.script_editor_font = QtGui.QFont()
        self.script_editor_font.setFamily("Courier")
        self.script_editor_font.setStyleHint(QtGui.QFont.Monospace)
        self.script_editor_font.setFixedPitch(True)
        self.script_editor_font.setPointSize(11)
        self.filepath_lineEdit.setFont(self.script_editor_font)

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

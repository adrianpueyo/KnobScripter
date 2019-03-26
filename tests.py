import nuke
import nukescripts
import re
import os
import json
from functools import partial
from types import MethodType

#IDEAS TODO
# When you define a snippet, you can put some code inside like #%c# meaning where the cursor will be moved to after pressing tab.

# PySide import switch
try:
    from PySide import QtCore, QtGui as QtWidgets
except ImportError:
    from PySide2 import QtWidgets, QtGui, QtCore
    from PySide2.QtCore import Qt

# Aux Functions
def findScriptEditors():
    #se_editor = find_se().children()[-1].children()[0]
    script_editors = []
    for widget in QtWidgets.QApplication.allWidgets():
        if "Script Editor" in widget.windowTitle():
            script_editors.append(widget)
    return script_editors


def getCursorInfo(self):
        self.cursor = self.textCursor()
        self.firstChar =  self.cursor.selectionStart()
        self.lastChar =  self.cursor.selectionEnd()
        self.noSelection = False
        if self.firstChar == self.lastChar:
            self.noSelection = True
        self.originalPosition = self.cursor.position()
        self.cursorBlockPos = self.cursor.positionInBlock()

# Snippets dictionary. Longest match gets priority. Must be before the cursor, and cursor must be at a block end.
snippets_dic = {
    'n'			: 'nuke.thisNode()',
    'an'    	: 'something else',
    'cat'		: 'dog',
    'cosa'      : 'otrra cosa'
}


def findLongestEndingMatch(text, dic):
    '''
    If the text ends with a key in the dictionary, it returns the key and value.
    If there are several matches, returns the longest one.
    False if no matches.
    '''
    longest = 0 #len of longest match
    match_key = None
    match_snippet = ""
    for key, val in dic.items():
        match = re.search(r"[\s]"+key+"$",text)
        if match or text == key:
            if len(key) > longest:
                longest = len(key)
                match_key = key
                match_snippet = val
    if match_key is None:
        return False
    print(match_key+"\n"+match_snippet)
    return match_key, match_snippet

class TPanel(QtWidgets.QDialog):
    def __init__(self):
        super(TPanel,self).__init__()
        self.setWindowTitle("this is a test")
        self.snippets_txt_path = os.path.expandvars(os.path.expanduser("~/.nuke/apSnippets.txt"))
        self.editor = QtWidgets.QPlainTextEdit(self)
        self.frw = FindReplaceWidget(self.editor)
        self.frw_btn = QtWidgets.QPushButton("Searchreplace")
        self.frw_btn.clicked.connect(self.toggleFrw)
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.editor)
        layout.addWidget(self.frw)
        layout.addWidget(self.frw_btn)
        layout.setSpacing(0)
        layout.setMargin(0)

        self.setLayout(layout)
        self.loadSnippets()

    def openSnippets(self):
        ''' Open the preferences panel '''
        global snippet_panel
        snippet_panel = SnippetsPanel(self)
        if snippet_panel.show():
            self.loadSnippets()
    def loadSnippets(self):
        ''' Load prefs '''
        if not os.path.isfile(self.snippets_txt_path):
            return []
        else:
            with open(self.snippets_txt_path, "r") as f:
                self.snippets = json.load(f)
                return self.snippets
    def toggleFrw(self):
        self.frw.setVisible(not self.frw.isVisible())

class SnippetsPanel(QtWidgets.QDialog):
    def __init__(self, mainWidget):
        super(SnippetsPanel, self).__init__()
        self.mainWidget = mainWidget

        self.snippets_txt_path = self.mainWidget.snippets_txt_path
        self.snippets_dict = self.mainWidget.loadSnippets()
        #self.snippets_dict = snippets_dic

        #self.saveSnippets(snippets_dic)

        self.initUI()

    def initUI(self):
        self.layout = QtWidgets.QVBoxLayout()

        # First Area (Titles)
        title_layout = QtWidgets.QHBoxLayout()
        shortcuts_label = QtWidgets.QLabel("Shortcut")
        code_label = QtWidgets.QLabel("Code snippet")
        title_layout.addWidget(shortcuts_label,stretch=1)
        title_layout.addWidget(code_label,stretch=2)
        self.layout.addLayout(title_layout)


        # Main Scroll area
        self.scroll_content = QtWidgets.QWidget()
        self.scroll_layout = QtWidgets.QVBoxLayout()

        for i, (key, val) in enumerate(self.snippets_dict.items()):
            snippet_edit = SnippetEdit(key, val)
            self.scroll_layout.insertWidget(-1, snippet_edit)

        self.scroll_content.setLayout(self.scroll_layout)

        # Scroll Area Properties
        self.scroll = QtWidgets.QScrollArea()
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setWidgetResizable(True)
        self.scroll.setWidget(self.scroll_content)

        self.layout.addWidget(self.scroll)

        # Lower buttons
        self.btn_layout = QtWidgets.QHBoxLayout()

        self.add_btn = QtWidgets.QPushButton("Add snippet")
        self.add_btn.setToolTip("Create empty fields for an extra snippet.")
        self.add_btn.clicked.connect(self.addSnippet)
        self.btn_layout.addWidget(self.add_btn)

        self.btn_layout.addStretch()

        self.save_btn = QtWidgets.QPushButton('OK')
        self.save_btn.setToolTip("Save the snippets into a json file and close the panel.")
        self.save_btn.clicked.connect(self.okPressed)
        self.btn_layout.addWidget(self.save_btn)

        self.cancel_btn = QtWidgets.QPushButton("Cancel")
        self.cancel_btn.setToolTip("Cancel any new snippets or modifications.")
        self.cancel_btn.clicked.connect(self.close)
        self.btn_layout.addWidget(self.cancel_btn)

        self.apply_btn = QtWidgets.QPushButton('Apply')
        self.apply_btn.setToolTip("Save the snippets into a json file.")
        self.apply_btn.clicked.connect(self.saveSnippets)
        self.btn_layout.addWidget(self.apply_btn)


        self.layout.addLayout(self.btn_layout)

        self.setLayout(self.layout)

    def getSnippetsAsDict(self):
        dic = {}
        num_snippets = self.scroll_layout.count()
        for s in range(num_snippets):
            se = self.scroll_layout.itemAt(s).widget()
            key = se.shortcut_editor.text()
            val = se.snippet_editor.toPlainText()
            if key != "":
                dic[key] = val
        return dic

    def saveSnippets(self,snippets = ""):
        if snippets == "":
            snippets = self.getSnippetsAsDict()
        with open(self.snippets_txt_path,"w") as f:
            prefs = json.dump(snippets, f)
        return prefs

    def okPressed(self):
        self.saveSnippets()
        self.accept()

    def addSnippet(self):
        self.scroll_layout.insertWidget(0, SnippetEdit())
        self.show()
        return

class SnippetEdit(QtWidgets.QWidget):
    ''' Simple widget containing two fields, for the snippet shortcut and content '''
    def __init__(self, key="", val=""):
        super(SnippetEdit,self).__init__()

        self.layout = QtWidgets.QHBoxLayout()

        self.shortcut_editor = QtWidgets.QLineEdit(self)
        f = self.shortcut_editor.font()
        f.setWeight(QtGui.QFont.Bold)
        self.shortcut_editor.setFont(f)
        self.shortcut_editor.setText(str(key))
        self.snippet_editor = QtWidgets.QTextEdit(self)
        self.snippet_editor.resize(90,90)
        self.snippet_editor.setPlainText(str(val))
        self.layout.addWidget(self.shortcut_editor, stretch=1, alignment = Qt.AlignTop)
        self.layout.addWidget(self.snippet_editor, stretch=2)

        self.layout.setMargin(0)
        self.layout.setMargin(0)

        self.setLayout(self.layout)

def seKeyPressEvent(self, event):
    if type(event) == QtGui.QKeyEvent:
        if event.key()==Qt.Key_Tab:
            # 1. Set the cursor
            self.cursor = self.textCursor()

            # 2. Save text before and after
            cpos = self.cursor.position()
            text_before_cursor = self.toPlainText()[:cpos]
            text_after_cursor = self.toPlainText()[cpos:]

            # 3. Check coincidences in snippets dicts
            try:
                match_key, match_snippet = findLongestEndingMatch(text_before_cursor,self.parent().snippets)
                for i in range(len(match_key)):
                    self.cursor.deletePreviousChar()
                self.cursor.insertText(match_snippet)
            except:
                QtWidgets.QPlainTextEdit.keyPressEvent(self,event)
        elif event.modifiers():
            self.parentWidget().openSnippets()
        else:
            QtWidgets.QPlainTextEdit.keyPressEvent(self,event)

# SearchReplace
class FindReplaceWidget(QtWidgets.QWidget):
    ''' SearchReplace Widget for the knobscripter. FindReplaceWidget(editor = QPlainTextEdit) '''
    def __init__(self, editor):
        super(FindReplaceWidget,self).__init__()

        self.editor = editor

        self.initUI()

    def initUI(self):

        #--------------
        # Find Row
        #--------------

        # Widgets
        self.find_label = QtWidgets.QLabel("Find:")
        #self.find_label.setSizePolicy(QtWidgets.QSizePolicy.Fixed,QtWidgets.QSizePolicy.Fixed)
        self.find_label.setFixedWidth(50)
        self.find_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.find_lineEdit = QtWidgets.QLineEdit()
        self.find_next_button = QtWidgets.QPushButton("Next")
        self.find_next_button.clicked.connect(self.find)
        self.find_prev_button = QtWidgets.QPushButton("Previous")

        # Layout
        self.find_layout = QtWidgets.QHBoxLayout()
        self.find_layout.addWidget(self.find_label)
        self.find_layout.addWidget(self.find_lineEdit, stretch = 1)
        self.find_layout.addWidget(self.find_next_button)
        self.find_layout.addWidget(self.find_prev_button)


        #--------------
        # Replace Row
        #--------------

        # Widgets
        self.replace_label = QtWidgets.QLabel("Replace:")
        #self.replace_label.setSizePolicy(QtWidgets.QSizePolicy.Fixed,QtWidgets.QSizePolicy.Fixed)
        self.replace_label.setFixedWidth(50)
        self.replace_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.replace_lineEdit = QtWidgets.QLineEdit()
        self.replace_button = QtWidgets.QPushButton("Replace")
        self.replace_all_button = QtWidgets.QPushButton("Replace All")

        # Layout
        self.replace_layout = QtWidgets.QHBoxLayout()
        self.replace_layout.addWidget(self.replace_label)
        self.replace_layout.addWidget(self.replace_lineEdit, stretch = 1)
        self.replace_layout.addWidget(self.replace_button)
        self.replace_layout.addWidget(self.replace_all_button)


        #--------------
        # Main Layout
        #--------------

        self.layout = QtWidgets.QVBoxLayout()

        self.layout.addLayout(self.find_layout)
        self.layout.addLayout(self.replace_layout)
        self.layout.setSpacing(4)
        self.setLayout(self.layout)
        #self.adjustSize()
        #self.setMaximumHeight(180)

    def find(self, find_str = None, match_case = True):
        if find_str is None:
            find_str = self.find_lineEdit.text()

        # Beginning of undo block
        cursor = self.editor.textCursor()
        cursor.beginEditBlock()

        # Use flags for case match
        flags = QtGui.QTextDocument.FindFlags()
        if match_case:
            flags=flags|QtGui.QTextDocument.FindCaseSensitively

        # Find next
        r = self.editor.find(find_str,flags)

        # If
        print r
        self.editor.setFocus()

        return r













# Next two are useless
def wks(self, event):
    #self.getCursorInfo()
    self.cursor = self.textCursor()
    self.cursor.insertText("match_snippet")
def tuneSE():
    script_editors = findScriptEditors()
    for script_editor in script_editors:
        s = script_editor.findChild(QtWidgets.QPlainTextEdit)

def go():
    panel = TPanel()
    te = panel.findChildren(QtWidgets.QPlainTextEdit)[0]
    te.keyPressEvent = MethodType(seKeyPressEvent, te)

    if panel.exec_():
        return

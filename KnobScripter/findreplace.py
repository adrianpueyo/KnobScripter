# -*- coding: utf-8 -*-
""" FindReplaceWidget: Search and Replace widget for a QPlainTextEdit! Designed for KnobScripter

adrianpueyo.com

"""

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


class FindReplaceWidget(QtWidgets.QWidget):
    """
    SearchReplace Widget for the knobscripter. FindReplaceWidget(parent = QPlainTextEdit)
    """

    def __init__(self, textedit, parent=None):
        super(FindReplaceWidget, self).__init__(parent)

        self.editor = textedit

        self.initUI()

    def initUI(self):

        # --------------
        # Find Row
        # --------------

        # Widgets
        self.find_label = QtWidgets.QLabel("Find:")
        # self.find_label.setSizePolicy(QtWidgets.QSizePolicy.Fixed,QtWidgets.QSizePolicy.Fixed)
        self.find_label.setFixedWidth(50)
        self.find_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.find_lineEdit = QtWidgets.QLineEdit()
        self.find_next_button = QtWidgets.QPushButton("Next")
        self.find_next_button.clicked.connect(self.find)
        self.find_prev_button = QtWidgets.QPushButton("Previous")
        self.find_prev_button.clicked.connect(self.findBack)
        self.find_lineEdit.returnPressed.connect(self.find_next_button.click)

        # Layout
        self.find_layout = QtWidgets.QHBoxLayout()
        self.find_layout.addWidget(self.find_label)
        self.find_layout.addWidget(self.find_lineEdit, stretch=1)
        self.find_layout.addWidget(self.find_next_button)
        self.find_layout.addWidget(self.find_prev_button)

        # --------------
        # Replace Row
        # --------------

        # Widgets
        self.replace_label = QtWidgets.QLabel("Replace:")
        # self.replace_label.setSizePolicy(QtWidgets.QSizePolicy.Fixed,QtWidgets.QSizePolicy.Fixed)
        self.replace_label.setFixedWidth(50)
        self.replace_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.replace_lineEdit = QtWidgets.QLineEdit()
        self.replace_button = QtWidgets.QPushButton("Replace")
        self.replace_button.clicked.connect(self.replace)
        self.replace_all_button = QtWidgets.QPushButton("Replace All")
        self.replace_all_button.clicked.connect(lambda: self.replace(rep_all=True))
        self.replace_lineEdit.returnPressed.connect(self.replace_button.click)

        # Layout
        self.replace_layout = QtWidgets.QHBoxLayout()
        self.replace_layout.addWidget(self.replace_label)
        self.replace_layout.addWidget(self.replace_lineEdit, stretch=1)
        self.replace_layout.addWidget(self.replace_button)
        self.replace_layout.addWidget(self.replace_all_button)

        # Info text
        self.info_text = QtWidgets.QLabel("")
        self.info_text.setVisible(False)
        self.info_text.mousePressEvent = lambda x: self.info_text.setVisible(False)
        # f = self.info_text.font()
        # f.setItalic(True)
        # self.info_text.setFont(f)
        # self.info_text.clicked.connect(lambda:self.info_text.setVisible(False))

        # Divider line
        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.HLine)
        line.setFrameShadow(QtWidgets.QFrame.Sunken)
        line.setLineWidth(0)
        line.setMidLineWidth(1)
        line.setFrameShadow(QtWidgets.QFrame.Sunken)

        # --------------
        # Main Layout
        # --------------

        self.layout = QtWidgets.QVBoxLayout()
        self.layout.addSpacing(4)
        self.layout.addWidget(self.info_text)
        self.layout.addLayout(self.find_layout)
        self.layout.addLayout(self.replace_layout)
        self.layout.setSpacing(4)
        if nuke.NUKE_VERSION_MAJOR >= 11:
            self.layout.setMargin(2)
        else:
            self.layout.setContentsMargins(2, 2, 2, 2)
        self.layout.addSpacing(4)
        self.layout.addWidget(line)
        self.setLayout(self.layout)
        self.setTabOrder(self.find_lineEdit, self.replace_lineEdit)
        # self.adjustSize()
        # self.setMaximumHeight(180)

    def find(self, find_str="", match_case=True):
        if find_str == "":
            find_str = self.find_lineEdit.text()

        matches = self.editor.toPlainText().count(find_str)
        if not matches or matches == 0:
            self.info_text.setText("              No more matches.")
            self.info_text.setVisible(True)
            return
        else:
            self.info_text.setVisible(False)

        # Beginning of undo block
        cursor = self.editor.textCursor()
        cursor.beginEditBlock()

        # Use flags for case match
        flags = QtGui.QTextDocument.FindFlags()
        if match_case:
            flags = flags | QtGui.QTextDocument.FindCaseSensitively

        # Find next
        r = self.editor.find(find_str, flags)

        cursor.endEditBlock()

        self.editor.setFocus()
        self.editor.show()
        return r

    def findBack(self, find_str="", match_case=True):
        if find_str == "":
            find_str = self.find_lineEdit.text()

        matches = self.editor.toPlainText().count(find_str)
        if not matches or matches == 0:
            self.info_text.setText("              No more matches.")
            self.info_text.setVisible(True)
            return
        else:
            self.info_text.setVisible(False)

        # Beginning of undo block
        cursor = self.editor.textCursor()
        cursor.beginEditBlock()

        # Use flags for case match
        flags = QtGui.QTextDocument.FindFlags()
        flags = flags | QtGui.QTextDocument.FindBackward
        if match_case:
            flags = flags | QtGui.QTextDocument.FindCaseSensitively

        # Find prev
        r = self.editor.find(find_str, flags)
        cursor.endEditBlock()
        self.editor.setFocus()
        return r

    def replace(self, find_str="", rep_str="", rep_all=False):
        if find_str == "":
            find_str = self.find_lineEdit.text()
        if rep_str == "":
            rep_str = self.replace_lineEdit.text()

        matches = self.editor.toPlainText().count(find_str)
        if not matches or matches == 0:
            self.info_text.setText("              No more matches.")
            self.info_text.setVisible(True)
            return
        else:
            self.info_text.setVisible(False)

        # Beginning of undo block
        cursor = self.editor.textCursor()
        # cursor_orig_pos = cursor.position()
        cursor.beginEditBlock()

        # Use flags for case match
        flags = QtGui.QTextDocument.FindFlags()
        flags = flags | QtGui.QTextDocument.FindCaseSensitively

        if rep_all:
            cursor.movePosition(QtGui.QTextCursor.Start)
            self.editor.setTextCursor(cursor)
            cursor = self.editor.textCursor()
            rep_count = 0
            while True:
                if not cursor.hasSelection() or cursor.selectedText() != find_str:
                    self.editor.find(find_str, flags)  # Find next
                    cursor = self.editor.textCursor()
                    if not cursor.hasSelection():
                        break
                else:
                    cursor.insertText(rep_str)
                    rep_count += 1
            self.info_text.setText("              Replaced " + str(rep_count) + " matches.")
            self.info_text.setVisible(True)
        else:  # If not "find all"
            if not cursor.hasSelection() or cursor.selectedText() != find_str:
                self.editor.find(find_str, flags)  # Find next
                if not cursor.hasSelection() and matches > 0:  # If not found but there are matches, start over
                    cursor.movePosition(QtGui.QTextCursor.Start)
                    self.editor.setTextCursor(cursor)
                    self.editor.find(find_str, flags)
            else:
                cursor.insertText(rep_str)
                self.editor.find(rep_str, flags | QtGui.QTextDocument.FindBackward)

        cursor.endEditBlock()
        self.replace_lineEdit.setFocus()
        return

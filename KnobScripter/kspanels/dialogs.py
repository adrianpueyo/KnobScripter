import nuke
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

def ask(question, parent=None, default_yes = True):
    msgBox = QtWidgets.QMessageBox(parent=parent)
    msgBox.setText(question)
    msgBox.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
    msgBox.setIcon(QtWidgets.QMessageBox.Question)
    msgBox.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
    if default_yes:
        msgBox.setDefaultButton(QtWidgets.QMessageBox.Yes)
    else:
        msgBox.setDefaultButton(QtWidgets.QMessageBox.No)
    reply = msgBox.exec_()
    return reply == QtWidgets.QMessageBox.Yes



class FileNameDialog(QtWidgets.QDialog):
    '''
    Dialog for creating new... (mode = "folder", "script" or "knob").
    '''
    def __init__(self, parent = None, mode = "folder", text = ""):
        if parent.isPane:
            super(FileNameDialog, self).__init__()
        else:
            super(FileNameDialog, self).__init__(parent)
        self.mode = mode
        self.text = text

        title = "Create new {}.".format(self.mode)
        self.setWindowTitle(title)

        self.initUI()

    def initUI(self):
        # Widgets
        self.name_label = QtWidgets.QLabel("Name: ")
        self.name_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.name_lineEdit = QtWidgets.QLineEdit()
        self.name_lineEdit.setText(self.text)
        self.name_lineEdit.textChanged.connect(self.nameChanged)

        # Buttons
        self.button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        self.button_box.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(self.text != "")
        self.button_box.accepted.connect(self.clickedOk)
        self.button_box.rejected.connect(self.clickedCancel)

        # Layout
        self.master_layout = QtWidgets.QVBoxLayout()
        self.name_layout = QtWidgets.QHBoxLayout()
        self.name_layout.addWidget(self.name_label)
        self.name_layout.addWidget(self.name_lineEdit)
        self.master_layout.addLayout(self.name_layout)
        self.master_layout.addWidget(self.button_box)
        self.setLayout(self.master_layout)

        self.name_lineEdit.setFocus()
        self.setMinimumWidth(250)

    def nameChanged(self):
        txt = self.name_lineEdit.text()
        m = r"[\w]*$"
        if self.mode == "knob": # Knobs can't start with a number...
            m = r"[a-zA-Z_]+" + m

        if re.match(m, txt) or txt == "":
            self.text = txt
        else:
            self.name_lineEdit.setText(self.text)

        self.button_box.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(self.text != "")
        return

    def clickedOk(self):
        self.accept()
        return

    def clickedCancel(self):
        self.reject()
        return


class TextInputDialog(QtWidgets.QDialog):
    '''
    Simple dialog for a text input.
    '''
    def __init__(self, parent = None, name = "", text = "", title=""):
        super(TextInputDialog, self).__init__(parent)

        self.name = name # title of textinput
        self.text = text # default content of textinput

        self.setWindowTitle(title)

        self.initUI()

    def initUI(self):
        # Widgets
        self.name_label = QtWidgets.QLabel(self.name+": ")
        self.name_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.name_lineEdit = QtWidgets.QLineEdit()
        self.name_lineEdit.setText(self.text)
        self.name_lineEdit.textChanged.connect(self.nameChanged)

        # Buttons
        self.button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        #self.button_box.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(self.text != "")
        self.button_box.accepted.connect(self.clickedOk)
        self.button_box.rejected.connect(self.clickedCancel)

        # Layout
        self.master_layout = QtWidgets.QVBoxLayout()
        self.name_layout = QtWidgets.QHBoxLayout()
        self.name_layout.addWidget(self.name_label)
        self.name_layout.addWidget(self.name_lineEdit)
        self.master_layout.addLayout(self.name_layout)
        self.master_layout.addWidget(self.button_box)
        self.setLayout(self.master_layout)

        self.name_lineEdit.setFocus()
        self.setMinimumWidth(250)

    def nameChanged(self):
        self.text = self.name_lineEdit.text()

    def clickedOk(self):
        self.accept()
        return

    def clickedCancel(self):
        self.reject()
        return


class ChooseNodeDialog(QtWidgets.QDialog):
    '''
    Dialog for selecting a node by its name. Only admits nodes that exist (including root, preferences...)
    '''
    def __init__(self, parent = None, name = ""):
        if parent.isPane:
            super(ChooseNodeDialog, self).__init__()
        else:
            super(ChooseNodeDialog, self).__init__(parent)

        self.name = name # Name of node (will be "" by default)
        self.allNodes = []

        self.setWindowTitle("Enter the node's name...")

        self.initUI()

    def initUI(self):
        # Widgets
        self.name_label = QtWidgets.QLabel("Name: ")
        self.name_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.name_lineEdit = QtWidgets.QLineEdit()
        self.name_lineEdit.setText(self.name)
        self.name_lineEdit.textChanged.connect(self.nameChanged)

        self.allNodes = self.getAllNodes()
        completer = QtWidgets.QCompleter(self.allNodes, self)
        completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.name_lineEdit.setCompleter(completer)

        # Buttons
        self.button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        self.button_box.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(nuke.exists(self.name))
        self.button_box.accepted.connect(self.clickedOk)
        self.button_box.rejected.connect(self.clickedCancel)

        # Layout
        self.master_layout = QtWidgets.QVBoxLayout()
        self.name_layout = QtWidgets.QHBoxLayout()
        self.name_layout.addWidget(self.name_label)
        self.name_layout.addWidget(self.name_lineEdit)
        self.master_layout.addLayout(self.name_layout)
        self.master_layout.addWidget(self.button_box)
        self.setLayout(self.master_layout)

        self.name_lineEdit.setFocus()
        self.setMinimumWidth(250)

    def getAllNodes(self):
        self.allNodes = [n.fullName() for n in nuke.allNodes(recurseGroups=True)] #if parent is in current context??
        self.allNodes.extend(["root","preferences"])
        return self.allNodes

    def nameChanged(self):
        self.name = self.name_lineEdit.text()
        self.button_box.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(self.name in self.allNodes)

    def clickedOk(self):
        self.accept()
        return

    def clickedCancel(self):
        self.reject()
        return
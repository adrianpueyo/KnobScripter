# -*- coding: utf-8 -*-
""" ScriptOutputWidget: Output utput console.

The Script Output Widget is a basic QTextEdit that works as the main output
window of the KnobScripter's Script Editor. Simple module that can grow
as needed in the future.

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


class ScriptOutputWidget(QtWidgets.QTextEdit):
    """
    Script Output Widget
    The output logger works the same way as Nuke's python script editor output window
    """

    def __init__(self, parent=None):
        super(ScriptOutputWidget, self).__init__(parent)
        self.knobScripter = parent
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.setMinimumHeight(20)

    def keyPressEvent(self, event):
        # ctrl = ((event.modifiers() and Qt.ControlModifier) != 0)
        # alt = ((event.modifiers() and Qt.AltModifier) != 0)
        # shift = ((event.modifiers() and Qt.ShiftModifier) != 0)
        key = event.key()
        if type(event) == QtGui.QKeyEvent:
            # print event.key()
            if key in [32]:  # Space
                return KnobScripter.keyPressEvent(self.knobScripter, event)
            elif key in [Qt.Key_Backspace, Qt.Key_Delete]:
                self.knobScripter.clearConsole()
        return QtWidgets.QTextEdit.keyPressEvent(self, event)

# -*- coding: utf-8 -*-
""" ScriptOutputWidget: Output console.

The Script Output Widget is a basic QTextEdit that works as the main output
window of KnobScripter's Script Editor. This module can be extended in the future.

adrianpueyo.com
"""

import nuke
import math
from KnobScripter import config

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


class ScriptOutputWidget(QtWidgets.QTextEdit):
    """
    Script Output Widget.

    This widget works as the output logger, similar to Nuke's python script editor output window.
    """
    def __init__(self, parent=None):
        super(ScriptOutputWidget, self).__init__(parent)
        self.knobScripter = parent
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.setMinimumHeight(20)
        self.setFont(config.script_editor_font)

    def set_custom_tab_stop(self, width):
        if hasattr(self, 'setTabStopDistance'):
            # PySide6
            self.setTabStopDistance(width)
        else:
            # PySide2
            self.setTabStopWidth(int(width))

    def get_custom_tab_stop(self):
        if hasattr(self, 'tabStopDistance'):
            # PySide6
            return self.tabStopDistance()
        else:
            # PySide2
            return self.tabStopWidth()

    def keyPressEvent(self, event):
        """
        Handle key press events.

        - Ctrl + Plus/Minus adjusts the font size via zoomIn/zoomOut.
        - Space key is forwarded to the knobScripter's keyPressEvent.
        - Backspace/Delete clears the console via knobScripter.clearConsole().
        Otherwise, the default QTextEdit key press event is used.
        """
        ctrl = bool(event.modifiers() & Qt.ControlModifier)
        key = event.key()

        if isinstance(event, QtGui.QKeyEvent):
            if ctrl and key == Qt.Key_Plus:
                self.zoomIn()
            elif ctrl and key == Qt.Key_Minus:
                self.zoomOut()
            elif key == 32:  # Space key
                return self.knobScripter.keyPressEvent(event)
            elif key in [Qt.Key_Backspace, Qt.Key_Delete]:
                self.knobScripter.clearConsole()
        return QtWidgets.QTextEdit.keyPressEvent(self, event)

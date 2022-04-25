# -*- coding: utf-8 -*-
""" KeywordHotbox: KnobScripter's floating panel for word suggestions while scripting.

adrianpueyo.com

"""
import nuke
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


class KeywordHotbox(QtWidgets.QDialog):
    """
    Floating panel with word suggestions
    Based on the given keywords dictionary of lists. Example:
    keyword_dict = {
        "Access method": {
            "keywords": ["eAccessPoint","eAccessRanged1D"],
            "help": "Full help! <with html tags and whatever><li><ul><b>..."
        },
    }
    When clicking on a button, the accept() signal is emitted, and the button's text is stored under self.selection
    """

    def __init__(self, parent, category="", category_dict=None):
        super(KeywordHotbox, self).__init__(parent)
        category_dict = category_dict or {}

        self.script_editor = parent
        self.setWindowFlags(
            QtCore.Qt.FramelessWindowHint | QtCore.Qt.Popup)  # Without self.windowFlags() first, closes as intended

        if not category or "keywords" not in category_dict:
            self.reject()
            return

        self.category = category
        self.category_dict = category_dict
        self.selection = ""

        self.initUI()

        # Move hotbox to appropriate position
        self.move(QtGui.QCursor().pos() - QtCore.QPoint((self.width() / 2), -6))
        self.installEventFilter(self)

    def initUI(self):

        master_layout = QtWidgets.QVBoxLayout()

        # 1. Main part: Hotbox Buttons
        for keyword in self.category_dict["keywords"]:
            button = KeywordHotboxButton(keyword, self)
            button.clicked.connect(partial(self.pressed, keyword))
            master_layout.insertWidget(-1, button)

        # 2. ToolTip etc
        if "help" in self.category_dict:
            category_help = self.category_dict["help"]
        else:
            category_help = ""

        if nuke.NUKE_VERSION_MAJOR < 11:
            master_layout.setContentsMargins(0, 0, 0, 0)
        else:
            master_layout.setMargin(0)
            master_layout.setSpacing(0)

        self.setToolTip("<h2>{}</h2>".format(self.category) + category_help)

        self.setStyleSheet('''QToolTip{
                                border: 1px solid black;
                                padding: 10px;
                                }
                            ''')
        self.setLayout(master_layout)
        self.adjustSize()

    def pressed(self, keyword=""):
        if keyword != "":
            self.selection = keyword
        self.accept()

    def focusOutEvent(self, event):
        self.close()
        QtWidgets.QDialog.focusOutEvent(event)


class KeywordHotboxButton(QtWidgets.QLabel):
    """
    Keyword button for the KeywordHotbox. It's really a label, with a selection color and stuff.
    """
    clicked = QtCore.Signal()

    def __init__(self, name, parent=None):

        super(KeywordHotboxButton, self).__init__(parent)

        self.parent = parent

        if hasattr(parent, 'script_editor') and hasattr(parent.script_editor, 'knob_scripter'):
            self.knobScripter = parent.script_editor.knob_scripter
        else:
            self.knobScripter = None

        self.name = name
        self.highlighted = False
        self.defaultStyle = self.style()

        self.setMouseTracking(True)
        # self.setTextFormat(QtCore.Qt.RichText)
        # self.setWordWrap(True)
        self.setText(self.name)
        self.setHighlighted(False)

        if self.knobScripter:
            self.setFont(self.knobScripter.script_editor_font)
        else:
            font = QtGui.QFont()
            font.setFamily("Monospace")
            font.setStyleHint(QtGui.QFont.Monospace)
            font.setFixedPitch(True)
            font.setPointSize(11)
            self.setFont(font)

    def setHighlighted(self, highlighted=False):
        """
        Define the style of the button for different states
        """

        # Selected
        if highlighted:
            # self.setStyle(QtWidgets.QStyleFactory.create('Plastique')) #background:#e90;
            self.setStyleSheet("""
                                border: 0px solid black;
                                background:#555; 
                                color:#eeeeee;
                                padding: 6px 4px;
                                """)

        # Deselected
        else:
            # self.setStyle(self.defaultStyle)
            self.setStyleSheet("""
                                border: 0px solid #000;
                                background:#3e3e3e;
                                color:#eeeeee;
                                padding: 6px 4px;
                                """)

        self.highlighted = highlighted

    def enterEvent(self, event):
        """ Mouse hovering """
        self.setHighlighted(True)
        return True

    def leaveEvent(self, event):
        """ Stopped hovering """
        self.setHighlighted(False)
        return True

    def mouseReleaseEvent(self, event):
        """
        Execute the buttons' self.function (str)
        """
        if self.highlighted:
            self.clicked.emit()
            pass
        super(KeywordHotboxButton, self).mouseReleaseEvent(event)

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


class CodeGallery(QtWidgets.QDialog):
    def __init__(self, knobScripter="", _parent=QtWidgets.QApplication.activeWindow()):
        super(CodeGallery, self).__init__(_parent)

        self.knobScripter = knobScripter
        self.setWindowTitle("Code Gallery + Snippet Editor")

        self.initUI()
        # self.resize(500,300)

    def initUI(self):
        master_layout = QtWidgets.QVBoxLayout()

        test_label = QtWidgets.QLabel("test")
        master_layout.addWidget(test_label)

        self.setLayout(master_layout)


# class CodeGalleryPane(CodeGallery)
# def __init__(self, node = "", knob="knobChanged"):
#        super(KnobScripterPane, self).__init__(isPane=True, _parent=QtWidgets.QApplication.activeWindow())
# TODO Pane instead, its own thing
# TODO: Snippets: button to delete snippet, add snippet to script
# TODO: Snippet editor and preferences apply changes (via "Reload Snippets and Settings button or whatever...") on all knobscripters? (by having a set of the active knobscripters and removing them on close)

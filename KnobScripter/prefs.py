import json
import nuke

from info import __version__, __author__, __date__
import config

try:
    if nuke.NUKE_VERSION_MAJOR < 11:
        from PySide import QtCore, QtGui, QtGui as QtWidgets
        from PySide.QtCore import Qt
    else:
        from PySide2 import QtWidgets, QtGui, QtCore
        from PySide2.QtCore import Qt
except ImportError:
    from Qt import QtCore, QtGui, QtWidgets


class PrefsWidget(QtWidgets.QDialog):
    def __init__(self, knobScripter="", _parent=QtWidgets.QApplication.activeWindow()):
        super(PrefsWidget, self).__init__(_parent)

        # Vars
        self.knobScripter = knobScripter
        self.oldFontSize = config.script_editor_font.pointSize()
        self.oldFont = config.script_editor_font.family()
        self.oldScheme = config.prefs["code_style_python"]
        self.font = self.oldFont

        # Widgets
        kspTitle = QtWidgets.QLabel("KnobScripter v" + __version__)
        kspTitle.setStyleSheet("font-weight:bold;color:#CCCCCC;font-size:24px;")
        kspSubtitle = QtWidgets.QLabel("Script editor for python and callback knobs")
        kspSubtitle.setStyleSheet("color:#999")
        kspLine = QtWidgets.QFrame()
        kspLine.setFrameShape(QtWidgets.QFrame.HLine)
        kspLine.setFrameShadow(QtWidgets.QFrame.Sunken)
        kspLine.setLineWidth(0)
        kspLine.setMidLineWidth(1)
        kspLine.setFrameShadow(QtWidgets.QFrame.Sunken)
        kspLineBottom = QtWidgets.QFrame()
        kspLineBottom.setFrameShape(QtWidgets.QFrame.HLine)
        kspLineBottom.setFrameShadow(QtWidgets.QFrame.Sunken)
        kspLineBottom.setLineWidth(0)
        kspLineBottom.setMidLineWidth(1)
        kspLineBottom.setFrameShadow(QtWidgets.QFrame.Sunken)
        kspSignature = QtWidgets.QLabel(
            '<a href="http://www.adrianpueyo.com/" style="color:#888;text-decoration:none"><b>adrianpueyo.com</b></a>, 2016-2020')
        kspSignature.setOpenExternalLinks(True)
        kspSignature.setStyleSheet('''color:#555;font-size:9px;''')
        kspSignature.setAlignment(QtCore.Qt.AlignRight)

        fontLabel = QtWidgets.QLabel("Font:")
        self.fontBox = QtWidgets.QFontComboBox()
        self.fontBox.setCurrentFont(QtGui.QFont(self.font))
        self.fontBox.currentFontChanged.connect(self.fontChanged)

        fontSizeLabel = QtWidgets.QLabel("Font size:")
        self.fontSizeBox = QtWidgets.QSpinBox()
        self.fontSizeBox.setValue(self.oldFontSize)
        self.fontSizeBox.setMinimum(6)
        self.fontSizeBox.setMaximum(100)
        self.fontSizeBox.valueChanged.connect(self.fontSizeChanged)

        windowWLabel = QtWidgets.QLabel("Width (px):")
        windowWLabel.setToolTip("Default window width in pixels")
        self.windowWBox = QtWidgets.QSpinBox()
        self.windowWBox.setValue(config.prefs["ks_default_size"][0])
        self.windowWBox.setMinimum(200)
        self.windowWBox.setMaximum(4000)
        self.windowWBox.setToolTip("Default window width in pixels")

        windowHLabel = QtWidgets.QLabel("Height (px):")
        windowHLabel.setToolTip("Default window height in pixels")
        self.windowHBox = QtWidgets.QSpinBox()
        self.windowHBox.setValue(config.prefs["ks_default_size"][1])
        self.windowHBox.setMinimum(100)
        self.windowHBox.setMaximum(2000)
        self.windowHBox.setToolTip("Default window height in pixels")

        self.grabDimensionsButton = QtWidgets.QPushButton("Grab current dimensions")
        self.grabDimensionsButton.clicked.connect(self.grabDimensions)

        tabSpaceLabel = QtWidgets.QLabel("Tab spaces:")
        tabSpaceLabel.setToolTip("Number of spaces to add with the tab key.")
        self.tabSpace2 = QtWidgets.QRadioButton("2")
        self.tabSpace4 = QtWidgets.QRadioButton("4")
        tabSpaceButtonGroup = QtWidgets.QButtonGroup(self)
        tabSpaceButtonGroup.addButton(self.tabSpace2)
        tabSpaceButtonGroup.addButton(self.tabSpace4)
        self.tabSpace2.setChecked(config.prefs["se_tab_spaces"] == 2)
        self.tabSpace4.setChecked(config.prefs["se_tab_spaces"] == 4)

        contextDefaultLabel = QtWidgets.QLabel("Run in context (beta):")
        contextDefaultLabel.setToolTip("Default mode for running code in context (when in node mode).")
        self.contextDefaultOn = QtWidgets.QRadioButton("On")
        self.contextDefaultOff = QtWidgets.QRadioButton("Off")
        contextDefaultButtonGroup = QtWidgets.QButtonGroup(self)
        contextDefaultButtonGroup.addButton(self.contextDefaultOn)
        contextDefaultButtonGroup.addButton(self.contextDefaultOff)
        self.contextDefaultOn.setChecked(config.prefs["ks_run_in_context"] == True)
        self.contextDefaultOff.setChecked(config.prefs["ks_run_in_context"] == False)
        self.contextDefaultOn.clicked.connect(lambda: self.knobScripter.setRunInContext(True))
        self.contextDefaultOff.clicked.connect(lambda: self.knobScripter.setRunInContext(False))

        colorSchemeLabel = QtWidgets.QLabel("Color scheme:")
        colorSchemeLabel.setToolTip("Syntax highlighting text style.")
        self.colorSchemeSublime = QtWidgets.QRadioButton("subl")
        self.colorSchemeNuke = QtWidgets.QRadioButton("nuke")
        colorSchemeButtonGroup = QtWidgets.QButtonGroup(self)
        colorSchemeButtonGroup.addButton(self.colorSchemeSublime)
        colorSchemeButtonGroup.addButton(self.colorSchemeNuke)
        colorSchemeButtonGroup.buttonClicked.connect(self.colorSchemeChanged)
        self.colorSchemeSublime.setChecked(config.prefs["code_style_python"] == "sublime")
        self.colorSchemeNuke.setChecked(config.prefs["code_style_python"] == "nuke")

        showLabelsLabel = QtWidgets.QLabel("Show labels:")
        showLabelsLabel.setToolTip("Display knob labels on the knob dropdown\nOtherwise, shows the internal name only.")
        self.showLabelsOn = QtWidgets.QRadioButton("On")
        self.showLabelsOff = QtWidgets.QRadioButton("Off")
        showLabelsButtonGroup = QtWidgets.QButtonGroup(self)
        showLabelsButtonGroup.addButton(self.showLabelsOn)
        showLabelsButtonGroup.addButton(self.showLabelsOff)
        self.showLabelsOn.setChecked(config.prefs["ks_show_knob_labels"] == True)
        self.showLabelsOff.setChecked(config.prefs["ks_show_knob_labels"] == False)

        self.buttonBox = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        self.buttonBox.accepted.connect(self.savePrefs)
        self.buttonBox.rejected.connect(self.cancelPrefs)

        # Loaded custom values
        self.ksPrefs = self.knobScripter.loadPrefs() #TODO This function should go here, and not be nested? Or leave this just for the panel?? there should probably be a prefs file and a prefs panel/widget...
        if self.ksPrefs != []:
            try:
                self.fontSizeBox.setValue(self.ksPrefs['font_size'])
                self.windowWBox.setValue(self.ksPrefs['window_default_w'])
                self.windowHBox.setValue(self.ksPrefs['window_default_h'])
                self.tabSpace2.setChecked(self.ksPrefs['tab_spaces'] == 2)
                self.tabSpace4.setChecked(self.ksPrefs['tab_spaces'] == 4)
                self.contextDefaultOn.setChecked(self.ksPrefs['context_default'] == 1)
                self.contextDefaultOff.setChecked(self.ksPrefs['context_default'] == 0)
                self.showLabelsOn.setChecked(self.ksPrefs['show_labels'] == 1)
                self.showLabelsOff.setChecked(self.ksPrefs['show_labels'] == 0)
                self.colorSchemeSublime.setChecked(self.ksPrefs['color_scheme'] == "sublime")
                self.colorSchemeNuke.setChecked(self.ksPrefs['color_scheme'] == "nuke")
            except:
                pass

        # Layouts
        font_layout = QtWidgets.QHBoxLayout()
        font_layout.addWidget(fontLabel)
        font_layout.addWidget(self.fontBox)

        fontSize_layout = QtWidgets.QHBoxLayout()
        fontSize_layout.addWidget(fontSizeLabel)
        fontSize_layout.addWidget(self.fontSizeBox)

        windowW_layout = QtWidgets.QHBoxLayout()
        windowW_layout.addWidget(windowWLabel)
        windowW_layout.addWidget(self.windowWBox)

        windowH_layout = QtWidgets.QHBoxLayout()
        windowH_layout.addWidget(windowHLabel)
        windowH_layout.addWidget(self.windowHBox)

        tabSpacesButtons_layout = QtWidgets.QHBoxLayout()
        tabSpacesButtons_layout.addWidget(self.tabSpace2)
        tabSpacesButtons_layout.addWidget(self.tabSpace4)
        tabSpaces_layout = QtWidgets.QHBoxLayout()
        tabSpaces_layout.addWidget(tabSpaceLabel)
        tabSpaces_layout.addLayout(tabSpacesButtons_layout)

        contextDefaultButtons_layout = QtWidgets.QHBoxLayout()
        contextDefaultButtons_layout.addWidget(self.contextDefaultOn)
        contextDefaultButtons_layout.addWidget(self.contextDefaultOff)
        contextDefault_layout = QtWidgets.QHBoxLayout()
        contextDefault_layout.addWidget(contextDefaultLabel)
        contextDefault_layout.addLayout(contextDefaultButtons_layout)

        showLabelsButtons_layout = QtWidgets.QHBoxLayout()
        showLabelsButtons_layout.addWidget(self.showLabelsOn)
        showLabelsButtons_layout.addWidget(self.showLabelsOff)
        showLabels_layout = QtWidgets.QHBoxLayout()
        showLabels_layout.addWidget(showLabelsLabel)
        showLabels_layout.addLayout(showLabelsButtons_layout)

        colorSchemeButtons_layout = QtWidgets.QHBoxLayout()
        colorSchemeButtons_layout.addWidget(self.colorSchemeSublime)
        colorSchemeButtons_layout.addWidget(self.colorSchemeNuke)
        colorScheme_layout = QtWidgets.QHBoxLayout()
        colorScheme_layout.addWidget(colorSchemeLabel)
        colorScheme_layout.addLayout(colorSchemeButtons_layout)

        self.master_layout = QtWidgets.QVBoxLayout()
        self.master_layout.addWidget(kspTitle)
        self.master_layout.addWidget(kspSignature)
        self.master_layout.addWidget(kspLine)
        self.master_layout.addLayout(font_layout)
        self.master_layout.addLayout(fontSize_layout)
        self.master_layout.addLayout(windowW_layout)
        self.master_layout.addLayout(windowH_layout)
        self.master_layout.addWidget(self.grabDimensionsButton)
        self.master_layout.addLayout(tabSpaces_layout)
        self.master_layout.addLayout(contextDefault_layout)
        self.master_layout.addLayout(showLabels_layout)
        self.master_layout.addLayout(colorScheme_layout)
        self.master_layout.addWidget(self.buttonBox)
        self.setLayout(self.master_layout)
        # self.setFixedSize(self.minimumSize())

    def savePrefs(self):
        self.font = self.fontBox.currentFont().family()
        ks_prefs = {
            'font_size': self.fontSizeBox.value(),
            'window_default_w': self.windowWBox.value(),
            'window_default_h': self.windowHBox.value(),
            'tab_spaces': self.tabSpaceValue(),
            'context_default': self.contextDefaultValue(),
            'show_labels': self.showLabelsValue(),
            'font': self.font,
            'color_scheme': self.colorSchemeValue(),
        }
        config.script_editor_font.setFamily(self.font)
        self.knobScripter.script_editor.setFont(config.script_editor_font)
        self.knobScripter.font = self.font
        self.knobScripter.color_scheme = self.colorSchemeValue()
        self.knobScripter.runInContext = self.contextDefaultValue()
        self.knobScripter.runInContextAct.setChecked(self.contextDefaultValue())
        self.knobScripter.tabSpaces = self.tabSpaceValue()
        self.knobScripter.script_editor.tab_spaces = self.tabSpaceValue()
        with open(config.prefs_txt_path, "w") as f:
            prefs = json.dump(ks_prefs, f, sort_keys=True, indent=4)
        self.accept()
        self.knobScripter.highlighter.rehighlight()
        self.knobScripter.show_labels = self.showLabelsValue()
        if self.knobScripter.nodeMode:
            self.knobScripter.refreshClicked()
        return prefs

    def cancelPrefs(self):
        config.script_editor_font.setPointSize(self.oldFontSize)
        self.knobScripter.script_editor.setFont(config.script_editor_font)
        self.knobScripter.color_scheme = self.oldScheme
        self.knobScripter.highlighter.rehighlight()
        self.reject()
        global PrefsPanel
        PrefsPanel = ""

    def fontSizeChanged(self):
        config.script_editor_font.setPointSize(self.fontSizeBox.value())
        self.knobScripter.script_editor.setFont(config.script_editor_font)
        return

    def fontChanged(self):
        self.font = self.fontBox.currentFont().family()
        config.script_editor_font.setFamily(self.font)
        self.knobScripter.script_editor.setFont(config.script_editor_font)
        return

    def colorSchemeChanged(self):
        config.prefs["code_style_python"] = self.colorSchemeValue()
        self.knobScripter.highlighter.rehighlight()
        return

    def tabSpaceValue(self):
        if self.tabSpace2.isChecked():
            return 2
        elif self.tabSpace4.isChecked():
            return 2
        else:
            return 0

    def grabDimensions(self):
        self.windowHBox.setValue(self.knobScripter.height())
        self.windowWBox.setValue(self.knobScripter.width())

    def contextDefaultValue(self):
        return 1 if self.contextDefaultOn.isChecked() else 0

    def showLabelsValue(self):
        return 1 if self.showLabelsOn.isChecked() else 0

    def colorSchemeValue(self):
        return "nuke" if self.colorSchemeNuke.isChecked() else "sublime"

    def closeEvent(self, event):
        self.cancelPrefs()
        global PrefsPanel
        PrefsPanel = ""
        self.close()
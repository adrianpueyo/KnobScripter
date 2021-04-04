import json
import os
import nuke

from info import __version__, __author__, __date__
import config
import widgets
import utils

try:
    if nuke.NUKE_VERSION_MAJOR < 11:
        from PySide import QtCore, QtGui, QtGui as QtWidgets
        from PySide.QtCore import Qt
    else:
        from PySide2 import QtWidgets, QtGui, QtCore
        from PySide2.QtCore import Qt
except ImportError:
    from Qt import QtCore, QtGui, QtWidgets

def load_prefs():
    ''' Load prefs json file and overwrite config.prefs '''
    path = config.prefs_txt_path

    # Setup config font
    config.script_editor_font = QtGui.QFont()
    config.script_editor_font.setStyleHint(QtGui.QFont.Monospace)
    config.script_editor_font.setFixedPitch(True)
    config.script_editor_font.setFamily("Monospace")
    config.script_editor_font.setPointSize(10)

    if not os.path.isfile(path):
        return None
    else:
        with open(path, "r") as f:
            prefs = json.load(f)
            for pref in prefs:
                config.prefs[pref] = prefs[pref]
            config.script_editor_font.setFamily(config.prefs["se_font_family"])
            config.script_editor_font.setPointSize(config.prefs["se_font_size"])
            return prefs

class PrefsWidget(QtWidgets.QWidget):
    def __init__(self, knob_scripter="", _parent=QtWidgets.QApplication.activeWindow()):
        super(PrefsWidget, self).__init__(_parent)
        self.knob_scripter = knob_scripter
        self.initUI()
        self.refresh_prefs()

    def initUI(self):
        self.layout = QtWidgets.QVBoxLayout()

        # 1. Title (name, version)
        title_label = QtWidgets.QLabel("KnobScripter v" + __version__)
        title_label.setStyleSheet("font-weight:bold;color:#CCCCCC;font-size:20px;")
        subtitle_label = QtWidgets.QLabel("Script editor for python and callback knobs")
        subtitle_label.setStyleSheet("color:#999")
        line1 = widgets.HLine()

        signature = QtWidgets.QLabel(
            '<a href="http://www.adrianpueyo.com/" style="color:#888;text-decoration:none"><b>adrianpueyo.com</b></a>, 2016-2020')
        signature.setOpenExternalLinks(True)
        signature.setStyleSheet('''color:#555;font-size:9px;''')
        signature.setAlignment(QtCore.Qt.AlignLeft)
        self.layout.addWidget(title_label)
        self.layout.addWidget(signature)
        self.layout.addWidget(line1)

        # 2. Scroll Area
        # 2.1. Inner scroll content
        self.scroll_content = QtWidgets.QWidget()
        self.scroll_layout = QtWidgets.QVBoxLayout()
        self.scroll_layout.setMargin(0)

        self.scroll_content.setLayout(self.scroll_layout)
        self.scroll_content.setContentsMargins(0,0,8,0)

        # 2.2. External Scroll Area
        self.scroll = QtWidgets.QScrollArea()
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setWidgetResizable(True)
        self.scroll.setWidget(self.scroll_content)
        self.scroll.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.MinimumExpanding)

        self.layout.addWidget(self.scroll)

        # 3. Build prefs inside scroll layout
        self.form_layout = QtWidgets.QFormLayout()
        self.scroll_layout.addLayout(self.form_layout)
        self.scroll_layout.addStretch()

        # 3.1. General
        self.form_layout.addRow("<b>General</b>",QtWidgets.QWidget())
        # Font
        self.font_box = QtWidgets.QFontComboBox()
        self.font_box.currentFontChanged.connect(self.font_changed)
        self.form_layout.addRow("Font:", self.font_box)

        # Font size
        self.font_size_box = QtWidgets.QSpinBox()
        self.font_size_box.setMinimum(6)
        self.font_size_box.setMaximum(100)
        self.font_size_box.setFixedHeight(24)
        self.font_size_box.valueChanged.connect(self.font_size_changed)
        self.form_layout.addRow("Font size:", self.font_size_box)

        # Window size
        self.window_size_box = QtWidgets.QFrame()
        self.window_size_box.setContentsMargins(0,0,0,0)
        window_size_layout = QtWidgets.QHBoxLayout()
        window_size_layout.setMargin(0)
        self.window_size_w_box = QtWidgets.QSpinBox()
        self.window_size_w_box.setValue(config.prefs["ks_default_size"][0])
        self.window_size_w_box.setMinimum(200)
        self.window_size_w_box.setMaximum(4000)
        self.window_size_w_box.setFixedHeight(24)
        self.window_size_w_box.setToolTip("Default window width in pixels")
        window_size_layout.addWidget(self.window_size_w_box)
        window_size_layout.addWidget(QtWidgets.QLabel("x"))
        self.window_size_h_box = QtWidgets.QSpinBox()
        self.window_size_h_box.setValue(config.prefs["ks_default_size"][1])
        self.window_size_h_box.setMinimum(100)
        self.window_size_h_box.setMaximum(2000)
        self.window_size_h_box.setFixedHeight(24)
        self.window_size_h_box.setToolTip("Default window height in pixels")
        window_size_layout.addWidget(self.window_size_h_box)
        self.window_size_box.setLayout(window_size_layout)
        self.form_layout.addRow("Floating window:", self.window_size_box)

        self.grab_dimensions_button = QtWidgets.QPushButton("Grab current dimensions")
        self.grab_dimensions_button.clicked.connect(self.grab_dimensions)
        self.form_layout.addRow("", self.grab_dimensions_button)

        # 3.2. Python
        self.form_layout.addRow(" ", None)
        self.form_layout.addRow("<b>Python</b>",QtWidgets.QWidget())

        # Tab spaces
        self.tab_spaces_combobox = QtWidgets.QComboBox()
        self.tab_spaces_combobox.addItem("2",2)
        self.tab_spaces_combobox.addItem("4",4)
        self.tab_spaces_combobox.currentIndexChanged.connect(self.tab_spaces_changed)
        self.form_layout.addRow("Tab spaces:", self.tab_spaces_combobox)

        # Color scheme
        self.python_color_scheme_combobox = QtWidgets.QComboBox()
        self.python_color_scheme_combobox.addItem("nuke","nuke")
        self.python_color_scheme_combobox.addItem("monokai","monokai")
        self.python_color_scheme_combobox.currentIndexChanged.connect(self.color_scheme_changed)
        self.form_layout.addRow("Color scheme:", self.python_color_scheme_combobox)

        # Run in context
        self.run_in_context_checkbox = QtWidgets.QCheckBox("Run in context")
        self.run_in_context_checkbox.setToolTip("Default mode for running code in context (when in node mode).")
        #self.run_in_context_checkbox.stateChanged.connect(self.run_in_context_changed)
        self.form_layout.addRow("", self.run_in_context_checkbox)

        # Show labels
        self.show_knob_labels_checkbox = QtWidgets.QCheckBox("Show knob labels")
        self.show_knob_labels_checkbox.setToolTip("Display knob labels on the knob dropdown\n"
                                             "Otherwise, show the internal name only.")
        self.form_layout.addRow("", self.show_knob_labels_checkbox)

        """
        # 3.3. Blink
        self.form_layout.addRow(" ")
        self.form_layout.addRow("<b>Blink</b>")

        # Color scheme
        self.blink_color_scheme_combobox = QtWidgets.QComboBox()
        self.blink_color_scheme_combobox.addItem("nuke default")
        self.blink_color_scheme_combobox.addItem("adrians flavour")
        self.form_layout.addRow("Tab spaces:", self.blink_color_scheme_combobox)
        """

        # 4. Lower buttons?
        self.lower_buttons_layout = QtWidgets.QHBoxLayout()
        self.lower_buttons_layout.addStretch()

        self.save_prefs_button = QtWidgets.QPushButton("Save")
        self.save_prefs_button.clicked.connect(self.save_prefs)
        self.lower_buttons_layout.addWidget(self.save_prefs_button)
        self.apply_prefs_button = QtWidgets.QPushButton("Apply")
        self.apply_prefs_button.clicked.connect(self.apply_prefs)
        self.lower_buttons_layout.addWidget(self.apply_prefs_button)
        self.cancel_prefs_button = QtWidgets.QPushButton("Cancel")
        self.cancel_prefs_button.clicked.connect(self.cancel_prefs)
        self.lower_buttons_layout.addWidget(self.cancel_prefs_button)

        self.layout.addLayout(self.lower_buttons_layout)
        self.setLayout(self.layout)

    def font_size_changed(self):
        config.script_editor_font.setPointSize(self.font_size_box.value())
        for ks in nuke.AllKnobScripters:
            try:
                ks.script_editor.setFont(config.script_editor_font)
            except:
                pass

    def font_changed(self):
        self.font = self.font_box.currentFont().family()
        config.script_editor_font.setFamily(self.font)
        for ks in nuke.AllKnobScripters:
            try:
                ks.script_editor.setFont(config.script_editor_font)
            except:
                pass

    def tab_spaces_changed(self):
        config.prefs["se_tab_spaces"] = self.tab_spaces_combobox.currentData()
        for ks in nuke.AllKnobScripters:
            try:
                ks.highlighter.rehighlight()
            except:
                pass
        return

    def color_scheme_changed(self):
        config.prefs["code_style_python"] = self.python_color_scheme_combobox.currentData()
        for ks in nuke.AllKnobScripters:
            try:
                if ks.script_editor.code_language == "python":
                    ks.script_editor.highlighter.setStyle(config.prefs["code_style_python"])
                ks.script_editor.highlighter.rehighlight()
            except:
                pass
        return

    def grab_dimensions(self):
        self.knob_scripter = utils.getKnobScripter(self.knob_scripter)
        self.window_size_w_box.setValue(self.knob_scripter.width())
        self.window_size_h_box.setValue(self.knob_scripter.height())

    def refresh_prefs(self):
        """ Reload the json prefs, apply them on config.prefs, and repopulate the knobs """
        load_prefs()

        self.font_box.setCurrentFont(QtGui.QFont(config.prefs["se_font_family"]))
        self.font_size_box.setValue(config.prefs["se_font_size"])

        self.window_size_w_box.setValue(config.prefs["ks_default_size"][0])
        self.window_size_h_box.setValue(config.prefs["ks_default_size"][1])

        self.show_knob_labels_checkbox.setChecked(config.prefs["ks_show_knob_labels"] == True)
        self.run_in_context_checkbox.setChecked(config.prefs["ks_run_in_context"] == True)

        i = self.python_color_scheme_combobox.findData(config.prefs["code_style_python"])
        if i != -1:
            self.python_color_scheme_combobox.setCurrentIndex(i)

        i = self.tab_spaces_combobox.findData(config.prefs["se_tab_spaces"])
        if i != -1:
            self.tab_spaces_combobox.setCurrentIndex(i)

    def get_prefs_dict(self):
        """ Return a dictionary with the prefs from the current knob state """
        ks_prefs = {
            'ks_default_size': [self.window_size_w_box.value(), self.window_size_h_box.value()],
            'ks_run_in_context': self.run_in_context_checkbox.isChecked(),
            'ks_show_knob_labels': self.show_knob_labels_checkbox.isChecked(),
            'code_style_python': self.python_color_scheme_combobox.currentData(),
            'se_font_family': self.font_box.currentFont().family(),
            'se_font_size': self.font_size_box.value(),
            'se_tab_spaces': self.tab_spaces_combobox.currentData(),
        }
        return ks_prefs

    def save_config(self,prefs=None):
        """ Saves the given prefs dict in config.prefs """
        if not prefs:
            prefs = self.get_prefs_dict()
        for pref in prefs:
            config.prefs[pref] = prefs[pref]
        config.script_editor_font.setFamily(config.prefs["se_font_family"])
        config.script_editor_font.setPointSize(config.prefs["se_font_size"])


    def save_prefs(self):
        """ Save current prefs on json, config, and apply on KnobScripters """
        # 1. Save json
        ks_prefs = self.get_prefs_dict()
        with open(config.prefs_txt_path, "w") as f:
            prefs = json.dump(ks_prefs, f, sort_keys=True, indent=4)
            nuke.message("Preferences saved!")

        # 2. Save config
        self.save_config(ks_prefs)

        # 3. Apply on KnobScripters
        self.apply_prefs()


    def apply_prefs(self):
        """ Apply the current knob values to the KnobScripters """
        self.save_config()
        for ks in nuke.AllKnobScripters:
                ks.script_editor.setFont(config.script_editor_font)
                ks.script_editor.tab_spaces = config.prefs["se_tab_spaces"]
                ks.script_editor.highlighter.rehighlight()
                ks.runInContext = config.prefs["ks_run_in_context"]
                ks.runInContextAct.setChecked(config.prefs["ks_run_in_context"])
                ks.show_labels = config.prefs["ks_show_knob_labels"]
                if ks.nodeMode:
                    ks.refreshClicked()


    def cancel_prefs(self):
        """ Revert to saved json prefs """
        # 1. Reload json and populate knobs
        self.refresh_prefs()
        # 2. Apply values to KnobScripters
        self.apply_prefs()

class PrefsWidgetOld(QtWidgets.QDialog):
    def __init__(self, knobScripter="", _parent=QtWidgets.QApplication.activeWindow()):
        super(PrefsWidgetOld, self).__init__(_parent)

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
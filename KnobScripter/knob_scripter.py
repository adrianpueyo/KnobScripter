# -*- coding: utf-8 -*-
"""KnobScripter 3 by Adrian Pueyo - Complete python script editor for Nuke.

This is the main KnobScripter module, which defines the classes necessary
to create the floating and docked KnobScripters. Also handles the main
initialization and menu creation in Nuke.

adrianpueyo.com

"""

import os
import json
from nukescripts import panels
import nuke
import re
import subprocess
import platform
from webbrowser import open as open_url
import logging

# Symlinks on windows.
if os.name == "nt" and nuke.NUKE_VERSION_MAJOR < 13:
    def symlink_ms(source, link_name):
        import ctypes
        csl = ctypes.windll.kernel32.CreateSymbolicLinkW
        csl.argtypes = (ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint32)
        csl.restype = ctypes.c_ubyte
        flags = 1 if os.path.isdir(source) else 0
        try:
            if csl(link_name, source.replace('/', '\\'), flags) == 0:
                raise ctypes.WinError()
        except AttributeError:
            pass


    os.symlink = symlink_ms

try:
    if nuke.NUKE_VERSION_MAJOR < 11:
        from PySide import QtCore, QtGui, QtGui as QtWidgets
        from PySide.QtCore import Qt
    else:
        from PySide2 import QtWidgets, QtGui, QtCore
        from PySide2.QtCore import Qt
except ImportError:
    from Qt import QtCore, QtGui, QtWidgets

KS_DIR = os.path.dirname(__file__)
icons_path = KS_DIR + "/icons/"
nuke.ks_multipanel = ""
PrefsPanel = ""
SnippetEditPanel = ""
CodeGalleryPanel = ""

# ks imports
from KnobScripter.info import __version__, __date__
from KnobScripter import config, prefs, utils, dialogs, widgets, ksscripteditormain
from KnobScripter import snippets, codegallery, script_output, findreplace, content

# logging.basicConfig(level=logging.DEBUG)

nuke.tprint('KnobScripter v{}, built {}.\n'
            'Copyright (c) 2016-2022 Adrian Pueyo. All Rights Reserved.'.format(__version__, __date__))
# logging.debug('Initializing KnobScripter')

# Init config.script_editor_font (will be overwritten once reading the prefs)
prefs.load_prefs()


def is_blink_knob(knob):
    """
    Args:
        knob (nuke.Knob): Any Nuke Knob.

    Returns:
        bool: True if knob is Blink type, False otherwise

    """
    node = knob.node()
    kn = knob.name()
    if kn in ["kernelSource"] and node.Class() in ["BlinkScript"]:
        return True
    else:
        return False


def string(text):
    """Quick workaround for python 2 vs 3 unicode str headache.

    Args:
        text (str): any string or bytes object

    Returns:
        str: text utf8 encoded

    """

    if type(text) != str:
        text = text.encode("utf8")
    return text


class KnobScripterWidget(QtWidgets.QDialog):
    """ Main KnobScripter Widget, which is defined as a floating QDialog by default.

    Attributes:
        node (nuke.Node, optional): Node on which this KnobScripter widget will run.
        knob (nuke.Knob, optional): Knob on which this KnobScripter widget will run.
        is_pane (bool, optional): Utility variable for KnobScripterPane.
        _parent (QWidget, optional): Parent widget.
    """

    def __init__(self, node="", knob="", is_pane=False, _parent=QtWidgets.QApplication.activeWindow()):

        super(KnobScripterWidget, self).__init__(_parent)

        # Autosave the other knobscripters and add this one
        for ks in config.all_knobscripters:
            if hasattr(ks, 'autosave'):
                ks.autosave()

        if self not in config.all_knobscripters:
            config.all_knobscripters.append(self)

        self.nodeMode = (node != "")
        if node == "":
            self.node = nuke.toNode("root")
        else:
            self.node = node

        if knob == "":

            if "kernelSource" in self.node.knobs() and self.node.Class() == "BlinkScript":
                knob = "kernelSource"
            else:
                knob = "knobChanged"
        self.knob = knob

        self._parent = _parent
        self.isPane = is_pane
        self.show_labels = False  # For the option to also display the knob labels on the knob dropdown
        self.unsaved_knobs = {}
        self.modifiedKnobs = set()
        self.py_scroll_positions = {}
        self.py_cursor_positions = {}
        self.py_state_dict = {}
        #self.knob_scroll_positions = {}
        #self.knob_cursor_positions = {}
        self.current_node_state_dict = {}
        self.to_load_knob = True
        self.frw_open = False  # Find replace widget closed by default
        self.omit_se_console_text = ""
        self.nukeSE = utils.findSE()
        self.nukeSEOutput = utils.findSEConsole(self.nukeSE)
        self.nukeSEInput = utils.findSEInput(self.nukeSE)
        self.nukeSERunBtn = utils.findSERunBtn(self.nukeSE)

        self.current_folder = "scripts"
        self.folder_index = 0
        self.current_script = "Untitled.py"
        self.current_script_modified = False
        self.script_index = 0
        self.toAutosave = False
        self.runInContext = config.prefs["ks_run_in_context"]  # Experimental, python only
        self.code_language = None
        self.current_knob_modified = False  # Convenience variable holding if the current script_editor is modified

        self.defaultKnobs = ["knobChanged", "onCreate", "onScriptLoad", "onScriptSave", "onScriptClose", "onDestroy",
                             "updateUI", "autolabel", "beforeRender", "beforeFrameRender", "afterFrameRender",
                             "afterRender"]
        self.python_knob_classes = ["PyScript_Knob", "PythonCustomKnob"]

        # Load prefs
        # self.loadedPrefs = self.loadPrefs()

        # Load snippets
        content.all_snippets = snippets.load_snippets_dict()

        # Init UI
        self.initUI()
        utils.setSEConsoleChanged()
        self.omit_se_console_text = self.nukeSEOutput.document().toPlainText()
        self.clearConsole()
        #print(self.py_state_dict) # We need to update it!!!!

    def initUI(self):
        """ Initializes the tool UI"""
        # -------------------
        # 1. MAIN WINDOW
        # -------------------
        self.resize(config.prefs["ks_default_size"][0], config.prefs["ks_default_size"][1])
        self.setWindowTitle("KnobScripter - %s %s" % (self.node.fullName(), self.knob))
        self.setObjectName("com.adrianpueyo.knobscripter")
        self.move(QtGui.QCursor().pos() - QtCore.QPoint(32, 74))

        # ---------------------
        # 2. TOP BAR
        # ---------------------
        # ---
        # 2.1. Left buttons
        self.change_btn = widgets.APToolButton("pick")
        self.change_btn.setToolTip("Change to node if selected. Otherwise, change to Script Mode.")
        self.change_btn.clicked.connect(self.changeClicked)

        # ---
        # 2.2.A. Node mode UI
        self.exit_node_btn = widgets.APToolButton("exitnode")
        self.exit_node_btn.setToolTip("Exit the node, and change to Script Mode.")
        self.exit_node_btn.clicked.connect(self.exitNodeMode)
        self.current_node_label_node = QtWidgets.QLabel(" Node:")
        self.current_node_label_name = QtWidgets.QLabel(self.node.fullName())
        self.current_node_label_name.setStyleSheet("font-weight:bold;")
        self.current_knob_label = QtWidgets.QLabel("Knob: ")
        self.current_knob_dropdown = QtWidgets.QComboBox()
        self.current_knob_dropdown.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)
        self.updateKnobDropdown()
        self.current_knob_dropdown.currentIndexChanged.connect(lambda: self.loadKnobValue(False, update_dict=True))

        # Layout
        self.node_mode_bar_layout = QtWidgets.QHBoxLayout()
        self.node_mode_bar_layout.addWidget(self.exit_node_btn)
        self.node_mode_bar_layout.addSpacing(2)
        self.node_mode_bar_layout.addWidget(self.current_node_label_node)
        self.node_mode_bar_layout.addWidget(self.current_node_label_name)
        self.node_mode_bar_layout.addSpacing(2)
        self.node_mode_bar_layout.addWidget(self.current_knob_dropdown)
        self.node_mode_bar = QtWidgets.QWidget()
        self.node_mode_bar.setLayout(self.node_mode_bar_layout)

        self.node_mode_bar_layout.setContentsMargins(0, 0, 0, 0)

        # ---
        # 2.2.B. Script mode UI
        self.script_label = QtWidgets.QLabel("Script: ")

        self.current_folder_dropdown = QtWidgets.QComboBox()
        self.current_folder_dropdown.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)
        self.current_folder_dropdown.currentIndexChanged.connect(self.folderDropdownChanged)

        self.current_script_dropdown = QtWidgets.QComboBox()
        self.current_script_dropdown.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)
        self.updateFoldersDropdown()
        self.updateScriptsDropdown()
        self.current_script_dropdown.currentIndexChanged.connect(self.scriptDropdownChanged)

        # Layout
        self.script_mode_bar_layout = QtWidgets.QHBoxLayout()
        self.script_mode_bar_layout.addWidget(self.script_label)
        self.script_mode_bar_layout.addSpacing(2)
        self.script_mode_bar_layout.addWidget(self.current_folder_dropdown)
        self.script_mode_bar_layout.addWidget(self.current_script_dropdown)
        self.script_mode_bar = QtWidgets.QWidget()
        self.script_mode_bar.setLayout(self.script_mode_bar_layout)

        self.script_mode_bar_layout.setContentsMargins(0, 0, 0, 0)

        # ---
        # 2.3. File-system buttons
        # Refresh dropdowns
        self.refresh_btn = widgets.APToolButton("refresh")
        self.refresh_btn.setToolTip("Refresh the dropdowns.\nShortcut: F5")
        self.refresh_btn.setShortcut('F5')
        self.refresh_btn.clicked.connect(self.refreshClicked)

        # Reload script
        self.reload_btn = widgets.APToolButton("download")
        self.reload_btn.setToolTip(
            "Reload the current script. Will overwrite any changes made to it.\nShortcut: Ctrl+R")
        self.reload_btn.setShortcut('Ctrl+R')
        self.reload_btn.clicked.connect(self.reloadClicked)

        # Save script
        self.save_btn = widgets.APToolButton("save")

        if not self.isPane:
            self.save_btn.setShortcut('Ctrl+S')
            self.save_btn.setToolTip("Save the script into the selected knob or python file.\nShortcut: Ctrl+S")
        else:
            self.save_btn.setToolTip("Save the script into the selected knob or python file.")
        self.save_btn.clicked.connect(self.saveClicked)

        # Layout
        self.top_file_bar_layout = QtWidgets.QHBoxLayout()
        self.top_file_bar_layout.addWidget(self.refresh_btn)
        self.top_file_bar_layout.addWidget(self.reload_btn)
        self.top_file_bar_layout.addWidget(self.save_btn)

        # ---
        # 2.4. Right Side buttons

        # Python: Run script
        self.run_script_button = widgets.APToolButton("run")
        self.run_script_button.setToolTip(
            "Execute the current selection on the KnobScripter, or the whole script if no selection.\n"
            "Shortcut: Ctrl+Enter")
        self.run_script_button.clicked.connect(self.runScript)

        # Python: Clear console
        self.clear_console_button = widgets.APToolButton("clear_console")
        self.clear_console_button.setToolTip(
            "Clear the text in the console window.\nShortcut: Ctrl+Backspace, or click+Backspace on the console.")
        self.clear_console_button.setShortcut('Ctrl+Backspace')
        self.clear_console_button.clicked.connect(self.clearConsole)

        # Blink: Save & Compile
        self.save_recompile_button = widgets.APToolButton("play")
        self.save_recompile_button.setToolTip(
            "Save the blink code and recompile the Blinkscript node.\nShortcut: Ctrl+Enter")
        self.save_recompile_button.clicked.connect(self.blinkSaveRecompile)

        # Blink: Backups
        self.createBlinkBackupsMenu()
        self.backup_button = QtWidgets.QPushButton()
        self.backup_button.setIcon(QtGui.QIcon(os.path.join(config.ICONS_DIR, "icon_backups.png")))
        self.backup_button.setIconSize(QtCore.QSize(config.prefs["qt_icon_size"], config.prefs["qt_icon_size"]))
        self.backup_button.setFixedSize(QtCore.QSize(config.prefs["qt_btn_size"], config.prefs["qt_btn_size"]))
        self.backup_button.setToolTip("Blink: Enable and retrieve auto-saves of the code.")
        self.backup_button.setMenu(self.blink_menu)
        # self.backup_button.setFixedSize(QtCore.QSize(self.btn_size+10,self.btn_size))
        self.backup_button.setStyleSheet("text-align:left;padding-left:2px;")
        # self.backup_button.clicked.connect(self.blinkBackup) #TODO: whatever this does

        # FindReplace button
        self.find_button = widgets.APToolButton("search")
        self.find_button.setToolTip("Call the snippets by writing the shortcut and pressing Tab.\nShortcut: Ctrl+F")
        self.find_button.setShortcut('Ctrl+F')
        self.find_button.setCheckable(True)
        self.find_button.setFocusPolicy(QtCore.Qt.NoFocus)
        self.find_button.clicked[bool].connect(self.toggleFRW)
        if self.frw_open:
            self.find_button.toggle()

        # Gallery
        self.codegallery_button = widgets.APToolButton("enter")
        self.codegallery_button.setToolTip("Open the code gallery panel.")
        self.codegallery_button.clicked.connect(lambda: self.open_multipanel(tab="code_gallery"))

        # Snippets
        self.snippets_button = widgets.APToolButton("snippets")
        self.snippets_button.setToolTip("Call the snippets by writing the shortcut and pressing Tab.")
        self.snippets_button.clicked.connect(lambda: self.open_multipanel(tab="snippet_editor"))

        # Prefs
        self.createPrefsMenu()
        self.prefs_button = QtWidgets.QPushButton()
        self.prefs_button.setIcon(QtGui.QIcon(os.path.join(config.ICONS_DIR, "icon_prefs.png")))
        self.prefs_button.setIconSize(QtCore.QSize(config.prefs["qt_icon_size"], config.prefs["qt_icon_size"]))
        self.prefs_button.setFixedSize(QtCore.QSize(config.prefs["qt_btn_size"] + 10, config.prefs["qt_btn_size"]))
        self.prefs_button.setMenu(self.prefsMenu)
        self.prefs_button.setStyleSheet("text-align:left;padding-left:2px;")

        # Layout
        self.top_right_bar_layout = QtWidgets.QHBoxLayout()
        self.top_right_bar_layout.addWidget(self.run_script_button)
        self.top_right_bar_layout.addWidget(self.save_recompile_button)
        self.top_right_bar_layout.addWidget(self.clear_console_button)
        self.top_right_bar_layout.addWidget(self.backup_button)
        self.top_right_bar_layout.addWidget(self.codegallery_button)
        self.top_right_bar_layout.addWidget(self.find_button)
        # self.top_right_bar_layout.addWidget(self.snippets_button)
        # self.top_right_bar_layout.addSpacing(10)
        self.top_right_bar_layout.addWidget(self.prefs_button)

        # ---
        # Layout
        self.top_layout = QtWidgets.QHBoxLayout()
        self.top_layout.setContentsMargins(0, 0, 0, 0)
        # self.top_layout.setSpacing(10)
        self.top_layout.addWidget(self.change_btn)
        self.top_layout.addWidget(self.node_mode_bar)
        self.top_layout.addWidget(self.script_mode_bar)
        self.node_mode_bar.setVisible(False)
        # self.top_layout.addSpacing(10)
        self.top_layout.addLayout(self.top_file_bar_layout)
        self.top_layout.addStretch()
        self.top_layout.addLayout(self.top_right_bar_layout)

        # ----------------------
        # 3. SCRIPTING SECTION
        # ----------------------
        # Splitter
        self.splitter = QtWidgets.QSplitter(Qt.Vertical)

        # Output widget
        self.script_output = script_output.ScriptOutputWidget(parent=self)
        self.script_output.setReadOnly(1)
        self.script_output.setAcceptRichText(0)
        if config.prefs["se_tab_spaces"] != 0:
            self.script_output.setTabStopWidth(self.script_output.tabStopWidth() / 4)
        self.script_output.setFocusPolicy(Qt.ClickFocus)
        self.script_output.setAutoFillBackground(0)
        self.script_output.installEventFilter(self)

        # Script Editor
        self.script_editor = ksscripteditormain.KSScriptEditorMain(self, self.script_output)
        self.script_editor.setMinimumHeight(30)
        self.script_editor.textChanged.connect(self.setModified)
        self.script_editor.set_code_language("python")
        self.script_editor.cursorPositionChanged.connect(self.setTextSelection)

        if config.prefs["se_tab_spaces"] != 0:
            self.script_editor.setTabStopWidth(
                config.prefs["se_tab_spaces"] * QtGui.QFontMetrics(config.script_editor_font).width(' '))

        # Add input and output to splitter
        self.splitter.addWidget(self.script_output)
        self.splitter.addWidget(self.script_editor)
        self.splitter.setStretchFactor(0, 0)

        # FindReplace widget
        self.frw = findreplace.FindReplaceWidget(self.script_editor, self)
        self.frw.setVisible(self.frw_open)

        # ---
        # Layout
        self.scripting_layout = QtWidgets.QVBoxLayout()
        self.scripting_layout.setContentsMargins(0, 0, 0, 0)
        self.scripting_layout.setSpacing(0)
        self.scripting_layout.addWidget(self.splitter)
        self.scripting_layout.addWidget(self.frw)

        # ---------------
        # MASTER LAYOUT
        # ---------------
        self.master_layout = QtWidgets.QVBoxLayout()
        self.master_layout.setSpacing(5)
        self.master_layout.setContentsMargins(8, 8, 8, 8)
        self.master_layout.addLayout(self.top_layout)
        self.master_layout.addLayout(self.scripting_layout)
        self.setLayout(self.master_layout)

        # ----------------
        # MAIN WINDOW UI
        # ----------------
        size_policy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        self.setSizePolicy(size_policy)
        self.setMinimumWidth(160)

        # Set default values based on mode
        if self.nodeMode:
            self.current_knob_dropdown.blockSignals(True)
            self.node_mode_bar.setVisible(True)
            self.script_mode_bar.setVisible(False)

            # Load stored state of knobs
            self.loadKnobState()
            state_dict = self.current_node_state_dict
            if "open_knob" in state_dict and state_dict["open_knob"] in self.node.knobs():
                self.knob = state_dict["open_knob"]
            elif "kernelSource" in self.node.knobs() and self.node.Class() == "BlinkScript":
                self.knob = "kernelSource"
            else:
                self.knob = "knobChanged"

            self.setCurrentKnob(self.knob)
            self.loadKnobValue(check=False)
            self.setKnobModified(False)
            self.current_knob_dropdown.blockSignals(False)
            self.splitter.setSizes([0, 1])
        else:
            self.exitNodeMode()

        self.script_editor.setFocus()


    # Preferences submenus
    def createPrefsMenu(self):
        # Actions
        self.echoAct = QtWidgets.QAction("Echo python commands", self, checkable=True,
                                         statusTip="Toggle nuke's 'Echo all python commands to ScriptEditor'",
                                         triggered=self.toggleEcho)
        if nuke.toNode("preferences").knob("echoAllCommands").value():
            self.echoAct.toggle()
        self.runInContextAct = QtWidgets.QAction("Run in context (beta)", self, checkable=True,
                                                 statusTip="When inside a node, run the code replacing "
                                                           "nuke.thisNode() to the node's name, etc.",
                                                 triggered=self.toggleRunInContext)
        self.runInContextAct.setChecked(self.runInContext)
        self.helpAct = QtWidgets.QAction("&Help", self, statusTip="Open the KnobScripter help in your browser.",
                                         shortcut="F1", triggered=self.showHelp)
        self.nukepediaAct = QtWidgets.QAction("Show in Nukepedia", self,
                                              statusTip="Open the KnobScripter download page on Nukepedia.",
                                              triggered=self.showInNukepedia)
        self.githubAct = QtWidgets.QAction("Show in GitHub", self, statusTip="Open the KnobScripter repo on GitHub.",
                                           triggered=self.showInGithub)
        self.snippetsAct = QtWidgets.QAction("Snippets", self, statusTip="Open the Snippets editor.",
                                             triggered=lambda: self.open_multipanel(tab="snippet_editor"))
        self.snippetsAct.setIcon(QtGui.QIcon(icons_path + "icon_snippets.png"))
        self.prefsAct = QtWidgets.QAction("Preferences", self, statusTip="Open the Preferences panel.",
                                          triggered=lambda: self.open_multipanel(tab="ks_prefs"))
        self.prefsAct.setIcon(QtGui.QIcon(icons_path + "icon_prefs.png"))

        # Menus
        self.prefsMenu = QtWidgets.QMenu("Preferences")
        self.prefsMenu.addAction(self.echoAct)
        self.prefsMenu.addAction(self.runInContextAct)
        self.prefsMenu.addSeparator()
        self.prefsMenu.addAction(self.nukepediaAct)
        self.prefsMenu.addAction(self.githubAct)
        self.prefsMenu.addSeparator()
        self.prefsMenu.addAction(self.helpAct)
        self.prefsMenu.addSeparator()
        self.prefsMenu.addAction(self.snippetsAct)
        self.prefsMenu.addAction(self.prefsAct)

    def initEcho(self):
        """ Initializes the echo chechable QAction based on nuke's state """
        echo_knob = nuke.toNode("preferences").knob("echoAllCommands")
        self.echoAct.setChecked(echo_knob.value())

    def toggleEcho(self):
        """ Toggle the "Echo python commands" from Nuke """
        echo_knob = nuke.toNode("preferences").knob("echoAllCommands")
        echo_knob.setValue(self.echoAct.isChecked())

    def toggleRunInContext(self):
        """ Toggles preference to replace everything needed so that code can be run in proper context
        of its node and knob."""
        self.setRunInContext(not self.runInContext)

    @staticmethod
    def showInNukepedia():
        open_url("http://www.nukepedia.com/python/ui/knobscripter")

    @staticmethod
    def showInGithub():
        open_url("https://github.com/adrianpueyo/KnobScripter")

    @staticmethod
    def showHelp():
        open_url("https://vimeo.com/adrianpueyo/knobscripter2")

    # Blink Backups menu
    def createBlinkBackupsMenu(self):

        # Actions
        # TODO On opening the blink menu, show the .blink file name (../name.blink) in grey and update the checkboxes
        self.blink_autoSave_act = QtWidgets.QAction("Auto-save to disk on compile", self, checkable=True,
                                                    statusTip="Auto-save code backup on disk every time you save it",
                                                    triggered=self.blink_toggle_autosave_action)
        self.blink_autoSave_act.setChecked(config.prefs["ks_blink_autosave_on_compile"])
        # self.blinkBackups_createFile_act = QtWidgets.QAction("Create .blink scratch file",
        self.blink_load_act = QtWidgets.QAction("Load .blink", self, statusTip="Load the .blink code.",
                                                triggered=self.blink_load_triggered)
        self.blink_save_act = QtWidgets.QAction("Save .blink", self, statusTip="Save the .blink code.",
                                                triggered=self.blink_save_triggered)
        self.blink_versionup_act = QtWidgets.QAction("Version Up", self, statusTip="Version up the .blink file.",
                                                     triggered=self.blink_versionup_triggered)
        self.blink_browse_act = QtWidgets.QAction("Browse...", self, statusTip="Browse to the blink file's directory.",
                                                  triggered=self.blink_browse_action)

        self.blink_filename_info_act = QtWidgets.QAction("No file specified.", self,
                                                         statusTip="Displays the filename specified "
                                                                   "in the kernelSourceFile knob.")
        self.blink_filename_info_act.setEnabled(False)

        # Menus
        self.blink_menu = QtWidgets.QMenu("Blink")
        self.blink_menu.addAction(self.blink_autoSave_act)
        self.blink_menu.addSeparator()
        self.blink_menu.addAction(self.blink_filename_info_act)
        self.blink_menu.addAction(self.blink_load_act)
        self.blink_menu.addAction(self.blink_save_act)
        self.blink_menu.addAction(self.blink_versionup_act)
        self.blink_menu.addAction(self.blink_browse_act)

        self.blink_menu.aboutToShow.connect(self.blink_menu_refresh)
        # TODO: Checkbox autosave should be enabled or disabled by default based on preferences...

    # Node Mode
    def updateKnobDropdown(self):
        """ Populate knob dropdown list """
        self.current_knob_dropdown.clear()  # First remove all items
        counter = 0

        for i in self.node.knobs():
            k = self.node.knob(i)
            if i not in self.defaultKnobs and self.node.knob(i).Class() in self.python_knob_classes:
                if is_blink_knob(k):
                    i_full = "Blinkscript Code (kernelSource)"
                elif self.show_labels:
                    i_full = "{} ({})".format(self.node.knob(i).label(), i)
                else:
                    i_full = i

                if i in self.unsaved_knobs.keys():
                    self.current_knob_dropdown.addItem(i_full + "(*)", i)
                else:
                    self.current_knob_dropdown.addItem(i_full, i)

                counter += 1
        if counter > 0:
            self.current_knob_dropdown.insertSeparator(counter)
            counter += 1
            self.current_knob_dropdown.insertSeparator(counter)
            counter += 1
        for i in self.node.knobs():
            if i in self.defaultKnobs:
                if i in self.unsaved_knobs.keys():
                    self.current_knob_dropdown.addItem(i + "(*)", i)
                else:
                    self.current_knob_dropdown.addItem(i, i)
                counter += 1
        return

    def loadKnobValue(self, check=True, update_dict=False):
        """ Get the content of the knob value and populate the editor """
        if not self.to_load_knob:
            return
        dropdown_value = self.current_knob_dropdown.itemData(
            self.current_knob_dropdown.currentIndex())  # knobChanged...
        knob_language = self.knobLanguage(self.node, dropdown_value)
        try:
            # If blinkscript, use getValue.
            if knob_language == "blink":
                obtained_knob_value = str(self.node[dropdown_value].getValue())
            elif knob_language == "python":
                obtained_knob_value = str(self.node[dropdown_value].value())
                logging.debug(obtained_knob_value)
            else:  # TODO: knob language is None -> try to get the expression for tcl???
                return
            obtained_scroll_value = 0
            edited_knob_value = string(self.script_editor.toPlainText())
        except:
            try:
                error_message = QtWidgets.QMessageBox.information(None, "", "Unable to find %s.%s" % (
                    self.node.name(), dropdown_value))
            except:
                error_message = QtWidgets.QMessageBox.information(None, "",
                                                                  "Unable to find the node's {}".format(dropdown_value))
            error_message.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
            error_message.exec_()
            return

        # If there were changes to the previous knob, update the dictionary
        if update_dict is True:
            self.unsaved_knobs[self.knob] = edited_knob_value
            #self.py_scroll_positions[self.knob] = self.script_editor.verticalScrollBar().value()
            # Remember scroll and cursor values
            self.saveKnobState()

        prev_knob = self.knob  # knobChanged...

        self.knob = self.current_knob_dropdown.itemData(self.current_knob_dropdown.currentIndex())  # knobChanged...

        if check and obtained_knob_value != edited_knob_value:
            msg_box = QtWidgets.QMessageBox()
            msg_box.setText("The Script Editor has been modified.")
            msg_box.setInformativeText("Do you want to overwrite the current code on this editor?")
            msg_box.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
            msg_box.setIcon(QtWidgets.QMessageBox.Question)
            msg_box.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
            msg_box.setDefaultButton(QtWidgets.QMessageBox.Yes)
            reply = msg_box.exec_()
            if reply == QtWidgets.QMessageBox.No:
                self.setCurrentKnob(prev_knob)
                return
        # If order comes from a dropdown update, update value from dictionary if possible, otherwise update normally
        self.setWindowTitle("KnobScripter - %s %s" % (self.node.name(), self.knob))
        self.script_editor.blockSignals(True)
        if update_dict:
            if self.knob in self.unsaved_knobs:
                if self.unsaved_knobs[self.knob] == obtained_knob_value:
                    self.script_editor.setPlainText(obtained_knob_value)
                    self.setKnobModified(False)
                else:
                    obtained_knob_value = self.unsaved_knobs[self.knob]
                    self.script_editor.setPlainText(obtained_knob_value)
                    self.setKnobModified(True)
            else:
                self.script_editor.setPlainText(obtained_knob_value)
                self.setKnobModified(False)

        else:
            self.script_editor.setPlainText(obtained_knob_value)

        self.setCodeLanguage(knob_language)
        self.script_editor.blockSignals(False)
        self.loadKnobState() # Loads cursor and scroll values
        self.setKnobState() # Sets cursor and scroll values
        self.script_editor.setFocus()
        self.script_editor.verticalScrollBar().setValue(1)
        return

    def loadAllKnobValues(self):
        """ Load all knobs button's function """
        if len(self.unsaved_knobs) >= 1:
            msg_box = QtWidgets.QMessageBox()
            msg_box.setText("Do you want to reload all python and callback knobs?")
            msg_box.setInformativeText("Unsaved changes on this editor will be lost.")
            msg_box.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
            msg_box.setIcon(QtWidgets.QMessageBox.Question)
            msg_box.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
            msg_box.setDefaultButton(QtWidgets.QMessageBox.Yes)
            reply = msg_box.exec_()
            if reply == QtWidgets.QMessageBox.No:
                return
        self.unsaved_knobs = {}
        return

    def saveKnobValue(self, check=True):
        """ Save the text from the editor to the node's knobChanged knob """
        dropdown_value = self.current_knob_dropdown.itemData(self.current_knob_dropdown.currentIndex())
        try:
            obtained_knob_value = self.getKnobValue(dropdown_value)
            # If blinkscript, use getValue.
            # if dropdown_value == "kernelSource" and self.node.Class()=="BlinkScript":
            #    obtained_knob_value = str(self.node[dropdown_value].getValue())
            # else:
            #    obtained_knob_value = str(self.node[dropdown_value].value())
            self.knob = dropdown_value
        except:
            error_message = QtWidgets.QMessageBox.information(None, "", "Unable to find %s.%s" % (
                self.node.name(), dropdown_value))
            error_message.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
            error_message.exec_()
            return
        edited_knob_value = string(self.script_editor.toPlainText())
        if check and obtained_knob_value != edited_knob_value:
            msg_box = QtWidgets.QMessageBox()
            msg_box.setText("Do you want to overwrite %s.%s?" % (self.node.name(), dropdown_value))
            msg_box.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
            msg_box.setIcon(QtWidgets.QMessageBox.Question)
            msg_box.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
            msg_box.setDefaultButton(QtWidgets.QMessageBox.Yes)
            reply = msg_box.exec_()
            if reply == QtWidgets.QMessageBox.No:
                return
        # Save the value if it's Blinkscript code
        if dropdown_value == "kernelSource" and self.node.Class() == "BlinkScript":
            nuke.tcl('''knob {}.kernelSource "{}"'''.format(self.node.fullName(),
                                                            edited_knob_value.replace('"', '\\"').replace('[', '\[')))
        else:
            self.node[dropdown_value].setValue(string(edited_knob_value))
        self.setKnobModified(modified=False, knob=dropdown_value, change_title=True)
        nuke.tcl("modified 1")
        if self.knob in self.unsaved_knobs:
            del self.unsaved_knobs[self.knob]
        return

    def saveAllKnobValues(self, check=True):
        """ Save all knobs button's function """
        if self.updateUnsavedKnobs() > 0 and check:
            msg_box = QtWidgets.QMessageBox()
            msg_box.setText("Do you want to save all modified python and callback knobs?")
            msg_box.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
            msg_box.setIcon(QtWidgets.QMessageBox.Question)
            msg_box.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
            msg_box.setDefaultButton(QtWidgets.QMessageBox.Yes)
            reply = msg_box.exec_()
            if reply == QtWidgets.QMessageBox.No:
                return
        save_errors = 0
        saved_count = 0
        for k in self.unsaved_knobs.copy():
            try:
                self.node.knob(k).setValue(self.unsaved_knobs[k])
                del self.unsaved_knobs[k]
                saved_count += 1
                nuke.tcl("modified 1")
            except:
                save_errors += 1
        if save_errors > 0:
            error_box = QtWidgets.QMessageBox()
            error_box.setText("Error saving %s knob%s." % (str(save_errors), int(save_errors > 1) * "s"))
            error_box.setIcon(QtWidgets.QMessageBox.Warning)
            error_box.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
            error_box.setDefaultButton(QtWidgets.QMessageBox.Yes)
            error_box.exec_()
        else:
            logging.debug("KnobScripter: %s knobs saved" % str(saved_count))
        return

    def setCurrentKnob(self, knob_to_set):
        """ Set current knob """
        knob_dropdown_items = []
        for i in range(self.current_knob_dropdown.count()):
            if self.current_knob_dropdown.itemData(i) is not None:
                knob_dropdown_items.append(self.current_knob_dropdown.itemData(i))
            else:
                knob_dropdown_items.append("---")
        if knob_to_set in knob_dropdown_items:
            index = knob_dropdown_items.index(knob_to_set)
            self.current_knob_dropdown.setCurrentIndex(index)
            return True
        return False

    def updateUnsavedKnobs(self):
        """ Clear unchanged knobs from the dict and return the number of unsaved knobs """
        if not self.node:
            # Node has been deleted, so simply return 0. Who cares.
            return 0

        edited_knob_value = string(self.script_editor.toPlainText())
        self.unsaved_knobs[self.knob] = edited_knob_value

        if len(self.unsaved_knobs) > 0:
            for k in self.unsaved_knobs.copy():
                if self.node.knob(k):
                    if str(self.getKnobValue(k)) == str(self.unsaved_knobs[k]):
                        del self.unsaved_knobs[k]
                else:
                    del self.unsaved_knobs[k]
        # Set appropriate knobs modified...
        knobs_dropdown = self.current_knob_dropdown
        all_knobs = [knobs_dropdown.itemData(i) for i in range(knobs_dropdown.count())]
        all_knobs = list(filter(None, all_knobs))
        for key in all_knobs:
            if key in self.unsaved_knobs.keys():
                self.setKnobModified(modified=True, knob=key, change_title=False)
            else:
                self.setKnobModified(modified=False, knob=key, change_title=False)

        return len(self.unsaved_knobs)

    def getKnobValue(self, knob=""):
        """
        Returns the relevant value of the knob:
            For python knobs, uses value
            For blinkscript, getValue
            For others, gets the expression
        """
        if knob == "":
            knob = self.knob
        if knob == "kernelSource" and self.node.Class() == "BlinkScript":
            return self.node[knob].getValue()
        else:
            return self.node[knob].value()
            # TODO: Return expression otherwise

    def setKnobModified(self, modified=True, knob="", change_title=True):
        """ Sets the current knob modified, title and whatever else we need """
        if knob == "":
            knob = self.knob
        if modified:
            self.modifiedKnobs.add(knob)
        else:
            self.modifiedKnobs.discard(knob)

        if change_title:
            title_modified_string = " [modified]"
            window_title = self.windowTitle().split(title_modified_string)[0]
            if modified:
                window_title += title_modified_string
            self.current_knob_modified = modified
            self.setWindowTitle(window_title)

        try:
            knobs_dropdown = self.current_knob_dropdown
            kd_index = knobs_dropdown.currentIndex()
            kd_data = knobs_dropdown.itemData(kd_index)
            if self.show_labels and kd_data not in self.defaultKnobs:
                if kd_data == "kernelSource" and self.node.Class() == "BlinkScript":
                    kd_data = "Blinkscript Code (kernelSource)"
                else:
                    kd_data = "{} ({})".format(self.node.knob(kd_data).label(), kd_data)
            if not modified:
                knobs_dropdown.setItemText(kd_index, kd_data)
            else:
                knobs_dropdown.setItemText(kd_index, kd_data + "(*)")
        except:
            pass

    def knobLanguage(self, node, knob_name="knobChanged"):
        """ Given a node and a knob name, guesses the appropriate code language """
        if knob_name not in node.knobs():
            return None
        if knob_name == "kernelSource" and node.Class() == "BlinkScript":
            return "blink"
        elif knob_name in self.defaultKnobs or node.knob(knob_name).Class() in self.python_knob_classes:
            return "python"
        else:
            return None

    def setCodeLanguage(self, code_language="python"):
        """Performs all UI changes neccesary for editing a different language! Syntax highlighter, menu buttons, etc.

        Args:
            code_language (str, Optional): Language to change to. Can be "python","blink" or None

        """

        # 1. Allow for string or int, 0 being "no language", 1 "python", 2 "blink"
        code_language_list = [None, "python", "blink"]
        if code_language is None:
            new_code_language = code_language
        elif isinstance(code_language, str) and code_language.lower() in code_language_list:
            new_code_language = code_language.lower()
        elif isinstance(code_language, int) and code_language_list[code_language]:
            new_code_language = code_language_list[code_language]
        else:
            return False

        # 2. Syntax highlighter
        self.script_editor.set_code_language(new_code_language)

        self.code_language = new_code_language

        # 3. Menus
        self.run_script_button.setVisible(code_language != "blink")
        self.clear_console_button.setVisible(code_language != "blink")
        self.save_recompile_button.setVisible(code_language == "blink")
        self.backup_button.setVisible(code_language == "blink")

    def loadKnobState(self):
        """
        Loads the state of the knobs from the place where it's stored file inside the SE directory's root.
        """

        prefs_state = config.prefs["ks_save_knob_state"]
        if prefs_state == 0: # Do not save
            logging.debug("Not loading the knob state dictionary (chosen in preferences).")
        elif prefs_state == 1: # Saved in memory
            full_knob_state_dict = config.knob_state_dict
            nk_path = utils.nk_saved_path()
            node_fullname = self.node.fullName()
            if nk_path in full_knob_state_dict:
                if node_fullname in full_knob_state_dict[nk_path]:
                    self.current_node_state_dict = config.knob_state_dict[nk_path][node_fullname]
        elif prefs_state == 2: # Saved to disk
            if not os.path.isfile(config.knob_state_txt_path):
                return False
            else:
                full_knob_state_dict = {}
                with open(config.knob_state_txt_path, "r") as f:
                    full_knob_state_dict = json.load(f)
                nk_path = utils.nk_saved_path()
                node_fullname = self.node.fullName()
                if nk_path in full_knob_state_dict:
                    if node_fullname in full_knob_state_dict[nk_path]:
                        self.current_node_state_dict = full_knob_state_dict[nk_path][node_fullname]

    def setKnobState(self):
        """
        Sets the saved knob state from self.current_node_state_dict into the current knob's script if applicable
        """
        nk_path = utils.nk_saved_path()
        node_fullname = self.node.fullName()
        logging.debug("knob is "+self.knob)

        # current_node_state_dict: {"cursor_pos":{},"scroll_pos":{},"open_knob"=None}
        node_state_dict = self.current_node_state_dict

        if "cursor_pos" in node_state_dict:
            if self.knob in node_state_dict["cursor_pos"]:
                cursor = self.script_editor.textCursor()
                cursor.setPosition(int(node_state_dict["cursor_pos"][self.knob][1]),
                                   QtGui.QTextCursor.MoveAnchor)
                cursor.setPosition(int(node_state_dict["cursor_pos"][self.knob][0]),
                                   QtGui.QTextCursor.KeepAnchor)
                self.script_editor.setTextCursor(cursor)

        if "scroll_pos" in node_state_dict:
            if self.knob in node_state_dict["scroll_pos"]:
                logging.debug("Scroll value found: "+str(node_state_dict["scroll_pos"][self.knob]))
                self.script_editor.verticalScrollBar().setValue(
                    int(node_state_dict["scroll_pos"][self.knob]))

    def saveKnobState(self):
        """ Stores the current state of the script """
        logging.debug("About to save knob state...")

        # 1. Save state in own dict
        # 1.1. Save scroll value in own dict
        if "scroll_pos" not in self.current_node_state_dict:
            self.current_node_state_dict["scroll_pos"] = {}
        self.current_node_state_dict["scroll_pos"][self.knob] = self.script_editor.verticalScrollBar().value()

        # 1.2. Save cursor value in own dict
        if "cursor_pos" not in self.current_node_state_dict:
            self.current_node_state_dict["cursor_pos"] = {}
        self.current_node_state_dict["cursor_pos"][self.knob] = [self.script_editor.textCursor().position(),
                                                                 self.script_editor.textCursor().anchor()]

        # 1.3. Save current open knob in own dict
        self.current_node_state_dict["open_knob"] = self.knob

        logging.debug("Current knob state dict for this knob...:")
        logging.debug(self.current_node_state_dict)

        # 2. Get full dict...
        prefs_state = config.prefs["ks_save_knob_state"]
        logging.debug("prefs state for knobs: "+str(prefs_state))

        if prefs_state == 0: # Do not save
            logging.debug("Not saving the script state dictionary (chosen in preferences).")
            return

        if prefs_state == 1: # Saved in memory
            full_knob_state_dict = config.knob_state_dict
        elif prefs_state == 2: # Saved to disk
            full_knob_state_dict = {}
            if os.path.isfile(config.knob_state_txt_path):
                with open(config.knob_state_txt_path, "r") as f:
                    full_knob_state_dict = json.load(f)
        else:
            raise Exception("Error: config.prefs['ks_save_knob_state'] value should be 0, 1 or 2.")
            return False

        nk_path = utils.nk_saved_path()
        node_fullname = self.node.fullName()
        logging.debug("Node fullname: "+node_fullname)

        if nk_path not in full_knob_state_dict:
            full_knob_state_dict[nk_path] = {}

        if node_fullname not in full_knob_state_dict[nk_path]:
            full_knob_state_dict[nk_path][node_fullname] = {} # {"cursor_pos":{},"scroll_pos":{},"open_knob"=None}

        full_knob_state_dict[nk_path][node_fullname] = self.current_node_state_dict

        # 4. Store in memory/disk/none
        if prefs_state == 1: # Saved in memory
            config.knob_state_dict = full_knob_state_dict
        elif prefs_state == 2: # Saved to disk
            with open(config.knob_state_txt_path, "w") as f:
                json.dump(full_knob_state_dict, f, sort_keys=True, indent=4)

    # Blink Options in node mode

    def blinkSaveRecompile(self):
        """
        If blink mode on, tries to save the blink code in the node (and backups), then executes the Recompile button.
        """
        if self.code_language != "blink":
            return False

        # TODO perform backup first!! backupBlink function or something...
        self.saveKnobValue(check=False)
        if self.blink_autoSave_act.isChecked():
            if self.blink_check_file():
                self.blink_save_file()
        try:
            self.node.knob("recompile").execute()
        except:
            logging.debug("Error recompiling the Blinkscript node.")

    def blink_toggle_autosave_action(self):
        if self.blink_autoSave_act.isChecked():
            self.blink_check_file(create=True)
        return

    def blink_load_triggered(self):
        if "reloadKernelSourceFile" not in self.node.knobs():
            logging.debug("reloadKernelSourceFile knob not found in node {}".format(str(node.name())))
        else:
            self.node.knob("reloadKernelSourceFile").execute()
            self.loadKnobValue()
        return

    def blink_save_triggered(self):
        self.saveKnobValue(check=False)
        self.blink_save_file(native=True)
        return

    def blink_versionup_triggered(self):
        node = self.node
        if "kernelSourceFile" not in node.knobs():
            logging.debug("kernelSourceFile knob not found in node {}".format(str(node.name())))
            return False
        current_path = node.knob("kernelSourceFile").value()
        versioned_up_path = utils.filepath_version_up(current_path)
        node.knob("kernelSourceFile").setValue(versioned_up_path)
        self.blink_save_file()

    def blink_save_file(self, native=False):
        """ Saves the blink contents into file.

        Args:
            native: Whether to execute the node's Save button (asks for confirmation) or do it manually.

        """
        try:
            if self.blink_check_file():
                if native:
                    self.node.knob("saveKernelFile").execute()  # This one asks for confirmation...
                else:
                    file = open(self.node.knob("kernelSourceFile").value(), 'w')
                    file.write(string(self.script_editor.toPlainText()))
                    file.close()
        except:
            logging.debug("Error saving the Blinkscript file.")

    def blink_check_file(self, node=None, create=True):
        """Checks if the node's kernelSourceFile is populated. Otherwise, if create == True, creates it.

        Args:
            node (nuke.Node, Optional): The selected node where to perform the check.
            create (bool, Optional): Whether to create the file otherwise.

        Returns:
            bool: True if populated in the end
        """
        if not node:
            node = self.node
        if "kernelSourceFile" not in node.knobs():
            logging.debug("kernelSourceFile knob not found in node {}".format(str(node.name())))
            return False
        filepath = node.knob("kernelSourceFile").value()
        if not len(filepath.strip()):
            if create:
                # Make the path!
                kernel_name_re = r"kernel ([\w]+)[ ]*:[ ]*Image[a-zA-Z]+Kernel[ ]*<"
                kernel_name_search = re.search(kernel_name_re, string(self.script_editor.toPlainText()))
                if not kernel_name_search:
                    name = "Kernel"
                else:
                    name = kernel_name_search.groups()[0]

                version = 1
                while True:
                    new_path = os.path.join(config.blink_dir, "{0}{1}_v001.blink".format(name, str(version).zfill(2)))
                    if not os.path.exists(new_path):
                        fn = nuke.getFilename("Please name the blink file.", default=new_path.replace("\\", "/"))
                        if fn:
                            node.knob("kernelSourceFile").setValue(fn)
                            node.knob("saveKernelFile").execute()
                            return True
                        break
                    version += 1
        else:
            return True
        return False

    def blink_menu_refresh(self):
        """ Updates and populates the information on the blink menu, on demand. Showing kernel file name etc... """
        # self.blink_menu
        node = self.node

        # 1. Display file name
        if "kernelSourceFile" not in node.knobs():
            logging.debug("kernelSourceFile knob not found in node {}".format(str(node.name())))
        else:
            filepath = node.knob("kernelSourceFile").value()
            if self.blink_check_file(create=False):
                self.blink_filename_info_act.setText(filepath.rsplit("/", 1)[-1])
            else:
                self.blink_filename_info_act.setText("No file specified.")

        # 2. Enable/disable load-save buttons
        if "reloadKernelSourceFile" not in node.knobs():
            logging.debug("reloadKernelSourceFile knob not found in node {}".format(str(node.name())))
        else:
            # The next thing doesn't work before the properties panel of the node is opened for the first time,
            # as the buttons are disabled even when they shouldn't.
            # self.blink_load_act.setEnabled(node.knob("reloadKernelSourceFile").enabled())
            # self.blink_save_act.setEnabled(node.knob("saveKernelFile").enabled())
            pass

        return

    def blink_browse_action(self):
        """
        Browses to the blink file's directory.
        """
        if "kernelSourceFile" not in self.node.knobs():
            logging.debug("kernelSourceFile knob not found in node {}".format(str(node.name())))
        else:
            filepath = self.node.knob("kernelSourceFile").value()
            self.openInFileBrowser(filepath)

    # Script Mode
    def updateFoldersDropdown(self):
        """ Populate folders dropdown list """
        self.current_folder_dropdown.blockSignals(True)
        self.current_folder_dropdown.clear()  # First remove all items
        default_folders = ["scripts"]
        script_folders = []
        counter = 0
        for f in default_folders:
            self.makeScriptFolder(f)
            self.current_folder_dropdown.addItem(f + "/", f)
            counter += 1

        try:
            script_folders = sorted([f for f in os.listdir(config.py_scripts_dir) if
                                     os.path.isdir(os.path.join(config.py_scripts_dir, f))])  # Accepts symlinks!!!
        except:
            logging.debug("Couldn't read any script folders.")

        for f in script_folders:
            fname = f.split("/")[-1]
            if fname in default_folders:
                continue
            self.current_folder_dropdown.addItem(fname + "/", fname)
            counter += 1

        # print script_folders
        if counter > 0:
            self.current_folder_dropdown.insertSeparator(counter)
            counter += 1
            # self.current_folder_dropdown.insertSeparator(counter)
            # counter += 1
        self.current_folder_dropdown.addItem("New", "create new")
        self.current_folder_dropdown.addItem("Open...", "open in browser")
        self.current_folder_dropdown.addItem("Add custom", "add custom path")
        self.folder_index = self.current_folder_dropdown.currentIndex()
        self.current_folder = self.current_folder_dropdown.itemData(self.folder_index)
        self.current_folder_dropdown.blockSignals(False)
        return

    def updateScriptsDropdown(self):
        """ Populate py scripts dropdown list """
        self.current_script_dropdown.blockSignals(True)
        self.current_script_dropdown.clear()  # First remove all items
        QtWidgets.QApplication.processEvents()
        logging.debug("# Updating scripts dropdown...")
        logging.debug("scripts dir:" + config.py_scripts_dir)
        logging.debug("current folder:" + self.current_folder)
        logging.debug("previous current script:" + self.current_script)
        # current_folder = self.current_folder_dropdown.itemData(self.current_folder_dropdown.currentIndex())
        current_folder_path = os.path.join(config.py_scripts_dir, self.current_folder)
        default_scripts = ["Untitled.py"]
        found_scripts = []
        found_temp_scripts = []
        counter = 0
        dir_list = os.listdir(current_folder_path)  # All files and folders inside of the folder
        try:
            found_scripts = sorted([f for f in dir_list if f.endswith(".py")])
            found_temp_scripts = [f for f in dir_list if f.endswith(".py.autosave")]
        except:
            logging.debug("Couldn't find any scripts in the selected folder.")
        if not len(found_scripts):
            for s in default_scripts:
                if s + ".autosave" in found_temp_scripts:
                    self.current_script_dropdown.addItem(s + "(*)", s)
                else:
                    self.current_script_dropdown.addItem(s, s)
                counter += 1
        else:
            for s in default_scripts:
                if s + ".autosave" in found_temp_scripts:
                    self.current_script_dropdown.addItem(s + "(*)", s)
                elif s in found_scripts:
                    self.current_script_dropdown.addItem(s, s)
            for s in found_scripts:
                if s in default_scripts:
                    continue
                sname = s.split("/")[-1]
                if s + ".autosave" in found_temp_scripts:
                    self.current_script_dropdown.addItem(sname + "(*)", sname)
                else:
                    self.current_script_dropdown.addItem(sname, sname)
                counter += 1
        # else: #Add the found scripts to the dropdown
        if counter > 0:
            counter += 1
            self.current_script_dropdown.insertSeparator(counter)
            counter += 1
            self.current_script_dropdown.insertSeparator(counter)
        self.current_script_dropdown.addItem("New", "create new")
        self.current_script_dropdown.addItem("Duplicate", "create duplicate")
        self.current_script_dropdown.addItem("Delete", "delete script")
        self.current_script_dropdown.addItem("Open", "open in browser")
        # self.script_index = self.current_script_dropdown.currentIndex()
        self.script_index = 0
        self.current_script = self.current_script_dropdown.itemData(self.script_index)
        logging.debug("Finished updating scripts dropdown.")
        logging.debug("current_script:" + self.current_script)
        self.current_script_dropdown.blockSignals(False)
        return

    @staticmethod
    def makeScriptFolder(name="scripts"):
        folder_path = os.path.join(config.py_scripts_dir, name)
        if not os.path.exists(folder_path):
            try:
                os.makedirs(folder_path)
                return True
            except:
                print("Couldn't create the scripting folders.\nPlease check your OS write permissions.")
                return False

    def makeScriptFile(self, name="Untitled.py"):
        script_path = os.path.join(config.py_scripts_dir, self.current_folder, name)
        if not os.path.isfile(script_path):
            try:
                self.current_script_file = open(script_path, 'w')
                return True
            except:
                print("Couldn't create the scripting folders.\nPlease check your OS write permissions.")
                return False

    def setCurrentFolder(self, folder_name):
        """ Set current folder ON THE DROPDOWN ONLY"""
        folder_list = [self.current_folder_dropdown.itemData(i) for i in range(self.current_folder_dropdown.count())]
        if folder_name in folder_list:
            index = folder_list.index(folder_name)
            self.current_folder_dropdown.blockSignals(True)
            self.current_folder_dropdown.setCurrentIndex(index)
            self.current_folder_dropdown.blockSignals(False)
            self.current_folder = folder_name
        self.folder_index = self.current_folder_dropdown.currentIndex()
        self.current_folder = self.current_folder_dropdown.itemData(self.folder_index)
        return

    def setCurrentScript(self, script_name):
        """ Set current script ON THE DROPDOWN ONLY """
        script_list = [self.current_script_dropdown.itemData(i) for i in range(self.current_script_dropdown.count())]
        if script_name in script_list:
            index = script_list.index(script_name)
            self.current_script_dropdown.blockSignals(True)
            self.current_script_dropdown.setCurrentIndex(index)
            self.current_script_dropdown.blockSignals(False)
            self.current_script = script_name
        self.script_index = self.current_script_dropdown.currentIndex()
        self.current_script = self.current_script_dropdown.itemData(self.script_index)
        return

    def loadScriptContents(self, check=False, py_only=False, folder=""):
        """ Gets the contents of the selected script and populates the editor """
        logging.debug("# About to load script contents now.")
        obtained_scroll_value = 0
        # obtained_cursor_pos_value = [0, 0]  # Position, anchor
        if folder == "":
            folder = self.current_folder
        script_path = os.path.join(config.py_scripts_dir, folder, self.current_script)
        script_path_temp = script_path + ".autosave"
        if (self.current_folder + "/" + self.current_script) in self.py_scroll_positions:
            obtained_scroll_value = self.py_scroll_positions[self.current_folder + "/" + self.current_script]
        # if (self.current_folder + "/" + self.current_script) in self.cursorPos:
        #     obtained_cursor_pos_value = self.cursorPos[self.current_folder + "/" + self.current_script]

        # 1: If autosave exists and pyOnly is false, load it
        if os.path.isfile(script_path_temp) and not py_only:
            logging.debug("Loading .py.autosave file\n---")
            with open(script_path_temp, 'r') as script:
                script_content = script.read()
            self.script_editor.setPlainText(script_content)
            self.setScriptModified(True)
            self.script_editor.verticalScrollBar().setValue(obtained_scroll_value)

        # 2: Try to load the .py as first priority, if it exists
        elif os.path.isfile(script_path):
            logging.debug("Loading .py file\n---")
            with open(script_path, 'r') as script:
                script_content = script.read()
            current_text = string(self.script_editor.toPlainText())
            if check and current_text != script_content and current_text.strip() != "":
                msg_box = QtWidgets.QMessageBox()
                msg_box.setText("The script has been modified.")
                msg_box.setInformativeText("Do you want to overwrite the current code on this editor?")
                msg_box.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
                msg_box.setIcon(QtWidgets.QMessageBox.Question)
                msg_box.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
                msg_box.setDefaultButton(QtWidgets.QMessageBox.Yes)
                reply = msg_box.exec_()
                if reply == QtWidgets.QMessageBox.No:
                    return
            # Clear trash
            if os.path.isfile(script_path_temp):
                os.remove(script_path_temp)
                logging.debug("Removed " + script_path_temp)
            self.setScriptModified(False)
            self.script_editor.setPlainText(script_content)
            self.script_editor.verticalScrollBar().setValue(obtained_scroll_value)
            self.setScriptModified(False)

        # 3: If .py doesn't exist... only then stick to the autosave
        elif os.path.isfile(script_path_temp):
            # with open(script_path_temp, 'r') as script:
            #     script_content = script.read()

            msg_box = QtWidgets.QMessageBox()
            msg_box.setText("The .py file hasn't been found.")
            msg_box.setInformativeText("Do you want to clear the current code on this editor?")
            msg_box.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
            msg_box.setIcon(QtWidgets.QMessageBox.Question)
            msg_box.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
            msg_box.setDefaultButton(QtWidgets.QMessageBox.Yes)
            reply = msg_box.exec_()
            if reply == QtWidgets.QMessageBox.No:
                return

            # Clear trash
            os.remove(script_path_temp)
            logging.debug("Removed " + script_path_temp)
            self.script_editor.setPlainText("")
            self.updateScriptsDropdown()
            self.loadScriptContents(check=False)
            self.loadScriptState()
            self.setScriptState()

        else:
            script_content = ""
            self.script_editor.setPlainText(script_content)
            self.setScriptModified(False)
            if self.current_folder + "/" + self.current_script in self.py_scroll_positions:
                del self.py_scroll_positions[self.current_folder + "/" + self.current_script]
            if self.current_folder + "/" + self.current_script in self.py_cursor_positions:
                del self.py_cursor_positions[self.current_folder + "/" + self.current_script]

        self.setWindowTitle("KnobScripter - %s/%s" % (self.current_folder, self.current_script))
        return

    def saveScriptContents(self, temp=True):
        """ Save the current contents of the editor into the python file. If temp == True, saves a .py.autosave file """
        logging.debug("\n# About to save script contents now.")
        logging.debug("Temp mode is: " + str(temp))
        logging.debug("self.current_folder: " + self.current_folder)
        logging.debug("self.current_script: " + self.current_script)
        script_path = os.path.join(config.py_scripts_dir, self.current_folder, self.current_script)
        script_path_temp = script_path + ".autosave"
        orig_content = ""
        script_content = string(self.script_editor.toPlainText())

        if temp:
            if os.path.isfile(script_path):
                with open(script_path, 'r') as script:
                    orig_content = script.read()
            elif script_content == "" and os.path.isfile(
                    script_path_temp):  # If script path doesn't exist and autosave does but the script is empty...
                os.remove(script_path_temp)
                return
            if script_content != orig_content:
                with open(script_path_temp, 'w') as script:
                    script.write(script_content)
            else:
                if os.path.isfile(script_path_temp):
                    os.remove(script_path_temp)
                logging.debug("Nothing to save")
                return
        else:
            with open(script_path, 'w') as script:
                script.write(string(self.script_editor.toPlainText()))
            # Clear trash
            if os.path.isfile(script_path_temp):
                os.remove(script_path_temp)
                logging.debug("Removed " + script_path_temp)
            self.setScriptModified(False)
        self.saveScriptState()
        logging.debug("Saved " + script_path + "\n---")
        return

    def deleteScript(self, check=True, folder=""):
        """ Get the contents of the selected script and populate the editor """
        logging.debug("# About to delete the .py and/or autosave script now.")
        if folder == "":
            folder = self.current_folder
        script_path = os.path.join(config.py_scripts_dir, folder, self.current_script)
        script_path_temp = script_path + ".autosave"
        if check:
            msg_box = QtWidgets.QMessageBox()
            msg_box.setText("You're about to delete this script.")
            msg_box.setInformativeText("Are you sure you want to delete {}?".format(self.current_script))
            msg_box.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
            msg_box.setIcon(QtWidgets.QMessageBox.Question)
            msg_box.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
            msg_box.setDefaultButton(QtWidgets.QMessageBox.No)
            reply = msg_box.exec_()
            if reply == QtWidgets.QMessageBox.No:
                return False

        if os.path.isfile(script_path_temp):
            os.remove(script_path_temp)
            logging.debug("Removed " + script_path_temp)

        if os.path.isfile(script_path):
            os.remove(script_path)
            logging.debug("Removed " + script_path)

        return True

    def folderDropdownChanged(self):
        """ Executed when the current folder dropdown is changed. """
        self.saveScriptState()
        logging.debug("# folder dropdown changed")
        folders_dropdown = self.current_folder_dropdown
        # fd_value = folders_dropdown.currentText()
        fd_index = folders_dropdown.currentIndex()
        fd_data = folders_dropdown.itemData(fd_index)
        if fd_data == "create new":
            panel = dialogs.FileNameDialog(self, mode="folder")
            # panel.setWidth(260)
            # panel.addSingleLineInput("Name:","")
            if panel.exec_():
                # Accepted
                folder_name = panel.text
                if os.path.isdir(os.path.join(config.py_scripts_dir, folder_name)):
                    self.message_box("Folder already exists.")
                    self.setCurrentFolder(self.current_folder)
                if self.makeScriptFolder(name=folder_name):
                    self.saveScriptContents(temp=True)
                    # Success creating the folder
                    self.current_folder = folder_name
                    self.updateFoldersDropdown()
                    self.setCurrentFolder(folder_name)
                    self.updateScriptsDropdown()
                    self.loadScriptContents(check=False)
                else:
                    self.message_box("There was a problem creating the folder.")
                    self.current_folder_dropdown.blockSignals(True)
                    self.current_folder_dropdown.setCurrentIndex(self.folder_index)
                    self.current_folder_dropdown.blockSignals(False)
            else:
                # Canceled/rejected
                self.current_folder_dropdown.blockSignals(True)
                self.current_folder_dropdown.setCurrentIndex(self.folder_index)
                self.current_folder_dropdown.blockSignals(False)
                return

        elif fd_data == "open in browser":
            current_folder_path = os.path.join(config.py_scripts_dir, self.current_folder)
            self.openInFileBrowser(current_folder_path)
            self.current_folder_dropdown.blockSignals(True)
            self.current_folder_dropdown.setCurrentIndex(self.folder_index)
            self.current_folder_dropdown.blockSignals(False)
            return

        elif fd_data == "add custom path":
            folder_path = nuke.getFilename('Select custom folder.')
            if folder_path is not None:
                if folder_path.endswith("/"):
                    alias_name = folder_path.split("/")[-2]
                else:
                    alias_name = folder_path.split("/")[-1]
                if not os.path.isdir(folder_path):
                    self.message_box("Folder not found. Please try again with the full path to a folder.")
                elif not len(alias_name):
                    self.message_box("Folder with the same name already exists. Please delete or rename it first.")
                else:
                    # All good
                    os.symlink(folder_path, os.path.join(config.py_scripts_dir, alias_name))
                    self.saveScriptContents(temp=True)
                    self.current_folder = alias_name
                    self.updateFoldersDropdown()
                    self.setCurrentFolder(alias_name)
                    self.updateScriptsDropdown()
                    self.loadScriptContents(check=False)
                    self.script_editor.setFocus()
                    return
            self.current_folder_dropdown.blockSignals(True)
            self.current_folder_dropdown.setCurrentIndex(self.folder_index)
            self.current_folder_dropdown.blockSignals(False)
        else:
            # 1: Save current script as temp if needed
            self.saveScriptContents(temp=True)
            # 2: Set the new folder in the variables
            self.current_folder = fd_data
            self.folder_index = fd_index
            # 3: Update the scripts dropdown
            self.updateScriptsDropdown()
            # 4: Load the current script!
            self.loadScriptContents()

            self.loadScriptState()
            self.setScriptState()
            self.script_editor.setFocus()

        return

    def scriptDropdownChanged(self):
        """ Executed when the current script dropdown is changed. Only be called by the manual dropdown change. """
        self.saveScriptState()
        scripts_dropdown = self.current_script_dropdown
        # sd_value = scripts_dropdown.currentText()
        sd_index = scripts_dropdown.currentIndex()
        sd_data = scripts_dropdown.itemData(sd_index)
        if sd_data == "create new":
            self.current_script_dropdown.blockSignals(True)
            panel = dialogs.FileNameDialog(self, mode="script")
            if panel.exec_():
                # Accepted
                script_name = panel.text + ".py"
                script_path = os.path.join(config.py_scripts_dir, self.current_folder, script_name)
                logging.debug(script_name)
                logging.debug(script_path)
                if os.path.isfile(script_path):
                    self.message_box("Script already exists.")
                    self.current_script_dropdown.setCurrentIndex(self.script_index)
                if self.makeScriptFile(name=script_name):
                    # Success creating the folder
                    self.saveScriptContents(temp=True)
                    if self.current_script != "Untitled.py":
                        self.script_editor.setPlainText("")
                    self.updateScriptsDropdown()
                    self.current_script = script_name
                    self.setCurrentScript(script_name)
                    self.saveScriptContents(temp=False)
                else:
                    self.message_box("There was a problem creating the script.")
                    self.current_script_dropdown.setCurrentIndex(self.script_index)
            else:
                # Canceled/rejected
                self.current_script_dropdown.setCurrentIndex(self.script_index)
                self.current_script_dropdown.blockSignals(False)
                return
            self.current_script_dropdown.blockSignals(False)

        elif sd_data == "create duplicate":
            self.current_script_dropdown.blockSignals(True)
            # current_folder_path = os.path.join(config.py_scripts_dir, self.current_folder, self.current_script)
            # current_script_path = os.path.join(config.py_scripts_dir, self.current_folder, self.current_script)

            current_name = self.current_script
            if self.current_script.endswith(".py"):
                current_name = current_name[:-3]

            test_name = current_name
            while True:
                test_name += "_copy"
                new_script_path = os.path.join(config.py_scripts_dir, self.current_folder, test_name + ".py")
                if not os.path.isfile(new_script_path):
                    break

            script_name = test_name + ".py"

            if self.makeScriptFile(name=script_name, folder=self.current_folder):
                # Success creating the folder
                self.saveScriptContents(temp=True)
                self.updateScriptsDropdown()
                # self.script_editor.setPlainText("")
                self.current_script = script_name
                self.setCurrentScript(script_name)
                self.script_editor.setFocus()
            else:
                self.message_box("There was a problem duplicating the script.")
                self.current_script_dropdown.setCurrentIndex(self.script_index)

            self.current_script_dropdown.blockSignals(False)

        elif sd_data == "open in browser":
            current_script_path = os.path.join(config.py_scripts_dir, self.current_folder, self.current_script)
            self.openInFileBrowser(current_script_path)
            self.current_script_dropdown.blockSignals(True)
            self.current_script_dropdown.setCurrentIndex(self.script_index)
            self.current_script_dropdown.blockSignals(False)
            return

        elif sd_data == "delete script":
            if self.deleteScript():
                self.updateScriptsDropdown()
                self.loadScriptContents()
            else:
                self.current_script_dropdown.blockSignals(True)
                self.current_script_dropdown.setCurrentIndex(self.script_index)
                self.current_script_dropdown.blockSignals(False)

        else:
            self.saveScriptContents()
            self.current_script = sd_data
            self.script_index = sd_index
            self.setCurrentScript(self.current_script)
            self.loadScriptContents()
            self.script_editor.setFocus()
            self.loadScriptState()
            self.setScriptState()
        return

    def setScriptModified(self, modified=True):
        """ Sets self.current_script_modified, title and whatever else we need. """
        self.current_script_modified = modified
        title_modified_string = " [modified]"
        window_title = self.windowTitle().split(title_modified_string)[0]
        if modified:
            window_title += title_modified_string
        self.setWindowTitle(window_title)
        try:
            scripts_dropdown = self.current_script_dropdown
            sd_index = scripts_dropdown.currentIndex()
            sd_data = scripts_dropdown.itemData(sd_index)
            if not modified:
                scripts_dropdown.setItemText(sd_index, sd_data)
            else:
                scripts_dropdown.setItemText(sd_index, sd_data + "(*)")
        except:
            pass

    @staticmethod
    def openInFileBrowser(path=""):
        the_os = platform.system()
        if not os.path.exists(path):
            path = KS_DIR
        if the_os == "Windows":
            # os.startfile(path)
            filebrowser_path = os.path.join(os.getenv('WINDIR'), 'explorer.exe')
            path = os.path.normpath(path)
            if os.path.isdir(path):
                subprocess.Popen([filebrowser_path, path])
            elif os.path.isfile(path):
                subprocess.Popen([filebrowser_path, '/select,', path])
        elif the_os == "Darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])

    def loadScriptState(self):
        """
        Loads the last state of the script from the appropriate location into self.py_state_dict
        Appropriate location: None, config.py_state_dict, or on disk
        """

        prefs_state = config.prefs["ks_save_py_state"]
        if prefs_state == 0: # Do not save
            logging.debug("Not loading the script state dictionary (chosen in preferences).")
        elif prefs_state == 1: # Saved in memory
            self.py_state_dict = config.py_state_dict
        elif prefs_state == 2: # Saved to disk
            logging.debug("Prefs ks_save_py_state is 2")
            if not os.path.isfile(config.py_state_txt_path):
                return {}
            else:
                with open(config.py_state_txt_path, "r") as f:
                    self.py_state_dict = json.load(f)

        return self.py_state_dict

        # Rest is not needed anymore. Use self.py_state_dict only
        # TODO Remove the following stuff...
        if "scroll_pos" in self.py_state_dict:
            self.py_scroll_positions = self.py_state_dict["scroll_pos"]
        if "cursor_pos" in self.py_state_dict:
            self.py_cursor_positions = self.py_state_dict["cursor_pos"]

    def setScriptState(self):
        """
        Sets the stored (only if stored) script state from self.py_state_dict into the current script
        """
        script_fullname = self.current_folder + "/" + self.current_script

        logging.debug("Setting script state")

        if "cursor_pos" in self.py_state_dict:
            cp_dict = self.py_state_dict["cursor_pos"]
            if script_fullname in cp_dict:
                cursor = self.script_editor.textCursor()
                cursor.setPosition(int(cp_dict[script_fullname][1]), QtGui.QTextCursor.MoveAnchor)
                cursor.setPosition(int(cp_dict[script_fullname][0]), QtGui.QTextCursor.KeepAnchor)
                self.script_editor.setTextCursor(cursor)

        if "scroll_pos" in self.py_state_dict:
            sp_dict = self.py_state_dict["scroll_pos"]
            if script_fullname in sp_dict:
                self.script_editor.verticalScrollBar().setValue(int(sp_dict[script_fullname]))

        if 'splitter_sizes' in self.py_state_dict:
            self.splitter.setSizes(self.py_state_dict['splitter_sizes'])

    def saveScriptState(self):
        """ Stores the current state of the script into the self.py_state_dict. Then, also stores the full dict
        into the location specified in preferences (None, memory or disk).
        """
        logging.debug("Saving script state")

        script_fullname = self.current_folder + "/" + self.current_script

        # 1. Save into this instance's own dict first (self.py_state_dict)
        # 1.1. Save current scroll pos into own dict
        scroll_pos = self.script_editor.verticalScrollBar().value()
        if "scroll_pos" not in self.py_state_dict:
            self.py_state_dict["scroll_pos"] = {}
        self.py_state_dict["scroll_pos"][script_fullname] = scroll_pos

        # 1.2. Save current cursor pos into own dict
        if "cursor_pos" not in self.py_state_dict:
            self.py_state_dict["cursor_pos"] = {}
        cursor_pos = [self.script_editor.textCursor().position(), self.script_editor.textCursor().anchor()]
        self.py_state_dict["cursor_pos"][script_fullname] = cursor_pos

        # 1.3. Last folder, script and splitter sizes
        self.py_state_dict['last_folder'] = self.current_folder
        self.py_state_dict['last_script'] = self.current_script
        self.py_state_dict['splitter_sizes'] = self.splitter.sizes()

        # 2. Store to appropriate location
        prefs_state = config.prefs["ks_save_py_state"]
        if prefs_state == 0: # Do not save
            logging.debug("Not saving the script state dictionary (chosen in prefs).")
        elif prefs_state == 1: # Saved in memory
            config.py_state_dict = self.py_state_dict
        elif prefs_state == 2: # Saved to disk
            with open(config.py_state_txt_path, "w") as f:
                json.dump(self.py_state_dict, f, sort_keys=True, indent=4)

    def setLastScript(self):
        if 'last_folder' in self.py_state_dict and 'last_script' in self.py_state_dict:
            self.updateFoldersDropdown()
            self.setCurrentFolder(self.py_state_dict['last_folder'])
            self.updateScriptsDropdown()
            self.setCurrentScript(self.py_state_dict['last_script'])


    # Autosave background loop
    def autosave(self):
        if self.toAutosave:
            # Save the script...
            self.saveScriptContents()
            self.toAutosave = False
            logging.debug("autosaving...")
            return

    # Global stuff
    def setTextSelection(self):
        self.script_editor.highlighter.selected_text = string(self.script_editor.textCursor().selection().toPlainText())
        return

    def resizeEvent(self, res_event):
        w = self.frameGeometry().width()
        self.current_node_label_node.setVisible(w > 460)
        self.script_label.setVisible(w > 460)
        return super(KnobScripterWidget, self).resizeEvent(res_event)

    def changeClicked(self, new_node=""):
        """ Change node """
        try:
            logging.debug("Changing from " + self.node.name())
            self.clearConsole()
        except:
            self.node = None
            if not len(nuke.selectedNodes()):
                self.exitNodeMode()
                return
        nuke.menu("Nuke").findItem("Edit/Node/Update KnobScripter Context").invoke()
        selection = nuke.knobScripterSelectedNodes
        if self.nodeMode:  # Only update the number of unsaved knobs if we were already in node mode
            if self.node is not None:
                changed_knobs_count = self.updateUnsavedKnobs()
            else:
                changed_knobs_count = 0
        else:
            changed_knobs_count = 0
            self.autosave()
        if new_node and new_node != "" and nuke.exists(new_node):
            selection = [new_node]
        elif not len(selection):
            node_dialog = dialogs.ChooseNodeDialog(self)
            if node_dialog.exec_():
                # Accepted
                selection = [nuke.toNode(node_dialog.name)]
            else:
                return

        # Change to node mode...
        self.node_mode_bar.setVisible(True)
        self.script_mode_bar.setVisible(False)
        if not self.nodeMode:
            self.saveScriptContents()
            self.toAutosave = False
            self.saveScriptState()
            # self.splitter.setSizes([0,1])

        # If already selected, pass
        if self.node is not None and selection[0].fullName() == self.node.fullName() and self.nodeMode:
            self.message_box("Please select a different node first!")
            return
        elif changed_knobs_count > 0:
            msg_box = QtWidgets.QMessageBox()
            msg_box.setText(
                "Save changes to %s knob%s before changing the node?" % (
                    str(changed_knobs_count), int(changed_knobs_count > 1) * "s"))
            msg_box.setStandardButtons(
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No | QtWidgets.QMessageBox.Cancel)
            msg_box.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
            msg_box.setDefaultButton(QtWidgets.QMessageBox.Yes)
            reply = msg_box.exec_()
            if reply == QtWidgets.QMessageBox.Yes:
                self.saveAllKnobValues(check=False)
            elif reply == QtWidgets.QMessageBox.Cancel:
                return
        if len(selection) > 1:
            self.message_box("More than one node selected.\n"
                             "Changing knobChanged editor to %s" % selection[0].fullName())
        # Reinitialise everything, wooo!
        self.current_knob_dropdown.blockSignals(True)
        self.current_node_state_dict = {}
        self.node = selection[0]
        self.nodeMode = True

        # Load stored state of knobs
        self.current_node_state_dict = {}
        self.loadKnobState()
        state_dict = self.current_node_state_dict
        if "open_knob" in state_dict and state_dict["open_knob"] in self.node.knobs():
            self.knob = state_dict["open_knob"]
        elif "kernelSource" in self.node.knobs() and self.node.Class() == "BlinkScript":
            self.knob = "kernelSource"
        else:
            self.knob = "knobChanged"


        self.script_editor.setPlainText("")
        self.unsaved_knobs = {}
        # self.knob_scroll_positions = {}
        self.setWindowTitle("KnobScripter - %s %s" % (self.node.fullName(), self.knob))
        self.current_node_label_name.setText(self.node.fullName())

        self.to_load_knob = False
        self.updateKnobDropdown()  # onee
        self.to_load_knob = True

        self.setCurrentKnob(self.knob) # TODO: If a knob was previously open, open that one instead (load...)
        self.loadKnobValue(check=False)
        self.script_editor.setFocus()
        self.setKnobState()
        self.setKnobModified(False)
        self.current_knob_dropdown.blockSignals(False)
        return

    def exitNodeMode(self):
        self.nodeMode = False
        self.setWindowTitle("KnobScripter - Script Mode")
        self.node_mode_bar.setVisible(False)
        self.script_mode_bar.setVisible(True)
        self.setCodeLanguage("python")
        self.node = nuke.toNode("root")
        # self.updateFoldersDropdown()
        # self.updateScriptsDropdown()
        self.splitter.setSizes([1, 1])
        self.loadScriptState()
        self.setLastScript()
        self.loadScriptContents(check=False)
        self.setScriptState()

    def clearConsole(self):
        self.omit_se_console_text = string(self.nukeSEOutput.document().toPlainText())
        self.script_output.setPlainText("")

    def toggleFRW(self, frw_pressed):
        self.frw_open = frw_pressed
        self.frw.setVisible(self.frw_open)
        if self.frw_open:
            self.frw.find_lineEdit.setFocus()
            self.frw.find_lineEdit.selectAll()
        else:
            self.script_editor.setFocus()
        return

    def open_multipanel(self, tab="code_gallery", lang=None):
        """ Open the floating multipanel (although it can also be opened as pane) """
        if self.isPane:
            multipanel_parent = QtWidgets.QApplication.activeWindow()
        else:
            multipanel_parent = self._parent
        if nuke.ks_multipanel == "":
            nuke.ks_multipanel = MultiPanel(self, multipanel_parent, initial_tab=tab,
                                            lang=lang or self.script_editor.code_language)
        else:
            try:
                if lang:
                    nuke.ks_multipanel.set_lang(lang)
                nuke.ks_multipanel.set_tab(tab)
                nuke.ks_multipanel.set_knob_scripter(self)
            except:
                pass

        if not nuke.ks_multipanel.isVisible():
            nuke.ks_multipanel.reload()
            nuke.ks_multipanel.set_lang(lang or self.script_editor.code_language)

        nuke.ks_multipanel.activateWindow()

        if nuke.ks_multipanel.show():
            # Something else to do when clicking OK?
            content.all_snippets = snippets.load_snippets_dict()

            nuke.ks_multipanel = ""

    def message_box(self, the_text=""):
        """ Just a simple message box """
        if self.isPane:
            msg_box = QtWidgets.QMessageBox()
        else:
            msg_box = QtWidgets.QMessageBox(self)
        msg_box.setText(the_text)
        msg_box.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        msg_box.exec_()

    def loadPrefs(self):
        """ Load prefs """
        if not os.path.isfile(config.prefs_txt_path):
            return []
        else:
            with open(config.prefs_txt_path, "r") as f:
                preferences = json.load(f)
                return preferences

    def runScript(self):
        """ Run the current script... """
        self.script_editor.runScript()

    def closeEvent(self, close_event):
        if self.nodeMode:
            updated_count = self.updateUnsavedKnobs()
            self.saveKnobState()
            if updated_count > 0:
                msg_box = QtWidgets.QMessageBox()
                msg_box.setText(
                    "Save changes to %s knob%s before closing?" % (str(updated_count), int(updated_count > 1) * "s"))
                msg_box.setStandardButtons(
                    QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No | QtWidgets.QMessageBox.Cancel)
                msg_box.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
                msg_box.setDefaultButton(QtWidgets.QMessageBox.Yes)
                reply = msg_box.exec_()
                if reply == QtWidgets.QMessageBox.Yes:
                    self.saveAllKnobValues(check=False)
                    close_event.accept()
                    return
                elif reply == QtWidgets.QMessageBox.Cancel:
                    close_event.ignore()
                    return
            else:
                close_event.accept()
        else:
            self.saveScriptState()
            self.autosave()

        if self in config.all_knobscripters:
            config.all_knobscripters.remove(self)
        close_event.accept()

    # Landing functions
    def refreshClicked(self):
        """ Refresh the dropdowns. """
        if self.nodeMode:
            knob = str(self.current_knob_dropdown.currentData())
            self.current_knob_dropdown.blockSignals(True)
            self.current_knob_dropdown.clear()  # First remove all items
            self.updateKnobDropdown()
            available_knobs = []
            for i in range(self.current_knob_dropdown.count()):
                if self.current_knob_dropdown.itemData(i) is not None:
                    available_knobs.append(str(self.current_knob_dropdown.itemData(i)))
            if knob in available_knobs:
                self.setCurrentKnob(knob)
            self.current_knob_dropdown.blockSignals(False)
        else:
            folder = self.current_folder
            script = self.current_script
            self.autosave()
            self.updateFoldersDropdown()
            self.setCurrentFolder(folder)
            self.updateScriptsDropdown()
            self.setCurrentScript(script)
            self.script_editor.setFocus()

    def reloadClicked(self):
        if self.nodeMode:
            self.loadKnobValue()
        else:
            logging.debug("Node mode is off")
            self.loadScriptContents(check=True, py_only=True)

    def saveClicked(self):
        if self.nodeMode:
            self.saveKnobValue(False)
        else:
            self.saveScriptContents(temp=False)

    def setModified(self):
        if self.nodeMode:
            if not self.current_knob_modified:
                if self.getKnobValue(self.knob) != string(self.script_editor.toPlainText()):
                    self.setKnobModified(True)
        elif not self.current_script_modified:
            self.setScriptModified(True)
        if not self.nodeMode:
            self.toAutosave = True

    def setRunInContext(self, pressed):
        self.runInContext = pressed
        self.runInContextAct.setChecked(pressed)


class KnobScripterPane(KnobScripterWidget):
    def __init__(self):
        super(KnobScripterPane, self).__init__(is_pane=True, _parent=QtWidgets.QApplication.activeWindow())
        ctrl_s_shortcut = QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+S"), self)
        ctrl_s_shortcut.activatedAmbiguously.connect(self.saveClicked)

    def showEvent(self, the_event):
        try:
            utils.killPaneMargins(self)
        except:
            pass
        return KnobScripterWidget.showEvent(self, the_event)

    def hideEvent(self, the_event):
        self.autosave()
        return KnobScripterWidget.hideEvent(self, the_event)


def updateContext():
    """ Gets the current selection of nodes with their appropiate context.

    Doing this outside the KnobScripter -> forces context update inside groups when needed
    """
    nuke.knobScripterSelectedNodes = nuke.selectedNodes()
    return


# --------------------------------------
# Code Gallery + Snippets + Prefs panel
# --------------------------------------
class MultiPanel(QtWidgets.QDialog):
    def __init__(self, knob_scripter="", _parent=None, initial_tab="code_gallery", lang="python"):
        _parent = _parent or QtWidgets.QApplication.activeWindow()
        super(MultiPanel, self).__init__(_parent)

        # TODO future (really, future): enable drag and drop of snippet and gallery into the knobscripter??
        # TODO add on knobscripter button to Reload Style and Snippets

        self.knob_scripter = knob_scripter
        self.setWindowTitle("KnobScripter Multi-Panel")
        self.resize(600, 400)
        self.lang = lang

        self.initUI()
        self.set_tab(initial_tab)
        self.set_lang(self.lang)

    def initUI(self):
        master_layout = QtWidgets.QVBoxLayout()

        # Main TabWidget
        self.tab_widget = QtWidgets.QTabWidget()

        self.code_gallery = codegallery.CodeGalleryWidget(self.knob_scripter, None)
        self.snippet_editor = snippets.SnippetsWidget(self.knob_scripter, None)
        self.ks_prefs = prefs.PrefsWidget(self.knob_scripter, None)

        self.tab_widget.addTab(self.code_gallery, "Code Gallery")
        self.tab_widget.addTab(self.snippet_editor, "Snippet Editor")
        self.tab_widget.addTab(self.ks_prefs, "Preferences")

        tab_style = '''QTabBar { }
                   QTabBar::tab:!selected {font-weight:bold; height: 30px; width:125px;}
                   QTabBar::tab:selected {font-weight:bold; height: 30px; width:125px;}'''
        self.tab_widget.setStyleSheet(tab_style)

        master_layout.addWidget(self.tab_widget)
        self.setLayout(master_layout)

    def set_knob_scripter(self, knob_scripter=None):
        self.code_gallery.knob_scripter = knob_scripter
        self.snippet_editor.knob_scripter = knob_scripter
        self.ks_prefs.knobScripter = knob_scripter
        self.knob_scripter = knob_scripter

    def set_tab(self, tab):
        if tab == "code_gallery":
            self.tab_widget.setCurrentWidget(self.code_gallery)
        elif tab == "snippet_editor":
            self.tab_widget.setCurrentWidget(self.snippet_editor)
        elif tab == "ks_prefs":
            self.tab_widget.setCurrentWidget(self.ks_prefs)

    def set_lang(self, lang="python"):
        self.lang = lang
        self.code_gallery.change_lang(lang)
        self.snippet_editor.change_lang(lang)
        # TODO Add prefs when they have some sort of customization per language

    def reload(self):
        self.snippet_editor.reload()
        self.code_gallery.reload()
        self.ks_prefs.refresh_prefs()


# --------------------------------
# Implementation
# --------------------------------

def showKnobScripter(knob=""):
    selection = nuke.selectedNodes()
    if not len(selection):
        pan = KnobScripterWidget(_parent=QtWidgets.QApplication.activeWindow())
    else:
        pan = KnobScripterWidget(selection[0], knob, _parent=QtWidgets.QApplication.activeWindow())
    pan.show()


def addKnobScripterPane():
    try:
        nuke.knobScripterPane = panels.registerWidgetAsPanel('nuke.KnobScripterPane', 'Knob Scripter',
                                                             'com.adrianpueyo.KnobScripterPane')
        nuke.knobScripterPane.addToPane(nuke.getPaneFor('Properties.1'))

    except:
        nuke.knobScripterPane = panels.registerWidgetAsPanel('nuke.KnobScripterPane', 'Knob Scripter',
                                                             'com.adrianpueyo.KnobScripterPane')


nuke.KnobScripterPane = KnobScripterPane
logging.debug("KS LOADED")
ksShortcut = "alt+z"
addKnobScripterPane()
nuke.menu('Nuke').addCommand('Edit/Node/Open Floating Knob Scripter', showKnobScripter, ksShortcut)
nuke.menu('Nuke').addCommand('Edit/Node/Update KnobScripter Context', updateContext).setVisible(False)

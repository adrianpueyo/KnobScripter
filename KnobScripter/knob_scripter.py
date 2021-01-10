'''
KnobScripterWidget 3 by Adrian Pueyo - Complete python script editor for Nuke
adrianpueyo.com, 2016-2020
'''

import os
import json
from nukescripts import panels
import nuke
import re
import subprocess
import platform
from webbrowser import open as open_url
import logging

# Symlinks on windows...
if os.name == "nt":
    def symlink_ms(source, link_name):
        import ctypes
        csl = ctypes.windll.kernel32.CreateSymbolicLinkW
        csl.argtypes = (ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint32)
        csl.restype = ctypes.c_ubyte
        flags = 1 if os.path.isdir(source) else 0
        try:
            if csl(link_name, source.replace('/', '\\'), flags) == 0:
                raise ctypes.WinError()
        except:
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
nuke.AllKnobScripters = []  # All open instances at a given time
PrefsPanel = ""
SnippetEditPanel = ""
CodeGalleryPanel = ""

"""
nuke.KnobScripterPrefs = {
    "python_color_style" : "sublime",
    "blink_color_style" : "default",
}
"""

# ks imports
from info import __version__, __date__
import config
from kspanels import snippets
from kspanels.codegallery import CodeGalleryWidget
from kspanels.prefs import KnobScripterPrefs
from kspanels.dialogs import FileNameDialog, ChooseNodeDialog
from scripteditor.ksscripteditormain import KSScriptEditorMain
from scripteditor.findreplace import FindReplaceWidget
from scripteditor import blinkhighlighter
from scripteditor import pythonhighlighter
from script_output import ScriptOutputWidget
from utils import killPaneMargins, findSE, findSEInput, findSEConsole, findSERunBtn, setSEConsoleChanged

logging.basicConfig(level=logging.DEBUG)


# TODO: Move the next things (all the initializations) into a different script! leave this one just for the knob_scripter widget etc. All global vars etc go elsewhere. In a way that a KS widget is not needed in order to have the font setup etc, like in the preferences panel and snippets etc
nuke.tprint(
    'KnobScripter v{}, built {}.\nCopyright (c) 2016-2020 Adrian Pueyo. All Rights Reserved.'.format(__version__, __date__))
logging.debug('Initializing KnobScripter')

# Init config.script_editor_font (will be overwritten once reading the prefs)
config.script_editor_font = QtGui.QFont()
config.script_editor_font.setFamily(config.prefs["se_font_family"])
config.script_editor_font.setStyleHint(QtGui.QFont.Monospace)
config.script_editor_font.setFixedPitch(True)
config.script_editor_font.setPointSize(config.prefs["se_font_size"])

def loadPrefs():
    ''' Load prefs json file '''
    path = config.prefs_txt_path
    if not os.path.isfile(path):
        return []
    else:
        with open(path, "r") as f:
            prefs = json.load(f)
            return prefs

loaded_prefs = loadPrefs()
for pref in loaded_prefs:
    config.prefs[pref] = loaded_prefs[pref]

# TODO ctrl + +/- for live-changing the font size just for the current script editor????? nice
# TODO Different snippets for python and blink etc. With the lang selector.

def is_blink_knob(knob):
    ''' Return True if knob is Blink type '''
    node = knob.node()
    kn = knob.name()
    if kn in ["kernelSource"] and node.Class() in ["BlinkScript"]:
        return True
    else:
        return False


class KnobScripterWidget(QtWidgets.QDialog):

    def __init__(self, node="", knob="", isPane=False, _parent=QtWidgets.QApplication.activeWindow()):
        super(KnobScripterWidget, self).__init__(_parent)

        #TODO remove
        import kspanels.codegallery
        reload(kspanels.codegallery)

        global CodeGallery
        CodeGallery = kspanels.codegallery.CodeGalleryWidget

        # Autosave the other knobscripters and add this one
        for ks in nuke.AllKnobScripters:
            try:
                ks.autosave()
            except:
                pass
        if self not in nuke.AllKnobScripters:
            nuke.AllKnobScripters.append(self)

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
        self.isPane = isPane
        self.show_labels = False  # For the option to also display the knob labels on the knob dropdown
        self.unsavedKnobs = {}
        self.modifiedKnobs = set()
        self.scrollPos = {}
        self.cursorPos = {}
        self.font_size = config.prefs["se_font_size"] #Can potentially be changed at runtime per ks instance
        self.toLoadKnob = True
        self.frw_open = False  # Find replace widget closed by default
        self.icon_size = 17
        self.btn_size = 24
        self.qt_icon_size = QtCore.QSize(self.icon_size, self.icon_size)
        self.qt_btn_size = QtCore.QSize(self.btn_size, self.btn_size)
        self.omit_se_console_text = ""
        self.nukeSE = findSE()
        self.nukeSEOutput = findSEConsole(self.nukeSE)
        self.nukeSEInput = findSEInput(self.nukeSE)
        self.nukeSERunBtn = findSERunBtn(self.nukeSE)

        self.current_folder = "scripts"
        self.folder_index = 0
        self.current_script = "Untitled.py"
        self.current_script_modified = False
        self.script_index = 0
        self.toAutosave = False
        self.runInContext = False  # Experimental, python only
        self.code_language = None
        self.current_knob_modified = False  # Convenience variable holding if the current script_editor is modified

        self.defaultKnobs = ["knobChanged", "onCreate", "onScriptLoad", "onScriptSave", "onScriptClose", "onDestroy",
                             "updateUI", "autolabel", "beforeRender", "beforeFrameRender", "afterFrameRender",
                             "afterRender"]
        self.python_knob_classes = ["PyScript_Knob", "PythonCustomKnob"]

        # Load prefs
        # TODO THIS SHOULD JUST RELOAD THEM? OR ACTIVATE THE GLOBAL LOADPREFS
        # self.loadedPrefs = self.loadPrefs()

        # Load snippets
        self.snippets = snippets.loadAllSnippets(max_depth=5)

        # Init UI
        self.initUI()
        setSEConsoleChanged()
        self.omit_se_console_text = self.nukeSEOutput.document().toPlainText()
        self.clearConsole()

    def initUI(self):
        ''' Initializes the tool UI'''
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
        self.change_btn = QtWidgets.QToolButton()
        # self.exit_node_btn.setIcon(QtGui.QIcon(KS_DIR+"/KnobScripter/icons/icons8-delete-26.png"))
        self.change_btn.setIcon(QtGui.QIcon(icons_path + "icon_pick.png"))
        self.change_btn.setIconSize(self.qt_icon_size)
        self.change_btn.setFixedSize(self.qt_btn_size)
        self.change_btn.setToolTip("Change to node if selected. Otherwise, change to Script Mode.")
        self.change_btn.clicked.connect(self.changeClicked)

        # ---
        # 2.2.A. Node mode UI
        self.exit_node_btn = QtWidgets.QToolButton()
        self.exit_node_btn.setIcon(QtGui.QIcon(icons_path + "icon_exitnode.png"))
        self.exit_node_btn.setIconSize(self.qt_icon_size)
        self.exit_node_btn.setFixedSize(self.qt_btn_size)
        self.exit_node_btn.setToolTip("Exit the node, and change to Script Mode.")
        self.exit_node_btn.clicked.connect(self.exitNodeMode)
        self.current_node_label_node = QtWidgets.QLabel(" Node:")
        self.current_node_label_name = QtWidgets.QLabel(self.node.fullName())
        self.current_node_label_name.setStyleSheet("font-weight:bold;")
        self.current_knob_label = QtWidgets.QLabel("Knob: ")
        self.current_knob_dropdown = QtWidgets.QComboBox()
        self.current_knob_dropdown.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)
        self.updateKnobDropdown()
        self.current_knob_dropdown.currentIndexChanged.connect(lambda: self.loadKnobValue(False, updateDict=True))

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
        # self.current_folder_dropdown.setEditable(True)
        # self.current_folder_dropdown.lineEdit().setReadOnly(True)
        # self.current_folder_dropdown.lineEdit().setAlignment(Qt.AlignRight)

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
        self.refresh_btn = QtWidgets.QToolButton()
        self.refresh_btn.setIcon(QtGui.QIcon(icons_path + "icon_refresh.png"))
        self.refresh_btn.setIconSize(QtCore.QSize(50, 50))
        self.refresh_btn.setIconSize(self.qt_icon_size)
        self.refresh_btn.setFixedSize(self.qt_btn_size)
        self.refresh_btn.setToolTip("Refresh the dropdowns.\nShortcut: F5")
        self.refresh_btn.setShortcut('F5')
        self.refresh_btn.clicked.connect(self.refreshClicked)

        # Reload script
        self.reload_btn = QtWidgets.QToolButton()
        self.reload_btn.setIcon(QtGui.QIcon(icons_path + "icon_download.png"))
        self.reload_btn.setIconSize(QtCore.QSize(50, 50))
        self.reload_btn.setIconSize(self.qt_icon_size)
        self.reload_btn.setFixedSize(self.qt_btn_size)
        self.reload_btn.setToolTip(
            "Reload the current script. Will overwrite any changes made to it.\nShortcut: Ctrl+R")
        self.reload_btn.setShortcut('Ctrl+R')
        self.reload_btn.clicked.connect(self.reloadClicked)

        # Save script
        self.save_btn = QtWidgets.QToolButton()
        self.save_btn.setIcon(QtGui.QIcon(icons_path + "icon_save.png"))
        self.save_btn.setIconSize(QtCore.QSize(50, 50))
        self.save_btn.setIconSize(self.qt_icon_size)
        self.save_btn.setFixedSize(self.qt_btn_size)

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
        self.run_script_button = QtWidgets.QToolButton()
        self.run_script_button.setIcon(QtGui.QIcon(icons_path + "icon_run.png"))
        # self.run_script_button.setIcon(QtGui.QIcon(icons_path+"icon_enter.png"))
        self.run_script_button.setIconSize(self.qt_icon_size)
        self.run_script_button.setFixedSize(self.qt_btn_size)
        self.run_script_button.setToolTip(
            "Execute the current selection on the KnobScripter, or the whole script if no selection.\nShortcut: Ctrl+Enter")
        self.run_script_button.clicked.connect(self.runScript)

        # Python: Clear console
        self.clear_console_button = QtWidgets.QToolButton()
        self.clear_console_button.setIcon(QtGui.QIcon(icons_path + "icon_clearConsole.png"))
        self.clear_console_button.setIconSize(QtCore.QSize(50, 50))
        self.clear_console_button.setIconSize(self.qt_icon_size)
        self.clear_console_button.setFixedSize(self.qt_btn_size)
        self.clear_console_button.setToolTip(
            "Clear the text in the console window.\nShortcut: Ctrl+Backspace, or click+Backspace on the console.")
        self.clear_console_button.setShortcut('Ctrl+Backspace')
        self.clear_console_button.clicked.connect(self.clearConsole)

        # Blink: Save & Compile
        self.save_recompile_button = QtWidgets.QToolButton()
        self.save_recompile_button.setIcon(QtGui.QIcon(icons_path + "icon_play.png"))
        self.save_recompile_button.setIconSize(self.qt_icon_size)
        self.save_recompile_button.setFixedSize(self.qt_btn_size)
        self.save_recompile_button.setToolTip(
            "Save the blink code and recompile the Blinkscript node.\nShortcut: Ctrl+Enter")
        self.save_recompile_button.clicked.connect(self.blinkSaveRecompile)

        # Blink: Backups
        self.createBlinkBackupsMenu()
        self.backup_button = QtWidgets.QPushButton()
        self.backup_button.setIcon(QtGui.QIcon(icons_path + "icon_backups.png"))
        self.backup_button.setIconSize(self.qt_icon_size)
        self.backup_button.setFixedSize(self.qt_btn_size)
        self.backup_button.setToolTip("Enable and retrieve auto-saves of the code")
        self.backup_button.setMenu(self.blinkBackupMenu)
        # self.backup_button.setFixedSize(QtCore.QSize(self.btn_size+10,self.btn_size))
        self.backup_button.setStyleSheet("text-align:left;padding-left:2px;")
        # self.backup_button.clicked.connect(self.blinkBackup) #TODO: whatever this does

        # FindReplace button
        self.find_button = QtWidgets.QToolButton()
        self.find_button.setIcon(QtGui.QIcon(icons_path + "icon_search.png"))
        self.find_button.setIconSize(self.qt_icon_size)
        self.find_button.setFixedSize(self.qt_btn_size)
        self.find_button.setToolTip("Call the snippets by writing the shortcut and pressing Tab.\nShortcut: Ctrl+F")
        self.find_button.setShortcut('Ctrl+F')
        # self.find_button.setMaximumWidth(self.find_button.fontMetrics().boundingRect("Find").width() + 20)
        self.find_button.setCheckable(True)
        self.find_button.setFocusPolicy(QtCore.Qt.NoFocus)
        self.find_button.clicked[bool].connect(self.toggleFRW)
        if self.frw_open:
            self.find_button.toggle()

        # Gallery
        self.codegallery_button = QtWidgets.QToolButton()
        self.codegallery_button.setIcon(QtGui.QIcon(icons_path + "icon_enter.png"))
        self.codegallery_button.setIconSize(QtCore.QSize(50, 50))
        self.codegallery_button.setIconSize(self.qt_icon_size)
        self.codegallery_button.setFixedSize(self.qt_btn_size)
        self.codegallery_button.setToolTip("Open the code gallery panel.")
        self.codegallery_button.clicked.connect(self.openCodeGallery)

        # Snippets
        self.snippets_button = QtWidgets.QToolButton()
        self.snippets_button.setIcon(QtGui.QIcon(icons_path + "icon_snippets.png"))
        self.snippets_button.setIconSize(QtCore.QSize(50, 50))
        self.snippets_button.setIconSize(self.qt_icon_size)
        self.snippets_button.setFixedSize(self.qt_btn_size)
        self.snippets_button.setToolTip("Call the snippets by writing the shortcut and pressing Tab.")
        self.snippets_button.clicked.connect(self.openSnippets)

        # Prefs
        self.createPrefsMenu()
        self.prefs_button = QtWidgets.QPushButton()
        self.prefs_button.setIcon(QtGui.QIcon(icons_path + "icon_prefs.png"))
        self.prefs_button.setIconSize(self.qt_icon_size)
        self.prefs_button.setFixedSize(QtCore.QSize(self.btn_size + 10, self.btn_size))
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
        ##self.top_right_bar_layout.addWidget(self.snippets_button)
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
        self.script_output = ScriptOutputWidget(parent=self)
        self.script_output.setReadOnly(1)
        self.script_output.setAcceptRichText(0)
        if config.prefs["se_tab_spaces"] != 0:
            self.script_output.setTabStopWidth(self.script_output.tabStopWidth() / 4)
        self.script_output.setFocusPolicy(Qt.ClickFocus)
        self.script_output.setAutoFillBackground(0)
        self.script_output.installEventFilter(self)

        # Script Editor
        self.script_editor = KSScriptEditorMain(self, self.script_output)
        self.script_editor.setMinimumHeight(30)
        self.script_editor.setStyleSheet('background:#282828;color:#EEE;')  # Main Colors
        self.script_editor.textChanged.connect(self.setModified)
        self.highlighter = pythonhighlighter.KSPythonHighlighter(self.script_editor.document())
        self.highlighter.setStyle(config.prefs["code_style_python"])
        self.script_editor.cursorPositionChanged.connect(self.setTextSelection)

        self.script_editor.setFont(config.script_editor_font)

        if config.prefs["se_tab_spaces"] != 0:
            self.script_editor.setTabStopWidth(config.prefs["se_tab_spaces"] * QtGui.QFontMetrics(config.script_editor_font).width(' '))

        # Add input and output to splitter
        self.splitter.addWidget(self.script_output)
        self.splitter.addWidget(self.script_editor)
        self.splitter.setStretchFactor(0, 0)

        # FindReplace widget
        self.frw = FindReplaceWidget(self.script_editor, self)
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
        ##self.master_layout.addLayout(self.bottom_layout)
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
            self.setCurrentKnob(self.knob)
            self.loadKnobValue(check=False)
            self.setKnobModified(False)
            self.current_knob_dropdown.blockSignals(False)
            self.splitter.setSizes([0, 1])
        else:
            self.setCodeLanguage("python")
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
                                                 statusTip="When inside a node, run the code replacing nuke.thisNode() to the node's name, etc.",
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
                                             triggered=self.openSnippets)
        self.snippetsAct.setIcon(QtGui.QIcon(icons_path + "icon_snippets.png"))
        self.prefsAct = QtWidgets.QAction("Preferences", self, statusTip="Open the Preferences panel.",
                                          triggered=self.openPrefs)
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
        ''' Initializes the echo chechable QAction based on nuke's state '''
        echo_knob = nuke.toNode("preferences").knob("echoAllCommands")
        self.echoAct.setChecked(echo_knob.value())

    def toggleEcho(self):
        ''' Toggle the "Echo python commands" from Nuke '''
        echo_knob = nuke.toNode("preferences").knob("echoAllCommands")
        echo_knob.setValue(self.echoAct.isChecked())

    def toggleRunInContext(self):
        ''' Toggle preference to replace everything needed so that code can be run in proper context of the node and knob that's selected.'''
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

        # (..)Click on button = save current state? or better just open menu
        # [] Auto-save .blink scratch file <- toggle on/off <- if .blink is set-up, it saves it there. otherwise it saves it on the knobscripter blink temp path (.nuke/KnobScripter_Scripts/autosave.blink)
        # Create .blink scratch file <- should be bold, and visible only when there's no .blink scratch file added on the Blinkscript kernel
        # [] Load .blink contents
        # [] Save .blink contents
        # ---
        # [] Open (in sublime or whatever)
        # Version-up blink

        # Actions
        self.blinkBackups_autoSave_act = QtWidgets.QAction("Auto-save to disk on compile", self, checkable=True,
                                                           statusTip="Auto-save code backup on disk every time you save it",
                                                           triggered=self.toggleBlinkBackupsAutosave)
        self.blinkBackups_createFile_act = QtWidgets.QAction("Create .blink scratch file", self,
                                                             statusTip="Auto-save code backup on disk every time you save it",
                                                             triggered=self.blinkCreateFile)
        self.blinkBackups_load_act = QtWidgets.QAction("Load .blink", self, statusTip="Load the .blink code.",
                                                       triggered=self.toggleBlinkBackupsAutosave)
        self.blinkBackups_save_act = QtWidgets.QAction("Save .blink", self, statusTip="Save the .blink code.",
                                                       triggered=self.toggleBlinkBackupsAutosave)

        font = self.blinkBackups_createFile_act.font()
        font.setBold(True)
        self.blinkBackups_createFile_act.setFont(font)
        self.blinkBackups_createFile_act.setEnabled(False)

        # if nuke.toNode("preferences").knob("echoAllCommands").value():
        #    self.echoAct.toggle()
        # self.runInContextAct = QtWidgets.QAction("Run in context (beta)", self, checkable=True, statusTip="When inside a node, run the code replacing nuke.thisNode() to the node's name, etc.", triggered=self.toggleRunInContext)
        # self.runInContextAct.setChecked(self.runInContext)
        # self.helpAct = QtWidgets.QAction("&Help", self, statusTip="Open the KnobScripter help in your browser.", shortcut="F1", triggered=self.showHelp)
        # self.nukepediaAct = QtWidgets.QAction("Show in Nukepedia", self, statusTip="Open the KnobScripter download page on Nukepedia.", triggered=self.showInNukepedia)
        # self.githubAct = QtWidgets.QAction("Show in GitHub", self, statusTip="Open the KnobScripter repo on GitHub.", triggered=self.showInGithub)
        # self.snippetsAct = QtWidgets.QAction("Snippets", self, statusTip="Open the Snippets editor.", triggered=self.openSnippets)
        # self.snippetsAct.setIcon(QtGui.QIcon(icons_path+"icon_snippets.png"))
        # self.prefsAct = QtWidgets.QAction("Preferences", self, statusTip="Open the Preferences panel.", triggered=self.openPrefs)
        # self.prefsAct.setIcon(QtGui.QIcon(icons_path+"icon_prefs.png"))

        # Menus
        self.blinkBackupMenu = QtWidgets.QMenu("Blink Backups")
        self.blinkBackupMenu.addAction(self.blinkBackups_autoSave_act)
        self.blinkBackupMenu.addSeparator()
        self.blinkBackupMenu.addAction(
            self.blinkBackups_createFile_act)  # This should be visible when no blink file only
        # TODO Show the blink name here when found
        self.blinkBackupMenu.addAction(self.blinkBackups_load_act)
        self.blinkBackupMenu.addAction(self.blinkBackups_save_act)
        # TODO: Checkbox autosave should be enabled or disabled by default based on preferences...
        # TODO: the actions should do something! inc. regex

    # Node Mode
    def updateKnobDropdown(self):
        ''' Populate knob dropdown list '''
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

                if i in self.unsavedKnobs.keys():
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
                if i in self.unsavedKnobs.keys():
                    self.current_knob_dropdown.addItem(i + "(*)", i)
                else:
                    self.current_knob_dropdown.addItem(i, i)
                counter += 1
        return

    def loadKnobValue(self, check=True, updateDict=False):
        ''' Get the content of the knob value and populate the editor '''
        if self.toLoadKnob == False:
            return
        dropdown_value = self.current_knob_dropdown.itemData(
            self.current_knob_dropdown.currentIndex())  # knobChanged...
        knob_language = self.knobLanguage(self.node, dropdown_value)
        try:
            # If blinkscript, use getValue.
            if knob_language == "blink":
                obtained_knobValue = str(self.node[dropdown_value].getValue())
            elif knob_language == "python":
                obtained_knobValue = str(self.node[dropdown_value].value())
            else:  # knob language is None -> try to get the expression for tcl???
                return
            obtained_scrollValue = 0
            edited_knobValue = self.script_editor.toPlainText()
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
        if updateDict == True:
            self.unsavedKnobs[self.knob] = edited_knobValue
            self.scrollPos[self.knob] = self.script_editor.verticalScrollBar().value()
        prev_knob = self.knob  # knobChanged...

        self.knob = self.current_knob_dropdown.itemData(self.current_knob_dropdown.currentIndex())  # knobChanged...

        if check and obtained_knobValue != edited_knobValue:
            msgBox = QtWidgets.QMessageBox()
            msgBox.setText("The Script Editor has been modified.")
            msgBox.setInformativeText("Do you want to overwrite the current code on this editor?")
            msgBox.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
            msgBox.setIcon(QtWidgets.QMessageBox.Question)
            msgBox.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
            msgBox.setDefaultButton(QtWidgets.QMessageBox.Yes)
            reply = msgBox.exec_()
            if reply == QtWidgets.QMessageBox.No:
                self.setCurrentKnob(prev_knob)
                return
        # If order comes from a dropdown update, update value from dictionary if possible, otherwise update normally
        self.setWindowTitle("KnobScripter - %s %s" % (self.node.name(), self.knob))
        self.script_editor.blockSignals(True)
        if updateDict:
            if self.knob in self.unsavedKnobs:
                if self.unsavedKnobs[self.knob] == obtained_knobValue:
                    self.script_editor.setPlainText(obtained_knobValue)
                    self.setKnobModified(False)
                else:
                    obtained_knobValue = self.unsavedKnobs[self.knob]
                    self.script_editor.setPlainText(obtained_knobValue)
                    self.setKnobModified(True)
            else:
                self.script_editor.setPlainText(obtained_knobValue)
                self.setKnobModified(False)

            if self.knob in self.scrollPos:
                obtained_scrollValue = self.scrollPos[self.knob]
        else:
            self.script_editor.setPlainText(obtained_knobValue)

        cursor = self.script_editor.textCursor()
        self.script_editor.setTextCursor(cursor)
        self.script_editor.verticalScrollBar().setValue(obtained_scrollValue)
        self.setCodeLanguage(knob_language)
        self.script_editor.blockSignals(False)
        return

    def loadAllKnobValues(self):
        ''' Load all knobs button's function '''
        if len(self.unsavedKnobs) >= 1:
            msgBox = QtWidgets.QMessageBox()
            msgBox.setText("Do you want to reload all python and callback knobs?")
            msgBox.setInformativeText("Unsaved changes on this editor will be lost.")
            msgBox.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
            msgBox.setIcon(QtWidgets.QMessageBox.Question)
            msgBox.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
            msgBox.setDefaultButton(QtWidgets.QMessageBox.Yes)
            reply = msgBox.exec_()
            if reply == QtWidgets.QMessageBox.No:
                return
        self.unsavedKnobs = {}
        return

    def saveKnobValue(self, check=True):
        ''' Save the text from the editor to the node's knobChanged knob '''
        dropdown_value = self.current_knob_dropdown.itemData(self.current_knob_dropdown.currentIndex())
        try:
            obtained_knobValue = self.getKnobValue(dropdown_value)
            # If blinkscript, use getValue.
            # if dropdown_value == "kernelSource" and self.node.Class()=="BlinkScript":
            #    obtained_knobValue = str(self.node[dropdown_value].getValue()) 
            # else:
            #    obtained_knobValue = str(self.node[dropdown_value].value())
            self.knob = dropdown_value
        except:
            error_message = QtWidgets.QMessageBox.information(None, "", "Unable to find %s.%s" % (
                self.node.name(), dropdown_value))
            error_message.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
            error_message.exec_()
            return
        edited_knobValue = self.script_editor.toPlainText()
        if check and obtained_knobValue != edited_knobValue:
            msgBox = QtWidgets.QMessageBox()
            msgBox.setText("Do you want to overwrite %s.%s?" % (self.node.name(), dropdown_value))
            msgBox.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
            msgBox.setIcon(QtWidgets.QMessageBox.Question)
            msgBox.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
            msgBox.setDefaultButton(QtWidgets.QMessageBox.Yes)
            reply = msgBox.exec_()
            if reply == QtWidgets.QMessageBox.No:
                return
        # Save the value if it's Blinkscript code
        if dropdown_value == "kernelSource" and self.node.Class() == "BlinkScript":
            nuke.tcl('''knob {}.kernelSource "{}"'''.format(self.node.fullName(),
                                                            edited_knobValue.replace('"', '\\"').encode("utf8")))
        else:
            self.node[dropdown_value].setValue(edited_knobValue.encode("utf8"))
        self.setKnobModified(modified=False, knob=dropdown_value, changeTitle=True)
        nuke.tcl("modified 1")
        if self.knob in self.unsavedKnobs:
            del self.unsavedKnobs[self.knob]
        return

    def saveAllKnobValues(self, check=True):
        ''' Save all knobs button's function '''
        if self.updateUnsavedKnobs() > 0 and check:
            msgBox = QtWidgets.QMessageBox()
            msgBox.setText("Do you want to save all modified python and callback knobs?")
            msgBox.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
            msgBox.setIcon(QtWidgets.QMessageBox.Question)
            msgBox.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
            msgBox.setDefaultButton(QtWidgets.QMessageBox.Yes)
            reply = msgBox.exec_()
            if reply == QtWidgets.QMessageBox.No:
                return
        saveErrors = 0
        savedCount = 0
        for k in self.unsavedKnobs.copy():
            try:
                self.node.knob(k).setValue(self.unsavedKnobs[k])
                del self.unsavedKnobs[k]
                savedCount += 1
                nuke.tcl("modified 1")
            except:
                saveErrors += 1
        if saveErrors > 0:
            errorBox = QtWidgets.QMessageBox()
            errorBox.setText("Error saving %s knob%s." % (str(saveErrors), int(saveErrors > 1) * "s"))
            errorBox.setIcon(QtWidgets.QMessageBox.Warning)
            errorBox.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
            errorBox.setDefaultButton(QtWidgets.QMessageBox.Yes)
            reply = errorBox.exec_()
        else:
            logging.debug("KnobScripter: %s knobs saved" % str(savedCount))
        return

    def setCurrentKnob(self, knobToSet):
        ''' Set current knob '''
        KnobDropdownItems = []
        for i in range(self.current_knob_dropdown.count()):
            if self.current_knob_dropdown.itemData(i) is not None:
                KnobDropdownItems.append(self.current_knob_dropdown.itemData(i))
            else:
                KnobDropdownItems.append("---")
        if knobToSet in KnobDropdownItems:
            index = KnobDropdownItems.index(knobToSet)
            self.current_knob_dropdown.setCurrentIndex(index)
            return True
        return False

    def updateUnsavedKnobs(self, first_time=False):
        ''' Clear unchanged knobs from the dict and return the number of unsaved knobs '''
        if not self.node:
            # Node has been deleted, so simply return 0. Who cares.
            return 0

        edited_knobValue = self.script_editor.toPlainText()
        self.unsavedKnobs[self.knob] = edited_knobValue

        if len(self.unsavedKnobs) > 0:
            for k in self.unsavedKnobs.copy():
                if self.node.knob(k):
                    if str(self.getKnobValue(k)) == str(self.unsavedKnobs[k]):
                        del self.unsavedKnobs[k]
                else:
                    del self.unsavedKnobs[k]
        # Set appropriate knobs modified...
        knobs_dropdown = self.current_knob_dropdown
        all_knobs = [knobs_dropdown.itemData(i) for i in range(knobs_dropdown.count())]
        all_knobs = list(filter(None, all_knobs))
        for key in all_knobs:
            if key in self.unsavedKnobs.keys():
                self.setKnobModified(modified=True, knob=key, changeTitle=False)
            else:
                self.setKnobModified(modified=False, knob=key, changeTitle=False)

        return len(self.unsavedKnobs)

    def getKnobValue(self, knob=""):
        '''
        Returns the relevant value of the knob:
            For python knobs, uses value
            For blinkscript, getValue
            For others, gets the expression
        '''
        if knob == "":
            knob = self.knob
        if knob == "kernelSource" and self.node.Class() == "BlinkScript":
            return self.node[knob].getValue()
        else:
            return self.node[knob].value()
            # TODO: Return expression otherwise

    def setKnobModified(self, modified=True, knob="", changeTitle=True):
        ''' Sets the current knob modified, title and whatever else we need '''
        if knob == "":
            knob = self.knob
        if modified:
            self.modifiedKnobs.add(knob)
        else:
            self.modifiedKnobs.discard(knob)

        if changeTitle:
            title_modified_string = " [modified]"
            windowTitle = self.windowTitle().split(title_modified_string)[0]
            if modified == True:
                windowTitle += title_modified_string
            self.current_knob_modified = modified
            self.setWindowTitle(windowTitle)

        try:
            knobs_dropdown = self.current_knob_dropdown
            kd_index = knobs_dropdown.currentIndex()
            kd_data = knobs_dropdown.itemData(kd_index)
            if self.show_labels and kd_data not in self.defaultKnobs:
                if kd_data == "kernelSource" and self.node.Class() == "BlinkScript":
                    kd_data = "Blinkscript Code (kernelSource)"
                else:
                    kd_data = "{} ({})".format(self.node.knob(kd_data).label(), kd_data)
            if modified == False:
                knobs_dropdown.setItemText(kd_index, kd_data)
            else:
                knobs_dropdown.setItemText(kd_index, kd_data + "(*)")
        except:
            pass

    def knobLanguage(self, node, knobName="knobChanged"):
        ''' Given a node and a knob name, guesses the appropriate code language '''
        if knobName not in node.knobs():
            return None
        if knobName == "kernelSource" and node.Class() == "BlinkScript":
            return "blink"
        elif knobName in self.defaultKnobs or node.knob(knobName).Class() in self.python_knob_classes:
            return "python"
        else:
            return None

    def setCodeLanguage(self, code_language="python"):
        '''
        Perform all UI changes neccesary for editing a different language! Syntax highlighter, menu buttons, etc.
        '''

        # 1. Allow for string or int, 0 being "no language", 1 "python", 2 "blink"
        code_language_list = [None, "python", "blink"]
        if code_language == None:
            new_code_language = code_language
        elif isinstance(code_language, str) and code_language.lower() in code_language_list:
            new_code_language = code_language.lower()
        elif isinstance(code_language, int) and code_language_list[code_language]:
            new_code_language = code_language_list[code_language]
        else:
            return False

        # 2. Syntax highlighter
        if new_code_language != self.code_language:
            self.highlighter.setDocument(None)
            if code_language == "blink":
                self.highlighter = blinkhighlighter.KSBlinkHighlighter(self.script_editor.document())
                self.highlighter.setStyle(config.prefs["code_style_blink"])
                self.script_editor.setColorStyle("blink_default")
            else:
                self.highlighter = pythonhighlighter.KSPythonHighlighter(self.script_editor.document())
                self.highlighter.setStyle(config.prefs["code_style_python"])
                self.script_editor.setColorStyle("default")

        self.code_language = new_code_language

        # 3. Menus
        self.run_script_button.setVisible(code_language != "blink")
        self.clear_console_button.setVisible(code_language != "blink")
        self.save_recompile_button.setVisible(code_language == "blink")
        self.backup_button.setVisible(code_language == "blink")

    def blinkSaveRecompile(self):
        '''
        If blink mode is on, tries to save the blink code in the node (and performs a backup) and executes the Recompile button.
        '''
        if self.code_language != "blink":
            return False

        # TODO perform backup first!! backupBlink function or something...
        self.saveKnobValue(check=False)
        try:
            self.node.knob("recompile").execute()
        except:
            print("Error recompiling the Blinkscript node.")

    def toggleBlinkBackupsAutosave(self):
        ''' TODO Figure out the best behavior for this '''
        autosave_selection = self.blinkBackups_autoSave_act.isChecked()  # TODO Finish this and put it on the prefs too...
        return

    def blinkCreateFile(self):
        '''
        Make a .blink file and populate the Blinkscript file knob.
        Name for the file is chosen through a floating panel that by default tries to guess the kernel name (+ 1st available integer) or a hash-
        '''
        # 1. Guess a good name via regex etc (except if SaturationKernel)

        # 2. Open panel asking for name+location
        # 3. make the file
        # 4. populate the knob on the node

    # Script Mode
    def updateFoldersDropdown(self):
        ''' Populate folders dropdown list '''
        self.current_folder_dropdown.blockSignals(True)
        self.current_folder_dropdown.clear()  # First remove all items
        defaultFolders = ["scripts"]
        scriptFolders = []
        counter = 0
        for f in defaultFolders:
            self.makeScriptFolder(f)
            self.current_folder_dropdown.addItem(f + "/", f)
            counter += 1

        try:
            scriptFolders = sorted([f for f in os.listdir(config.scripts_dir) if
                                    os.path.isdir(os.path.join(config.scripts_dir, f))])  # Accepts symlinks!!!
        except:
            logging.debug("Couldn't read any script folders.")

        for f in scriptFolders:
            fname = f.split("/")[-1]
            if fname in defaultFolders:
                continue
            self.current_folder_dropdown.addItem(fname + "/", fname)
            counter += 1

        # print scriptFolders
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
        ''' Populate py scripts dropdown list '''
        self.current_script_dropdown.blockSignals(True)
        self.current_script_dropdown.clear()  # First remove all items
        QtWidgets.QApplication.processEvents()
        logging.debug("# Updating scripts dropdown...")
        logging.debug("scripts dir:" + config.scripts_dir)
        logging.debug("current folder:" + self.current_folder)
        logging.debug("previous current script:" + self.current_script)
        # current_folder = self.current_folder_dropdown.itemData(self.current_folder_dropdown.currentIndex())
        current_folder_path = os.path.join(config.scripts_dir, self.current_folder)
        defaultScripts = ["Untitled.py"]
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
            for s in defaultScripts:
                if s + ".autosave" in found_temp_scripts:
                    self.current_script_dropdown.addItem(s + "(*)", s)
                else:
                    self.current_script_dropdown.addItem(s, s)
                counter += 1
        else:
            for s in defaultScripts:
                if s + ".autosave" in found_temp_scripts:
                    self.current_script_dropdown.addItem(s + "(*)", s)
                elif s in found_scripts:
                    self.current_script_dropdown.addItem(s, s)
            for s in found_scripts:
                if s in defaultScripts:
                    continue
                sname = s.split("/")[-1]
                if s + ".autosave" in found_temp_scripts:
                    self.current_script_dropdown.addItem(sname + "(*)", sname)
                else:
                    self.current_script_dropdown.addItem(sname, sname)
                counter += 1
        ##else: #Add the found scripts to the dropdown
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

    def makeScriptFolder(self, name="scripts"):
        folder_path = os.path.join(config.scripts_dir, name)
        if not os.path.exists(folder_path):
            try:
                os.makedirs(folder_path)
                return True
            except:
                print("Couldn't create the scripting folders.\nPlease check your OS write permissions.")
                return False

    def makeScriptFile(self, name="Untitled.py", folder="scripts", empty=True):
        script_path = os.path.join(config.scripts_dir, self.current_folder, name)
        if not os.path.isfile(script_path):
            try:
                self.current_script_file = open(script_path, 'w')
                return True
            except:
                print("Couldn't create the scripting folders.\nPlease check your OS write permissions.")
                return False

    def setCurrentFolder(self, folderName):
        ''' Set current folder ON THE DROPDOWN ONLY'''
        folderList = [self.current_folder_dropdown.itemData(i) for i in range(self.current_folder_dropdown.count())]
        if folderName in folderList:
            index = folderList.index(folderName)
            self.current_folder_dropdown.setCurrentIndex(index)
            self.current_folder = folderName
        self.folder_index = self.current_folder_dropdown.currentIndex()
        self.current_folder = self.current_folder_dropdown.itemData(self.folder_index)
        return

    def setCurrentScript(self, scriptName):
        ''' Set current script ON THE DROPDOWN ONLY '''
        scriptList = [self.current_script_dropdown.itemData(i) for i in range(self.current_script_dropdown.count())]
        if scriptName in scriptList:
            index = scriptList.index(scriptName)
            self.current_script_dropdown.setCurrentIndex(index)
            self.current_script = scriptName
        self.script_index = self.current_script_dropdown.currentIndex()
        self.current_script = self.current_script_dropdown.itemData(self.script_index)
        return

    def loadScriptContents(self, check=False, pyOnly=False, folder=""):
        ''' Get the contents of the selected script and populate the editor '''
        logging.debug("# About to load script contents now.")
        obtained_scrollValue = 0
        obtained_cursorPosValue = [0, 0]  # Position, anchor
        if folder == "":
            folder = self.current_folder
        script_path = os.path.join(config.scripts_dir, folder, self.current_script)
        script_path_temp = script_path + ".autosave"
        if (self.current_folder + "/" + self.current_script) in self.scrollPos:
            obtained_scrollValue = self.scrollPos[self.current_folder + "/" + self.current_script]
        if (self.current_folder + "/" + self.current_script) in self.cursorPos:
            obtained_cursorPosValue = self.cursorPos[self.current_folder + "/" + self.current_script]

        # 1: If autosave exists and pyOnly is false, load it
        if os.path.isfile(script_path_temp) and not pyOnly:
            logging.debug("Loading .py.autosave file\n---")
            with open(script_path_temp, 'r') as script:
                content = script.read()
            self.script_editor.setPlainText(content)
            self.setScriptModified(True)
            self.script_editor.verticalScrollBar().setValue(obtained_scrollValue)

        # 2: Try to load the .py as first priority, if it exists
        elif os.path.isfile(script_path):
            logging.debug("Loading .py file\n---")
            with open(script_path, 'r') as script:
                content = script.read()
            current_text = self.script_editor.toPlainText()
            if check and current_text != content and current_text.strip() != "":
                msgBox = QtWidgets.QMessageBox()
                msgBox.setText("The script has been modified.")
                msgBox.setInformativeText("Do you want to overwrite the current code on this editor?")
                msgBox.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
                msgBox.setIcon(QtWidgets.QMessageBox.Question)
                msgBox.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
                msgBox.setDefaultButton(QtWidgets.QMessageBox.Yes)
                reply = msgBox.exec_()
                if reply == QtWidgets.QMessageBox.No:
                    return
            # Clear trash
            if os.path.isfile(script_path_temp):
                os.remove(script_path_temp)
                logging.debug("Removed " + script_path_temp)
            self.setScriptModified(False)
            self.script_editor.setPlainText(content)
            self.script_editor.verticalScrollBar().setValue(obtained_scrollValue)
            self.setScriptModified(False)
            self.loadScriptState()
            self.setScriptState()

        # 3: If .py doesn't exist... only then stick to the autosave
        elif os.path.isfile(script_path_temp):
            with open(script_path_temp, 'r') as script:
                content = script.read()

            msgBox = QtWidgets.QMessageBox()
            msgBox.setText("The .py file hasn't been found.")
            msgBox.setInformativeText("Do you want to clear the current code on this editor?")
            msgBox.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
            msgBox.setIcon(QtWidgets.QMessageBox.Question)
            msgBox.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
            msgBox.setDefaultButton(QtWidgets.QMessageBox.Yes)
            reply = msgBox.exec_()
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
            content = ""
            self.script_editor.setPlainText(content)
            self.setScriptModified(False)
            if self.current_folder + "/" + self.current_script in self.scrollPos:
                del self.scrollPos[self.current_folder + "/" + self.current_script]
            if self.current_folder + "/" + self.current_script in self.cursorPos:
                del self.cursorPos[self.current_folder + "/" + self.current_script]

        self.setWindowTitle("KnobScripter - %s/%s" % (self.current_folder, self.current_script))
        return

    def saveScriptContents(self, temp=True):
        ''' Save the current contents of the editor into the python file. If temp == True, saves a .py.autosave file '''
        logging.debug("\n# About to save script contents now.")
        logging.debug("Temp mode is: " + str(temp))
        logging.debug("self.current_folder: " + self.current_folder)
        logging.debug("self.current_script: " + self.current_script)
        script_path = os.path.join(config.scripts_dir, self.current_folder, self.current_script)
        script_path_temp = script_path + ".autosave"
        orig_content = ""
        content = self.script_editor.toPlainText()

        if temp == True:
            if os.path.isfile(script_path):
                with open(script_path, 'r') as script:
                    orig_content = script.read()
            elif content == "" and os.path.isfile(
                    script_path_temp):  # If script path doesn't exist and autosave does but the script is empty...
                os.remove(script_path_temp)
                return
            if content != orig_content:
                with open(script_path_temp, 'w') as script:
                    script.write(content)
            else:
                if os.path.isfile(script_path_temp):
                    os.remove(script_path_temp)
                logging.debug("Nothing to save")
                return
        else:
            with open(script_path, 'w') as script:
                script.write(str(self.script_editor.toPlainText()))
            # Clear trash
            if os.path.isfile(script_path_temp):
                os.remove(script_path_temp)
                logging.debug("Removed " + script_path_temp)
            self.setScriptModified(False)
        self.saveScrollValue()
        self.saveCursorPosValue()
        logging.debug("Saved " + script_path + "\n---")
        return

    def deleteScript(self, check=True, folder=""):
        ''' Get the contents of the selected script and populate the editor '''
        logging.debug("# About to delete the .py and/or autosave script now.")
        if folder == "":
            folder = self.current_folder
        script_path = os.path.join(config.scripts_dir, folder, self.current_script)
        script_path_temp = script_path + ".autosave"
        if check:
            msgBox = QtWidgets.QMessageBox()
            msgBox.setText("You're about to delete this script.")
            msgBox.setInformativeText("Are you sure you want to delete {}?".format(self.current_script))
            msgBox.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
            msgBox.setIcon(QtWidgets.QMessageBox.Question)
            msgBox.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
            msgBox.setDefaultButton(QtWidgets.QMessageBox.No)
            reply = msgBox.exec_()
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
        '''Executed when the current folder dropdown is changed'''
        self.saveScriptState()
        logging.debug("# folder dropdown changed")
        folders_dropdown = self.current_folder_dropdown
        fd_value = folders_dropdown.currentText()
        fd_index = folders_dropdown.currentIndex()
        fd_data = folders_dropdown.itemData(fd_index)
        if fd_data == "create new":
            panel = FileNameDialog(self, mode="folder")
            # panel.setWidth(260)
            # panel.addSingleLineInput("Name:","")
            if panel.exec_():
                # Accepted
                folder_name = panel.text
                if os.path.isdir(os.path.join(config.scripts_dir, folder_name)):
                    self.messageBox("Folder already exists.")
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
                    self.messageBox("There was a problem creating the folder.")
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
            current_folder_path = os.path.join(config.scripts_dir, self.current_folder)
            self.openInFileBrowser(current_folder_path)
            self.current_folder_dropdown.blockSignals(True)
            self.current_folder_dropdown.setCurrentIndex(self.folder_index)
            self.current_folder_dropdown.blockSignals(False)
            return

        elif fd_data == "add custom path":
            folder_path = nuke.getFilename('Select custom folder.')
            if folder_path is not None:
                if folder_path.endswith("/"):
                    aliasName = folder_path.split("/")[-2]
                else:
                    aliasName = folder_path.split("/")[-1]
                if not os.path.isdir(folder_path):
                    self.messageBox("Folder not found. Please try again with the full path to a folder.")
                elif not len(aliasName):
                    self.messageBox("Folder with the same name already exists. Please delete or rename it first.")
                else:
                    # All good
                    os.symlink(folder_path, os.path.join(config.scripts_dir, aliasName))
                    self.saveScriptContents(temp=True)
                    self.current_folder = aliasName
                    self.updateFoldersDropdown()
                    self.setCurrentFolder(aliasName)
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
            self.script_editor.setFocus()

            self.loadScriptState()
            self.setScriptState()

        return

    def scriptDropdownChanged(self):
        '''Executed when the current script dropdown is changed. Should only be called by the manual dropdown change. Not by other functions.'''
        self.saveScriptState()
        scripts_dropdown = self.current_script_dropdown
        sd_value = scripts_dropdown.currentText()
        sd_index = scripts_dropdown.currentIndex()
        sd_data = scripts_dropdown.itemData(sd_index)
        if sd_data == "create new":
            self.current_script_dropdown.blockSignals(True)
            panel = FileNameDialog(self, mode="script")
            if panel.exec_():
                # Accepted
                script_name = panel.text + ".py"
                script_path = os.path.join(config.scripts_dir, self.current_folder, script_name)
                logging.debug(script_name)
                logging.debug(script_path)
                if os.path.isfile(script_path):
                    self.messageBox("Script already exists.")
                    self.current_script_dropdown.setCurrentIndex(self.script_index)
                if self.makeScriptFile(name=script_name, folder=self.current_folder):
                    # Success creating the folder
                    self.saveScriptContents(temp=True)
                    self.updateScriptsDropdown()
                    if self.current_script != "Untitled.py":
                        self.script_editor.setPlainText("")
                    self.current_script = script_name
                    self.setCurrentScript(script_name)
                    self.saveScriptContents(temp=False)
                    # self.loadScriptContents()
                else:
                    self.messageBox("There was a problem creating the script.")
                    self.current_script_dropdown.setCurrentIndex(self.script_index)
            else:
                # Canceled/rejected
                self.current_script_dropdown.setCurrentIndex(self.script_index)
                return
            self.current_script_dropdown.blockSignals(False)

        elif sd_data == "create duplicate":
            self.current_script_dropdown.blockSignals(True)
            current_folder_path = os.path.join(config.scripts_dir, self.current_folder, self.current_script)
            current_script_path = os.path.join(config.scripts_dir, self.current_folder, self.current_script)

            current_name = self.current_script
            if self.current_script.endswith(".py"):
                current_name = current_name[:-3]

            test_name = current_name
            while True:
                test_name += "_copy"
                new_script_path = os.path.join(config.scripts_dir, self.current_folder, test_name + ".py")
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
                self.messageBox("There was a problem duplicating the script.")
                self.current_script_dropdown.setCurrentIndex(self.script_index)

            self.current_script_dropdown.blockSignals(False)

        elif sd_data == "open in browser":
            current_script_path = os.path.join(config.scripts_dir, self.current_folder, self.current_script)
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
        ''' Sets self.current_script_modified, title and whatever else we need '''
        self.current_script_modified = modified
        title_modified_string = " [modified]"
        windowTitle = self.windowTitle().split(title_modified_string)[0]
        if modified == True:
            windowTitle += title_modified_string
        self.setWindowTitle(windowTitle)
        try:
            scripts_dropdown = self.current_script_dropdown
            sd_index = scripts_dropdown.currentIndex()
            sd_data = scripts_dropdown.itemData(sd_index)
            if modified == False:
                scripts_dropdown.setItemText(sd_index, sd_data)
            else:
                scripts_dropdown.setItemText(sd_index, sd_data + "(*)")
        except:
            pass

    def openInFileBrowser(self, path=""):
        OS = platform.system()
        if not os.path.exists(path):
            path = KS_DIR
        if OS == "Windows":
            os.startfile(path)
        elif OS == "Darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])

    def loadScriptState(self):
        '''
        Loads the last state of the script from a file inside the SE directory's root.
        SAVES self.scroll_pos, self.cursor_pos, self.last_open_script
        '''
        self.state_dict = {}
        if not os.path.isfile(config.state_txt_path):
            return False
        else:
            with open(config.state_txt_path, "r") as f:
                self.state_dict = json.load(f)

        logging.debug("Loading script state into self.state_dict, self.scrollPos, self.cursorPos")
        logging.debug(self.state_dict)

        if "scroll_pos" in self.state_dict:
            self.scrollPos = self.state_dict["scroll_pos"]
        if "cursor_pos" in self.state_dict:
            self.cursorPos = self.state_dict["cursor_pos"]

    def setScriptState(self):
        '''
        Sets the already script state from self.state_dict into the current script if applicable
        '''
        script_fullname = self.current_folder + "/" + self.current_script

        if "scroll_pos" in self.state_dict:
            if script_fullname in self.state_dict["scroll_pos"]:
                self.script_editor.verticalScrollBar().setValue(int(self.state_dict["scroll_pos"][script_fullname]))

        if "cursor_pos" in self.state_dict:
            if script_fullname in self.state_dict["cursor_pos"]:
                cursor = self.script_editor.textCursor()
                cursor.setPosition(int(self.state_dict["cursor_pos"][script_fullname][1]), QtGui.QTextCursor.MoveAnchor)
                cursor.setPosition(int(self.state_dict["cursor_pos"][script_fullname][0]), QtGui.QTextCursor.KeepAnchor)
                self.script_editor.setTextCursor(cursor)

        if 'splitter_sizes' in self.state_dict:
            self.splitter.setSizes(self.state_dict['splitter_sizes'])

    def setLastScript(self):
        if 'last_folder' in self.state_dict and 'last_script' in self.state_dict:
            self.updateFoldersDropdown()
            self.setCurrentFolder(self.state_dict['last_folder'])
            self.updateScriptsDropdown()
            self.setCurrentScript(self.state_dict['last_script'])
            self.loadScriptContents()
            self.script_editor.setFocus()

    def saveScriptState(self):
        ''' Stores the current state of the script into a file inside the SE directory's root '''
        logging.debug("About to save script state...")
        '''
        # self.state_dict = {}
        if os.path.isfile(config.state_txt_path):
            with open(config.state_txt_path, "r") as f:
                self.state_dict = json.load(f)

        if "scroll_pos" in self.state_dict:
            self.scrollPos = self.state_dict["scroll_pos"]
        if "cursor_pos" in self.state_dict:
            self.cursorPos = self.state_dict["cursor_pos"]

        '''
        self.loadScriptState()

        # Overwrite current values into the scriptState
        self.saveScrollValue()
        self.saveCursorPosValue()

        self.state_dict['scroll_pos'] = self.scrollPos
        self.state_dict['cursor_pos'] = self.cursorPos
        self.state_dict['last_folder'] = self.current_folder
        self.state_dict['last_script'] = self.current_script
        self.state_dict['splitter_sizes'] = self.splitter.sizes()

        with open(config.state_txt_path, "w") as f:
            state = json.dump(self.state_dict, f, sort_keys=True, indent=4)
        return state

    # Autosave background loop
    def autosave(self):
        if self.toAutosave:
            # Save the script...
            self.saveScriptContents()
            self.toAutosave = False
            self.saveScriptState()
            logging.debug("autosaving...")
            return

    # Global stuff
    def setTextSelection(self):
        self.highlighter.selected_text = self.script_editor.textCursor().selection().toPlainText()
        return

    def resizeEvent(self, res_event):
        w = self.frameGeometry().width()
        self.current_node_label_node.setVisible(w > 460)
        self.script_label.setVisible(w > 460)
        return super(KnobScripterWidget, self).resizeEvent(res_event)

    def changeClicked(self, newNode=""):
        ''' Change node '''
        try:
            print("Changing from " + self.node.name())
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
                updatedCount = self.updateUnsavedKnobs()
            else:
                updatedCount = 0
        else:
            updatedCount = 0
            self.autosave()
        if newNode and newNode != "" and nuke.exists(newNode):
            selection = [newNode]
        elif not len(selection):
            node_dialog = ChooseNodeDialog(self)
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
            self.messageBox("Please select a different node first!")
            return
        elif updatedCount > 0:
            msgBox = QtWidgets.QMessageBox()
            msgBox.setText(
                "Save changes to %s knob%s before changing the node?" % (
                    str(updatedCount), int(updatedCount > 1) * "s"))
            msgBox.setStandardButtons(
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No | QtWidgets.QMessageBox.Cancel)
            msgBox.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
            msgBox.setDefaultButton(QtWidgets.QMessageBox.Yes)
            reply = msgBox.exec_()
            if reply == QtWidgets.QMessageBox.Yes:
                self.saveAllKnobValues(check=False)
            elif reply == QtWidgets.QMessageBox.Cancel:
                return
        if len(selection) > 1:
            self.messageBox("More than one node selected.\nChanging knobChanged editor to %s" % selection[0].fullName())
        # Reinitialise everything, wooo!
        self.current_knob_dropdown.blockSignals(True)
        self.node = selection[0]
        self.nodeMode = True

        # TODO: try to save/retrieve from memory what was the last knob opened, scroll etc? Can save it in some root knob too if needed. Sort of a list/json.

        if "kernelSource" in self.node.knobs() and self.node.Class() == "BlinkScript":
            self.knob = "kernelSource"
        else:
            self.knob = "knobChanged"

        self.script_editor.setPlainText("")
        self.unsavedKnobs = {}
        self.scrollPos = {}
        self.setWindowTitle("KnobScripter - %s %s" % (self.node.fullName(), self.knob))
        self.current_node_label_name.setText(self.node.fullName())

        self.toLoadKnob = False
        self.updateKnobDropdown()  # onee
        self.toLoadKnob = True
        self.setCurrentKnob(self.knob)
        self.loadKnobValue(False)
        self.script_editor.setFocus()
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
        self.omit_se_console_text = self.nukeSEOutput.document().toPlainText()
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

    def openSnippets(self):
        ''' Whenever the 'snippets' button is pressed... open the panel '''
        global SnippetEditPanel
        if SnippetEditPanel == "":
            SnippetEditPanel = snippets.SnippetsPanel(self, self._parent)

        if not SnippetEditPanel.isVisible():
            SnippetEditPanel.reload()

        if SnippetEditPanel.show():
            self.snippets = self.loadAllSnippets(max_depth=5)
            SnippetEditPanel = ""

    def openCodeGallery(self):
        ''' Open the floating code gallery panel (although it'll also be able to be opened as pane) '''
        global CodeGalleryPanel
        if CodeGalleryPanel == "":
            CodeGalleryPanel = GalleryAndSnippets(self, self._parent)
        else:
            CodeGalleryPanel.setKnobScripter(self)

        # if not CodeGalleryPanel.isVisible():
        #    CodeGalleryPanel.reload()

        if CodeGalleryPanel.show():
            # Something else to do when clicking OK?
            CodeGalleryPanel = ""

    def messageBox(self, the_text=""):
        ''' Just a simple message box '''
        if self.isPane:
            msgBox = QtWidgets.QMessageBox()
        else:
            msgBox = QtWidgets.QMessageBox(self)
        msgBox.setText(the_text)
        msgBox.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        msgBox.exec_()

    def openPrefs(self):
        ''' Open the preferences panel '''
        global PrefsPanel
        if PrefsPanel == "":
            PrefsPanel = KnobScripterPrefs(self, self._parent)
        else:
            try:
                PrefsPanel.knobScripter = self
            except:
                pass

        if PrefsPanel.show():
            PrefsPanel = ""

    def loadPrefs(self):
        ''' Load prefs '''
        if not os.path.isfile(config.prefs_txt_path):
            return []
        else:
            with open(config.prefs_txt_path, "r") as f:
                prefs = json.load(f)
                return prefs

    def runScript(self):
        ''' Run the current script... '''
        self.script_editor.runScript()

    def saveScrollValue(self):
        ''' Save scroll values '''
        if self.nodeMode:
            self.scrollPos[self.knob] = self.script_editor.verticalScrollBar().value()
        else:
            self.scrollPos[
                self.current_folder + "/" + self.current_script] = self.script_editor.verticalScrollBar().value()

    def saveCursorPosValue(self):
        ''' Save cursor pos and anchor values '''
        self.cursorPos[self.current_folder + "/" + self.current_script] = [self.script_editor.textCursor().position(),
                                                                           self.script_editor.textCursor().anchor()]

    def closeEvent(self, close_event):
        if self.nodeMode:
            updatedCount = self.updateUnsavedKnobs()
            if updatedCount > 0:
                msgBox = QtWidgets.QMessageBox()
                msgBox.setText(
                    "Save changes to %s knob%s before closing?" % (str(updatedCount), int(updatedCount > 1) * "s"))
                msgBox.setStandardButtons(
                    QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No | QtWidgets.QMessageBox.Cancel)
                msgBox.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
                msgBox.setDefaultButton(QtWidgets.QMessageBox.Yes)
                reply = msgBox.exec_()
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
            self.autosave()
            if self in nuke.AllKnobScripters:
                nuke.AllKnobScripters.remove(self)
            close_event.accept()

    # Landing functions
    def refreshClicked(self):
        ''' Function to refresh the dropdowns '''
        if self.nodeMode:
            knob = self.current_knob_dropdown.itemData(str(self.current_knob_dropdown.currentIndex()).encode('UTF8'))
            self.current_knob_dropdown.blockSignals(True)
            self.current_knob_dropdown.clear()  # First remove all items
            self.updateKnobDropdown()
            availableKnobs = []
            for i in range(self.current_knob_dropdown.count()):
                if self.current_knob_dropdown.itemData(i) is not None:
                    availableKnobs.append(str(self.current_knob_dropdown.itemData(i).encode('UTF8')))
            if knob in availableKnobs:
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
            self.loadScriptContents(check=True, pyOnly=True)

    def saveClicked(self):
        if self.nodeMode:
            self.saveKnobValue(False)
        else:
            self.saveScriptContents(temp=False)

    def setModified(self):
        if self.nodeMode:
            if not self.current_knob_modified:
                if self.getKnobValue(self.knob) != self.script_editor.toPlainText():
                    self.setKnobModified(True)
        elif not self.current_script_modified:
            self.setScriptModified(True)
        if not self.nodeMode:
            self.toAutosave = True

    def setRunInContext(self, pressed):
        self.runInContext = pressed
        self.runInContextAct.setChecked(pressed)

class KnobScripterPane(KnobScripterWidget):
    def __init__(self, node="", knob="knobChanged"):
        super(KnobScripterPane, self).__init__(isPane=True, _parent=QtWidgets.QApplication.activeWindow())
        ctrlS_shortcut = QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+S"), self)
        ctrlS_shortcut.activatedAmbiguously.connect(self.saveClicked)

    def showEvent(self, the_event):
        try:
            killPaneMargins(self)
        except:
            pass
        return KnobScripterWidget.showEvent(self, the_event)

    def hideEvent(self, the_event):
        self.autosave()
        return KnobScripterWidget.hideEvent(self, the_event)

def updateContext():
    ''' 
    Get the current selection of nodes with their appropiate context
    Doing this outside the KnobScripter -> forces context update inside groups when needed
    '''
    nuke.knobScripterSelectedNodes = nuke.selectedNodes()
    return

# --------------------------------------
# Code Gallery + Snippets super panel
# --------------------------------------
class GalleryAndSnippets(QtWidgets.QDialog):  # TODO Rename to multipanel
    def __init__(self, knobScripter="", _parent=QtWidgets.QApplication.activeWindow()):
        super(GalleryAndSnippets, self).__init__(_parent)

        # TODO future (for now current method works, this is only for when this is a Pane) Find a way to connect this to a KnobScripter!!! Or open the panel as part of the KnobScripter itself??????? Showing the tabs+widgets on the right
        # TODO future (really, future): enable drag and drop of snippet and gallery into the knobscripter??
        # TODO add on knobscripter button to Reload Style and Snippets

        self.knobScripter = knobScripter
        self.setWindowTitle("Code Gallery + Snippet Editor")

        self.initUI()
        # self.resize(500,300)

    def initUI(self):
        master_layout = QtWidgets.QVBoxLayout()

        '''

        # 1. First Area (Mode and language)

        # 1.1. Mode! Code Gallery VS Snippet Editor
        self.modeCodeGallery_button = QtWidgets.QPushButton("Code Gallery") #TODO set margin 0 or spacing, set pressed etc. and maybe no need for buttongroup
        self.modeSnippets_button = QtWidgets.QPushButton("Snippet Editor")

        modeLanguage_layout = QtWidgets.QHBoxLayout()
        #modeLanguage_layout.addWidget(self.modeCodeGallery_button)
        #modeLanguage_layout.addWidget(self.modeSnippets_button)
        modeLanguage_layout.addStretch()

        #modeGroupBox.setLayout(modeLanguage_layout)

        # 1.2. Code language
        codeLanguage_label = QtWidgets.QLabel("Language:")
        self.languagePython_button = QtWidgets.QRadioButton("Python")
        self.languageBlink_button = QtWidgets.QRadioButton("Blink")
        #self.languageTCL_button = QtWidgets.QRadioButton("TCL") #Snippets and code that will work on TCL language
        #self.languageAll_button = QtWidgets.QRadioButton("All") #Snippets and code that will work on TCL language
        #TODO Compatible with expressions and TCL knobs too!!
        
        langButtonGroup = QtWidgets.QButtonGroup(self)
        langButtonGroup.addButton(self.languagePython_button)
        langButtonGroup.addButton(self.languageBlink_button)
        langButtonGroup.buttonClicked.connect(self.printLangBtnGroup)

        modeLanguage_layout.addWidget(codeLanguage_label)
        modeLanguage_layout.addWidget(self.languagePython_button)
        modeLanguage_layout.addWidget(self.languageBlink_button)
        modeLanguage_layout.addStretch()

        self.reload_button = QtWidgets.QPushButton("Reload")
        modeLanguage_layout.addWidget(self.reload_button)

        modeLanguage_groupBox = QtWidgets.QGroupBox()
        modeLanguage_groupBox.setLayout(modeLanguage_layout)
        '''

        # Main TabWidget
        tabWidget = QtWidgets.QTabWidget()

        self.code_gallery = CodeGallery(self.knobScripter, None)
        self.snippet_editor = snippets.SnippetsPanel(self.knobScripter,
                                            None)  # TODO The widget (not panel mode) shouldn't have the OK button etc. Only apply... OK doesn't really make sense in this context, right? or it can be below everything? or simply the OK button closes the full panel (parent) too and thats it
        self.ks_prefs = KnobScripterPrefs(self.knobScripter, None)
        # TODO ADD PREFERENCES IN A THIRD TAB!!!!!!

        tabWidget.addTab(self.code_gallery, "Code Gallery")
        tabWidget.addTab(self.snippet_editor, "Snippet Editor")
        tabWidget.addTab(self.ks_prefs, "Preferences")

        tabStyle = '''QTabBar { }
                   QTabBar::tab:!selected {font-weight:bold; height: 30px; width:150px;}
                   QTabBar::tab:selected {font-weight:bold; height: 30px; width:150px;}'''
        tabWidget.setStyleSheet(tabStyle)

        master_layout.addWidget(tabWidget)
        self.setLayout(master_layout)

    def setKnobScripter(self, knobScripter = None):
        self.code_gallery.knobScripter = knobScripter
        self.snippet_editor.knob_scripter = knobScripter
        self.ks_prefs.knobScripter = knobScripter
        self.knobScripter = knobScripter


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

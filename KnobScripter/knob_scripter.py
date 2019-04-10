#-------------------------------------------------
# Knob Scripter by Adrian Pueyo
# Script editor for python and callback knobs
# adrianpueyo.com, 2017-2018
version = "1.3BETA"
#-------------------------------------------------

import nuke
import os
import json
from nukescripts import panels
import sys
import nuke
import re
import traceback, string
from functools import partial

try:
    from PySide import QtCore, QtGui, QtGui as QtWidgets
    from PySide.QtCore import Qt
except ImportError:
    from PySide2 import QtWidgets, QtGui, QtCore
    from PySide2.QtCore import Qt

KS_DIR = os.path.dirname(__file__)
icons_path = KS_DIR+"/icons/"


class KnobScripter(QtWidgets.QWidget):

    def __init__(self, node="", knob="knobChanged"):
        super(KnobScripter,self).__init__()
        self.nodeMode = (node != "")
        if node == "":
            self.node = nuke.toNode("root")
        else:
            self.node = node
        self.knob = knob
        self.unsavedKnobs = {}
        self.scrollPos = {}
        self.fontSize = 11
        self.tabSpaces = 4
        self.windowDefaultSize = [500, 300]
        self.pinned = 1
        self.toLoadKnob = True
        self.frw_open = False # Find replace widget closed by default
        self.icon_size = 17
        self.btn_size = 24
        self.qt_icon_size = QtCore.QSize(self.icon_size,self.icon_size)
        self.qt_btn_size = QtCore.QSize(self.btn_size,self.btn_size)
        self.origConsoleText = ""
        self.nukeSE = self.findSE()
        self.nukeSEOutput = self.findSEOutput(self.nukeSE)
        self.nukeSEInput = self.findSEInput(self.nukeSE)
        self.nukeSERunBtn = self.findSERunBtn(self.nukeSE)

        self.scripts_dir = os.path.expandvars(os.path.expanduser("~/.nuke/KnobScripter_Scripts"))
        self.current_folder = "scripts"
        self.folder_index = 0
        self.current_script = "Untitled.py"
        self.current_script_modified = False
        self.script_index = 0


        # Load prefs
        self.prefs_txt = os.path.expandvars(os.path.expanduser("~/.nuke/KnobScripter_prefs_"+version+".txt"))
        self.loadedPrefs = self.loadPrefs()
        if self.loadedPrefs != []:
            try:
                self.fontSize = self.loadedPrefs['font_size']
                self.windowDefaultSize = [self.loadedPrefs['window_default_w'], self.loadedPrefs['window_default_h']]
                self.tabSpaces = self.loadedPrefs['tab_spaces']
                self.pinned = self.loadedPrefs['pin_default']
            except TypeError:
                print("KnobScripter: Failed to load preferences.")

        # Load snippets
        self.snippets_txt_path = os.path.expandvars(os.path.expanduser("~/.nuke/apSnippets.txt"))
        self.snippets = self.loadSnippets()

        # Init UI
        self.initUI()

        # Talk to Nuke's Script Editor
        self.setSEOutputEvent() # Make the output windowS listen!

    def initUI(self): 
        ''' Initializes the tool UI'''
        #-------------------
        # 1. MAIN WINDOW
        #-------------------
        self.resize(self.windowDefaultSize[0],self.windowDefaultSize[1])
        self.setWindowTitle("KnobScripter - %s %s" % (self.node.fullName(),self.knob))
        self.setObjectName( "com.adrianpueyo.knobscripter" )
        self.move(QtGui.QCursor().pos() - QtCore.QPoint(32,74))

        #---------------------
        # 2. TOP BAR
        #---------------------

        # ---
        # 2.1. Left buttons
        self.change_btn = QtWidgets.QToolButton()
        #self.exit_node_btn.setIcon(QtGui.QIcon(KS_DIR+"/KnobScripter/icons/icons8-delete-26.png"))
        self.change_btn.setIcon(QtGui.QIcon(icons_path+"icon_pick.png"))
        self.change_btn.setIconSize(self.qt_icon_size)
        self.change_btn.setFixedSize(self.qt_btn_size)
        self.change_btn.setToolTip("Change to node if selected. Otherwise, change to Script Mode.")
        self.change_btn.clicked.connect(self.changeClicked)

        # ---
        # 2.2.A. Node mode UI
        self.exit_node_btn = QtWidgets.QToolButton()
        self.exit_node_btn.setIcon(QtGui.QIcon(icons_path+"icon_exitnode.png"))
        self.exit_node_btn.setIconSize(self.qt_icon_size)
        self.exit_node_btn.setFixedSize(self.qt_btn_size)
        self.exit_node_btn.setToolTip("Exit the node, and change to Script Mode.")
        self.exit_node_btn.clicked.connect(self.exitNodeMode)
        self.current_node_label_node = QtWidgets.QLabel(" Node:")
        self.current_node_label_name = QtWidgets.QLabel(self.node.fullName()) #TODO: This will accept click, to change the name of the node on a floating lineedit.
        self.current_node_label_name.setStyleSheet("font-weight:bold;")
        self.current_knob_label = QtWidgets.QLabel("Knob: ")
        self.current_knob_dropdown = QtWidgets.QComboBox()
        self.current_knob_dropdown.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)
        self.updateKnobDropdown()
        self.current_knob_dropdown.currentIndexChanged.connect(lambda: self.loadKnobValue(False,updateDict=True))

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

        self.node_mode_bar_layout.setContentsMargins(0,0,0,0)

        # ---
        # 2.2.B. Script mode UI
        self.script_label = QtWidgets.QLabel("Script: ")

        self.current_folder_dropdown = QtWidgets.QComboBox()
        self.current_folder_dropdown.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)
        self.current_folder_dropdown.currentIndexChanged.connect(self.folderDropdownChanged)
        #self.current_folder_dropdown.setEditable(True)
        #self.current_folder_dropdown.lineEdit().setReadOnly(True)
        #self.current_folder_dropdown.lineEdit().setAlignment(Qt.AlignRight)

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

        self.script_mode_bar_layout.setContentsMargins(0,0,0,0)

        # ---
        # 2.3. File-system buttons
        # Refresh dropdowns
        self.refresh_btn = QtWidgets.QToolButton()
        self.refresh_btn.setIcon(QtGui.QIcon(icons_path+"icon_refresh.png"))
        self.refresh_btn.setIconSize(QtCore.QSize(50,50))
        self.refresh_btn.setIconSize(self.qt_icon_size)
        self.refresh_btn.setFixedSize(self.qt_btn_size)
        self.refresh_btn.setToolTip("Refresh the dropdowns.\nShortcut: F5")
        self.refresh_btn.setShortcut('F5')
        ##self.refresh_btn.clicked.connect(self.refreshClicked)

        # Reload script
        self.reload_btn = QtWidgets.QToolButton()
        self.reload_btn.setIcon(QtGui.QIcon(icons_path+"icon_download.png"))
        self.reload_btn.setIconSize(QtCore.QSize(50,50))
        self.reload_btn.setIconSize(self.qt_icon_size)
        self.reload_btn.setFixedSize(self.qt_btn_size)
        self.reload_btn.setToolTip("Reload the current script. Will overwrite any changes made to it.\nShortcut: Ctrl+R")
        self.reload_btn.setShortcut('Ctrl+R')
        self.reload_btn.clicked.connect(self.reloadClicked)

        # Save script
        self.save_btn = QtWidgets.QToolButton()
        self.save_btn.setIcon(QtGui.QIcon(icons_path+"icon_save.png"))
        self.save_btn.setIconSize(QtCore.QSize(50,50))
        self.save_btn.setIconSize(self.qt_icon_size)
        self.save_btn.setFixedSize(self.qt_btn_size)
        self.save_btn.setToolTip("Save the script into the selected knob or python file.\nShortcut: Ctrl+S")
        self.save_btn.setShortcut('Ctrl+S')
        self.save_btn.clicked.connect(self.saveClicked)

        # Layout
        self.top_file_bar_layout = QtWidgets.QHBoxLayout()
        self.top_file_bar_layout.addWidget(self.refresh_btn)
        self.top_file_bar_layout.addWidget(self.reload_btn)
        self.top_file_bar_layout.addWidget(self.save_btn)

        # ---
        # 2.4. Right Side buttons
        # Clear console
        self.clear_console_button = QtWidgets.QToolButton()
        self.clear_console_button.setIcon(QtGui.QIcon(icons_path+"icon_clearConsole.png"))
        self.clear_console_button.setIconSize(QtCore.QSize(50,50))
        self.clear_console_button.setIconSize(self.qt_icon_size)
        self.clear_console_button.setFixedSize(self.qt_btn_size)
        self.clear_console_button.setToolTip("Clear the text in the console window.\nShortcut: Right click on the console.")
        self.clear_console_button.clicked.connect(self.clearConsole)

        # FindReplace button
        self.find_button = QtWidgets.QToolButton()
        self.find_button.setIcon(QtGui.QIcon(icons_path+"icon_search.png"))
        self.find_button.setIconSize(self.qt_icon_size)
        self.find_button.setFixedSize(self.qt_btn_size)
        self.find_button.setToolTip("Call the snippets by writing the shortcut and pressing Tab.\nShortcut: Ctrl+F")
        self.find_button.setShortcut('Ctrl+F')
        #self.find_button.setMaximumWidth(self.find_button.fontMetrics().boundingRect("Find").width() + 20)
        self.find_button.setCheckable(True)
        self.find_button.setFocusPolicy(QtCore.Qt.NoFocus)
        self.find_button.clicked[bool].connect(self.toggleFRW)
        if self.frw_open:
            self.find_button.toggle()

        # Snippets
        self.snippets_button = QtWidgets.QToolButton()
        self.snippets_button.setIcon(QtGui.QIcon(icons_path+"icon_snippets.png"))
        self.snippets_button.setIconSize(QtCore.QSize(50,50))
        self.snippets_button.setIconSize(self.qt_icon_size)
        self.snippets_button.setFixedSize(self.qt_btn_size)
        self.snippets_button.setToolTip("Call the snippets by writing the shortcut and pressing Tab.")
        self.snippets_button.clicked.connect(self.openSnippets)

        # Prefs
        self.prefs_button = QtWidgets.QToolButton()
        self.prefs_button.setIcon(QtGui.QIcon(icons_path+"icon_prefs.png"))
        self.prefs_button.setIconSize(self.qt_icon_size)
        self.prefs_button.setFixedSize(self.qt_btn_size)
        self.prefs_button.clicked.connect(self.openPrefs)
        #self.prefs_button.setMaximumWidth(self.prefs_button.fontMetrics().boundingRect("Prefs").width() + 12)

        # Layout
        self.top_right_bar_layout = QtWidgets.QHBoxLayout()
        self.top_right_bar_layout.addWidget(self.clear_console_button)
        self.top_right_bar_layout.addWidget(self.find_button)
        self.top_right_bar_layout.addWidget(self.snippets_button)
        #self.top_right_bar_layout.addSpacing(10)
        self.top_right_bar_layout.addWidget(self.prefs_button)

        # ---
        # Layout
        self.top_layout = QtWidgets.QHBoxLayout()
        self.top_layout.setContentsMargins(0,0,0,0)
        #self.top_layout.setSpacing(10)
        self.top_layout.addWidget(self.change_btn)
        self.top_layout.addWidget(self.node_mode_bar)
        self.top_layout.addWidget(self.script_mode_bar)
        self.node_mode_bar.setVisible(False)
        #TODO: Add the script mode bar layout here too, then hide one of them
        #self.top_layout.addSpacing(10)
        self.top_layout.addLayout(self.top_file_bar_layout)
        self.top_layout.addStretch()
        self.top_layout.addLayout(self.top_right_bar_layout)


        #----------------------
        # 3. SCRIPTING SECTION
        #----------------------
        # Splitter
        self.splitter = QtWidgets.QSplitter(Qt.Vertical)

        # Output widget
        self.script_output = ScriptOutputWidget(parent=self)
        self.script_output.setReadOnly(1)
        self.script_output.setAcceptRichText(0)
        self.script_output.setTabStopWidth(self.script_output.tabStopWidth() / 4)
        self.script_output.setFocusPolicy(Qt.ClickFocus)
        self.script_output.setAutoFillBackground( 0 )
        self.script_output.installEventFilter(self)

        # Script Editor
        self.script_editor = KnobScripterTextEditMain(self, self.script_output)
        self.script_editor.setMinimumHeight(30)
        self.script_editor.setStyleSheet('background:#282828;color:#EEE;') # Main Colors
        KSScriptEditorHighlighter(self.script_editor.document())
        self.script_editor_font = QtGui.QFont()
        self.script_editor_font.setFamily("Courier")
        self.script_editor_font.setStyleHint(QtGui.QFont.Monospace)
        self.script_editor_font.setFixedPitch(True)
        self.script_editor_font.setPointSize(self.fontSize)
        self.script_editor.setFont(self.script_editor_font)
        self.script_editor.setTabStopWidth(self.tabSpaces * QtGui.QFontMetrics(self.script_editor_font).width(' '))

        # Add input and output to splitter
        self.splitter.addWidget(self.script_output)
        self.splitter.addWidget(self.script_editor)
        self.splitter.setStretchFactor(0,0)

        # FindReplace widget
        self.frw = FindReplaceWidget(self)
        self.frw.setVisible(self.frw_open)

        # ---
        # Layout
        self.scripting_layout = QtWidgets.QVBoxLayout()
        self.scripting_layout.setContentsMargins(0,0,0,0)
        self.scripting_layout.setSpacing(0)
        self.scripting_layout.addWidget(self.splitter) #TODO: Set splitter bar position based on ks mode
        self.scripting_layout.addWidget(self.frw)


        #----------------------
        # 3. LOWER BAR
        #----------------------

        # Reload/All and Save/All Buttons
        # self.reload_all_btn = QtWidgets.QPushButton("All")
        # self.reload_all_btn.setToolTip("Reload the contents of all knobs. Will clear the KnobScripter's memory.")
        # self.reload_all_btn.clicked.connect(self.loadAllKnobValues)
        # self.reload_all_btn.setMaximumWidth(self.reload_all_btn.fontMetrics().boundingRect("All").width() + 24)

        # self.arrows_label = QtWidgets.QLabel("&raquo;")
        # self.arrows_label.setTextFormat(QtCore.Qt.RichText)
        # self.arrows_label.setStyleSheet('color:#BBB')
       
        # self.save_all_btn = QtWidgets.QPushButton("All")
        # self.save_all_btn.setToolTip("Save all changes into the knobs.")
        # self.save_all_btn.clicked.connect(self.saveAllKnobValues)
        # self.save_all_btn.setMaximumWidth(self.save_all_btn.fontMetrics().boundingRect("All").width() + 24)

        # PIN Button
        ##self.pin_btn = QtWidgets.QPushButton("PIN") #TODO: Add Pin icon
        ##self.pin_btn.setCheckable(True)
        #if self.pinned:
        ##    self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)
        ##    self.pin_btn.toggle()
        ##self.pin_btn.setToolTip("Keep the KnobScripter on top of all other windows.")
        ##self.pin_btn.setFocusPolicy(QtCore.Qt.NoFocus)
        ##self.pin_btn.setMaximumWidth(self.pin_btn.fontMetrics().boundingRect("pin").width() + 12)
        ##self.pin_btn.clicked[bool].connect(self.pin)

        # Close Button
        ##self.close_btn = QtWidgets.QPushButton("Close")
        ##self.close_btn.clicked.connect(self.close)

        # ---
        # Layout
        ##self.bottom_layout = QtWidgets.QHBoxLayout()
        ##self.bottom_layout.addWidget(self.reload_all_btn)
        ##self.bottom_layout.addWidget(self.arrows_label)
        ##self.bottom_layout.addWidget(self.save_all_btn)
        ##self.bottom_layout.addStretch()
        ##self.bottom_layout.addWidget(self.pin_btn)
        ##self.bottom_layout.addWidget(self.close_btn)
        #self.bottom_layout.setSpacing(8)

        #---------------
        # MASTER LAYOUT
        #---------------
        self.master_layout = QtWidgets.QVBoxLayout()
        self.master_layout.setSpacing(5)
        self.master_layout.setContentsMargins(8,8,8,8)
        self.master_layout.addLayout(self.top_layout)
        self.master_layout.addLayout(self.scripting_layout)
        ##self.master_layout.addLayout(self.bottom_layout)
        self.setLayout(self.master_layout)

        #----------------
        # MAIN WINDOW UI
        #----------------
        size_policy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        self.setSizePolicy(size_policy)
        self.setMinimumWidth(160)

        if self.pinned:
            self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)

        # Set default values based on mode
        if self.nodeMode:
            self.node_mode_bar.setVisible(True)
            self.script_mode_bar.setVisible(False)
            self.setCurrentKnob(self.knob)
            self.loadKnobValue(check = False)
            self.splitter.setSizes([0,1])
        else:
            self.exitNodeMode()
            self.loadScriptContents(check = False)
        self.script_editor.setFocus()

    # Node Mode
    def updateKnobDropdown(self):
        ''' Populate knob dropdown list '''
        self.current_knob_dropdown.clear() # First remove all items
        defaultKnobs = ["knobChanged", "onCreate", "onScriptLoad", "onScriptSave", "onScriptClose", "onDestroy",
                        "updateUI", "autolabel", "beforeRender", "beforeFrameRender", "afterFrameRender", "afterRender"]
        permittedKnobClasses = ["PyScript_Knob", "PythonCustomKnob"]
        counter = 0
        for i in self.node.knobs():
            if i not in defaultKnobs and self.node.knob(i).Class() in permittedKnobClasses:
                self.current_knob_dropdown.addItem(i)# + " (" + self.node.knob(i).name()+")")
                counter += 1
        if counter > 0:
            self.current_knob_dropdown.insertSeparator(counter)
            counter += 1
            self.current_knob_dropdown.insertSeparator(counter)
            counter += 1
        for i in self.node.knobs():
            if i in defaultKnobs:
                self.current_knob_dropdown.addItem(i)
                counter += 1
        return

    def loadKnobValue(self, check=True, updateDict=False):
        ''' Get the content of the knob knobChanged and populate the editor '''
        if self.toLoadKnob == False:
            return
        dropdown_value = self.current_knob_dropdown.currentText().split(" (")[0]
        try:
            obtained_knobValue = str(self.node[dropdown_value].value())
            obtained_scrollValue = 0
            edited_knobValue = self.script_editor.toPlainText()
        except:
            error_message = QtWidgets.QMessageBox.information(None, "", "Unable to find %s.%s"%(self.node.name(),dropdown_value))
            error_message.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
            error_message.exec_()
            return
        # If there were changes to the previous knob, update the dictionary
        if updateDict==True:
            self.unsavedKnobs[self.knob] = edited_knobValue
            self.scrollPos[self.knob] = self.script_editor.verticalScrollBar().value()
        prev_knob = self.knob
        self.knob = self.current_knob_dropdown.currentText().split(" (")[0]
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
        if updateDict:
            if self.knob in self.unsavedKnobs:
                obtained_knobValue = self.unsavedKnobs[self.knob]
            if self.knob in self.scrollPos:
                obtained_scrollValue = self.scrollPos[self.knob]
        self.script_editor.setPlainText(obtained_knobValue)
        self.setScriptModified(False)
        self.script_editor.verticalScrollBar().setValue(obtained_scrollValue)
        self.setWindowTitle("KnobScripter - %s %s" % (self.node.name(), self.knob))
        return

    def loadAllKnobValues(self):
        ''' Load all knobs button's function '''
        if len(self.unsavedKnobs)>=1:
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
        dropdown_value = self.current_knob_dropdown.currentText().split(" (")[0]
        try:
            obtained_knobValue = str(self.node[dropdown_value].value())
            self.knob = self.current_knob_dropdown.currentText().split(" (")[0]
        except:
            error_message = QtWidgets.QMessageBox.information(None, "", "Unable to find %s.%s"%(self.node.name(),dropdown_value))
            error_message.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
            error_message.exec_()
            return
        edited_knobValue = self.script_editor.toPlainText()
        if check and obtained_knobValue != edited_knobValue:
            msgBox = QtWidgets.QMessageBox()
            msgBox.setText("Do you want to overwrite %s.%s?"%(self.node.name(),dropdown_value))
            msgBox.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
            msgBox.setIcon(QtWidgets.QMessageBox.Question)
            msgBox.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
            msgBox.setDefaultButton(QtWidgets.QMessageBox.Yes)
            reply = msgBox.exec_()
            if reply == QtWidgets.QMessageBox.No:
                return
        self.node[self.current_knob_dropdown.currentText().split(" (")[0]].setValue(edited_knobValue)
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
            except:
                saveErrors+=1
        if saveErrors > 0:
            errorBox = QtWidgets.QMessageBox()
            errorBox.setText("Error saving %s knob%s." % (str(saveErrors),int(saveErrors>1)*"s"))
            errorBox.setIcon(QtWidgets.QMessageBox.Warning)
            errorBox.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
            errorBox.setDefaultButton(QtWidgets.QMessageBox.Yes)
            reply = errorBox.exec_()
        else:
            print "KnobScripter: %s knobs saved" % str(savedCount)
        return

    def setCurrentKnob(self, knobToSet):
        ''' Set current knob '''
        KnobDropdownItems = [self.current_knob_dropdown.itemText(i).split(" (")[0] for i in range(self.current_knob_dropdown.count())]
        if knobToSet in KnobDropdownItems:
            knobIndex = self.current_knob_dropdown.findText(knobToSet, QtCore.Qt.MatchFixedString)
            if knobIndex >= 0:
                self.current_knob_dropdown.setCurrentIndex(knobIndex)
        return

    def updateUnsavedKnobs(self):
        ''' Clear unchanged knobs from the dict and return the number of unsaved knobs '''
        edited_knobValue = self.script_editor.toPlainText()
        self.unsavedKnobs[self.knob] = edited_knobValue
        if len(self.unsavedKnobs) > 0:
            for k in self.unsavedKnobs.copy():
                if self.node.knob(k):
                    if str(self.node.knob(k).value()) == str(self.unsavedKnobs[k]):
                        del self.unsavedKnobs[k]
                else:
                    del self.unsavedKnobs[k]
        return len(self.unsavedKnobs)

    # Script Mode
    def updateFoldersDropdown(self):
        ''' Populate folders dropdown list '''
        self.current_folder_dropdown.blockSignals(True)
        self.current_folder_dropdown.clear() # First remove all items
        defaultFolders = ["scripts"]
        scriptFolders = []
        counter = 0
        for f in defaultFolders:
            self.makeScriptFolder(f)
            self.current_folder_dropdown.addItem(f+"/", f)
            counter += 1

        try:
            scriptFolders = [x[0] for x in os.walk(self.scripts_dir)][1:]
        except:
            print "Couldn't read any script folders."

        for f in scriptFolders:
            fname = f.split("/")[-1]
            if fname in defaultFolders:
                continue
            self.current_folder_dropdown.addItem(fname+"/", fname)
            counter += 1

        #print scriptFolders
        if counter > 0:
            self.current_folder_dropdown.insertSeparator(counter)
            counter += 1
            #self.current_folder_dropdown.insertSeparator(counter)
            #counter += 1
        self.current_folder_dropdown.addItem("New", "create new")
        self.current_folder_dropdown.addItem("Browse...", "open in browser")
        self.folder_index = self.current_folder_dropdown.currentIndex()
        self.current_folder = self.current_folder_dropdown.itemData(self.folder_index)
        self.current_folder_dropdown.blockSignals(False)
        #TODO: remember last opened folder... in a prefs file or sth
        return

    def updateScriptsDropdown(self):
        ''' Populate py scripts dropdown list '''
        self.current_script_dropdown.blockSignals(True)
        self.current_script_dropdown.clear() # First remove all items
        print "# Updating scripts dropdown..."
        print "scripts dir:"+self.scripts_dir
        print "current folder:"+self.current_folder
        print "previous current script:"+self.current_script
        #current_folder = self.current_folder_dropdown.itemData(self.current_folder_dropdown.currentIndex())
        current_folder_path = os.path.join(self.scripts_dir,self.current_folder)
        defaultScripts = ["Untitled.py"]
        found_scripts = []
        counter = 0
        dir_list = os.listdir(current_folder_path) # All files and folders inside of the folder
        try:
            found_scripts = [f for f in dir_list if f.endswith(".py")]
            found_temp_scripts = [f for f in dir_list if f.endswith(".py.autosave")]
        except:
            print "Couldn't find any scripts in the selected folder."
        #TODO: Check which ones have been modified (thus a modified script also exists)
        if not len(found_scripts):
            for s in defaultScripts:
                if s+".autosave" in found_temp_scripts:
                    self.current_script_dropdown.addItem(s+"(*)",s)
                else:
                    self.current_script_dropdown.addItem(s,s)
                counter += 1
        else:
            for s in found_scripts:
                sname = s.split("/")[-1]
                self.current_script_dropdown.addItem(sname, sname)
                counter += 1
        ##else: #Add the found scripts to the dropdown
        if counter > 0:
            self.current_script_dropdown.insertSeparator(counter)
            counter += 1
            self.current_script_dropdown.insertSeparator(counter)
            counter += 1
        self.current_script_dropdown.addItem("New", "create new")
        self.current_script_dropdown.addItem("Duplicate", "create duplicate")
        self.current_script_dropdown.addItem("Delete", "delete script")
        #self.script_index = self.current_script_dropdown.currentIndex()
        self.script_index = 0
        self.current_script = self.current_script_dropdown.itemData(self.script_index)
        print "Finished updating scripts dropdown."
        print "current_script:"+self.current_script
        self.current_script_dropdown.blockSignals(False)
        return

    def makeScriptFolder(self, name = "scripts"):
        folder_path = os.path.join(self.scripts_dir,name)
        if not os.path.exists(folder_path):
            try:
                os.makedirs(folder_path)
                return True
            except:
                print "Couldn't create the scripting folders.\nPlease check your OS write permissions."
                return False

    def makeScriptFile(self, name = "Untitled.py", folder = "scripts", empty = True):
        script_path = os.path.join(self.scripts_dir, self.current_folder, name)
        if not os.path.isfile(script_path):
            try:
                self.current_script_file = open(script_path, 'w')
                return True
            except:
                print "Couldn't create the scripting folders.\nPlease check your OS write permissions."
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

    def loadScriptContents(self, check = False, folder=""):
        ''' Get the contents of the selected script and populate the editor '''
        print "# About to load script contents now."
        print "self.scripts_dir: "+self.scripts_dir
        print "self.current_folder: "+self.current_folder
        print "self.current_script: "+self.current_script
        script_path = os.path.join(self.scripts_dir, self.current_folder, self.current_script)
        script_path_temp = script_path + ".autosave"
        self.setWindowTitle("KnobScripter - %s/%s" % (self.current_folder, self.current_script))
        if os.path.isfile(script_path_temp):
            print "Loading .py.autosave file"
            with open(script_path_temp, 'r') as script:
                content = script.read()
            self.setScriptModified(True)
        elif os.path.isfile(script_path):
            print "Loading .py file"
            with open(script_path, 'r') as script:
                content = script.read()
            self.setScriptModified(False)
        else:
            content = ""
            self.setScriptModified(False)
        self.script_editor.setPlainText(content)
        print "loaded "+script_path
        print "---"
        return

    def saveCurrentScript(self, temp = True):
        ''' Save the current contents of the editor into the python file. If temp == True, saves a different file '''
        print "\n# About to save script contents now."
        print "Temp mode is: "+str(temp)
        print "self.current_folder: "+self.current_folder
        print "self.current_script: "+self.current_script
        script_path = os.path.join(self.scripts_dir, self.current_folder, self.current_script)
        script_path_temp = script_path + ".autosave"

        if temp == True:
            with open(script_path_temp, 'w') as script:
                script.write(self.script_editor.toPlainText())
            self.setScriptModified(True)
        else:
            with open(script_path, 'w') as script:
                script.write(self.script_editor.toPlainText())
            # Clear trash
            if os.path.isfile(script_path_temp):
                os.remove(script_path_temp)
                print "Removed "+script_path_temp
            self.setScriptModified(False)
        print "Saved "+script_path
        print "---"
        return

    """
    def loadKnobValue(self, check=True, updateDict=False):
        ''' Get the content of the knob knobChanged and populate the editor '''
        if self.toLoadKnob == False:
            return
        dropdown_value = self.current_knob_dropdown.currentText().split(" (")[0]
        try:
            obtained_knobValue = str(self.node[dropdown_value].value())
            obtained_scrollValue = 0
            edited_knobValue = self.script_editor.toPlainText()
        except:
            error_message = QtWidgets.QMessageBox.information(None, "", "Unable to find %s.%s"%(self.node.name(),dropdown_value))
            error_message.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
            error_message.exec_()
            return
        # If there were changes to the previous knob, update the dictionary
        if updateDict==True:
            self.unsavedKnobs[self.knob] = edited_knobValue
            self.scrollPos[self.knob] = self.script_editor.verticalScrollBar().value()
        prev_knob = self.knob
        self.knob = self.current_knob_dropdown.currentText().split(" (")[0]
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
        if updateDict:
            if self.knob in self.unsavedKnobs:
                obtained_knobValue = self.unsavedKnobs[self.knob]
            if self.knob in self.scrollPos:
                obtained_scrollValue = self.scrollPos[self.knob]
        self.script_editor.setPlainText(obtained_knobValue)
        self.script_editor.verticalScrollBar().setValue(obtained_scrollValue)
        self.setWindowTitle("KnobScripter - %s %s" % (self.node.name(), self.knob))
        return
    """
    def folderDropdownChanged(self):
        '''Executed when the current folder dropdown is changed'''
        #TODO: Save temp file for current!!!!!
        print "# folder dropdown changed"
        folders_dropdown = self.current_folder_dropdown
        fd_value = folders_dropdown.currentText()
        fd_index = folders_dropdown.currentIndex()
        fd_data = folders_dropdown.itemData(fd_index)
        if fd_data == "create new":
            panel = FileNameDialog(self, mode="folder")
            #panel.setWidth(260)
            #panel.addSingleLineInput("Name:","")
            if panel.exec_():
                # Accepted
                folder_name = panel.text
                if os.path.isdir(os.path.join(self.scripts_dir,folder_name)):
                    self.messageBox("Folder already exists.")
                    self.setCurrentFolder(self.current_folder)
                if self.makeScriptFolder(name = folder_name):
                    # Success creating the folder
                    self.current_folder = folder_name
                    self.updateFoldersDropdown()
                    self.setCurrentFolder(folder_name)
                    self.updateScriptsDropdown()
                else:
                    self.messageBox("There was a problem creating the folder.")
                    self.current_folder_dropdown.setCurrentIndex(self.folder_index)
            else:
                # Canceled/rejected
                self.current_folder_dropdown.setCurrentIndex(self.folder_index)
                return
        else:
            #TODO: Save temp file before changing anything
            self.saveCurrentScript(temp = True)
            self.current_folder = fd_data
            self.folder_index = fd_index
            print "about to update the scripts dropdown."
            self.updateScriptsDropdown()
            self.scriptDropdownChanged()
        return

    def scriptDropdownChanged(self):
        '''Executed when the current script dropdown is changed'''

        #TODO: Save temp file for current!!!!!
        scripts_dropdown = self.current_script_dropdown
        sd_value = scripts_dropdown.currentText()
        sd_index = scripts_dropdown.currentIndex()
        sd_data = scripts_dropdown.itemData(sd_index)
        if sd_data == "create new":
            panel = FileNameDialog(self, mode="script")
            if panel.exec_():
                # Accepted
                script_name = panel.text + ".py"
                script_path = os.path.join(self.scripts_dir, self.current_folder, script_name)
                print script_name, script_path
                if os.path.isfile(script_path):
                    self.messageBox("Script already exists.")
                    self.current_script_dropdown.setCurrentIndex(self.script_index)
                if self.makeScriptFile(name = script_name, folder = self.current_folder):
                    # Success creating the folder
                    #self.updateFoldersDropdown()
                    self.updateScriptsDropdown()
                    self.current_script = script_name
                    self.setCurrentScript(script_name)
                else:
                    self.messageBox("There was a problem creating the script.")
                    self.current_script_dropdown.setCurrentIndex(self.script_index)
            else:
                # Canceled/rejected
                self.current_script_dropdown.setCurrentIndex(self.script_index)
                return
        else:
            self.saveCurrentScript()
            self.current_script = sd_data
            self.script_index = sd_index
            self.setCurrentScript(self.current_script)
            self.loadScriptContents()
        return

    def setScriptModified(self, modified = True):
        ''' Sets self.current_script_modified, title and whatever else we need '''
        self.current_script_modified = modified
        title_modified_string = " [modified]"
        windowTitle = self.windowTitle().split(title_modified_string)[0]
        if modified == True:
            windowTitle += title_modified_string
        self.setWindowTitle(windowTitle)

    # Global stuff
    def eventFilter(self, object, event):
        if event.type() == QtCore.QEvent.KeyPress:
            return QtWidgets.QWidget.eventFilter(self, object, event)
        else:
            return QtWidgets.QWidget.eventFilter(self, object, event)

    def resizeEvent(self, res_event):
        w = self.frameGeometry().width()
        self.current_node_label_node.setVisible(w>360)
        self.script_label.setVisible(w>360)
        return super(KnobScripter, self).resizeEvent(res_event)

    def changeClicked(self, newNode=""):
        ''' Change node '''
        nuke.menu("Nuke").findItem("Edit/Node/Update KnobScripter Context").invoke()
        selection = knobScripterSelectedNodes
        updatedCount = self.updateUnsavedKnobs()
        if not len(selection):
            self.messageBox("Please select one or more nodes!")
        else:
            # Change to node mode...
            self.node_mode_bar.setVisible(True)
            self.script_mode_bar.setVisible(False)
            if not self.nodeMode:
                self.splitter.setSizes([0,1])
            self.nodeMode = True

            # If already selected, pass
            if selection[0].fullName() == self.node.fullName():
                self.messageBox("Please select a different node first!")
                return
            elif updatedCount > 0:
                msgBox = QtWidgets.QMessageBox()
                msgBox.setText(
                    "Save changes to %s knob%s before changing the node?" % (str(updatedCount), int(updatedCount > 1) * "s"))
                msgBox.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No | QtWidgets.QMessageBox.Cancel)
                msgBox.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
                msgBox.setDefaultButton(QtWidgets.QMessageBox.Yes)
                reply = msgBox.exec_()
                if reply == QtWidgets.QMessageBox.Yes:
                    self.saveAllKnobValues(check=False)
                    print self.unsavedKnobs
                elif reply == QtWidgets.QMessageBox.Cancel:
                    return
            if len(selection) > 1:
                self.messageBox("More than one node selected.\nChanging knobChanged editor to %s" % selection[0].fullName())
            # Reinitialise everything, wooo!
            self.node = selection[0]
            self.script_editor.setPlainText("")
            self.unsavedKnobs = {}
            self.scrollPos = {}
            self.setWindowTitle("KnobScripter - %s %s" % (self.node.fullName(), self.knob))
            self.current_node_label_name.setText(self.node.fullName())

            ########TODO: REMOVE AND RE-ADD THE KNOB DROPDOWN
            self.toLoadKnob = False
            self.updateKnobDropdown()
            #self.current_knob_dropdown.repaint()
            ###self.current_knob_dropdown.setMinimumWidth(self.current_knob_dropdown.minimumSizeHint().width())
            self.toLoadKnob = True
            self.setCurrentKnob(self.knob)
            self.loadKnobValue(False)
            self.script_editor.setFocus()
            #self.current_knob_dropdown.setMinimumContentsLength(80)
        return
    
    def exitNodeMode(self):
        self.nodeMode = False
        self.setWindowTitle("KnobScripter - Script Mode")
        self.node_mode_bar.setVisible(False)
        self.script_mode_bar.setVisible(True)
        self.node = nuke.toNode("root")
        #self.updateFoldersDropdown()
        #self.updateScriptsDropdown()
        self.splitter.setSizes([1,1])

    def clearConsole(self):
        origConsoleText = self.origConsoleText
        self.origConsoleText = self.nukeSEOutput.document().toPlainText()
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
        global snippet_panel
        snippet_panel = SnippetsPanel(self)
        if snippet_panel.show():
            self.loadSnippets()

    def loadSnippets(self):
        ''' Load prefs '''
        if not os.path.isfile(self.snippets_txt_path):
            return {}
        else:
            with open(self.snippets_txt_path, "r") as f:
                self.snippets = json.load(f)
                return self.snippets

    def messageBox(self, the_text=""):
        ''' Just a simple message box '''
        msgBox = QtWidgets.QMessageBox(self)
        msgBox.setText(the_text)
        msgBox.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        msgBox.exec_()

    def openPrefs(self):
        ''' Open the preferences panel '''
        global ks_prefs
        ks_prefs = KnobScripterPrefs(self)
        ks_prefs.show()

    def loadPrefs(self):
        ''' Load prefs '''
        if not os.path.isfile(self.prefs_txt):
            return []
        else:
            with open(self.prefs_txt, "r") as f:
                prefs = json.load(f)
                return prefs

    def saveScrollValue(self):
        ''' Save scroll values '''
        self.scrollPos[self.knob] = self.script_editor.verticalScrollBar().value()

    def closeEvent(self, close_event):
        if self.nodeMode:
            updatedCount = self.updateUnsavedKnobs()
            if updatedCount > 0:
                msgBox = QtWidgets.QMessageBox()
                msgBox.setText("Save changes to %s knob%s before closing?" % (str(updatedCount),int(updatedCount>1)*"s"))
                msgBox.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No | QtWidgets.QMessageBox.Cancel)
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
            close_event.accept()

    # Landing functions
    def reloadClicked(self):
        if self.nodeMode:
            self.loadKnobValue()
        #TODO: If script mode...

    def saveClicked(self):
        if self.nodeMode:
            self.saveKnobValue(False)
        else:
            self.saveCurrentScript(temp = False)
        #TODO: If script mode...

    def pin(self, pressed):
        if pressed:
            self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)
            self.pinned = True
            self.show()
        else:
            self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowStaysOnTopHint)
            self.pinned = False
            self.show()

    def findSE(self):
        for widget in QtWidgets.QApplication.allWidgets():
            if "Script Editor" in widget.windowTitle():
                return widget

    # Functions for Nuke's Script Editor
    def findScriptEditors(self):
        script_editors = []
        for widget in QtWidgets.QApplication.allWidgets():
            if "Script Editor" in widget.windowTitle():
                script_editors.append(widget)
        return script_editors

    def findSEInput(self, se):
        return se.children()[-1].children()[0]

    def findSEOutput(self, se):
        return se.children()[-1].children()[1]

    def findSERunBtn(self, se):
        for btn in se.children():
            try:
                if "Run the current script" in btn.toolTip():
                    return btn
            except:
                pass
        return False

    def setSEOutputEvent(self):
        nukeScriptEditors = self.findScriptEditors()
        self.origConsoleText = self.nukeSEOutput.document().toPlainText() # Take the console from the first script editor found...
        for se in nukeScriptEditors:
            se_output = self.findSEOutput(se)
            se_output.textChanged.connect(partial(consoleChanged,se_output, self))
            consoleChanged(se_output, self) # Initialise.

class KnobScripterPane(KnobScripter):
    def __init__(self, node = "", knob="knobChanged"):
        super(KnobScripterPane, self).__init__()
    def event(self, the_event):
        if the_event.type() == QtCore.QEvent.Type.Show:
            try:
                killPaneMargins(self)
            except:
                pass
        return super(KnobScripterPane, self).event(the_event)

def consoleChanged(self, ks):
    ''' This will be called every time the ScriptEditor Output text is changed '''
    try:
        if ks: # KS exists
            origConsoleText = ks.origConsoleText # The text from the console that will be omitted
            ksOutput = ks.script_output # The console TextEdit widget
            ksText = self.document().toPlainText()
            if ksText.startswith(origConsoleText):
                ksText = ksText[len(origConsoleText):]
            else:
                ks.origConsoleText = ""
            ksOutput.setPlainText(ksText)
            ksOutput.verticalScrollBar().setValue(ksOutput.verticalScrollBar().maximum())
    except:
        pass

def killPaneMargins(widget_object):
    if widget_object:
        target_widgets = set()
        target_widgets.add(widget_object.parentWidget().parentWidget())
        target_widgets.add(widget_object.parentWidget().parentWidget().parentWidget().parentWidget())

        for widget_layout in target_widgets:
            try:
                widget_layout.layout().setContentsMargins(0, 0, 0, 0)
            except:
                pass

#---------------------------------------------------------------------
# Dialog for creating new... (folder, script or knob)
#---------------------------------------------------------------------
class FileNameDialog(QtWidgets.QDialog):
    '''
    Dialog for creating new... (mode = "folder", "script" or "knob").
    '''
    def __init__(self, parent = None, mode = "folder", text = ""):
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

#------------------------------------------------------------------------------------------------------
# Script Editor Widget
# Wouter Gilsing built an incredibly useful python script editor for his Hotbox Manager, so I had it
# really easy for this part! I made it a bit simpler, leaving just the part non associated to his tool
# and tweaking the style a bit to be compatible with font size changing and stuff.
# I think this bit of code has the potential to get used in many nuke tools.
# All credit to him: http://www.woutergilsing.com/
# Originally used on W_Hotbox v1.5: http://www.nukepedia.com/python/ui/w_hotbox
#------------------------------------------------------------------------------------------------------
class KnobScripterTextEdit(QtWidgets.QPlainTextEdit):
    # Signal that will be emitted when the user has changed the text
    userChangedEvent = QtCore.Signal()

    def __init__(self, knobScripter=""):
        super(KnobScripterTextEdit, self).__init__()

        self.knobScripter = knobScripter

        # Setup line numbers
        if self.knobScripter != "":
            self.tabSpaces = self.knobScripter.tabSpaces
        else:
            self.tabSpaces = 4
        self.lineNumberArea = KSLineNumberArea(self)
        self.blockCountChanged.connect(self.updateLineNumberAreaWidth)
        self.updateRequest.connect(self.updateLineNumberArea)
        self.updateLineNumberAreaWidth()

        # Highlight line
        self.cursorPositionChanged.connect(self.highlightCurrentLine)

    #--------------------------------------------------------------------------------------------------
    # Line Numbers (extract from original comment by Wouter Gilsing)
    # While researching the implementation of line number, I had a look at Nuke's Blinkscript node. [..]
    # thefoundry.co.uk/products/nuke/developers/100/pythonreference/nukescripts.blinkscripteditor-pysrc.html
    # I stripped and modified the useful bits of the line number related parts of the code [..]
    # Credits to theFoundry for writing the blinkscripteditor, best example code I could wish for.
    #--------------------------------------------------------------------------------------------------

    def lineNumberAreaWidth(self):
        digits = 1
        maxNum = max(1, self.blockCount())
        while (maxNum >= 10):
            maxNum /= 10
            digits += 1

        space = 7 + self.fontMetrics().width('9') * digits
        return space

    def updateLineNumberAreaWidth(self):
        self.setViewportMargins(self.lineNumberAreaWidth(), 0, 0, 0)

    def updateLineNumberArea(self, rect, dy):

        if (dy):
            self.lineNumberArea.scroll(0, dy)
        else:
            self.lineNumberArea.update(0, rect.y(), self.lineNumberArea.width(), rect.height())

        if (rect.contains(self.viewport().rect())):
            self.updateLineNumberAreaWidth()

    def resizeEvent(self, event):
        QtWidgets.QPlainTextEdit.resizeEvent(self, event)

        cr = self.contentsRect()
        self.lineNumberArea.setGeometry(QtCore.QRect(cr.left(), cr.top(), self.lineNumberAreaWidth(), cr.height()))

    def lineNumberAreaPaintEvent(self, event):

        if self.isReadOnly():
            return

        painter = QtGui.QPainter(self.lineNumberArea)
        painter.fillRect(event.rect(), QtGui.QColor(36, 36, 36)) # Number bg


        block = self.firstVisibleBlock()
        blockNumber = block.blockNumber()
        top = int( self.blockBoundingGeometry(block).translated(self.contentOffset()).top() )
        bottom = top + int( self.blockBoundingRect(block).height() )
        currentLine = self.document().findBlock(self.textCursor().position()).blockNumber()

        painter.setPen( self.palette().color(QtGui.QPalette.Text) )

        painterFont = QtGui.QFont()
        painterFont.setFamily("Courier")
        painterFont.setStyleHint(QtGui.QFont.Monospace)
        painterFont.setFixedPitch(True)
        if self.knobScripter != "":
            painterFont.setPointSize(self.knobScripter.fontSize)
            painter.setFont(self.knobScripter.script_editor_font)

        while (block.isValid() and top <= event.rect().bottom()):

            textColor = QtGui.QColor(110, 110, 110) # Numbers

            if blockNumber == currentLine and self.hasFocus():
                textColor = QtGui.QColor(255, 170, 0) # Number highlighted

            painter.setPen(textColor)

            number = "%s" % str(blockNumber + 1)
            painter.drawText(-3, top, self.lineNumberArea.width(), self.fontMetrics().height(), QtCore.Qt.AlignRight, number)

            # Move to the next block
            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            blockNumber += 1

    def keyPressEvent(self, event):
        '''
        Custom actions for specific keystrokes
        '''
        key = event.key()
        #if Tab convert to Space
        if key == 16777217:
            self.indentation('indent')

        #if Shift+Tab remove indent
        elif key == 16777218:
            self.indentation('unindent')

        #if BackSpace try to snap to previous indent level
        elif key == 16777219:
            if not self.unindentBackspace():
                QtWidgets.QPlainTextEdit.keyPressEvent(self, event)
        #if enter or return, match indent level
        elif key in [16777220 ,16777221]:
            self.indentNewLine()
        else:
            ### COOL BEHAVIORS SIMILAR TO SUBLIME GO NEXT!
            cursor = self.textCursor()
            cpos = cursor.position()
            apos = cursor.anchor()
            text_before_cursor = self.toPlainText()[:min(cpos,apos)]
            text_after_cursor = self.toPlainText()[max(cpos,apos):]
            if cursor.hasSelection():
                selection = cursor.selection().toPlainText()
            else:
                selection = ""

            if key == Qt.Key_ParenLeft:
                cursor.insertText("("+selection+")")
                cursor.movePosition(QtGui.QTextCursor.PreviousCharacter)
                self.setTextCursor(cursor)
            elif key == Qt.Key_ParenRight and text_after_cursor.startswith(")"):
                cursor.movePosition(QtGui.QTextCursor.NextCharacter)
                self.setTextCursor(cursor)
            elif key == 34: # "
                if text_after_cursor.startswith('"') and '"' in text_before_cursor.split("\n")[-1]:# and not re.search(r"(?:[\s)\]]+|$)",text_before_cursor):
                    cursor.movePosition(QtGui.QTextCursor.NextCharacter)
                elif not re.match(r"(?:[\s)\]]+|$)",text_after_cursor): # If chars after cursor, act normal
                    print text_before_cursor
                    QtWidgets.QPlainTextEdit.keyPressEvent(self, event)
                elif not re.search(r"[\s.({\[,]$", text_before_cursor) and text_before_cursor != "": # If chars before cursor, act normal
                    print text_before_cursor
                    QtWidgets.QPlainTextEdit.keyPressEvent(self, event)
                else:
                    cursor.insertText('"'+selection+'"')
                    cursor.movePosition(QtGui.QTextCursor.PreviousCharacter)
                self.setTextCursor(cursor)
            elif key == 39: # ''
                if text_after_cursor.startswith("'") and "'" in text_before_cursor.split("\n")[-1]:# and not re.search(r"(?:[\s)\]]+|$)",text_before_cursor):
                    cursor.movePosition(QtGui.QTextCursor.NextCharacter)
                elif not re.match(r"(?:[\s)\]]+|$)",text_after_cursor): # If chars after cursor, act normal
                    print text_before_cursor
                    QtWidgets.QPlainTextEdit.keyPressEvent(self, event)
                elif not re.search(r"[\s.({\[,]$", text_before_cursor) and text_before_cursor != "": # If chars before cursor, act normal
                    print text_before_cursor
                    QtWidgets.QPlainTextEdit.keyPressEvent(self, event)
                else:
                    cursor.insertText("'"+selection+"'")
                    cursor.movePosition(QtGui.QTextCursor.PreviousCharacter)
                self.setTextCursor(cursor)
            else:
                QtWidgets.QPlainTextEdit.keyPressEvent(self, event)
            
            #print key

            
        self.scrollToCursor()

    def scrollToCursor(self):
        self.cursor = self.textCursor()
        self.cursor.movePosition(QtGui.QTextCursor.NoMove) # Does nothing, but makes the scroll go to the right place...
        self.setTextCursor(self.cursor)

    def getCursorInfo(self):

        self.cursor = self.textCursor()

        self.firstChar =  self.cursor.selectionStart()
        self.lastChar =  self.cursor.selectionEnd()

        self.noSelection = False
        if self.firstChar == self.lastChar:
            self.noSelection = True

        self.originalPosition = self.cursor.position()
        self.cursorBlockPos = self.cursor.positionInBlock()

    def unindentBackspace(self):
        '''
        #snap to previous indent level
        '''
        self.getCursorInfo()

        if not self.noSelection or self.cursorBlockPos == 0:
            return False

        #check text in front of cursor
        textInFront = self.document().findBlock(self.firstChar).text()[:self.cursorBlockPos]

        #check whether solely spaces
        if textInFront != ' '*self.cursorBlockPos:
            return False

        #snap to previous indent level
        spaces = len(textInFront)
        for space in range(spaces - ((spaces -1) /self.tabSpaces) * self.tabSpaces -1):
            self.cursor.deletePreviousChar()

    def indentNewLine(self):

        #in case selection covers multiple line, make it one line first
        self.insertPlainText('')

        self.getCursorInfo()

        #check how many spaces after cursor
        text = self.document().findBlock(self.firstChar).text()

        textInFront = text[:self.cursorBlockPos]

        if len(textInFront) == 0:
            self.insertPlainText('\n')
            return

        indentLevel = 0
        for i in textInFront:
            if i == ' ':
                indentLevel += 1
            else:
                break

        indentLevel /= self.tabSpaces

        #find out whether textInFront's last character was a ':'
        #if that's the case add another indent.
        #ignore any spaces at the end, however also
        #make sure textInFront is not just an indent
        if textInFront.count(' ') != len(textInFront):
            while textInFront[-1] == ' ':
                textInFront = textInFront[:-1]

        if textInFront[-1] == ':':
            indentLevel += 1

        #new line
        self.insertPlainText('\n')
        #match indent
        self.insertPlainText(' '*(self.tabSpaces*indentLevel))

    def indentation(self, mode):

        self.getCursorInfo()

        #if nothing is selected and mode is set to indent, simply insert as many
        #space as needed to reach the next indentation level.
        if self.noSelection and mode == 'indent':

            remainingSpaces = self.tabSpaces - (self.cursorBlockPos%self.tabSpaces)
            self.insertPlainText(' '*remainingSpaces)
            return

        selectedBlocks = self.findBlocks(self.firstChar, self.lastChar)
        beforeBlocks = self.findBlocks(last = self.firstChar -1, exclude = selectedBlocks)
        afterBlocks = self.findBlocks(first = self.lastChar + 1, exclude = selectedBlocks)

        beforeBlocksText = self.blocks2list(beforeBlocks)
        selectedBlocksText = self.blocks2list(selectedBlocks, mode)
        afterBlocksText = self.blocks2list(afterBlocks)

        combinedText = '\n'.join(beforeBlocksText + selectedBlocksText + afterBlocksText)

        #make sure the line count stays the same
        originalBlockCount = len(self.toPlainText().split('\n'))
        combinedText = '\n'.join(combinedText.split('\n')[:originalBlockCount])

        self.clear()
        self.setPlainText(combinedText)

        if self.noSelection:
            self.cursor.setPosition(self.lastChar)

        #check whether the the orignal selection was from top to bottom or vice versa
        else:
            if self.originalPosition == self.firstChar:
                first = self.lastChar
                last = self.firstChar
                firstBlockSnap = QtGui.QTextCursor.EndOfBlock
                lastBlockSnap = QtGui.QTextCursor.StartOfBlock
            else:
                first = self.firstChar
                last = self.lastChar
                firstBlockSnap = QtGui.QTextCursor.StartOfBlock
                lastBlockSnap = QtGui.QTextCursor.EndOfBlock

            self.cursor.setPosition(first)
            self.cursor.movePosition(firstBlockSnap,QtGui.QTextCursor.MoveAnchor)
            self.cursor.setPosition(last,QtGui.QTextCursor.KeepAnchor)
            self.cursor.movePosition(lastBlockSnap,QtGui.QTextCursor.KeepAnchor)

        self.setTextCursor(self.cursor)

    def findBlocks(self, first = 0, last = None, exclude = []):
        blocks = []
        if last == None:
            last = self.document().characterCount()
        for pos in range(first,last+1):
            block = self.document().findBlock(pos)
            if block not in blocks and block not in exclude:
                blocks.append(block)
        return blocks

    def blocks2list(self, blocks, mode = None):
        text = []
        for block in blocks:
            blockText = block.text()
            if mode == 'unindent':
                if blockText.startswith(' '*self.tabSpaces):
                    blockText = blockText[self.tabSpaces:]
                    self.lastChar -= self.tabSpaces
                elif blockText.startswith('\t'):
                    blockText = blockText[1:]
                    self.lastChar -= 1

            elif mode == 'indent':
                blockText = ' '*self.tabSpaces + blockText
                self.lastChar += self.tabSpaces

            text.append(blockText)

        return text

    def highlightCurrentLine(self):
        '''
        Highlight currently selected line
        '''
        extraSelections = []

        selection = QtWidgets.QTextEdit.ExtraSelection()

        lineColor = QtGui.QColor(62, 62, 62, 255)

        selection.format.setBackground(lineColor)
        selection.format.setProperty(QtGui.QTextFormat.FullWidthSelection, True)
        selection.cursor = self.textCursor()
        selection.cursor.clearSelection()

        extraSelections.append(selection)

        self.setExtraSelections(extraSelections)

class KSLineNumberArea(QtWidgets.QWidget):
    def __init__(self, scriptEditor):
        super(KSLineNumberArea, self).__init__(scriptEditor)

        self.scriptEditor = scriptEditor
        self.setStyleSheet("text-align: center;")

    def paintEvent(self, event):
        self.scriptEditor.lineNumberAreaPaintEvent(event)
        return

class KSScriptEditorHighlighter(QtGui.QSyntaxHighlighter):
    '''
    Modified, simplified version of some code found I found when researching:
    wiki.python.org/moin/PyQt/Python%20syntax%20highlighting
    They did an awesome job, so credits to them. I only needed to make some
    modifications to make it fit my needs.
    '''

    def __init__(self, document):

        super(KSScriptEditorHighlighter, self).__init__(document)

        self.styles = {
            'keyword': self.format([238,117,181],'bold'),
            'string': self.format([242, 136, 135]),
            'comment': self.format([143, 221, 144 ]),
            'numbers': self.format([174, 129, 255])
            }

        self.keywords = [
            'and', 'assert', 'break', 'class', 'continue', 'def',
            'del', 'elif', 'else', 'except', 'exec', 'finally',
            'for', 'from', 'global', 'if', 'import', 'in',
            'is', 'lambda', 'not', 'or', 'pass', 'print',
            'raise', 'return', 'try', 'while', 'yield'
            ]

        self.operatorKeywords = [
            '=','==', '!=', '<', '<=', '>', '>=',
            '\+', '-', '\*', '/', '//', '\%', '\*\*',
            '\+=', '-=', '\*=', '/=', '\%=',
            '\^', '\|', '\&', '\~', '>>', '<<'
            ]

        self.numbers = ['True','False','None']

        self.tri_single = (QtCore.QRegExp("'''"), 1, self.styles['comment'])
        self.tri_double = (QtCore.QRegExp('"""'), 2, self.styles['comment'])

        #rules
        rules = []

        rules += [(r'\b%s\b' % i, 0, self.styles['keyword']) for i in self.keywords]
        rules += [(i, 0, self.styles['keyword']) for i in self.operatorKeywords]
        rules += [(r'\b%s\b' % i, 0, self.styles['numbers']) for i in self.numbers]

        rules += [

            # integers
            (r'\b[0-9]+\b', 0, self.styles['numbers']),
            # Double-quoted string, possibly containing escape sequences
            (r'"[^"\\]*(\\.[^"\\]*)*"', 0, self.styles['string']),
            # Single-quoted string, possibly containing escape sequences
            (r"'[^'\\]*(\\.[^'\\]*)*'", 0, self.styles['string']),
            # From '#' until a newline
            (r'#[^\n]*', 0, self.styles['comment']),
            ]

        # Build a QRegExp for each pattern
        self.rules = [(QtCore.QRegExp(pat), index, fmt) for (pat, index, fmt) in rules]

    def format(self,rgb, style=''):
        '''
        Return a QtWidgets.QTextCharFormat with the given attributes.
        '''

        color = QtGui.QColor(*rgb)
        textFormat = QtGui.QTextCharFormat()
        textFormat.setForeground(color)

        if 'bold' in style:
            textFormat.setFontWeight(QtGui.QFont.Bold)
        if 'italic' in style:
            textFormat.setFontItalic(True)

        return textFormat

    def highlightBlock(self, text):
        '''
        Apply syntax highlighting to the given block of text.
        '''
        # Do other syntax formatting
        for expression, nth, format in self.rules:
            index = expression.indexIn(text, 0)

            while index >= 0:
                # We actually want the index of the nth match
                index = expression.pos(nth)
                length = len(expression.cap(nth))
                self.setFormat(index, length, format)
                index = expression.indexIn(text, index + length)

        self.setCurrentBlockState(0)

        # Do multi-line strings
        in_multiline = self.match_multiline(text, *self.tri_single)
        if not in_multiline:
            in_multiline = self.match_multiline(text, *self.tri_double)

    def match_multiline(self, text, delimiter, in_state, style):
        '''
        Check whether highlighting reuires multiple lines.
        '''
        # If inside triple-single quotes, start at 0
        if self.previousBlockState() == in_state:
            start = 0
            add = 0
        # Otherwise, look for the delimiter on this line
        else:
            start = delimiter.indexIn(text)
            # Move past this match
            add = delimiter.matchedLength()

        # As long as there's a delimiter match on this line...
        while start >= 0:
            # Look for the ending delimiter
            end = delimiter.indexIn(text, start + add)
            # Ending delimiter on this line?
            if end >= add:
                length = end - start + add + delimiter.matchedLength()
                self.setCurrentBlockState(0)
            # No; multi-line string
            else:
                self.setCurrentBlockState(in_state)
                length = len(text) - start + add
            # Apply formatting
            self.setFormat(start, length, style)
            # Look for the next match
            start = delimiter.indexIn(text, start + length)

        # Return True if still inside a multi-line string, False otherwise
        if self.currentBlockState() == in_state:
            return True
        else:
            return False

#--------------------------------------------------------------------------------------
# Script Output Widget
# The output logger works the same way as Nuke's python script editor output window
#--------------------------------------------------------------------------------------

class ScriptOutputWidget(QtWidgets.QTextEdit) :
    def __init__(self, parent=None):
        super(ScriptOutputWidget, self).__init__(parent)
        self.knobScripter = parent
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.setMinimumHeight(20)

    def keyPressEvent(self, event):
        ctrl = ((event.modifiers() and (Qt.ControlModifier)) != 0)
        alt = ((event.modifiers() and (Qt.AltModifier)) != 0)
        shift = ((event.modifiers() and (Qt.ShiftModifier)) != 0)
        key = event.key()
        if type(event) == QtGui.QKeyEvent:
            #print event.key()
            if key in [32]: # Space
                return KnobScripter.keyPressEvent(self.knobScripter, event)
            elif key in [Qt.Key_Backspace, Qt.Key_Delete]:
                self.knobScripter.clearConsole()
        return QtWidgets.QTextEdit.keyPressEvent(self, event)

    #def mousePressEvent(self, QMouseEvent):
    #    if QMouseEvent.button() == Qt.RightButton:
    #        self.knobScripter.clearConsole()
    #    QtWidgets.QTextEdit.mousePressEvent(self, QMouseEvent)

#---------------------------------------------------------------------
# Modified KnobScripterTextEdit to include snippets etc.
#---------------------------------------------------------------------
class KnobScripterTextEditMain(KnobScripterTextEdit):
    def __init__(self, knobScripter, output=None, parent=None):
        super(KnobScripterTextEditMain,self).__init__(knobScripter)
        self.knobScripter = knobScripter
        self.script_output = output
        self._completer = None
        self._currentCompletion = None

        ########
        # FROM NUKE's SCRIPT EDITOR START
        ########
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        #Setup completer
        self._completer = QtWidgets.QCompleter(self)
        self._completer.setWidget(self)
        self._completer.setCompletionMode(QtWidgets.QCompleter.UnfilteredPopupCompletion)
        self._completer.setCaseSensitivity(Qt.CaseSensitive)
        self._completer.setModel(QtGui.QStringListModel())

        self._completer.activated.connect(self.insertCompletion)
        self._completer.highlighted.connect(self.completerHighlightChanged)
        ########
        # FROM NUKE's SCRIPT EDITOR END
        ########

    def findLongestEndingMatch(self, text, dic):
        '''
        If the text ends with a key in the dictionary, it returns the key and value.
        If there are several matches, returns the longest one.
        False if no matches.
        '''
        longest = 0 #len of longest match
        match_key = None
        match_snippet = ""
        for key, val in dic.items():
            match = re.search(r"[\s.({\[,]"+key+r"(?:[\s)\]\"]+|$)",text)
            if match or text == key:
                if len(key) > longest:
                    longest = len(key)
                    match_key = key
                    match_snippet = val
        if match_key is None:
            return False
        return match_key, match_snippet

    def placeholderToEnd(self,text,placeholder):
        '''Returns distance (int) from the first ocurrence of the placeholder, to the end of the string with placeholders removed'''
        from_start = text.find(placeholder)
        if from_start < 0:
            return -1
        #print("from_start="+str(from_start))
        total = len(text.replace(placeholder,""))
        #print("total="+str(total))
        to_end = total-from_start
        #print("to_end="+str(to_end))
        return to_end

    def keyPressEvent(self,event):

        # ADAPTED FROM NUKE's SCRIPT EDITOR
        ctrl = ((event.modifiers() and (Qt.ControlModifier)) != 0)
        alt = ((event.modifiers() and (Qt.AltModifier)) != 0)
        shift = ((event.modifiers() and (Qt.ShiftModifier)) != 0)
        key = event.key()

        #Get completer state
        self._completerShowing = self._completer.popup().isVisible()
        
        #If the completer is showing
        if self._completerShowing :
            tc = self.textCursor()
            #If we're hitting enter, do completion
            if key in [Qt.Key_Return, Qt.Key_Enter, Qt.Key_Tab]:
                if not self._currentCompletion:
                    self._completer.setCurrentRow(0)
                    self._currentCompletion = self._completer.currentCompletion()
                #print str(self._completer.completionModel[0])
                self.insertCompletion(self._currentCompletion)
                self._completer.popup().hide()
                self._completerShowing = False
            #If you're hitting right or escape, hide the popup
            elif key == Qt.Key_Right or key == Qt.Key_Escape:
                self._completer.popup().hide()
                self._completerShowing = False
            #If you hit tab, escape or ctrl-space, hide the completer
            elif key == Qt.Key_Tab or key == Qt.Key_Escape or (ctrl and key == Qt.Key_Space) :
                self._currentCompletion = ""
                self._completer.popup().hide()
                self._completerShowing = False
            #If none of the above, update the completion model
            else :
                QtWidgets.QPlainTextEdit.keyPressEvent(self, event)
                #Edit completion model
                colNum = tc.columnNumber()
                posNum = tc.position()
                inputText = self.toPlainText()
                inputTextSplit = inputText.splitlines()
                runningLength = 0
                currentLine = None
                for line in inputTextSplit :
                    length = len(line)
                    runningLength += length
                    if runningLength >= posNum : 
                        currentLine = line
                        break
                    runningLength += 1
                if currentLine : 
                    token = currentLine.split(" ")[-1]
                    if "(" in token :
                        token = token.split("(")[-1]
                    self.completeTokenUnderCursor(token)
            return

        if type(event) == QtGui.QKeyEvent:
            if not self.knobScripter.current_script_modified:
                self.knobScripter.setScriptModified(True)
            if key == Qt.Key_Escape: # Close the knobscripter...
                self.knobScripter.close()
            elif not ctrl and not alt and not shift and event.key()==Qt.Key_Tab:
                self.placeholder = "$$"
                # 1. Set the cursor
                self.cursor = self.textCursor()

                # 2. Save text before and after
                cpos = self.cursor.position()
                text_before_cursor = self.toPlainText()[:cpos]
                line_before_cursor = text_before_cursor.split('\n')[-1]
                text_after_cursor = self.toPlainText()[cpos:]

                # 3. Check coincidences in snippets dicts
                try: #Meaning snippet found
                    match_key, match_snippet = self.findLongestEndingMatch(line_before_cursor, self.knobScripter.snippets)
                    for i in range(len(match_key)):
                        self.cursor.deletePreviousChar()
                    placeholder_to_end = self.placeholderToEnd(match_snippet,self.placeholder)
                    self.cursor.insertText(match_snippet.replace(self.placeholder,""))
                    if placeholder_to_end >= 0:
                        for i in range(placeholder_to_end):
                            self.cursor.movePosition(QtGui.QTextCursor.PreviousCharacter)
                        self.setTextCursor(self.cursor)
                except: # Meaning snippet not found...
                    # FROM NUKE's SCRIPT EDITOR START
                    tc = self.textCursor()
                    allCode = self.toPlainText()
                    colNum = tc.columnNumber()
                    posNum = tc.position()

                    #...and if there's text in the editor
                    if len(allCode.split()) > 0 : 
                        #There is text in the editor
                        currentLine = tc.block().text()

                        #If you're not at the end of the line just add a tab
                        if colNum < len(currentLine):
                            #If there isn't a ')' directly to the right of the cursor add a tab
                            if currentLine[colNum:colNum+1] != ')' :
                                KnobScripterTextEdit.keyPressEvent(self,event)
                                return
                            #Else show the completer
                            else: 
                                token = currentLine[:colNum].split(" ")[-1]
                                if "(" in token :
                                    token = token.split("(")[-1]

                                self.completeTokenUnderCursor(token)

                                return

                        #If you are at the end of the line, 
                        else : 
                            #If there's nothing to the right of you add a tab
                            if currentLine[colNum-1:] == "" or currentLine.endswith(" "):
                                KnobScripterTextEdit.keyPressEvent(self,event)
                                return
                            #Else update token and show the completer
                            token = currentLine.split(" ")[-1]
                            if "(" in token :
                                token = token.split("(")[-1]

                            self.completeTokenUnderCursor(token)
                            return

                    KnobScripterTextEdit.keyPressEvent(self,event)
            elif event.key() in [Qt.Key_Enter, Qt.Key_Return]:
                modifiers = QtWidgets.QApplication.keyboardModifiers()
                if modifiers == QtCore.Qt.ControlModifier:
                    self.runScript()
                else:
                    KnobScripterTextEdit.keyPressEvent(self,event)
            else:
                KnobScripterTextEdit.keyPressEvent(self,event)

    # ADAPTED FROM NUKE's SCRIPT EDITOR
    def completionsForToken(self, token):
        #TODO: refactor all the snippets part
        def findModules(searchString):
            sysModules =  sys.modules
            globalModules = globals()
            allModules = dict(sysModules, **globalModules)
            allKeys = list(set(globals().keys() + sys.modules.keys()))
            allKeysSorted = [x for x in sorted(set(allKeys))]

            if searchString == '' : 
                matching = []
                for x in allModules :
                    if x.startswith(searchString) :
                        matching.append(x)
                return matching
            else : 
                try : 
                    if sys.modules.has_key(searchString) :
                        return dir(sys.modules['%s' % searchString])
                    elif globals().has_key(searchString): 
                        return dir(globals()['%s' % searchString])
                    else : 
                        return []
                except :
                    return None

        completerText = token

        #Get text before last dot
        moduleSearchString = '.'.join(completerText.split('.')[:-1])

        #Get text after last dot
        fragmentSearchString = completerText.split('.')[-1] if completerText.split('.')[-1] != moduleSearchString else ''

        #Get all the modules that match module search string
        allModules = findModules(moduleSearchString)

        #If no modules found, do a dir
        if not allModules :
            if len(moduleSearchString.split('.')) == 1 :
                matchedModules = []
            else :
                try : 
                    trimmedModuleSearchString = '.'.join(moduleSearchString.split('.')[:-1])
                    matchedModules = [x for x in dir(getattr(sys.modules[trimmedModuleSearchString], moduleSearchString.split('.')[-1])) if '__' not in x and x.startswith(fragmentSearchString)]
                except : 
                    matchedModules = []
        else : 
            matchedModules = [x for x in allModules if '__' not in x and x.startswith(fragmentSearchString)]

        return matchedModules

    def completeTokenUnderCursor(self, token) :

        #Clean token
        token = token.lstrip().rstrip()

        completionList = self.completionsForToken(token)
        if len(completionList) == 0 :
            return

        #Set model for _completer to completion list
        self._completer.model().setStringList(completionList)

        #Set the prefix
        self._completer.setCompletionPrefix(token)

        #Check if we need to make it visible
        if self._completer.popup().isVisible():
            rect = self.cursorRect()
            rect.setWidth(self._completer.popup().sizeHintForColumn(0) + self._completer.popup().verticalScrollBar().sizeHint().width())
            self._completer.complete(rect)
            return

        #Make it visible
        if len(completionList) == 1 :
            self.insertCompletion(completionList[0])
        else :
            rect = self.cursorRect()
            rect.setWidth(self._completer.popup().sizeHintForColumn(0) + self._completer.popup().verticalScrollBar().sizeHint().width())
            self._completer.complete(rect)

        return 

    def insertCompletion(self, completion):
        if completion:
            token = self._completer.completionPrefix()
            if len(token.split('.')) == 0 : 
                tokenFragment = token
            else :
                tokenFragment = token.split('.')[-1]

            textToInsert = completion[len(tokenFragment):]
            tc = self.textCursor()
            tc.insertText(textToInsert)
        return
        
    def completerHighlightChanged(self, highlighted):
        self._currentCompletion = highlighted

    def runScript(self):
        cursor = self.textCursor()
        nukeSEInput = self.knobScripter.nukeSEInput
        if cursor.hasSelection():
            code = cursor.selection().toPlainText()
        else:
            code = self.toPlainText()

        if code == "":
            return

        # Store original ScriptEditor status
        nukeSECursor = nukeSEInput.textCursor()
        origSelection = nukeSECursor.selectedText()
        oldAnchor = nukeSECursor.anchor()
        oldPosition = nukeSECursor.position()

        # Add the code to be executed and select it
        ##nukeSEInput.setFocus()
        nukeSEInput.insertPlainText(code)

        if oldAnchor < oldPosition:
            newAnchor = oldAnchor
            newPosition = nukeSECursor.position()
        else:
            newAnchor = nukeSECursor.position()
            newPosition = oldPosition

        nukeSECursor.setPosition(newAnchor, QtGui.QTextCursor.MoveAnchor)
        nukeSECursor.setPosition(newPosition, QtGui.QTextCursor.KeepAnchor)
        nukeSEInput.setTextCursor(nukeSECursor)

        # Run the code!
        self.knobScripter.nukeSERunBtn.click()

        # Revert ScriptEditor to original
        nukeSEInput.insertPlainText(origSelection)
        nukeSECursor.setPosition(oldAnchor, QtGui.QTextCursor.MoveAnchor)
        nukeSECursor.setPosition(oldPosition, QtGui.QTextCursor.KeepAnchor)
        nukeSEInput.setTextCursor(nukeSECursor)
        #self.setFocus()

#---------------------------------------------------------------------
# Preferences Panel
#---------------------------------------------------------------------
class KnobScripterPrefs(QtWidgets.QDialog):
    def __init__(self, knobScripter):
        super(KnobScripterPrefs, self).__init__(knobScripter)

        # Vars
        self.knobScripter = knobScripter
        self.prefs_txt = self.knobScripter.prefs_txt
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)
        self.oldFontSize = self.knobScripter.script_editor_font.pointSize()
        self.oldDefaultW = self.knobScripter.windowDefaultSize[0]
        self.oldDefaultH = self.knobScripter.windowDefaultSize[1]

        # Widgets
        kspTitle = QtWidgets.QLabel("KnobScripter v" + version)
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
        kspSignature = QtWidgets.QLabel('<a href="http://www.adrianpueyo.com/" style="color:#888;text-decoration:none"><b>adrianpueyo.com</b></a>, 2017-2018')
        kspSignature.setOpenExternalLinks(True)
        kspSignature.setStyleSheet('''color:#555;font-size:9px;''')
        kspSignature.setAlignment(QtCore.Qt.AlignRight)


        fontSizeLabel = QtWidgets.QLabel("Font size:")
        self.fontSizeBox = QtWidgets.QSpinBox()
        self.fontSizeBox.setValue(self.oldFontSize)
        self.fontSizeBox.setMinimum(6)
        self.fontSizeBox.setMaximum(100)
        self.fontSizeBox.valueChanged.connect(self.fontSizeChanged)

        windowWLabel = QtWidgets.QLabel("Width (px):")
        windowWLabel.setToolTip("Default window width in pixels")
        self.windowWBox = QtWidgets.QSpinBox()
        self.windowWBox.setValue(self.knobScripter.windowDefaultSize[0])
        self.windowWBox.setMinimum(200)
        self.windowWBox.setMaximum(4000)
        self.windowWBox.setToolTip("Default window width in pixels")

        windowHLabel = QtWidgets.QLabel("Height (px):")
        windowHLabel.setToolTip("Default window height in pixels")
        self.windowHBox = QtWidgets.QSpinBox()
        self.windowHBox.setValue(self.knobScripter.windowDefaultSize[1])
        self.windowHBox.setMinimum(100)
        self.windowHBox.setMaximum(2000)
        self.windowHBox.setToolTip("Default window height in pixels")
        
        tabSpaceLabel = QtWidgets.QLabel("Tab spaces:")
        tabSpaceLabel.setToolTip("Number of spaces to add with the tab key.")
        self.tabSpace2 = QtWidgets.QRadioButton("2")
        self.tabSpace4 = QtWidgets.QRadioButton("4")
        tabSpaceButtonGroup = QtWidgets.QButtonGroup(self)
        tabSpaceButtonGroup.addButton(self.tabSpace2)
        tabSpaceButtonGroup.addButton(self.tabSpace4)
        self.tabSpace2.setChecked(self.knobScripter.tabSpaces == 2)
        self.tabSpace4.setChecked(self.knobScripter.tabSpaces == 4)
        
        pinDefaultLabel = QtWidgets.QLabel("Always on top:")
        pinDefaultLabel.setToolTip("Default mode of the PIN toggle.")
        self.pinDefaultOn = QtWidgets.QRadioButton("On")
        self.pinDefaultOff = QtWidgets.QRadioButton("Off")
        pinDefaultButtonGroup = QtWidgets.QButtonGroup(self)
        pinDefaultButtonGroup.addButton(self.pinDefaultOn)
        pinDefaultButtonGroup.addButton(self.pinDefaultOff)
        self.pinDefaultOn.setChecked(self.knobScripter.pinned == True)
        self.pinDefaultOff.setChecked(self.knobScripter.pinned == False)
        self.pinDefaultOn.clicked.connect(lambda:self.knobScripter.pin(True))
        self.pinDefaultOff.clicked.connect(lambda:self.knobScripter.pin(False))


        self.buttonBox = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        self.buttonBox.accepted.connect(self.savePrefs)
        self.buttonBox.rejected.connect(self.cancelPrefs)

        # Loaded custom values
        self.ksPrefs = self.knobScripter.loadPrefs()
        if self.ksPrefs != []:
            try:
                self.fontSizeBox.setValue(self.ksPrefs['font_size'])
                self.windowWBox.setValue(self.ksPrefs['window_default_w'])
                self.windowHBox.setValue(self.ksPrefs['window_default_h'])
                self.tabSpace2.setChecked(self.ksPrefs['tab_spaces'] == 2)
                self.tabSpace4.setChecked(self.ksPrefs['tab_spaces'] == 4)
                self.pinDefaultOn.setChecked(self.ksPrefs['pin_default'] == 1)
                self.pinDefaultOff.setChecked(self.ksPrefs['pin_default'] == 0)
                
            except:
                pass

        # Layouts
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
        
        pinDefaultButtons_layout = QtWidgets.QHBoxLayout()
        pinDefaultButtons_layout.addWidget(self.pinDefaultOn)
        pinDefaultButtons_layout.addWidget(self.pinDefaultOff)
        pinDefault_layout = QtWidgets.QHBoxLayout()
        pinDefault_layout.addWidget(pinDefaultLabel)
        pinDefault_layout.addLayout(pinDefaultButtons_layout)
        

        self.master_layout = QtWidgets.QVBoxLayout()
        self.master_layout.addWidget(kspTitle)
        self.master_layout.addWidget(kspSignature)
        self.master_layout.addWidget(kspLine)
        self.master_layout.addLayout(fontSize_layout)
        self.master_layout.addLayout(windowW_layout)
        self.master_layout.addLayout(windowH_layout)
        self.master_layout.addLayout(tabSpaces_layout)
        self.master_layout.addLayout(pinDefault_layout)
        self.master_layout.addWidget(self.buttonBox)
        self.setLayout(self.master_layout)
        self.setFixedSize(self.minimumSize())

    def savePrefs(self):
        ks_prefs = {
            'font_size': self.fontSizeBox.value(),
            'window_default_w': self.windowWBox.value(),
            'window_default_h': self.windowHBox.value(),
            'tab_spaces': self.tabSpaceValue(),
            'pin_default': self.pinDefaultValue()
        }
        self.knobScripter.script_editor.setFont(self.knobScripter.script_editor_font)
        self.knobScripter.tabSpaces = self.tabSpaceValue()
        self.knobScripter.script_editor.tabSpaces = self.tabSpaceValue()
        with open(self.prefs_txt,"w") as f:
            prefs = json.dump(ks_prefs, f, sort_keys=True, indent=4)
            self.accept()
        return prefs

    def cancelPrefs(self):
        self.knobScripter.script_editor_font.setPointSize(self.oldFontSize)
        self.knobScripter.script_editor.setFont(self.knobScripter.script_editor_font)
        self.reject()

    def fontSizeChanged(self):
        self.knobScripter.script_editor_font.setPointSize(self.fontSizeBox.value())
        self.knobScripter.script_editor.setFont(self.knobScripter.script_editor_font)
        return
    def tabSpaceValue(self):
        return 2 if self.tabSpace2.isChecked() else 4
    def pinDefaultValue(self):
        return 1 if self.pinDefaultOn.isChecked() else 0

    def closeEvent(self,event):
        self.cancelPrefs()
        self.close()

def updateContext():
    ''' 
    Get the current selection of nodes with their appropiate context
    Doing this outside the KnobScripter -> forces context update inside groups when needed
    '''
    global knobScripterSelectedNodes
    knobScripterSelectedNodes = nuke.selectedNodes()
    return

#--------------------------------
# FindReplace
#--------------------------------
class FindReplaceWidget(QtWidgets.QWidget):
    ''' SearchReplace Widget for the knobscripter. FindReplaceWidget(editor = QPlainTextEdit) '''
    def __init__(self, parent):
        super(FindReplaceWidget,self).__init__(parent)

        self.editor = parent.script_editor

        self.initUI()

    def initUI(self):

        #--------------
        # Find Row
        #--------------

        # Widgets
        self.find_label = QtWidgets.QLabel("Find:")
        #self.find_label.setSizePolicy(QtWidgets.QSizePolicy.Fixed,QtWidgets.QSizePolicy.Fixed)
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
        self.find_layout.addWidget(self.find_lineEdit, stretch = 1)
        self.find_layout.addWidget(self.find_next_button)
        self.find_layout.addWidget(self.find_prev_button)


        #--------------
        # Replace Row
        #--------------

        # Widgets
        self.replace_label = QtWidgets.QLabel("Replace:")
        #self.replace_label.setSizePolicy(QtWidgets.QSizePolicy.Fixed,QtWidgets.QSizePolicy.Fixed)
        self.replace_label.setFixedWidth(50)
        self.replace_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.replace_lineEdit = QtWidgets.QLineEdit()
        self.replace_button = QtWidgets.QPushButton("Replace")
        self.replace_button.clicked.connect(self.replace)
        self.replace_all_button = QtWidgets.QPushButton("Replace All")
        self.replace_all_button.clicked.connect(lambda: self.replace(rep_all = True))
        self.replace_lineEdit.returnPressed.connect(self.replace_button.click)

        # Layout
        self.replace_layout = QtWidgets.QHBoxLayout()
        self.replace_layout.addWidget(self.replace_label)
        self.replace_layout.addWidget(self.replace_lineEdit, stretch = 1)
        self.replace_layout.addWidget(self.replace_button)
        self.replace_layout.addWidget(self.replace_all_button)


        # Info text
        self.info_text = QtWidgets.QLabel("")
        self.info_text.setVisible(False)
        self.info_text.mousePressEvent = lambda x:self.info_text.setVisible(False)
        #f = self.info_text.font()
        #f.setItalic(True)
        #self.info_text.setFont(f)
        #self.info_text.clicked.connect(lambda:self.info_text.setVisible(False))

        # Divider line
        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.HLine)
        line.setFrameShadow(QtWidgets.QFrame.Sunken)
        line.setLineWidth(0)
        line.setMidLineWidth(1)
        line.setFrameShadow(QtWidgets.QFrame.Sunken)

        #--------------
        # Main Layout
        #--------------

        self.layout = QtWidgets.QVBoxLayout()
        self.layout.addSpacing(4)
        self.layout.addWidget(self.info_text)
        self.layout.addLayout(self.find_layout)
        self.layout.addLayout(self.replace_layout)
        self.layout.setSpacing(4)
        try: #>n11
            self.layout.setMargin(2)
        except: #<n10
            self.layout.setContentsMargins(2,2,2,2)
        self.layout.addSpacing(4)
        self.layout.addWidget(line)
        self.setLayout(self.layout)
        self.setTabOrder(self.find_lineEdit, self.replace_lineEdit)
        #self.adjustSize()
        #self.setMaximumHeight(180)

    def find(self, find_str = "", match_case = True):
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
            flags=flags|QtGui.QTextDocument.FindCaseSensitively

        # Find next
        r = self.editor.find(find_str,flags)

        cursor.endEditBlock()

        self.editor.setFocus()
        self.editor.show()
        return r

    def findBack(self, find_str = "", match_case = True):
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
        flags=flags|QtGui.QTextDocument.FindBackward
        if match_case:
            flags=flags|QtGui.QTextDocument.FindCaseSensitively

        # Find prev
        r = self.editor.find(find_str,flags)
        cursor.endEditBlock()
        self.editor.setFocus()
        return r

    def replace(self, find_str = "", rep_str = "", rep_all=False):
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
        cursor_orig_pos = cursor.position()
        cursor.beginEditBlock()

        # Use flags for case match
        flags = QtGui.QTextDocument.FindFlags()
        flags=flags|QtGui.QTextDocument.FindCaseSensitively

        if rep_all == True:
            cursor.movePosition(QtGui.QTextCursor.Start)
            self.editor.setTextCursor(cursor)
            cursor = self.editor.textCursor()
            rep_count = 0
            while True:
                if not cursor.hasSelection() or cursor.selectedText() != find_str:
                    self.editor.find(find_str,flags) # Find next
                    cursor = self.editor.textCursor()
                    if not cursor.hasSelection():
                        break
                else:
                    cursor.insertText(rep_str)
                    rep_count += 1
            self.info_text.setText("              Replaced "+str(rep_count)+" matches.")
            self.info_text.setVisible(True)
        else: #If not "find all"
            if not cursor.hasSelection() or cursor.selectedText() != find_str:
                self.editor.find(find_str,flags) # Find next
                if not cursor.hasSelection() and matches>0: # If not found but there are matches, start over
                    cursor.movePosition(QtGui.QTextCursor.Start)
                    self.editor.setTextCursor(cursor)
                    self.editor.find(find_str,flags)
            else:
                cursor.insertText(rep_str)
                self.editor.find(rep_str,flags|QtGui.QTextDocument.FindBackward)

        cursor.endEditBlock()
        self.replace_lineEdit.setFocus()
        return


#--------------------------------
# Snippets
#--------------------------------
class SnippetsPanel(QtWidgets.QDialog):
    def __init__(self, parent):
        super(SnippetsPanel, self).__init__(parent)
        self.mainWidget = parent

        self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)
        self.setWindowTitle("Snippet editor")

        self.snippets_txt_path = self.mainWidget.snippets_txt_path
        self.snippets_dict = self.mainWidget.loadSnippets()
        #self.snippets_dict = snippets_dic

        #self.saveSnippets(snippets_dic)

        self.initUI()
        self.resize(500,300)

    def initUI(self):
        self.layout = QtWidgets.QVBoxLayout()

        # First Area (Titles)
        title_layout = QtWidgets.QHBoxLayout()
        shortcuts_label = QtWidgets.QLabel("Shortcut")
        code_label = QtWidgets.QLabel("Code snippet")
        title_layout.addWidget(shortcuts_label,stretch=1)
        title_layout.addWidget(code_label,stretch=2)
        self.layout.addLayout(title_layout)


        # Main Scroll area
        self.scroll_content = QtWidgets.QWidget()
        self.scroll_layout = QtWidgets.QVBoxLayout()

        for i, (key, val) in enumerate(self.snippets_dict.items()):
            snippet_edit = SnippetEdit(key, val)
            self.scroll_layout.insertWidget(-1, snippet_edit)

        self.scroll_content.setLayout(self.scroll_layout)

        # Scroll Area Properties
        self.scroll = QtWidgets.QScrollArea()
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setWidgetResizable(True)
        self.scroll.setWidget(self.scroll_content)

        self.layout.addWidget(self.scroll)

        # Lower buttons
        self.bottom_layout = QtWidgets.QHBoxLayout()

        self.add_btn = QtWidgets.QPushButton("Add snippet")
        self.add_btn.setToolTip("Create empty fields for an extra snippet.")
        self.add_btn.clicked.connect(self.addSnippet)
        self.bottom_layout.addWidget(self.add_btn)

        self.bottom_layout.addStretch()

        self.save_btn = QtWidgets.QPushButton('OK')
        self.save_btn.setToolTip("Save the snippets into a json file and close the panel.")
        self.save_btn.clicked.connect(self.okPressed)
        self.bottom_layout.addWidget(self.save_btn)

        self.cancel_btn = QtWidgets.QPushButton("Cancel")
        self.cancel_btn.setToolTip("Cancel any new snippets or modifications.")
        self.cancel_btn.clicked.connect(self.close)
        self.bottom_layout.addWidget(self.cancel_btn)

        self.apply_btn = QtWidgets.QPushButton('Apply')
        self.apply_btn.setToolTip("Save the snippets into a json file.")
        self.apply_btn.setShortcut('Ctrl+S')
        self.apply_btn.clicked.connect(self.saveSnippets)
        self.bottom_layout.addWidget(self.apply_btn)

        self.help_btn = QtWidgets.QPushButton('Help')
        self.help_btn.setShortcut('F1')
        self.help_btn.clicked.connect(self.showHelp)
        self.bottom_layout.addWidget(self.help_btn)


        self.layout.addLayout(self.bottom_layout)

        self.setLayout(self.layout)

    def getSnippetsAsDict(self):
        dic = {}
        num_snippets = self.scroll_layout.count()
        for s in range(num_snippets):
            se = self.scroll_layout.itemAt(s).widget()
            key = se.shortcut_editor.text()
            val = se.snippet_editor.toPlainText()
            if key != "":
                dic[key] = val
        return dic

    def saveSnippets(self,snippets = ""):
        if snippets == "":
            snippets = self.getSnippetsAsDict()
        with open(self.snippets_txt_path,"w") as f:
            prefs = json.dump(snippets, f, sort_keys=True, indent=4)
        return prefs

    def okPressed(self):
        self.saveSnippets()
        self.mainWidget.loadSnippets()
        self.accept()

    def addSnippet(self, key="", val=""):
        se = SnippetEdit(key, val)
        self.scroll_layout.insertWidget(0, se)
        self.show()
        return se

    def showHelp(self):
        ''' Create a new snippet, auto-completed with the help '''
        help_key = "help"
        help_val = """Snippets are a convenient way to have code blocks that you can call through a shortcut.\n\n1. Simply write a shortcut on the text input field on the left. You can see this one is set to "test".\n\n2. Then, write a code or whatever in this script editor. You can include $$ as the placeholder for where you'll want the mouse cursor to appear.\n\n3. Finally, click OK or Apply to save the snippets. On the main script editor, you'll be able to call any snippet by writing the shortcut (in this example: help) and pressing the Tab key.\n\nIn order to remove a snippet, simply leave the shortcut and contents blank, and save the snippets."""
        help_se = self.addSnippet(help_key,help_val)
        help_se.snippet_editor.resize(160,160)

class SnippetEdit(QtWidgets.QWidget):
    ''' Simple widget containing two fields, for the snippet shortcut and content '''
    def __init__(self, key="", val=""):
        super(SnippetEdit,self).__init__()

        self.layout = QtWidgets.QHBoxLayout()

        self.shortcut_editor = QtWidgets.QLineEdit(self)
        f = self.shortcut_editor.font()
        f.setWeight(QtGui.QFont.Bold)
        self.shortcut_editor.setFont(f)
        self.shortcut_editor.setText(str(key))
        #self.snippet_editor = QtWidgets.QTextEdit(self)
        self.snippet_editor = KnobScripterTextEdit()
        self.snippet_editor.setMinimumHeight(100)
        self.snippet_editor.setStyleSheet('background:#282828;color:#EEE;') # Main Colors
        KSScriptEditorHighlighter(self.snippet_editor.document())
        self.script_editor_font = QtGui.QFont()
        self.script_editor_font.setFamily("Courier")
        self.script_editor_font.setStyleHint(QtGui.QFont.Monospace)
        self.script_editor_font.setFixedPitch(True)
        self.script_editor_font.setPointSize(11)
        self.snippet_editor.setFont(self.script_editor_font)
        self.snippet_editor.setTabStopWidth(4 * QtGui.QFontMetrics(self.script_editor_font).width(' '))

        self.snippet_editor.resize(90,90)
        self.snippet_editor.setPlainText(str(val))
        self.layout.addWidget(self.shortcut_editor, stretch=1, alignment = Qt.AlignTop)
        self.layout.addWidget(self.snippet_editor, stretch=2)
        try: #>n11
            self.layout.setMargin(0)
        except: #<n10
            self.layout.setContentsMargins(0,0,0,0)


        self.setLayout(self.layout)

#--------------------------------
# Implementation
#--------------------------------

def showKnobScripter(knob="knobChanged"):
    selection = nuke.selectedNodes()
    if not len(selection):
        pan = KnobScripter()
    else:
        pan = KnobScripter(selection[0], knob)
    pan.show()

def addKnobScripterPanel():
    global knobScripterPanel
    try:
        knobScripterPanel = panels.registerWidgetAsPanel('nuke.KnobScripterPane', 'Knob Scripter',
                                     'com.adrianpueyo.KnobScripterPane')
        knobScripterPanel.addToPane(nuke.getPaneFor('Properties.1'))

    except:
        knobScripterPanel = panels.registerWidgetAsPanel('nuke.KnobScripterPane', 'Knob Scripter', 'com.adrianpueyo.KnobScripterPane')

nuke.KnobScripterPane = KnobScripterPane

ksShortcut = "alt+z"
addKnobScripterPanel()
nuke.menu('Nuke').addCommand('Edit/Node/Open Floating Knob Scripter', showKnobScripter, ksShortcut)
nuke.menu('Nuke').addCommand('Edit/Node/Update KnobScripter Context', updateContext).setVisible(False)

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

try:
    from PySide import QtCore, QtGui as QtWidgets
except ImportError:
    from PySide2 import QtWidgets, QtGui, QtCore
    from PySide2.QtCore import Qt


class KnobScripter(QtWidgets.QWidget):

    def __init__(self,node=nuke.root(),knob="knobChanged"):

        super(KnobScripter,self).__init__()
        self.node = node
        self.knob = knob
        self.unsavedKnobs = {}
        self.scrollPos = {}
        self.fontSize = 11
        self.tabSpaces = 4
        self.windowDefaultSize = [500, 300]
        self.pinned = 1
        self.toLoadKnob = True

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

        # KnobScripter Panel
        self.resize(self.windowDefaultSize[0],self.windowDefaultSize[1])
        self.setWindowTitle("KnobScripter - %s %s" % (self.node.fullName(),self.knob))
        self.move(QtGui.QCursor().pos() - QtCore.QPoint(32,74))

        # Node/Knob Selection menu
        self.current_node_label = QtWidgets.QLabel("Node: <b> %s </b>"%self.node.fullName())
        self.current_node_change_button = QtWidgets.QPushButton("Change")
        self.current_node_change_button.setToolTip("Change node to selected")
        self.current_node_change_button.clicked.connect(self.changeNode)
        self.current_knob_label = QtWidgets.QLabel("Knob: ")
        self.current_knob_dropdown = QtWidgets.QComboBox()
        self.current_knob_dropdown.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)
        self.updateKnobDropdown()
        self.current_knob_dropdown.currentIndexChanged.connect(lambda: self.loadKnobValue(False,updateDict=True))
        self.snippets_button = QtWidgets.QPushButton("Snippets")
        self.snippets_button.setToolTip("Call the snippets by writing the shortcut and pressing Tab.")
        self.snippets_button.clicked.connect(self.openSnippets)
        self.current_knob_prefs_button = QtWidgets.QPushButton("Preferences")
        self.current_knob_prefs_button.clicked.connect(self.openPrefs)

        # Script Editor (adapted from Wouter Gilsing's, read class definition below)
        self.scriptEditorScript = KnobScripterTextEditMain(self)
        self.scriptEditorScript.setMinimumHeight(100)
        self.scriptEditorScript.setStyleSheet('background:#282828;color:#EEE;') # Main Colors
        KSScriptEditorHighlighter(self.scriptEditorScript.document())
        self.scriptEditorFont = QtGui.QFont()
        self.scriptEditorFont.setFamily("Courier")
        self.scriptEditorFont.setStyleHint(QtGui.QFont.Monospace)
        self.scriptEditorFont.setFixedPitch(True)
        self.scriptEditorFont.setPointSize(self.fontSize)
        self.scriptEditorScript.setFont(self.scriptEditorFont)
        self.scriptEditorScript.setTabStopWidth(self.tabSpaces * QtGui.QFontMetrics(self.scriptEditorFont).width(' '))

        # Lower Buttons
        self.get_btn = QtWidgets.QPushButton("Reload")
        self.get_btn.setToolTip("Reload the contents of the knob. Will overwrite the KnobScripter's script.")
        self.get_all_btn = QtWidgets.QPushButton("Reload All")
        self.get_all_btn.setToolTip("Reload the contents of all knobs. Will clear the KnobScripter's memory.")
        self.arrows_label = QtWidgets.QLabel("&raquo;")
        self.arrows_label.setTextFormat(QtCore.Qt.RichText)
        self.arrows_label.setStyleSheet('color:#BBB')
        self.set_btn = QtWidgets.QPushButton("Save")
        self.set_btn.setShortcut('Ctrl+S')
        self.set_btn.setToolTip("(Ctrl+S) Save the script above into the knob. It won't be saved until you click this button.")
        self.set_all_btn = QtWidgets.QPushButton("Save All")
        self.set_all_btn.setToolTip("Save all changes into the knobs.")
        self.pin_btn = QtWidgets.QPushButton("PIN")
        self.pin_btn.setCheckable(True)
        if self.pinned:
            self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)
            self.pin_btn.toggle()
        self.pin_btn.setToolTip("Keep the KnobScripter on top of all other windows.")
        self.pin_btn.setFocusPolicy(QtCore.Qt.NoFocus)
        self.pin_btn.setMaximumWidth(self.pin_btn.fontMetrics().boundingRect("pin").width() + 12)
        self.close_btn = QtWidgets.QPushButton("Close")
        self.get_btn.clicked.connect(self.loadKnobValue)
        self.get_all_btn.clicked.connect(self.loadAllKnobValues)
        self.set_btn.clicked.connect(lambda: self.saveKnobValue(False))
        self.set_all_btn.clicked.connect(self.saveAllKnobValues)
        self.pin_btn.clicked[bool].connect(self.pin)
        self.close_btn.clicked.connect(self.close)

        # Layouts
        master_layout = QtWidgets.QVBoxLayout()
        nodeknob_layout = QtWidgets.QHBoxLayout()
        nodeknob_layout.addWidget(self.current_node_label)
        nodeknob_layout.addWidget(self.current_node_change_button)
        nodeknob_layout.addSpacing(10)
        nodeknob_layout.addWidget(self.current_knob_label)
        nodeknob_layout.addWidget(self.current_knob_dropdown)
        nodeknob_layout.addSpacing(10)
        nodeknob_layout.addStretch()
        nodeknob_layout.addWidget(self.snippets_button)
        nodeknob_layout.addWidget(self.current_knob_prefs_button)
        self.btn_layout = QtWidgets.QHBoxLayout()
        self.btn_layout.addWidget(self.get_btn)
        self.btn_layout.addWidget(self.get_all_btn)
        self.btn_layout.addWidget(self.arrows_label)
        self.btn_layout.addWidget(self.set_btn)
        self.btn_layout.addWidget(self.set_all_btn)
        self.btn_layout.addStretch()
        self.btn_layout.addWidget(self.pin_btn)
        self.btn_layout.addWidget(self.close_btn)
        master_layout.addLayout(nodeknob_layout)
        master_layout.addWidget(self.scriptEditorScript)
        master_layout.addLayout(self.btn_layout)
        self.setLayout(master_layout)

        # Set default values
        self.setCurrentKnob(self.knob)
        self.loadKnobValue(check = False)
        self.scriptEditorScript.setFocus()

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
        edited_knobValue = self.scriptEditorScript.toPlainText()
        self.unsavedKnobs[self.knob] = edited_knobValue
        if len(self.unsavedKnobs) > 0:
            for k in self.unsavedKnobs.copy():
                if self.node.knob(k):
                    if str(self.node.knob(k).value()) == str(self.unsavedKnobs[k]):
                        del self.unsavedKnobs[k]
                else:
                    del self.unsavedKnobs[k]
        return len(self.unsavedKnobs)
    def changeNode(self, newNode=""):
        ''' Change node '''
        nuke.menu("Nuke").findItem("Edit/Node/Update KnobScripter Context").invoke()
        selection = knobScripterSelectedNodes
        updatedCount = self.updateUnsavedKnobs()
        if not len(selection):
            self.messageBox("Please select one or more nodes!")
        else:
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
            self.scriptEditorScript.setPlainText("")
            self.unsavedKnobs = {}
            self.scrollPos = {}
            self.setWindowTitle("KnobScripter - %s %s" % (self.node.fullName(), self.knob))
            self.current_node_label.setText("Node: <b> %s </b>" % self.node.fullName())
            ########TODO: REMOVE AND RE-ADD THE KNOB DROPDOWN
            self.toLoadKnob = False
            self.updateKnobDropdown()
            #self.current_knob_dropdown.repaint()
            ###self.current_knob_dropdown.setMinimumWidth(self.current_knob_dropdown.minimumSizeHint().width())
            self.toLoadKnob = True
            self.setCurrentKnob(self.knob)
            self.loadKnobValue(False)
            self.scriptEditorScript.setFocus()
            #self.current_knob_dropdown.setMinimumContentsLength(80)
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
        msgBox = QtWidgets.QMessageBox()
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
        self.scrollPos[self.knob] = self.scriptEditorScript.verticalScrollBar().value()

    def loadKnobValue(self, check=True, updateDict=False):
        ''' Get the content of the knob knobChanged and populate the editor '''
        if self.toLoadKnob == False:
            return
        dropdown_value = self.current_knob_dropdown.currentText().split(" (")[0]
        try:
            obtained_knobValue = str(self.node[dropdown_value].value())
            obtained_scrollValue = 0
            edited_knobValue = self.scriptEditorScript.toPlainText()
        except:
            error_message = QtWidgets.QMessageBox.information(None, "", "Unable to find %s.%s"%(self.node.name(),dropdown_value))
            error_message.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
            error_message.exec_()
            return
        # If there were changes to the previous knob, update the dictionary
        if updateDict==True:
            self.unsavedKnobs[self.knob] = edited_knobValue
            self.scrollPos[self.knob] = self.scriptEditorScript.verticalScrollBar().value()
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
        self.scriptEditorScript.setPlainText(obtained_knobValue)
        self.scriptEditorScript.verticalScrollBar().setValue(obtained_scrollValue)
        self.setWindowTitle("KnobScripter - %s %s" % (self.node.name(), self.knob))
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
        edited_knobValue = self.scriptEditorScript.toPlainText()
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

    def pin(self, pressed):
        if pressed:
            self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)
            self.pinned = True
            self.show()
        else:
            self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowStaysOnTopHint)
            self.pinned = False
            self.show()
    def closeEvent(self, event):
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
                event.accept()
                return
            elif reply == QtWidgets.QMessageBox.Cancel:
                event.ignore()
                return
        else:
            event.accept()

class KnobScripterPane(KnobScripter):
    def __init__(self, node=nuke.root(), knob="knobChanged"):
        super(KnobScripterPane, self).__init__()
        self.btn_layout.removeWidget(self.pin_btn)
        self.btn_layout.removeWidget(self.close_btn)
        self.pin_btn.deleteLater()
        self.close_btn.deleteLater()
        self.pin_btn = None
        self.close_btn = None

        ksSignature = QtWidgets.QLabel(
            '<a href="http://www.adrianpueyo.com/" style="color:#888;text-decoration:none"><b>KnobScripter </b></a>v'+version)
        ksSignature.setOpenExternalLinks(True)
        ksSignature.setStyleSheet('''color:#555;font-size:9px;''')
        self.btn_layout.addWidget(ksSignature)

    def deleteCloseButton(self):
        b = self.btn_layout.takeAt(2)
        b.widget().deleteLater()



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
            painter.setFont(self.knobScripter.scriptEditorFont)

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

    #--------------------------------------------------------------------------------------------------
    # Auto indent
    #--------------------------------------------------------------------------------------------------

    def keyPressEvent(self, event):
        '''
        Custom actions for specific keystrokes
        '''

        #if Tab convert to Space
        if event.key() == 16777217:
            self.indentation('indent')

        #if Shift+Tab remove indent
        elif event.key() == 16777218:

            self.indentation('unindent')

        #if BackSpace try to snap to previous indent level
        elif event.key() == 16777219:
            if not self.unindentBackspace():
                QtWidgets.QPlainTextEdit.keyPressEvent(self, event)

        #if enter or return, match indent level
        elif event.key() in [16777220 ,16777221]:
            #QtWidgets.QPlainTextEdit.keyPressEvent(self, event)
            self.indentNewLine()
        else:
            QtWidgets.QPlainTextEdit.keyPressEvent(self, event)

    #--------------------------------------------------------------------------------------------------

    def getCursorInfo(self):

        self.cursor = self.textCursor()

        self.firstChar =  self.cursor.selectionStart()
        self.lastChar =  self.cursor.selectionEnd()

        self.noSelection = False
        if self.firstChar == self.lastChar:
            self.noSelection = True

        self.originalPosition = self.cursor.position()
        self.cursorBlockPos = self.cursor.positionInBlock()
    #--------------------------------------------------------------------------------------------------

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

    #--------------------------------------------------------------------------------------------------
    #current line hightlighting
    #--------------------------------------------------------------------------------------------------

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

#---------------------------------------------------------------------
# Modified KnobScripterTextEdit to include snippets etc.
#---------------------------------------------------------------------
class KnobScripterTextEditMain(KnobScripterTextEdit):
    def __init__(self, knobScripter):
        super(KnobScripterTextEditMain,self).__init__(knobScripter)
        self.knobScripter = knobScripter

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
            match = re.search(r"[\s.]"+key+"$",text)
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
        if type(event) == QtGui.QKeyEvent:
            if event.key()==Qt.Key_Tab:
                self.placeholder = "$$"
                # 1. Set the cursor
                self.cursor = self.textCursor()

                # 2. Save text before and after
                cpos = self.cursor.position()
                text_before_cursor = self.toPlainText()[:cpos]
                text_after_cursor = self.toPlainText()[cpos:]

                # 3. Check coincidences in snippets dicts
                try:
                    match_key, match_snippet = self.findLongestEndingMatch(text_before_cursor, self.knobScripter.snippets)
                    for i in range(len(match_key)):
                        self.cursor.deletePreviousChar()
                    placeholder_to_end = self.placeholderToEnd(match_snippet,self.placeholder)
                    self.cursor.insertText(match_snippet.replace(self.placeholder,""))
                    if placeholder_to_end >= 0:
                        for i in range(placeholder_to_end):
                            self.cursor.movePosition(QtGui.QTextCursor.PreviousCharacter)
                        self.setTextCursor(self.cursor)
                except:
                    KnobScripterTextEdit.keyPressEvent(self,event)
            else:
                KnobScripterTextEdit.keyPressEvent(self,event)


#---------------------------------------------------------------------
# Preferences Panel
#---------------------------------------------------------------------
class KnobScripterPrefs(QtWidgets.QDialog):
    def __init__(self, knobScripter):
        super(KnobScripterPrefs, self).__init__()

        # Vars
        self.knobScripter = knobScripter
        self.prefs_txt = self.knobScripter.prefs_txt
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)
        self.oldFontSize = self.knobScripter.scriptEditorFont.pointSize()
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
        
        pinDefaultLabel = QtWidgets.QLabel("PIN Default:")
        pinDefaultLabel.setToolTip("Default mode of the PIN toggle.")
        self.pinDefaultOn = QtWidgets.QRadioButton("On")
        self.pinDefaultOff = QtWidgets.QRadioButton("Off")
        pinDefaultButtonGroup = QtWidgets.QButtonGroup(self)
        pinDefaultButtonGroup.addButton(self.pinDefaultOn)
        pinDefaultButtonGroup.addButton(self.pinDefaultOff)
        self.pinDefaultOn.setChecked(self.knobScripter.pinned == True)
        self.pinDefaultOff.setChecked(self.knobScripter.pinned == False)


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
        

        master_layout = QtWidgets.QVBoxLayout()
        master_layout.addWidget(kspTitle)
        master_layout.addWidget(kspSignature)
        master_layout.addWidget(kspLine)
        master_layout.addLayout(fontSize_layout)
        master_layout.addLayout(windowW_layout)
        master_layout.addLayout(windowH_layout)
        master_layout.addLayout(tabSpaces_layout)
        master_layout.addLayout(pinDefault_layout)
        master_layout.addWidget(self.buttonBox)
        self.setLayout(master_layout)
        self.setFixedSize(self.minimumSize())

    def savePrefs(self):
        ks_prefs = {
            'font_size': self.fontSizeBox.value(),
            'window_default_w': self.windowWBox.value(),
            'window_default_h': self.windowHBox.value(),
            'tab_spaces': self.tabSpaceValue(),
            'pin_default': self.pinDefaultValue()
        }
        self.knobScripter.scriptEditorScript.setFont(self.knobScripter.scriptEditorFont)
        self.knobScripter.tabSpaces = self.tabSpaceValue()
        self.knobScripter.scriptEditorScript.tabSpaces = self.tabSpaceValue()
        with open(self.prefs_txt,"w") as f:
            prefs = json.dump(ks_prefs, f)
            self.accept()
        return prefs

    def cancelPrefs(self):
        self.knobScripter.scriptEditorFont.setPointSize(self.oldFontSize)
        self.knobScripter.scriptEditorScript.setFont(self.knobScripter.scriptEditorFont)
        self.reject()

    def fontSizeChanged(self):
        self.knobScripter.scriptEditorFont.setPointSize(self.fontSizeBox.value())
        self.knobScripter.scriptEditorScript.setFont(self.knobScripter.scriptEditorFont)
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
# Snippets
#--------------------------------
class SnippetsPanel(QtWidgets.QDialog):
    def __init__(self, mainWidget):
        super(SnippetsPanel, self).__init__()
        self.mainWidget = mainWidget

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
        self.btn_layout = QtWidgets.QHBoxLayout()

        self.add_btn = QtWidgets.QPushButton("Add snippet")
        self.add_btn.setToolTip("Create empty fields for an extra snippet.")
        self.add_btn.clicked.connect(self.addSnippet)
        self.btn_layout.addWidget(self.add_btn)

        self.btn_layout.addStretch()

        self.save_btn = QtWidgets.QPushButton('OK')
        self.save_btn.setToolTip("Save the snippets into a json file and close the panel.")
        self.save_btn.clicked.connect(self.okPressed)
        self.btn_layout.addWidget(self.save_btn)

        self.cancel_btn = QtWidgets.QPushButton("Cancel")
        self.cancel_btn.setToolTip("Cancel any new snippets or modifications.")
        self.cancel_btn.clicked.connect(self.close)
        self.btn_layout.addWidget(self.cancel_btn)

        self.apply_btn = QtWidgets.QPushButton('Apply')
        self.apply_btn.setToolTip("Save the snippets into a json file.")
        self.apply_btn.setShortcut('Ctrl+S')
        self.apply_btn.clicked.connect(self.saveSnippets)
        self.btn_layout.addWidget(self.apply_btn)

        self.help_btn = QtWidgets.QPushButton('Help')
        self.help_btn.setShortcut('F1')
        self.help_btn.clicked.connect(self.showHelp)
        self.btn_layout.addWidget(self.help_btn)


        self.layout.addLayout(self.btn_layout)

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
            prefs = json.dump(snippets, f)
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
        self.scriptEditorFont = QtGui.QFont()
        self.scriptEditorFont.setFamily("Courier")
        self.scriptEditorFont.setStyleHint(QtGui.QFont.Monospace)
        self.scriptEditorFont.setFixedPitch(True)
        self.scriptEditorFont.setPointSize(11)
        self.snippet_editor.setFont(self.scriptEditorFont)
        self.snippet_editor.setTabStopWidth(4 * QtGui.QFontMetrics(self.scriptEditorFont).width(' '))





        self.snippet_editor.resize(90,90)
        self.snippet_editor.setPlainText(str(val))
        self.layout.addWidget(self.shortcut_editor, stretch=1, alignment = Qt.AlignTop)
        self.layout.addWidget(self.snippet_editor, stretch=2)

        self.layout.setMargin(0)
        self.layout.setMargin(0)

        self.setLayout(self.layout)

#--------------------------------
# Implementation
#--------------------------------

def showKnobScripter(knob="knobChanged"):
    selection = nuke.selectedNodes()
    if not len(selection):
        nuke.message("Please select one or more nodes!")
    else:
        if len(selection) > 1:
            nuke.message("More than one node selected.\nOpening knobChanged editor for %s" % selection[0].name())
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

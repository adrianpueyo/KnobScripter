# -*- coding: utf-8 -*-
""" KnobScripter's Main Script Editor: Version of KSScriptEditor with extended functionality.

The KSScriptEditorMain is an extension of KSScriptEditor (QPlainTextEdit) which includes
snippet functionality, auto-completions, suggestions and other features useful to have
only in the main script editor, the one in the actual KnobScripter.

adrianpueyo.com

"""

import nuke
import re
import sys

try:
    if nuke.NUKE_VERSION_MAJOR < 11:
        from PySide import QtCore, QtGui, QtGui as QtWidgets
        from PySide.QtCore import Qt
    else:
        from PySide2 import QtWidgets, QtGui, QtCore
        from PySide2.QtCore import Qt
except ImportError:
    from Qt import QtCore, QtGui, QtWidgets


from KnobScripter.ksscripteditor import KSScriptEditor
from KnobScripter import keywordhotbox, content, dialogs

def best_ending_match(text, match_list):
    '''
    If the text ends with a key in the match_list, it returns the key and value.
    match_list example: [["ban","banana"],["ap","apple"],["or","orange"]]
    If there are several matches, returns the longest one.
    Except if one starts with space, in which case return the other.
    False if no matches.
    '''
    ending_matches = []

    # 1. Find which items from match_list are found
    for item in match_list:
        if item[0].startswith(" "):
            match = re.search(item[0] + r"$", text)
        else:
            match = re.search(r"[\s.(){}\[\],;:=+-]" + item[0] + r"$", text)
        if match or text == item[0]:
            ending_matches.append(item)
    if not len(ending_matches):
        return False

    # 2. If multiple matches, decide which is the best one
    # Order by length
    ending_matches = sorted(ending_matches, key = lambda a: len(a[0]))

    return ending_matches[-1]

def get_last_word(text):
    '''
    Return the last word (azAZ09_) appearing in the text or False.
    '''
    s = re.split(r"[\W]",text)
    if len(s):
        return s[-1]
    else:
        return False


class KSScriptEditorMain(KSScriptEditor):
    '''
    Modified KSScriptEditor to include snippets, tab menu, etc.
    '''

    def __init__(self, knob_scripter, output=None, parent=None):
        super(KSScriptEditorMain, self).__init__(knob_scripter)
        self.knobScripter = knob_scripter
        self.script_output = output
        self.nukeCompleter = None
        self.currentNukeCompletion = None

        ########
        # FROM NUKE's SCRIPT EDITOR START
        ########
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        # Setup Nuke Python completer
        self.nukeCompleter = QtWidgets.QCompleter(self)
        self.nukeCompleter.setWidget(self)
        self.nukeCompleter.setCompletionMode(QtWidgets.QCompleter.UnfilteredPopupCompletion)
        self.nukeCompleter.setCaseSensitivity(Qt.CaseSensitive)
        try:
            self.nukeCompleter.setModel(QtGui.QStringListModel())
        except:
            self.nukeCompleter.setModel(QtCore.QStringListModel())

        self.nukeCompleter.activated.connect(self.insertNukeCompletion)
        self.nukeCompleter.highlighted.connect(self.completerHighlightChanged)
        ########
        # FROM NUKE's SCRIPT EDITOR END
        ########

    def placeholderToEnd(self, text, placeholder):
        '''Returns distance (int) from the first ocurrence of the placeholder, to the end of the string with placeholders removed'''
        search = re.search(placeholder, text)
        if not search:
            return -1
        from_start = search.start()
        total = len(re.sub(placeholder, "", text))
        to_end = total - from_start
        return to_end

    def addSnippetText(self, snippet_text, last_word = None):
        ''' Adds the selected text as a snippet (taking care of $$, $name$ etc) to the script editor.
        If last_word arg supplied, it replaces $_$ for that word.
        '''
        cursor_placeholder_find = r"(?<!\\)(\$\$)"  # Matches $$
        variables_placeholder_find = r"(?:^|[^\\\$])(\$[\w]*[^\t\n\r\f\v\$\\]+\$)(?:$|[^\$])"  # Matches $thing$
        text = snippet_text
        while True:
            placeholder_variable = re.search(variables_placeholder_find, text)
            if not placeholder_variable:
                break
            word = placeholder_variable.groups()[0]
            word_bare = word[1:-1]
            if word == "$_$": # We just add the last word!
                if last_word:
                    text = text.replace(word, last_word)
                else:
                    text = text.replace(word, "$Variable!$")
            else: # Another variable to add.
                panel = dialogs.TextInputDialog(self.knobScripter, name=word_bare, text="", title="Set text for " + word_bare)
                if panel.exec_():
                    # Accepted
                    text = text.replace(word, panel.text)
                    if word_bare == "Variable!": # Meaning it was supposed to be "$_$"
                        if not last_word:
                            text = "{0}.{1}".format(panel.text,text)
                else:
                    text = text.replace(word, "")

        placeholder_to_end = self.placeholderToEnd(text, cursor_placeholder_find)

        cursors = re.finditer(r"(?<!\\)(\$\$)", text)
        positions = []
        cursor_len = 0
        for m in cursors:
            if len(positions) < 2:
                positions.append(m.start())
        if len(positions) > 1:
            cursor_len = positions[1] - positions[0] - 2

        text = re.sub(cursor_placeholder_find, "", text)
        self.cursor.insertText(text)
        if placeholder_to_end >= 0:
            for i in range(placeholder_to_end):
                self.cursor.movePosition(QtGui.QTextCursor.PreviousCharacter)
            for i in range(cursor_len):
                self.cursor.movePosition(QtGui.QTextCursor.NextCharacter, QtGui.QTextCursor.KeepAnchor)
            self.setTextCursor(self.cursor)

    def mouseDoubleClickEvent(self, event):
        ''' On doublelick on a word, suggestions might show up. i.e. eRead/eWrite, etc. '''
        KSScriptEditor.mouseDoubleClickEvent(self, event)
        selected_text = self.textCursor().selection().toPlainText()

        # 1. Doubleclick on blink!
        if self.knobScripter.code_language == "blink":
            # 1.1. Define all blink keywords
            blink_keyword_dict = content.blink_keyword_dict
            # 1.2. If there's a match, show the hotbox!
            category = self.findCategory(selected_text, blink_keyword_dict)  # Returns something like "Access Method"
            if category:
                keyword_hotbox = keywordhotbox.KeywordHotbox(self, category, blink_keyword_dict[category])
                if keyword_hotbox.exec_() == QtWidgets.QDialog.Accepted:
                    self.textCursor().insertText(keyword_hotbox.selection)

    def keyPressEvent(self, event):

        ctrl = bool(event.modifiers() & Qt.ControlModifier)
        alt = bool(event.modifiers() & Qt.AltModifier)
        shift = bool(event.modifiers() & Qt.ShiftModifier)
        key = event.key()

        # ADAPTED FROM NUKE's SCRIPT EDITOR:
        # Get completer state
        self.nukeCompleterShowing = self.nukeCompleter.popup().isVisible()

        # BEFORE ANYTHING ELSE, IF SPECIAL MODIFIERS SIMPLY IGNORE THE REST
        if not self.nukeCompleterShowing and (ctrl or shift or alt):
            # Bypassed!
            if key not in [Qt.Key_Return, Qt.Key_Enter, Qt.Key_Tab]:
                KSScriptEditor.keyPressEvent(self, event)
                return

        # If the python completer is showing
        if self.nukeCompleterShowing:
            tc = self.textCursor()
            # If we're hitting enter, do completion
            if key in [Qt.Key_Return, Qt.Key_Enter, Qt.Key_Tab]:
                if not self.currentNukeCompletion:
                    self.nukeCompleter.setCurrentRow(0)
                    self.currentNukeCompletion = self.nukeCompleter.currentCompletion()
                # print str(self.nukeCompleter.completionModel[0])
                self.insertNukeCompletion(self.currentNukeCompletion)
                self.nukeCompleter.popup().hide()
                self.nukeCompleterShowing = False
            # If you're hitting right or escape, hide the popup
            elif key == Qt.Key_Right or key == Qt.Key_Escape:
                self.nukeCompleter.popup().hide()
                self.nukeCompleterShowing = False
            # If you hit tab, escape or ctrl-space, hide the completer
            elif key == Qt.Key_Tab or key == Qt.Key_Escape or (ctrl and key == Qt.Key_Space):
                self.currentNukeCompletion = ""
                self.nukeCompleter.popup().hide()
                self.nukeCompleterShowing = False
            # If none of the above, update the completion model
            else:
                QtWidgets.QPlainTextEdit.keyPressEvent(self, event)
                # Edit completion model
                colNum = tc.columnNumber()
                posNum = tc.position()
                inputText = self.toPlainText()
                inputTextSplit = inputText.splitlines()
                runningLength = 0
                currentLine = None
                for line in inputTextSplit:
                    length = len(line)
                    runningLength += length
                    if runningLength >= posNum:
                        currentLine = line
                        break
                    runningLength += 1
                if currentLine:
                    completionPart = currentLine.split(" ")[-1]
                    if "(" in completionPart:
                        completionPart = completionPart.split("(")[-1]
                    self.completeNukePartUnderCursor(completionPart)
            return

        if type(event) == QtGui.QKeyEvent:
            if key == Qt.Key_Escape:  # Close the knobscripter...
                self.knobScripter.close()
            elif not ctrl and not alt and not shift and event.key() == Qt.Key_Tab:  # If only tab
                self.placeholder = "$$"
                # 1. Set the cursor
                self.cursor = self.textCursor()

                # 2. Save text before and after
                cpos = self.cursor.position()
                text_before_cursor = self.toPlainText()[:cpos]
                line_before_cursor = text_before_cursor.split('\n')[-1]
                # Remove tabs too, so it doesn't count as active space
                while line_before_cursor.startswith(" "*max(1,self.tab_spaces)):
                    line_before_cursor = line_before_cursor[self.tab_spaces:]
                text_after_cursor = self.toPlainText()[cpos:]

                # Abort mission if there's a tab or nothing before, or selected text
                if self.cursor.hasSelection() or any([text_before_cursor.endswith(_) for _ in ["\t","\n"]]):
                    KSScriptEditor.keyPressEvent(self, event)
                    return

                # 3. Check coincidences in snippets dicts
                try:  # Meaning snippet found
                    snippets_lang = []
                    snippets_all = []
                    if self.knobScripter.code_language in content.all_snippets:
                        snippets_lang = content.all_snippets[self.knobScripter.code_language]
                    if "all" in content.all_snippets:
                        snippets_all = content.all_snippets["all"]
                    snippets_list = snippets_lang + snippets_all
                    match_key, match_snippet = best_ending_match(line_before_cursor, snippets_list)
                    for i in range(len(match_key)):
                        self.cursor.deletePreviousChar()
                    new_line_before_cursor = text_before_cursor[:-len(match_key)].split('\n')[-1]

                    # Next we'll be able to check what's the last word before the cursor
                    word_before_cursor = None
                    if new_line_before_cursor.endswith("."):
                        word_before_cursor = get_last_word(new_line_before_cursor[:-1].strip())
                    self.addSnippetText(match_snippet,last_word = word_before_cursor)  # Add the appropriate snippet and move the cursor
                except:  # Meaning snippet not found...
                    # 3.1. Go with nuke/python completer
                    if self.knobScripter.code_language in ["python","blink"]:
                        # ADAPTED FROM NUKE's SCRIPT EDITOR:
                        tc = self.textCursor()
                        allCode = self.toPlainText()
                        colNum = tc.columnNumber()
                        posNum = tc.position()

                        # ...and if there's text in the editor
                        if len(allCode.split()) > 0:
                            # There is text in the editor
                            currentLine = tc.block().text()

                            # If you're not at the end of the line just add a tab (maybe not???)
                            if colNum < len(currentLine):
                                # If there's text right after the cursor, don't autocomplete
                                #if currentLine[colNum] not in [',', '<', ' ' ,')','.','[']:
                                if re.match(r'[\w]',currentLine[colNum:]):
                                    KSScriptEditor.keyPressEvent(self, event)
                                    return
                                # Else show the completer
                                else:
                                    completionPart = currentLine[:colNum].split(" ")[-1]
                                    if "(" in completionPart:
                                        completionPart = completionPart.split("(")[-1]

                                    self.completeNukePartUnderCursor(completionPart)

                                    return

                            # If you are at the end of the line,
                            else:
                                # If there's nothing to the right of you add a tab
                                if currentLine[colNum - 1:] == "" or currentLine.endswith(" "):
                                    KSScriptEditor.keyPressEvent(self, event)
                                    return
                                # Else update completionPart and show the completer
                                completionPart = currentLine.split(" ")[-1]
                                if "(" in completionPart:
                                    completionPart = completionPart.split("(")[-1]

                                self.completeNukePartUnderCursor(completionPart)
                                return

                        KSScriptEditor.keyPressEvent(self, event)
                    else:
                        KSScriptEditor.keyPressEvent(self, event)
            elif event.key() in [Qt.Key_Enter, Qt.Key_Return]:
                modifiers = QtWidgets.QApplication.keyboardModifiers()
                if modifiers == QtCore.Qt.ControlModifier:
                    # Ctrl + Enter! Python or blink?
                    if self.knobScripter.code_language == "python":
                        self.runScript()
                    else:
                        self.knobScripter.blinkSaveRecompile()
                else:
                    KSScriptEditor.keyPressEvent(self, event)
            else:
                KSScriptEditor.keyPressEvent(self, event)

    def getPyObjects(self, text):
        ''' Returns a list containing all the functions, classes and variables found within the selected python text (code) '''
        matches = []
        # 1: Remove text inside triple quotes (leaving the quotes)
        text_clean = '""'.join(text.split('"""')[::2])
        text_clean = '""'.join(text_clean.split("'''")[::2])

        # 2: Remove text inside of quotes (leaving the quotes) except if \"
        lines = text_clean.split("\n")
        text_clean = ""
        for line in lines:
            line_clean = '""'.join(line.split('"')[::2])
            line_clean = '""'.join(line_clean.split("'")[::2])
            line_clean = line_clean.split("#")[0]
            text_clean += line_clean + "\n"

        # 3. Split into segments (lines plus ";")
        segments = re.findall(r"[^\n;]+", text_clean)

        # 4. Go case by case.
        for s in segments:
            # Declared vars
            matches += re.findall(r"([\w.]+)(?=[,\s\w]*=[^=]+$)", s)
            # Def functions and arguments
            function = re.findall(r"[\s]*def[\s]+([\w.]+)[\s]*\([\s]*", s)
            if len(function):
                matches += function
                args = re.split(r"[\s]*def[\s]+([\w.]+)[\s]*\([\s]*", s)
                if len(args) > 1:
                    args = args[-1]
                    matches += re.findall(r"(?<![=\"\'])[\s]*([\w.]+)[\s]*(?=[=,)])", args)
            # Lambda
            matches += re.findall(r"^[^#]*lambda[\s]+([\w.]+)[\s()\w,]+", s)
            # Classes
            matches += re.findall(r"^[^#]*class[\s]+([\w.]+)[\s()\w,]+", s)
        return matches

    # Find category in keyword_dict
    def findCategory(self, keyword, keyword_dict):
        '''
        findCategory(self, keyword (str), keyword_dict (dict)) -> Returns category (str)
        Looks for keyword in keyword_dict and returns the relevant category name or None
        '''
        for category in keyword_dict:
            if keyword in keyword_dict[category]["keywords"]:
                return category
        return None

    # Nuke script editor's modules completer
    def completionsForcompletionPart(self, completionPart):
        if self.knobScripter.code_language == "python":
            return self.pythonCompletions(completionPart)
        elif self.knobScripter.code_language == "blink":
            return self.blinkCompletions(completionPart)

    def pythonCompletions(self,completionPart):
        def findModules(searchString):
            sysModules = sys.modules
            globalModules = globals()
            allModules = dict(sysModules, **globalModules)
            allKeys = list(set(list(globals().keys()) + list(sys.modules.keys())))
            allKeysSorted = [x for x in sorted(set(allKeys))]

            if searchString == '':
                matching = []
                for x in allModules:
                    if x.startswith(searchString):
                        matching.append(x)
                return matching
            else:
                try:
                    if sys.modules.has_key(searchString):
                        return dir(sys.modules['%s' % searchString])
                    elif globals().has_key(searchString):
                        return dir(globals()['%s' % searchString])
                    else:
                        return []
                except:
                    return None

        completerText = completionPart

        # Get text before last dot
        moduleSearchString = '.'.join(completerText.split('.')[:-1])

        # Get text after last dot
        fragmentSearchString = completerText.split('.')[-1] if completerText.split('.')[
                                                                   -1] != moduleSearchString else ''

        # Get all the modules that match module search string
        allModules = findModules(moduleSearchString)

        # If no modules found, do a dir
        if not allModules:
            if len(moduleSearchString.split('.')) == 1:
                matchedModules = []
            else:
                try:
                    trimmedModuleSearchString = '.'.join(moduleSearchString.split('.')[:-1])
                    matchedModules = [x for x in dir(
                        getattr(sys.modules[trimmedModuleSearchString], moduleSearchString.split('.')[-1])) if
                                      '__' not in x and x.startswith(fragmentSearchString)]
                except:
                    matchedModules = []
        else:
            matchedModules = [x for x in allModules if '__' not in x and x.startswith(fragmentSearchString)]

        selfObjects = list(set(self.getPyObjects(self.toPlainText())))
        for i in selfObjects:
            if i.startswith(completionPart):
                matchedModules.append(i)

        return matchedModules

    def blinkCompletions(self, completionPart):
        blink_keywords = content.blink_keywords
        matchedModules = []
        for i in blink_keywords:
            if i.startswith(completionPart):
                matchedModules.append(i)
        return matchedModules

    def completeNukePartUnderCursor(self, completionPart):

        completionPart = completionPart.lstrip().rstrip()
        completionList = self.completionsForcompletionPart(completionPart)
        if len(completionList) == 0:
            return
        self.nukeCompleter.model().setStringList(completionList)
        self.nukeCompleter.setCompletionPrefix(completionPart)

        if self.nukeCompleter.popup().isVisible():
            rect = self.cursorRect()
            rect.setWidth(self.nukeCompleter.popup().sizeHintForColumn(
                0) + self.nukeCompleter.popup().verticalScrollBar().sizeHint().width())
            self.nukeCompleter.complete(rect)
            return

        # Make it visible
        if len(completionList) == 1:
            self.insertNukeCompletion(completionList[0])
        else:
            rect = self.cursorRect()
            rect.setWidth(self.nukeCompleter.popup().sizeHintForColumn(
                0) + self.nukeCompleter.popup().verticalScrollBar().sizeHint().width())
            self.nukeCompleter.complete(rect)

        return

    def insertNukeCompletion(self, completion):
        """ Insert the appropriate text into the script editor. """
        if completion:
            # If python, insert text... If blink, insert as snippet?
            completionPart = self.nukeCompleter.completionPrefix()
            if len(completionPart.split('.')) == 0:
                completionPartFragment = completionPart
            else:
                completionPartFragment = completionPart.split('.')[-1]

            textToInsert = completion[len(completionPartFragment):]
            tc = self.textCursor()
            if self.code_language == "python":
                tc.insertText(textToInsert)
            elif self.code_language == "blink":
                self.addSnippetText(textToInsert)
        return

    def completerHighlightChanged(self, highlighted):
        self.currentNukeCompletion = highlighted

    def runScript(self):
        cursor = self.textCursor()
        if cursor.hasSelection():
            code = cursor.selection().toPlainText()
        else:
            code = self.toPlainText()

        if code == "":
            return

        if nuke.NUKE_VERSION_MAJOR >= 13 and self.knobScripter.nodeMode and self.knobScripter.runInContext:
            # The simple and nice approach for run in context!! Doesn't work with Nuke 12...
            run_context = "root"
            # If node mode and run in context (experimental) selected in preferences, run the code in its proper context!
            # if self.knobScripter.nodeMode and self.knobScripter.runInContext:
            nodeName = self.knobScripter.node.fullName()
            knobName = self.knobScripter.current_knob_dropdown.itemData(
                self.knobScripter.current_knob_dropdown.currentIndex())
            if nuke.exists(nodeName) and knobName in nuke.toNode(nodeName).knobs():
                run_context = "{}.{}".format(nodeName, knobName)
            # Run the code! Much cleaner in this way:
            nuke.runIn(run_context, code)

        else:
            nukeSEInput = self.knobScripter.nukeSEInput
            # If node mode and run in context (experimental) selected in preferences, run the code in its proper context!
            if self.knobScripter.nodeMode and self.knobScripter.runInContext:
                # 1. change thisNode, thisKnob...
                nodeName = self.knobScripter.node.fullName()
                knobName = self.knobScripter.current_knob_dropdown.itemData(
                    self.knobScripter.current_knob_dropdown.currentIndex())
                if nuke.exists(nodeName) and knobName in nuke.toNode(nodeName).knobs():
                    code = code.replace("nuke.thisNode()", "nuke.toNode('{}')".format(nodeName))
                    code = code.replace("nuke.thisKnob()", "nuke.toNode('{}').knob('{}')".format(nodeName, knobName))
                    # 2. If group, wrap all with: with nuke.toNode(fullNameOfGroup) and then indent every single line!
                    #      at least by one space. replace "\n" with "\n "
                    if self.knobScripter.node.Class() in ["Group", "LiveGroup", "Root"]:
                        code = code.replace("\n", "\n  ")
                        code = "with nuke.toNode('{}'):\n {}".format(nodeName, code)

            # Store original ScriptEditor status
            nukeSECursor = nukeSEInput.textCursor()
            origSelection = nukeSECursor.selectedText()
            oldAnchor = nukeSECursor.anchor()
            oldPosition = nukeSECursor.position()

            # Add the code to be executed and select it
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


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
    if nuke.NUKE_VERSION_MAJOR >= 16:
        from PySide6 import QtWidgets, QtGui, QtCore
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

from KnobScripter.ksscripteditor import KSScriptEditor
from KnobScripter import keywordhotbox, content, dialogs

def best_ending_match(text, match_list):
    '''
    If the text ends with a key in the match_list, returns the key and value.
    match_list example: [["ban","banana"],["ap","apple"],["or","orange"]]
    If several matches are found, returns the longest one,
    except if one starts with a space, in which case returns the other.
    Returns False if no match is found.
    '''
    ending_matches = []
    for item in match_list:
        if item[0].startswith(" "):
            match = re.search(item[0] + r"$", text)
        else:
            match = re.search(r"[\s.(){}\[\],;:=+\-]" + item[0] + r"$", text)
        if match or text == item[0]:
            ending_matches.append(item)
    if not ending_matches:
        return False
    ending_matches = sorted(ending_matches, key=lambda a: len(a[0]))
    return ending_matches[-1]

def get_last_word(text):
    '''
    Return the last word (letters, digits, or underscore) in the text, or False.
    '''
    s = re.split(r"[\W]", text)
    if s:
        return s[-1]
    else:
        return False


class KSScriptEditorMain(KSScriptEditor):
    '''
    Modified KSScriptEditor to include snippets, tab menu, completions, etc.
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
        '''Return the distance (int) from the first occurrence of the placeholder to the end
        of the string (with placeholders removed).'''
        search = re.search(placeholder, text)
        if not search:
            return -1
        from_start = search.start()
        total = len(re.sub(placeholder, "", text))
        to_end = total - from_start
        return to_end

    def addSnippetText(self, snippet_text, last_word=None):
        '''Adds the selected snippet text into the editor.
        If last_word is supplied, replaces the "$_$" placeholder with that word.'''
        cursor_placeholder_find = r"(?<!\\)(\$\$)"  # Matches $$
        variables_placeholder_find = r"(?:^|[^\\\$])(\$[\w]*[^\t\n\r\f\v\$\\]+\$)"  # Matches $thing$
        text = snippet_text
        while True:
            placeholder_variable = re.search(variables_placeholder_find, text)
            if not placeholder_variable:
                break
            word = placeholder_variable.groups()[0]
            word_bare = word[1:-1]
            if word == "$_$":
                if last_word:
                    text = text.replace(word, last_word)
                else:
                    text = text.replace(word, "$Variable!$")
            else:
                panel = dialogs.TextInputDialog(self.knobScripter, name=word_bare, text="", title="Set text for " + word_bare)
                if dialogs.exec_dialog(panel) == QtWidgets.QDialog.Accepted:
                    text = text.replace(word, panel.text)
                    if word_bare == "Variable!":
                        if not last_word:
                            text = "{0}.{1}".format(panel.text, text)
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
        '''On double-clicking a word, show suggestions if applicable.'''
        KSScriptEditor.mouseDoubleClickEvent(self, event)
        selected_text = self.textCursor().selection().toPlainText()
        if self.knobScripter.code_language == "blink":
            blink_keyword_dict = content.blink_keyword_dict
            category = self.findCategory(selected_text, blink_keyword_dict)
            if category:
                keyword_hotbox = keywordhotbox.KeywordHotbox(self, category, blink_keyword_dict[category])
                if dialogs.exec_dialog(keyword_hotbox) == QtWidgets.QDialog.Accepted:
                    self.textCursor().insertText(keyword_hotbox.selection)

    def keyPressEvent(self, event):
        ctrl = bool(event.modifiers() & Qt.ControlModifier)
        alt = bool(event.modifiers() & Qt.AltModifier)
        shift = bool(event.modifiers() & Qt.ShiftModifier)
        key = event.key()

        # Get completer state
        self.nukeCompleterShowing = self.nukeCompleter.popup().isVisible()

        if not self.nukeCompleterShowing and (ctrl or shift or alt):
            if key not in [Qt.Key_Return, Qt.Key_Enter, Qt.Key_Tab]:
                KSScriptEditor.keyPressEvent(self, event)
                return

        if self.nukeCompleterShowing:
            tc = self.textCursor()
            if key in [Qt.Key_Return, Qt.Key_Enter, Qt.Key_Tab]:
                if not self.currentNukeCompletion:
                    self.nukeCompleter.setCurrentRow(0)
                    self.currentNukeCompletion = self.nukeCompleter.currentCompletion()
                self.insertNukeCompletion(self.currentNukeCompletion)
                self.nukeCompleter.popup().hide()
                self.nukeCompleterShowing = False
            elif key == Qt.Key_Right or key == Qt.Key_Escape:
                self.nukeCompleter.popup().hide()
                self.nukeCompleterShowing = False
            elif key == Qt.Key_Tab or key == Qt.Key_Escape or (ctrl and key == Qt.Key_Space):
                self.currentNukeCompletion = ""
                self.nukeCompleter.popup().hide()
                self.nukeCompleterShowing = False
            else:
                QtWidgets.QPlainTextEdit.keyPressEvent(self, event)
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

        if isinstance(event, QtGui.QKeyEvent):
            if key == Qt.Key_Escape:
                if not isinstance(self.parent().parent(), nuke.KnobScripterPane):
                    self.knobScripter.close()
            elif not ctrl and not alt and not shift and event.key() == Qt.Key_Tab:
                self.placeholder = "$$"
                self.cursor = self.textCursor()
                cpos = self.cursor.position()
                text_before_cursor = self.toPlainText()[:cpos]
                line_before_cursor = text_before_cursor.split('\n')[-1]
                while line_before_cursor.startswith(" " * max(1, self.tab_spaces)):
                    line_before_cursor = line_before_cursor[self.tab_spaces:]
                text_after_cursor = self.toPlainText()[cpos:]
                if any([text_before_cursor.endswith(x) for x in ["\t", "\n"]]) or not len(line_before_cursor.strip()):
                    KSScriptEditor.keyPressEvent(self, event)
                    return
                if self.cursor.hasSelection():
                    cursor_text = self.cursor.selectedText()
                    if u"\u2029" not in cursor_text and len(line_before_cursor):
                        panel = dialogs.TextInputDialog(self.knobScripter, name="Wrap with", text="", title="Wrap selection.")
                        if dialogs.exec_dialog(panel) == QtWidgets.QDialog.Accepted:
                            cpos = self.cursor.position()
                            apos = self.cursor.anchor()
                            cpos = min(cpos, apos)
                            new_text = "{0}({1})".format(panel.text, cursor_text)
                            self.cursor.insertText(new_text)
                            self.cursor.setPosition(cpos, QtGui.QTextCursor.MoveAnchor)
                            self.cursor.setPosition(cpos + len(new_text), QtGui.QTextCursor.KeepAnchor)
                            self.setTextCursor(self.cursor)
                        return
                try:
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
                    word_before_cursor = None
                    if new_line_before_cursor.endswith("."):
                        word_before_cursor = get_last_word(new_line_before_cursor[:-1].strip())
                    self.addSnippetText(match_snippet, last_word=word_before_cursor)
                except:
                    if self.knobScripter.code_language in ["python", "blink"]:
                        tc = self.textCursor()
                        allCode = self.toPlainText()
                        colNum = tc.columnNumber()
                        posNum = tc.position()
                        if len(allCode.split()) > 0:
                            currentLine = tc.block().text()
                            if colNum < len(currentLine):
                                if re.match(r'[\w]', currentLine[colNum:]):
                                    KSScriptEditor.keyPressEvent(self, event)
                                    return
                                else:
                                    completionPart = currentLine[:colNum].split(" ")[-1]
                                    if "(" in completionPart:
                                        completionPart = completionPart.split("(")[-1]
                                    self.completeNukePartUnderCursor(completionPart)
                                    return
                            else:
                                if currentLine[colNum - 1:] == "" or currentLine.endswith(" "):
                                    KSScriptEditor.keyPressEvent(self, event)
                                    return
                                else:
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
                    if self.knobScripter.code_language == "python":
                        self.runScript()
                    else:
                        self.knobScripter.blinkSaveRecompile()
                else:
                    KSScriptEditor.keyPressEvent(self, event)
            else:
                KSScriptEditor.keyPressEvent(self, event)
            return
        else:
            KSScriptEditor.keyPressEvent(self, event)

    def getPyObjects(self, text):
        '''Returns a list containing functions, classes and variables found in the given python code.'''
        matches = []
        text_clean = '""'.join(text.split('"""')[::2])
        text_clean = '""'.join(text_clean.split("'''")[::2])
        lines = text_clean.split("\n")
        text_clean = ""
        for line in lines:
            line_clean = '""'.join(line.split('"')[::2])
            line_clean = '""'.join(line_clean.split("'")[::2])
            line_clean = line_clean.split("#")[0]
            text_clean += line_clean + "\n"
        segments = re.findall(r"[^\n;]+", text_clean)
        for s in segments:
            matches += re.findall(r"([\w.]+)(?=[,\s\w]*=[^=]+$)", s)
            function = re.findall(r"[\s]*def[\s]+([\w.]+)[\s]*\(", s)
            if function:
                matches += function
                args = re.split(r"[\s]*def[\s]+([\w.]+)[\s]*\(", s)
                if len(args) > 1:
                    args = args[-1]
                    matches += re.findall(r"(?<![=\"\'])[\s]*([\w.]+)[\s]*(?=[=,)])", args)
            matches += re.findall(r"^[^#]*lambda[\s]+([\w.]+)[\s()\w,]+", s)
            matches += re.findall(r"^[^#]*class[\s]+([\w.]+)[\s()\w,]+", s)
        return matches

    def findCategory(self, keyword, keyword_dict):
        '''
        Returns the category name from keyword_dict that contains the given keyword.
        '''
        for category in keyword_dict:
            if keyword in keyword_dict[category]["keywords"]:
                return category
        return None

    def completionsForcompletionPart(self, completionPart):
        if self.knobScripter.code_language == "python":
            return self.pythonCompletions(completionPart)
        elif self.knobScripter.code_language == "blink":
            return self.blinkCompletions(completionPart)

    def pythonCompletions(self, completionPart):
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
                    if searchString in sys.modules:
                        return dir(sys.modules[searchString])
                    elif searchString in globals():
                        return dir(globals()[searchString])
                    else:
                        return []
                except:
                    return None
        completerText = completionPart
        moduleSearchString = '.'.join(completerText.split('.')[:-1])
        fragmentSearchString = completerText.split('.')[-1] if completerText.split('.')[-1] != moduleSearchString else ''
        allModules = findModules(moduleSearchString)
        if not allModules:
            if len(moduleSearchString.split('.')) == 1:
                matchedModules = []
            else:
                try:
                    trimmedModuleSearchString = '.'.join(moduleSearchString.split('.')[:-1])
                    matchedModules = [x for x in dir(getattr(sys.modules[trimmedModuleSearchString], moduleSearchString.split('.')[-1])) if '__' not in x and x.startswith(fragmentSearchString)]
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
        completionPart = completionPart.strip()
        completionList = self.completionsForcompletionPart(completionPart)
        if not completionList:
            return
        self.nukeCompleter.model().setStringList(completionList)
        self.nukeCompleter.setCompletionPrefix(completionPart)
        if self.nukeCompleter.popup().isVisible():
            rect = self.cursorRect()
            rect.setWidth(self.nukeCompleter.popup().sizeHintForColumn(0) + self.nukeCompleter.popup().verticalScrollBar().sizeHint().width())
            self.nukeCompleter.complete(rect)
            return
        if len(completionList) == 1:
            self.insertNukeCompletion(completionList[0])
        else:
            rect = self.cursorRect()
            rect.setWidth(self.nukeCompleter.popup().sizeHintForColumn(0) + self.nukeCompleter.popup().verticalScrollBar().sizeHint().width())
            self.nukeCompleter.complete(rect)
        return

    def insertNukeCompletion(self, completion):
        """ Insert the appropriate text into the script editor. """
        if completion:
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
        if not code:
            return
        if nuke.NUKE_VERSION_MAJOR >= 13 and self.knobScripter.nodeMode and self.knobScripter.runInContext:
            run_context = "root"
            nodeName = self.knobScripter.node.fullName()
            knobName = self.knobScripter.current_knob_dropdown.itemData(self.knobScripter.current_knob_dropdown.currentIndex())
            if nuke.exists(nodeName) and knobName in nuke.toNode(nodeName).knobs():
                run_context = "{}.{}".format(nodeName, knobName)
                code = 'exec("""{}""")'.format(code.replace('\\', '\\\\'))
            nuke.runIn(run_context, code)
        else:
            nukeSEInput = self.knobScripter.nukeSEInput
            if self.knobScripter.nodeMode and self.knobScripter.runInContext:
                nodeName = self.knobScripter.node.fullName()
                knobName = self.knobScripter.current_knob_dropdown.itemData(self.knobScripter.current_knob_dropdown.currentIndex())
                if nuke.exists(nodeName) and knobName in nuke.toNode(nodeName).knobs():
                    code = code.replace("nuke.thisNode()", "nuke.toNode('{}')".format(nodeName))
                    code = code.replace("nuke.thisKnob()", "nuke.toNode('{}').knob('{}')".format(nodeName, knobName))
                    if self.knobScripter.node.Class() in ["Group", "LiveGroup", "Root"]:
                        code = code.replace("\n", "\n  ")
                        code = "with nuke.toNode('{}'):\n {}".format(nodeName, code)
            nukeSECursor = nukeSEInput.textCursor()
            origSelection = nukeSECursor.selectedText()
            oldAnchor = nukeSECursor.anchor()
            oldPosition = nukeSECursor.position()
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
            self.knobScripter.nukeSERunBtn.click()
            nukeSEInput.insertPlainText(origSelection)
            nukeSECursor.setPosition(oldAnchor, QtGui.QTextCursor.MoveAnchor)
            nukeSECursor.setPosition(oldPosition, QtGui.QTextCursor.KeepAnchor)
            nukeSEInput.setTextCursor(nukeSECursor)

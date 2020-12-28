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


from ksscripteditor import KSScriptEditor


class KSScriptEditorMain(KSScriptEditor):
    '''
    Modified KSScriptEditor to include snippets, tab menu, etc.
    '''

    def __init__(self, knobScripter, output=None, parent=None):
        super(KSScriptEditorMain, self).__init__(knobScripter)
        self.knobScripter = knobScripter
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

    def findLongestEndingMatch(self, text, dic):
        '''
        If the text ends with a key in the dictionary, it returns the key and value.
        If there are several matches, returns the longest one.
        False if no matches.
        '''
        longest = 0  # len of longest match
        match_key = None
        match_snippet = ""
        for key, val in dic.items():
            match = re.search(r"[\s.(){}\[\],;=+-]" + key + r"$", text)  # TODO check if worked
            if match or text == key:
                if len(key) > longest:
                    longest = len(key)
                    match_key = key
                    match_snippet = val
        if match_key is None:
            return False
        return match_key, match_snippet

    def placeholderToEnd(self, text, placeholder):
        '''Returns distance (int) from the first ocurrence of the placeholder, to the end of the string with placeholders removed'''
        search = re.search(placeholder, text)
        if not search:
            return -1
        from_start = search.start()
        total = len(re.sub(placeholder, "", text))
        to_end = total - from_start
        return to_end

    def addSnippetText(self, snippet_text):
        ''' Adds the selected text as a snippet (taking care of $$, $name$ etc) to the script editor '''
        cursor_placeholder_find = r"(?<!\\)(\$\$)"  # Matches $$
        variables_placeholder_find = r"(?:^|[^\\\$])(\$[\w]*[^\t\n\r\f\v\$\\]+\$)(?:$|[^\$])"  # Matches $thing$
        text = snippet_text
        while True:
            placeholder_variable = re.search(variables_placeholder_find, text)
            if not placeholder_variable:
                break
            word = placeholder_variable.groups()[0]
            word_bare = word[1:-1]
            panel = TextInputDialog(self.knobScripter, name=word_bare, text="", title="Set text for " + word_bare)
            if panel.exec_():
                #    # Accepted
                text = text.replace(word, panel.text)
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
            blink_keyword_dict = {
                "Access Pattern": {
                    "keywords": ["eAccessPoint", "eAccessRanged1D", "eAccessRanged2D", "eAccessRandom"],
                    "help": '''This describes how the kernel will access pixels in the image. The options are:
                                <ul>
                                    <li><b>eAccessPoint</b>: Access only the current position in the iteration space.</li>
                                    <li><b>eAccessRanged1D</b>: Access a one-dimensional range of positions relative to the current position in the iteration space.</li>
                                    <li><b>eAccessRanged2D</b>: Access a two-dimensional range of positions relative to the current position in the iteration space.</li>
                                    <li><b>eAccessRandom</b>: Access any pixel in the iteration space.</li>
                                </ul>
                                The default value is <b>eAccessPoint</b>.
                            '''
                },
                "Edge Method": {
                    "keywords": ["eEdgeClamped", "eEdgeConstant", "eEdgeNone"],
                    "help": '''The edge method for an image defines the behaviour if a kernel function tries to access data outside the image bounds. The options are:
                                <ul>
                                    <li><b>eEdgeClamped</b>: The edge values will be repeated outside the image bounds.</li>
                                    <li><b>eEdgeConstant</b>: Zero values will be returned outside the image bounds.</li>
                                    <li><b>eEdgeNone</b>: Values are undefined outside the image bounds and no within-bounds checks will be done when you access the image. This is the most efficient access method to use when you do not require access outside the bounds, because of the lack of bounds checks.</li>
                                </ul>
                                The default value is <b>eEdgeNone</b>.
                            '''
                },
                "Kernel Granularity": {
                    "keywords": ["eComponentWise", "ePixelWise"],
                    "help": '''A kernel can be iterated in either a componentwise or pixelwise manner. Componentwise iteration means that the kernel will be executed once for each component at every point in the iteration space. Pixelwise means it will be called once only for every point in the iteration space. The options for the kernel granularity are:
                                <ul>
                                    <li><b>eComponentWise</b>: The kernel processes the image one component at a time. Only the current component's value can be accessed in any of the input images, or written to in the output image.</li>
                                    <li><b>ePixelWise</b>: The kernel processes the image one pixel at a time. All component values can be read from and written to.</li>
                                </ul>
                            '''
                },
                "Read Spec": {
                    "keywords": ["eRead", "eWrite", "eReadWrite"],
                    "help": '''This describes how the data in the image can be accessed. The options are:
                                <ul>
                                    <li><b>eRead</b>: Read-only access to the image data. <i>Common for the input image/s.</i></li>
                                    <li><b>eWrite</b>: Write-only access to the image data. <i>Common for the output image.</i></li>
                                    <li><b>eReadWrite</b>: Both read and write access to the image data. <i>Useful when you need to write and read again from the output image.</i></li>
                                </ul>
                            '''
                },
                "Variable Types": {
                    "keywords": ["int", "int2", "int3", "int4", "float", "float2", "float3", "float4", "float3x3",
                                 "float4x4", "bool"],
                    "help": '''This describes how the data in the image can be accessed. The options are:
                                <ul>
                                    <li><b>eRead</b>: Read-only access to the image data. <i>Common for the input image/s.</i></li>
                                    <li><b>eWrite</b>: Write-only access to the image data. <i>Common for the output image.</i></li>
                                    <li><b>eReadWrite</b>: Both read and write access to the image data. <i>Useful when you need to write and read again from the output image.</i></li>
                                </ul>
                            '''
                    # TODO finish variable types documentation and do the kernel type (imagecomputation etc...)
                },
            }
            # 1.2. If there's a match, show the hotbox!
            category = self.findCategory(selected_text, blink_keyword_dict)  # Returns something like "Access Method"
            if category:
                keyword_hotbox = KeywordHotbox(self, category, blink_keyword_dict[category])
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
                text_after_cursor = self.toPlainText()[cpos:]

                # Abort mission if there's a tab before, or selected text
                if self.cursor.hasSelection() or text_before_cursor.endswith("\t"):
                    KSScriptEditor.keyPressEvent(self, event)
                    return

                # 3. Check coincidences in snippets dicts
                try:  # Meaning snippet found
                    match_key, match_snippet = self.findLongestEndingMatch(line_before_cursor,
                                                                           self.knobScripter.snippets)
                    for i in range(len(match_key)):
                        self.cursor.deletePreviousChar()
                    self.addSnippetText(
                        match_snippet)  # This function takes care of adding the appropriate snippet and moving the cursor...
                except:  # Meaning snippet not found...
                    # 3.1. If python mode, go with nuke/python completer
                    if self.knobScripter.code_language == "python":
                        # ADAPTED FROM NUKE's SCRIPT EDITOR:
                        tc = self.textCursor()
                        allCode = self.toPlainText()
                        colNum = tc.columnNumber()
                        posNum = tc.position()

                        # ...and if there's text in the editor
                        if len(allCode.split()) > 0:
                            # There is text in the editor
                            currentLine = tc.block().text()

                            # If you're not at the end of the line just add a tab
                            if colNum < len(currentLine):
                                # If there isn't a ')' directly to the right of the cursor add a tab
                                if currentLine[colNum:colNum + 1] != ')':
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
                        # 3.2. If blink mode, tab should do other stuff
                        # TODO make a blink completer?
                        # TODO add my words to the auto completer list: eComponentWise, ImageComputationKernel etc....
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
        def findModules(searchString):
            sysModules = sys.modules
            globalModules = globals()
            allModules = dict(sysModules, **globalModules)
            allKeys = list(set(globals().keys() + sys.modules.keys()))
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
        if completion:
            completionPart = self.nukeCompleter.completionPrefix()
            if len(completionPart.split('.')) == 0:
                completionPartFragment = completionPart
            else:
                completionPartFragment = completionPart.split('.')[-1]

            textToInsert = completion[len(completionPartFragment):]
            tc = self.textCursor()
            tc.insertText(textToInsert)
        return

    def completerHighlightChanged(self, highlighted):
        self.currentNukeCompletion = highlighted

    def runScript(self):
        # TODO this shouldn't go inside of this class probably?
        cursor = self.textCursor()
        nukeSEInput = self.knobScripter.nukeSEInput
        if cursor.hasSelection():
            code = cursor.selection().toPlainText()
        else:
            code = self.toPlainText()

        if code == "":
            return

        # If node mode and run in context (experimental) selected in preferences, run the code in its proper context!
        if self.knobScripter.nodeMode and self.knobScripter.runInContext:
            # 1. change thisNode, thisKnob...
            nodeName = self.knobScripter.node.fullName()
            knobName = self.knobScripter.current_knob_dropdown.itemData(
                self.knobScripter.current_knob_dropdown.currentIndex())
            if nuke.exists(nodeName) and knobName in nuke.toNode(nodeName).knobs():
                code = code.replace("nuke.thisNode()", "nuke.toNode('{}')".format(nodeName))
                code = code.replace("nuke.thisKnob()", "nuke.toNode('{}').knob('{}')".format(nodeName, knobName))
                # 2. If group, wrap all with: with nuke.toNode(fullNameOfGroup) and then indent every single line!! at least by one space. replace "\n" with "\n "
                if self.knobScripter.node.Class() in ["Group", "LiveGroup", "Root"]:
                    code = code.replace("\n", "\n  ")
                    code = "with nuke.toNode('{}'):\n{}".format(nodeName, code)

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
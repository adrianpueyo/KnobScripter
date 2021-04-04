import nuke
try:
    if nuke.NUKE_VERSION_MAJOR < 11:
        from PySide import QtGui as QtWidgets
    else:
        from PySide2 import QtWidgets
except ImportError:
    from Qt import QtWidgets

def remove_comments_and_docstrings(source):
    """
    Returns 'source' minus comments and docstrings.
    Awesome function by Dan McDougall
    https://github.com/liftoff/pyminifier
    TODO check Unused?
    """
    import cStringIO, tokenize
    io_obj = cStringIO.StringIO(source)
    out = ""
    prev_toktype = tokenize.INDENT
    last_lineno = -1
    last_col = 0
    for tok in tokenize.generate_tokens(io_obj.readline):
        token_type = tok[0]
        token_string = tok[1]
        start_line, start_col = tok[2]
        end_line, end_col = tok[3]
        ltext = tok[4]
        if start_line > last_lineno:
            last_col = 0
        if start_col > last_col:
            out += (" " * (start_col - last_col))
        if token_type == tokenize.COMMENT:
            pass
        elif token_type == tokenize.STRING:
            if prev_toktype != tokenize.INDENT:
                if prev_toktype != tokenize.NEWLINE:
                    if start_col > 0:
                        out += token_string
        else:
            out += token_string
        prev_toktype = token_type
        last_col = end_col
        last_lineno = end_line
    return out


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


def findSE():
    for widget in QtWidgets.QApplication.allWidgets():
        if widget.metaObject().className() == 'Nuke::NukeScriptEditor':
            return widget


def findSEInput(se):
    children = se.children()
    splitter = [w for w in children if isinstance(w, QtWidgets.QSplitter)]
    if not splitter:
        return None
    splitter = splitter[0]
    for widget in splitter.children():
        if widget.metaObject().className() == 'Foundry::PythonUI::ScriptInputWidget':
            return widget
    return None


def findSEConsole(se=None):
    if not se:
        se = findSE()
    children = se.children()
    splitter = [w for w in children if isinstance(w, QtWidgets.QSplitter)]
    if not splitter:
        return None
    splitter = splitter[0]
    for widget in splitter.children():
        if widget.metaObject().className() == 'Foundry::PythonUI::ScriptOutputWidget':
            return widget
    return None


def findSERunBtn(se):
    children = se.children()
    buttons = [b for b in children if isinstance(b, QtWidgets.QPushButton)]
    for button in buttons:
        tooltip = button.toolTip()
        if "Run the current script" in tooltip:
            return button
    return None


def setSEConsoleChanged():
    ''' Sets nuke's SE console textChanged event to change knobscripters too. '''
    se_console = findSEConsole()
    se_console.textChanged.connect(lambda: consoleChanged(se_console))


def consoleChanged(self):
    ''' This will be called every time the ScriptEditor Output text is changed '''
    for ks in nuke.AllKnobScripters:
        try:
            console_text = self.document().toPlainText()
            omit_se_console_text = ks.omit_se_console_text  # The text from the console that will be omitted
            ks_output = ks.script_output  # The console TextEdit widget
            if omit_se_console_text == "":
                ks_text = console_text
            elif console_text.startswith(omit_se_console_text):
                ks_text = str(console_text[len(omit_se_console_text):])
            else:
                ks_text = console_text
                ks.omit_se_console_text = ""
            ks_output.setPlainText(ks_text)
            ks_output.verticalScrollBar().setValue(ks_output.verticalScrollBar().maximum())
        except:
            pass


def relistAllKnobScripterPanes():
    """ Removes from nuke.AllKnobScripters the panes that are closed. """
    def topParent(qwidget):
        parent = qwidget.parent()
        if not parent:
            return qwidget
        else:
            return topParent(parent)
    for ks in nuke.AllKnobScripters:
        if ks.isPane:
            if topParent(ks).metaObject().className() != "Foundry::UI::DockMainWindow":
                nuke.AllKnobScripters.remove(ks)


def getKnobScripter(knob_scripter=None, alternative=True):
    """
    Return the given knobscripter if it exists.
    Otherwise if alternative == True, find+return another one.
    If no knobscripters found, returns None.
    """
    relistAllKnobScripterPanes()
    ks = None
    if knob_scripter in nuke.AllKnobScripters:
        ks = knob_scripter
        return ks
    elif len(nuke.AllKnobScripters) and alternative:
        for widget in nuke.AllKnobScripters:
            if widget.metaObject().className() == 'KnobScripterPane' and widget.isVisible():
                ks = widget
        if not ks:
            ks = nuke.AllKnobScripters[-1]
            return ks
    else:
        nuke.message("No KnobScripters found!")
        return None


def clear_layout(layout):
    if layout is not None:
        while layout.count():
            child = layout.takeAt(0)
            if child.widget() is not None:
                child.widget().deleteLater()
            elif child.layout() is not None:
                clearLayout(child.layout())
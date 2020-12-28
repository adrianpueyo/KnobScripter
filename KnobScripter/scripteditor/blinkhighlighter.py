import nuke

try:
    if nuke.NUKE_VERSION_MAJOR < 11:
        from PySide import QtCore, QtGui, QtGui as QtWidgets
        from PySide.QtCore import Qt
    else:
        from PySide2 import QtWidgets, QtGui, QtCore
        from PySide2.QtCore import Qt
except ImportError:
    from Qt import QtCore, QtGui, QtWidgets

class KSBlinkHighlighter(QtGui.QSyntaxHighlighter):
    '''
    Blink code highlighter class!
    Modified over Foundry's nukescripts.blinkscripteditor module.
    '''

    # TODO open curly braces { and enter should bring the } an extra line down

    def __init__(self, document, parent=None):

        super(KSBlinkHighlighter, self).__init__(document)
        self.knobScripter = parent
        self.script_editor = self.knobScripter.script_editor
        self.selected_text = ""
        self.selected_text_prev = ""

        self.styles = self.loadStyles()  # Holds a dict for each style
        self.setStyle()  # Set default style
        self.updateStyle()  # Load ks color scheme

    def loadStyles(self):
        ''' Loads the different sets of rules '''
        styles = dict()
        styles["nuke"] = self.loadStyleNuke()
        return styles

    def loadStyleNuke(self):
        '''
        My adaptation from the default style from Nuke, with some improvements.
        '''
        styles = {
            'keyword': self.format([122, 136, 53], 'bold'),
            'stringDoubleQuote': self.format([226, 138, 138]),
            'stringSingleQuote': self.format([110, 160, 121]),
            'comments': self.format([188, 179, 84]),
            'multiline_comments': self.format([188, 179, 84]),
            'types': self.format([25, 25, 80]),
            'variableKeywords': self.format([25, 25, 80]),
            'functions': self.format([3, 185, 191]),  # only needed till here for blink?
            'numbers': self.format([174, 129, 255]),
            'custom': self.format([255, 170, 0], 'italic'),
            'selected': self.format([255, 255, 255], 'bold underline'),
            'underline': self.format([240, 240, 240], 'underline'),
        }

        keywords = [
            "char", "class", "const", "double", "enum", "explicit",
            "friend", "inline", "int", "long", "namespace", "operator",
            "private", "protected", "public", "short", "signed",
            "static", "struct", "template", "typedef", "typename",
            "union", "unsigned", "virtual", "void", "volatile",
            "local", "param", "kernel",
        ]

        operatorKeywords = [
            '=', '==', '!=', '<', '<=', '>', '>=',
            '\+', '-', '\*', '/', '//', '\%', '\*\*',
            '\+=', '-=', '\*=', '/=', '\%=',
            '\^', '\|', '\&', '\~', '>>', '<<', '\+\+'
        ]

        variableKeywords = [
            "int", "int2", "int3", "int4",
            "float", "float2", "float3", "float4", "float3x3", "float4x4", "bool"
        ]

        blinkTypes = [
            "Image", "eRead", "eWrite", "eReadWrite", "eEdgeClamped", "eEdgeConstant", "eEdgeNull",
            "eAccessPoint", "eAccessRanged1D", "eAccessRanged2D", "eAccessRandom",
            "eComponentWise", "ePixelWise", "ImageComputationKernel",
        ]

        blinkFunctions = [
            "define", "defineParam", "process", "init", "setRange", "setAxis", "median", "bilinear",
        ]

        # Rules

        rules = []

        # 1. Keywords
        rules += [(r'\b%s\b' % i, 0, styles['keyword']) for i in keywords]

        # 2. Funcs
        rules += [(r'\b%s\b' % i, 0, styles['functions']) for i in blinkFunctions]

        # 3. Types
        rules += [(r'\b%s\b' % i, 0, styles['types']) for i in blinkTypes]
        rules += [(r'\b%s\b' % i, 0, styles['variableKeywords']) for i in variableKeywords]

        # 4. String Literals
        rules += [(r"\"([^\"\\\\]|\\\\.)*\"", 0, styles['stringDoubleQuote'])]

        # 5. String single quotes
        rules += [(r"'([^'\\\\]|\\\\.)*'", 0, styles['stringSingleQuote'])]

        # 6. Comments
        rules += [(r"//[^\n]*", 0, styles['comments'])]

        # 7. Multiline comments /* */
        multiline_delimiter = (QtCore.QRegExp("/\\*"), QtCore.QRegExp("\\*/"), 1, styles['multiline_comments'])

        # Return all rules
        style = {
            "rules": [(QtCore.QRegExp(pat), index, fmt) for (pat, index, fmt) in rules],
            "multiline_delimiter": multiline_delimiter,
        }
        return style

    def format(self, rgb, style=''):
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
        if 'underline' in style:
            textFormat.setUnderlineStyle(QtGui.QTextCharFormat.SingleUnderline)

        return textFormat

    def highlightBlock(self, text):
        '''
        Apply syntax highlighting to the given block of text.
        '''
        for expression, nth, format in self.rules:
            index = expression.indexIn(text, 0)

            while index >= 0:
                # We actually want the index of the nth match
                index = expression.pos(nth)
                length = len(expression.cap(nth))
                self.setFormat(index, length, format)
                index = expression.indexIn(text, index + length)

        self.setCurrentBlockState(0)

        # Multi-line strings etc. based on selected scheme
        in_multiline = self.match_multiline_blink(text, *self.commentStartEnd)

    def match_multiline_blink(self, text, delimiter_start, delimiter_end, in_state, style):
        '''
        Check whether highlighting requires multiple lines.
        '''
        # If inside multiline comment, start at 0
        if self.previousBlockState() == in_state:
            start = 0
            add = 0
        # Otherwise, look for the delimiter on this line
        else:
            start = delimiter_start.indexIn(text)
            # Move past this match
            add = delimiter_start.matchedLength()

        # As long as there's a delimiter match on this line...
        while start >= 0:
            # Look for the ending delimiter
            end = delimiter_end.indexIn(text, start + add)
            # Ending delimiter on this line?
            if end >= add:
                length = end - start + add + delimiter_end.matchedLength()
                self.setCurrentBlockState(0)
            # No; multi-line string
            else:
                self.setCurrentBlockState(in_state)
                length = len(text) - start + add
            # Apply formatting
            self.setFormat(start, length, style)
            # Look for the next match
            start = delimiter_start.indexIn(text, start + length)

        # Return True if still inside a multi-line string, False otherwise
        if self.currentBlockState() == in_state:
            return True
        else:
            return False
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

    def __init__(self, document,  style="default"):

        self.selected_text = ""
        self.selected_text_prev = ""

        self.styles = self.loadStyles()  # Holds a dict for each style
        self._style = style  # Can be set via setStyle
        self._style = "default"  # TODO REMOVE
        self.setStyle(self._style)  # Set default style

        super(KSBlinkHighlighter, self).__init__(document)

    def loadStyles(self):
        ''' Loads the different sets of rules '''
        styles = dict()

        # LOAD ANY STYLE
        default_styles_list = [
            {
                "title": "default",
                "desc": "My adaptation from the default style from Nuke, with some improvements.",
                "styles": {
                    'keyword': ([122, 136, 53], 'bold'),
                    'stringDoubleQuote': ([226, 138, 138]),
                    'stringSingleQuote': ([110, 160, 121]),
                    'comment': ([188, 179, 84]),
                    'multiline_comment': ([188, 179, 84]),
                    'type': ([25, 25, 80]),
                    'variableKeyword': ([25, 25, 80]),
                    'function': ([3, 185, 191]),  # only needed till here for blink?
                    'number': ([174, 129, 255]),
                    'custom': ([255, 170, 0], 'italic'),
                    'selected': ([255, 255, 255], 'bold underline'),
                    'underline': ([240, 240, 240], 'underline'),
                },
                "keywords": {},
            },
        ]

        for style_dict in default_styles_list:
            if all(k in style_dict.keys() for k in ["title", "styles"]):
                styles[style_dict["title"]] = self.loadStyle(style_dict)

        return styles

    def loadStyle(self, style_dict):
        '''
        Given a dictionary of styles and keywords, returns the style as a dict
        '''

        styles = style_dict["styles"]

        # 1. Base settings
        if "base" in styles:
            base_format = styles["base"]
        else:
            base_format = self.format([255, 255, 255])

        for key in styles:
            if type(styles[key]) == list:
                styles[key] = self.format(styles[key])
            elif styles[key][1]:
                styles[key] = self.format(styles[key][0], styles[key][1])

        mainKeywords = [
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
            "float", "float2", "float3", "float4", "float3x3", "float4x4", "bool",
        ]

        blinkTypes = [
            "Image", "eRead", "eWrite", "eReadWrite", "eEdgeClamped", "eEdgeConstant", "eEdgeNull",
            "eAccessPoint", "eAccessRanged1D", "eAccessRanged2D", "eAccessRandom",
            "eComponentWise", "ePixelWise", "ImageComputationKernel",
        ]

        blinkFunctions = [
            "define", "defineParam", "process", "init", "setRange", "setAxis", "median", "bilinear",
        ]

        singletons = ['true', 'false']

        if 'multiline_comments' in styles:
            multiline_delimiter = (QtCore.QRegExp("/\\*"), QtCore.QRegExp("\\*/"), 1, styles['multiline_comments'])
        else:
            multiline_delimiter = (QtCore.QRegExp("/\\*"), QtCore.QRegExp("\\*/"), 1, base_format)

        # 2. Rules
        rules = []

        # Keywords
        if 'keyword' in styles:
            rules += [(r'\b%s\b' % i, 0, styles['keyword']) for i in mainKeywords]

        # Funcs
        if 'function' in styles:
            rules += [(r'\b%s\b' % i, 0, styles['function']) for i in blinkFunctions]

        # Types
        if 'type' in styles:
            rules += [(r'\b%s\b' % i, 0, styles['type']) for i in blinkTypes]

        if 'variableKeyword' in styles:
            rules += [(r'\b%s\b' % i, 0, styles['variableKeyword']) for i in variableKeywords]

        # String Literals
        if 'stringDoubleQuote' in styles:
            rules += [(r"\"([^\"\\\\]|\\\\.)*\"", 0, styles['stringDoubleQuote'])]

        # String single quotes
        if 'stringSingleQuote' in styles:
            rules += [(r"'([^'\\\\]|\\\\.)*'", 0, styles['stringSingleQuote'])]

        # Comments
        if 'comment' in styles:
            rules += [(r"//[^\n]*", 0, styles['comment'])]

        # Return all rules
        result = {
            "rules": [(QtCore.QRegExp(pat), index, fmt) for (pat, index, fmt) in rules],
            "multiline_delimiter": multiline_delimiter,
        }
        return result

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

        for expression, nth, format in self.styles[self._style]["rules"]:
            index = expression.indexIn(text, 0)

            while index >= 0:
                # We actually want the index of the nth match
                index = expression.pos(nth)
                length = len(expression.cap(nth))
                self.setFormat(index, length, format)
                index = expression.indexIn(text, index + length)

        self.setCurrentBlockState(0)

        # Multi-line strings etc. based on selected scheme
        in_multiline = self.match_multiline_blink(text, *self.styles[self._style]["multiline_delimiter"])

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

    def setStyle(self,style=""):
        pass
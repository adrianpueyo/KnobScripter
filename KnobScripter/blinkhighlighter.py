import nuke

try:
    if nuke.NUKE_VERSION_MAJOR >= 16:
        from PySide6 import QtCore, QtGui, QtWidgets
        from PySide6.QtCore import Qt, QRegularExpression
        IS_PYSIDE6 = True
    elif nuke.NUKE_VERSION_MAJOR >= 11:
        from PySide2 import QtCore, QtGui, QtWidgets
        from PySide2.QtCore import Qt
        IS_PYSIDE6 = False
    else:
        from PySide import QtCore, QtGui, QtGui as QtWidgets
        from PySide.QtCore import Qt
        IS_PYSIDE6 = False
except ImportError:
    from Qt import QtCore, QtGui, QtWidgets
    IS_PYSIDE6 = False

# If using PySide6, provide a QRegExp compatibility wrapper using QRegularExpression.
if IS_PYSIDE6:
    class QRegExpCompat(object):
        """
        Compatibility wrapper for QRegExp using QRegularExpression in PySide6.
        Provides a subset of the QRegExp API required for highlighting.
        """
        def __init__(self, pattern):
            self.regex = QRegularExpression(pattern)
            self._match = None

        def indexIn(self, text, offset=0):
            match = self.regex.match(text, offset)
            if match.hasMatch():
                self._match = match
                return match.capturedStart(0)
            self._match = None
            return -1

        def pos(self, nth):
            if self._match is None:
                return -1
            return self._match.capturedStart(nth)

        def cap(self, nth):
            if self._match is None:
                return ""
            return self._match.captured(nth)

        def matchedLength(self):
            if self._match is None:
                return 0
            return self._match.capturedLength()
    # Override QtCore.QRegExp with our compatibility class.
    QtCore.QRegExp = QRegExpCompat

class KSBlinkHighlighter(QtGui.QSyntaxHighlighter):
    '''
    Blink code highlighter class.
    Modified over Foundry's nukescripts.blinkscripteditor module.
    '''

    # TODO open curly braces { and enter should bring the } an extra line down

    def __init__(self, document, style="default"):
        """
        Initialize the blink highlighter with the given document and style.

        :param document: The QTextDocument to apply highlighting.
        :param style: The name of the style to use.
        """
        super(KSBlinkHighlighter, self).__init__(document)
        self.selected_text = ""
        self.selected_text_prev = ""
        self.styles = self.loadStyles()  # Holds a dict for each style.
        self._style = style  # Can be set via setStyle.
        # For now forcing the default style
        self._style = "default"
        self.setStyle(self._style)  # Apply default style.


    def loadStyles(self):
        '''
        Loads the different sets of highlighting rules.

        :return: A dictionary mapping style names to their corresponding rules.
        '''
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
                    'function': ([3, 185, 191]),  # Only needed till here for blink?
                    'number': ([174, 129, 255]),
                    'custom': ([255, 170, 0], 'italic'),
                    'selected': ([255, 255, 255], 'bold underline'),
                    'underline': ([240, 240, 240], 'underline'),
                },
                "keywords": {},
            },
        ]

        for style_dict in default_styles_list:
            if all(k in style_dict for k in ["title", "styles"]):
                styles[style_dict["title"]] = self.loadStyle(style_dict)

        return styles

    def loadStyle(self, style_dict):
        '''
        Given a dictionary of styles and keywords, returns the style as a dict.

        :param style_dict: A dictionary containing style definitions.
        :return: A dictionary with formatting rules and a multiline delimiter.
        '''
        styles = style_dict["styles"]

        # 1. Base settings.
        if "base" in styles:
            base_format = styles["base"]
        else:
            base_format = self.format([255, 255, 255])

        for key in styles:
            if isinstance(styles[key], list):
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

        # 2. Rules.
        rules = []

        # Keywords.
        if 'keyword' in styles:
            rules += [(r'\b%s\b' % i, 0, styles['keyword']) for i in mainKeywords]

        # Functions.
        if 'function' in styles:
            rules += [(r'\b%s\b' % i, 0, styles['function']) for i in blinkFunctions]

        # Types.
        if 'type' in styles:
            rules += [(r'\b%s\b' % i, 0, styles['type']) for i in blinkTypes]

        if 'variableKeyword' in styles:
            rules += [(r'\b%s\b' % i, 0, styles['variableKeyword']) for i in variableKeywords]

        # String Literals.
        if 'stringDoubleQuote' in styles:
            rules += [(r"\"([^\"\\\\]|\\\\.)*\"", 0, styles['stringDoubleQuote'])]

        # String single quotes.
        if 'stringSingleQuote' in styles:
            rules += [(r"'([^'\\\\]|\\\\.)*'", 0, styles['stringSingleQuote'])]

        # Comments.
        if 'comment' in styles:
            rules += [(r"//[^\n]*", 0, styles['comment'])]

        # Return all rules.
        result = {
            "rules": [(QtCore.QRegExp(pat), index, fmt) for (pat, index, fmt) in rules],
            "multiline_delimiter": multiline_delimiter,
        }
        return result

    def format(self, rgb, style=''):
        '''
        Return a QTextCharFormat with the given attributes.

        :param rgb: A list of three integers for the RGB colour.
        :param style: A string with style attributes like 'bold', 'italic', 'underline'.
        :return: A configured QTextCharFormat object.
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

        :param text: A single block of text from the document.
        '''
        for expression, nth, fmt in self.styles[self._style]["rules"]:
            index = expression.indexIn(text, 0)
            while index >= 0:
                # Retrieve the position of the nth captured group.
                index = expression.pos(nth)
                length = len(expression.cap(nth))
                self.setFormat(index, length, fmt)
                index = expression.indexIn(text, index + length)

        self.setCurrentBlockState(0)
        # Apply multi-line comment formatting.
        self.match_multiline_blink(text, *self.styles[self._style]["multiline_delimiter"])

    def match_multiline_blink(self, text, delimiter_start, delimiter_end, in_state, style):
        '''
        Check whether highlighting requires multiple lines.

        :param text: The text block to search for multiline patterns.
        :param delimiter_start: The starting delimiter as a QRegExp.
        :param delimiter_end: The ending delimiter as a QRegExp.
        :param in_state: The state value indicating a multiline block.
        :param style: The QTextCharFormat to apply for multiline blocks.
        :return: True if still inside a multiline block, False otherwise.
        '''
        # If inside a multiline block, start at 0.
        if self.previousBlockState() == in_state:
            start = 0
            add = 0
        else:
            start = delimiter_start.indexIn(text)
            add = delimiter_start.matchedLength()

        while start >= 0:
            end = delimiter_end.indexIn(text, start + add)
            if end >= add:
                length = end - start + add + delimiter_end.matchedLength()
                self.setCurrentBlockState(0)
            else:
                self.setCurrentBlockState(in_state)
                length = len(text) - start + add
            self.setFormat(start, length, style)
            start = delimiter_start.indexIn(text, start + length)

        return self.currentBlockState() == in_state

    def setStyle(self, style="default"):
        """
        Set the syntax highlighting style.

        :param style: The name of the style to apply.
        """
        if style in self.styles:
            self._style = style
        else:
            self._style = "default"
        self.rehighlight()

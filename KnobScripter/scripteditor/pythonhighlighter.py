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

class KSPythonHighlighter(QtGui.QSyntaxHighlighter):
    '''
    Adapted from an original __version__ by Wouter Gilsing. His comments:
    Modified, simplified __version__ of some code found I found when researching:
    wiki.python.org/moin/PyQt/Python%20syntax%20highlighting
    They did an awesome job, so credits to them. I only needed to make some
    modifications to make it fit my needs.
    '''

    def __init__(self, document, style="sublime"):

        super(KSPythonHighlighter, self).__init__(document)
        self.selected_text = ""
        self.selected_text_prev = ""

        self.styles = self.loadStyles()  # Holds a dict for each style
        self._style = style # Can be set via setStyle
        self.setStyle(self._style)  # Set default style
        # self.updateStyle()  # Load ks color scheme

    def loadStyles(self):
        ''' Loads the different sets of rules '''
        styles = dict()

        # LOAD ANY STYLE
        default_styles_list = [
            {
                "title": "nuke",
                "styles": {
                    'base': self.format([255, 255, 255]),
                    'keyword': self.format([238, 117, 181], 'bold'),
                    'operator': self.format([238, 117, 181], 'bold'),
                    'number': self.format([174, 129, 255]),
                    'singleton': self.format([174, 129, 255]),
                    'string': self.format([242, 136, 135]),
                    'comment': self.format([143, 221, 144]),
                },
                "keywords": {},
            },
            {
                "title": "sublime",
                "styles": {
                    'base': self.format([255, 255, 255]),
                    'keyword': self.format([237, 36, 110]),
                    'operator': self.format([237, 36, 110]),
                    'string': self.format([237, 229, 122]),
                    'comment': self.format([125, 125, 125]),
                    'number': self.format([165, 120, 255]),
                    'singleton': self.format([165, 120, 255]),
                    'function': self.format([184, 237, 54]),
                    'argument': self.format([255, 170, 10], 'italic'),
                    'class': self.format([184, 237, 54]),
                    'callable': self.format([130, 226, 255]),
                    'error': self.format([130, 226, 255], 'italic'),
                    'underline': self.format([240, 240, 240], 'underline'),
                    'selected': self.format([255, 255, 255], 'bold underline'),
                    'custom': self.format([200, 200, 200], 'italic'),
                    'blue': self.format([130, 226, 255], 'italic'),
                    'self': self.format([255, 170, 10], 'italic'),
                },
                "keywords": {
                    'custom': ['nuke'],
                    'blue': ['def', 'class', 'int', 'str', 'float',
                             'bool', 'list', 'dict', 'set', ],
                    'base': [],
                    'self': ['self'],
                },
            }
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

        mainKeywords = [
            'and', 'assert', 'break', 'continue',
            'del', 'elif', 'else', 'except', 'exec', 'finally',
            'for', 'from', 'global', 'if', 'import', 'in',
            'is', 'lambda', 'not', 'or', 'pass', 'print',
            'raise', 'return', 'try', 'while', 'yield', 'with', 'as'
        ]

        errorKeywords = ['AssertionError', 'AttributeError', 'EOFError', 'FloatingPointError',
                         'FloatingPointError', 'GeneratorExit', 'ImportError', 'IndexError',
                         'KeyError', 'KeyboardInterrupt', 'MemoryError', 'NameError',
                         'NotImplementedError', 'OSError', 'OverflowError', 'ReferenceError',
                         'RuntimeError', 'StopIteration', 'SyntaxError', 'IndentationError',
                         'TabError', 'SystemError', 'SystemExit', 'TypeError', 'UnboundLocalError',
                         'UnicodeError', 'UnicodeEncodeError', 'UnicodeDecodeError', 'UnicodeTranslateError',
                         'ValueError', 'ZeroDivisionError',
                         ]

        baseKeywords = [',']

        operatorKeywords = [
            '=', '==', '!=', '<', '<=', '>', '>=',
            '\+', '-', '\*', '/', '//', '\%', '\*\*',
            '\+=', '-=', '\*=', '/=', '\%=',
            '\^', '\|', '\&', '\~', '>>', '<<'
        ]

        singletons = ['True', 'False', 'None']

        if 'comment' in styles:
            tri_single = (QtCore.QRegExp("'''"), 1, styles['comment'])
            tri_double = (QtCore.QRegExp('"""'), 2, styles['comment'])
        else:
            tri_single = (QtCore.QRegExp("'''"), 1, base_format)
            tri_double = (QtCore.QRegExp('"""'), 2, base_format)

        # 2. Rules
        rules = []

        if "argument" in styles:
            # Everything inside parentheses
            rules += [(r"def [\w]+[\s]*\((.*)\)", 1, styles['argument'])]
            # Now restore unwanted stuff...
            rules += [(i, 0, base_format) for i in baseKeywords]
            rules += [(r"[^\(\w),.][\s]*[\w]+", 0, base_format)]

        if "callable" in styles:
            rules += [(r"\b([\w]+)[\s]*[(]", 1, styles['callable'])]

        if "keyword" in styles:
            rules += [(r'\b%s\b' % i, 0, styles['keyword']) for i in mainKeywords]

        if "error" in styles:
            rules += [(r'\b%s\b' % i, 0, styles['error']) for i in errorKeywords]

        if "operator" in styles:
            rules += [(i, 0, styles['operator']) for i in operatorKeywords]

        if "singleton" in styles:
            rules += [(r'\b%s\b' % i, 0, styles['singleton']) for i in singletons]

        if "number" in styles:
            rules += [(r'\b[0-9]+\b', 0, styles['number'])]

        if "string" in styles:
            # Double-quoted string, possibly containing escape sequences
            rules += [(r'"[^"\\]*(\\.[^"\\]*)*"', 0, styles['string'])]
            # Single-quoted string, possibly containing escape sequences
            rules += [(r"'[^'\\]*(\\.[^'\\]*)*'", 0, styles['string'])]

        # Comments from '#' until a newline
        if "comment" in styles:
            rules += [(r'#[^\n]*', 0, styles['comment'])]

        # Function definitions
        if "function" in styles:
            rules += [(r"def[\s]+([\w\.]+)", 1, styles['function'])]

        # Class definitions
        if "class" in styles:
            rules += [(r"class[\s]+([\w\.]+)", 1, styles['class'])]
            # Class argument (which is also a class so must be same color)
            rules += [(r"class[\s]+[\w\.]+[\s]*\((.*)\)", 1, styles['class'])]

        # Function arguments
        if "argument" in styles:
            rules += [(r"def[\s]+[\w]+[\s]*\(([\w]+)", 1, styles['argument'])]

        # Custom keywords
        if "keywords" in style_dict.keys():
            keywords = style_dict["keywords"]
            for k in keywords.keys():
                if k in styles:
                    rules += [(r'\b%s\b' % i, 0, styles[k]) for i in keywords[k]]

        # 3. Resulting dictionary
        result = {
            "rules": [(QtCore.QRegExp(pat), index, fmt) for (pat, index, fmt) in rules],
            # Build a QRegExp for each pattern
            "tri_single": tri_single,
            "tri_double": tri_double,
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
        self.updateStyle()

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
        in_multiline = self.match_multiline(text, *self.styles[self._style]["tri_single"])
        if not in_multiline:
            in_multiline = self.match_multiline(text, *self.styles[self._style]["tri_double"])

        # TODO if there's a selection, highlight same occurrences in the full document. If no selection but something highlighted, unhighlight full document. (do it thru regex or sth)

    def updateStyle(self):
        try:
            self.setStyle(self.color_scheme)
        except:
            pass

    def setStyle(self, style_name="nuke"):
        if style_name in self.styles.keys():
            self._style = style_name
        else:
            raise Exception("Style {} not found.".format(str(style_name)))

    def match_multiline(self, text, delimiter, in_state, style):
        '''
        Check whether highlighting requires multiple lines.
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

    @property
    def style(self):
        return self._style

    @style.setter
    def style(self, style_name="nuke"):
        self.setStyle(style_name)
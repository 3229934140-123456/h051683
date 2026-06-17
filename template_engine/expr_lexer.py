class ExprToken:
    __slots__ = ('type', 'value')

    NAME = 'name'
    DOT = 'dot'
    PIPE = 'pipe'
    COMMA = 'comma'
    COLON = 'colon'
    STRING = 'string'
    NUMBER = 'number'
    LPAREN = 'lparen'
    RPAREN = 'rparen'
    LBRACKET = 'lbracket'
    RBRACKET = 'rbracket'
    EQ = 'eq'
    NE = 'ne'
    LT = 'lt'
    GT = 'gt'
    LE = 'le'
    GE = 'ge'
    PLUS = 'plus'
    MINUS = 'minus'
    STAR = 'star'
    SLASH = 'slash'
    AND = 'and'
    OR = 'or'
    NOT = 'not'
    IN = 'in'
    TRUE = 'true'
    FALSE = 'false'
    NONE = 'none'
    EOF = 'eof'

    def __init__(self, type, value=None):
        self.type = type
        self.value = value

    def __repr__(self):
        return f"ExprToken({self.type}, {self.value!r})"


_KEYWORDS = {
    'and': ExprToken.AND,
    'or': ExprToken.OR,
    'not': ExprToken.NOT,
    'in': ExprToken.IN,
    'True': ExprToken.TRUE,
    'False': ExprToken.FALSE,
    'true': ExprToken.TRUE,
    'false': ExprToken.FALSE,
    'None': ExprToken.NONE,
    'none': ExprToken.NONE,
}

_SYMBOLS = {
    '.': ExprToken.DOT,
    '|': ExprToken.PIPE,
    ',': ExprToken.COMMA,
    ':': ExprToken.COLON,
    '(': ExprToken.LPAREN,
    ')': ExprToken.RPAREN,
    '[': ExprToken.LBRACKET,
    ']': ExprToken.RBRACKET,
    '+': ExprToken.PLUS,
    '-': ExprToken.MINUS,
    '*': ExprToken.STAR,
    '/': ExprToken.SLASH,
}

_MULTI_CHAR_SYMBOLS = [
    ('==', ExprToken.EQ),
    ('!=', ExprToken.NE),
    ('<=', ExprToken.LE),
    ('>=', ExprToken.GE),
    ('<', ExprToken.LT),
    ('>', ExprToken.GT),
]


class ExprLexer:
    def __init__(self, source):
        self.source = source
        self.pos = 0
        self.length = len(source)

    def tokenize(self):
        tokens = []
        while self.pos < self.length:
            self._skip_whitespace()
            if self.pos >= self.length:
                break

            ch = self.source[self.pos]

            matched_multi = False
            for sym, tok_type in _MULTI_CHAR_SYMBOLS:
                if self.source[self.pos:self.pos + len(sym)] == sym:
                    tokens.append(ExprToken(tok_type, sym))
                    self.pos += len(sym)
                    matched_multi = True
                    break
            if matched_multi:
                continue

            if ch in _SYMBOLS:
                tokens.append(ExprToken(_SYMBOLS[ch], ch))
                self.pos += 1
                continue

            if ch == '"' or ch == "'":
                tokens.append(self._read_string())
                continue

            if ch.isdigit() or (ch == '.' and self.pos + 1 < self.length
                                and self.source[self.pos + 1].isdigit()):
                tokens.append(self._read_number())
                continue

            if ch.isalpha() or ch == '_':
                tokens.append(self._read_name())
                continue

            raise SyntaxError(
                f"Unexpected character {ch!r} at position {self.pos} "
                f"in expression: {self.source!r}"
            )

        tokens.append(ExprToken(ExprToken.EOF))
        return tokens

    def _skip_whitespace(self):
        while self.pos < self.length and self.source[self.pos] in ' \t\r\n':
            self.pos += 1

    def _read_string(self):
        quote = self.source[self.pos]
        self.pos += 1
        start = self.pos
        result = []
        while self.pos < self.length:
            ch = self.source[self.pos]
            if ch == '\\' and self.pos + 1 < self.length:
                next_ch = self.source[self.pos + 1]
                if next_ch == quote:
                    result.append(quote)
                    self.pos += 2
                elif next_ch == 'n':
                    result.append('\n')
                    self.pos += 2
                elif next_ch == 't':
                    result.append('\t')
                    self.pos += 2
                elif next_ch == '\\':
                    result.append('\\')
                    self.pos += 2
                else:
                    result.append(ch)
                    self.pos += 1
            elif ch == quote:
                self.pos += 1
                return ExprToken(ExprToken.STRING, ''.join(result))
            else:
                result.append(ch)
                self.pos += 1
        raise SyntaxError(f"Unterminated string in expression: {self.source!r}")

    def _read_number(self):
        start = self.pos
        has_dot = False
        while self.pos < self.length:
            ch = self.source[self.pos]
            if ch.isdigit():
                self.pos += 1
            elif ch == '.' and not has_dot:
                has_dot = True
                self.pos += 1
            else:
                break
        value = self.source[start:self.pos]
        if has_dot:
            return ExprToken(ExprToken.NUMBER, float(value))
        return ExprToken(ExprToken.NUMBER, int(value))

    def _read_name(self):
        start = self.pos
        while self.pos < self.length and (self.source[self.pos].isalnum()
                                          or self.source[self.pos] == '_'):
            self.pos += 1
        name = self.source[start:self.pos]
        if name in _KEYWORDS:
            return ExprToken(_KEYWORDS[name], name)
        return ExprToken(ExprToken.NAME, name)

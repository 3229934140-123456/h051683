class Token:
    __slots__ = ('type', 'value', 'line')

    TEXT = 'text'
    VAR_EXPR = 'var_expr'
    TAG_EXPR = 'tag_expr'
    COMMENT = 'comment'

    def __init__(self, type, value, line=0):
        self.type = type
        self.value = value
        self.line = line

    def __repr__(self):
        return f"Token({self.type}, {self.value!r}, line={self.line})"


class Lexer:
    VAR_OPEN = '{{'
    VAR_CLOSE = '}}'
    TAG_OPEN = '{%'
    TAG_CLOSE = '%}'
    COMMENT_OPEN = '{#'
    COMMENT_CLOSE = '#}'

    def __init__(self):
        pass

    def tokenize(self, source):
        tokens = []
        pos = 0
        line = 1
        length = len(source)

        while pos < length:
            var_pos = source.find(self.VAR_OPEN, pos)
            tag_pos = source.find(self.TAG_OPEN, pos)
            comment_pos = source.find(self.COMMENT_OPEN, pos)

            candidates = []
            if var_pos != -1:
                candidates.append((var_pos, 'var'))
            if tag_pos != -1:
                candidates.append((tag_pos, 'tag'))
            if comment_pos != -1:
                candidates.append((comment_pos, 'comment'))

            if not candidates:
                text = source[pos:]
                if text:
                    tokens.append(Token(Token.TEXT, text, line))
                break

            candidates.sort(key=lambda c: c[0])
            nearest_pos, nearest_type = candidates[0]

            if nearest_pos > pos:
                text = source[pos:nearest_pos]
                line += text.count('\n')
                tokens.append(Token(Token.TEXT, text, line))

            if nearest_type == 'var':
                close_pos = source.find(self.VAR_CLOSE, nearest_pos + 2)
                if close_pos == -1:
                    raise SyntaxError(
                        f"Unclosed variable tag at line {line}"
                    )
                expr = source[nearest_pos + 2:close_pos].strip()
                line += source[nearest_pos:close_pos + 2].count('\n')
                tokens.append(Token(Token.VAR_EXPR, expr, line))
                pos = close_pos + 2

            elif nearest_type == 'tag':
                close_pos = source.find(self.TAG_CLOSE, nearest_pos + 2)
                if close_pos == -1:
                    raise SyntaxError(
                        f"Unclosed tag at line {line}"
                    )
                expr = source[nearest_pos + 2:close_pos].strip()
                line += source[nearest_pos:close_pos + 2].count('\n')
                tokens.append(Token(Token.TAG_EXPR, expr, line))
                pos = close_pos + 2

            elif nearest_type == 'comment':
                close_pos = source.find(self.COMMENT_CLOSE, nearest_pos + 2)
                if close_pos == -1:
                    raise SyntaxError(
                        f"Unclosed comment at line {line}"
                    )
                line += source[nearest_pos:close_pos + 2].count('\n')
                pos = close_pos + 2

        return tokens

from .expr_lexer import ExprLexer, ExprToken
from .nodes import (
    NameExpr, GetAttrExpr, GetItemExpr, FilterExpr,
    LiteralExpr, CompareExpr, BoolOpExpr, NotExpr, InExpr,
    BinOpExpr,
)


class ExprParser:
    def __init__(self, source):
        self.tokens = ExprLexer(source).tokenize()
        self.pos = 0

    def current(self):
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return ExprToken(ExprToken.EOF)

    def advance(self):
        token = self.current()
        self.pos += 1
        return token

    def expect(self, token_type):
        token = self.current()
        if token.type != token_type:
            raise SyntaxError(
                f"Expected {token_type}, got {token.type} ({token.value!r})"
            )
        return self.advance()

    def parse(self):
        expr = self.parse_or()
        if self.current().type != ExprToken.EOF:
            raise SyntaxError(
                f"Unexpected token: {self.current().type} "
                f"({self.current().value!r})"
            )
        return expr

    def parse_or(self):
        left = self.parse_and()
        while self.current().type == ExprToken.OR:
            self.advance()
            right = self.parse_and()
            left = BoolOpExpr('or', left, right)
        return left

    def parse_and(self):
        left = self.parse_not()
        while self.current().type == ExprToken.AND:
            self.advance()
            right = self.parse_not()
            left = BoolOpExpr('and', left, right)
        return left

    def parse_not(self):
        if self.current().type == ExprToken.NOT:
            self.advance()
            node = self.parse_not()
            return NotExpr(node)
        return self.parse_comparison()

    def parse_comparison(self):
        left = self.parse_pipe()
        comp_ops = {
            ExprToken.EQ: '==',
            ExprToken.NE: '!=',
            ExprToken.LT: '<',
            ExprToken.GT: '>',
            ExprToken.LE: '<=',
            ExprToken.GE: '>=',
        }
        if self.current().type in comp_ops:
            op = comp_ops[self.current().type]
            self.advance()
            right = self.parse_pipe()
            return CompareExpr(left, op, right)
        if self.current().type == ExprToken.IN:
            self.advance()
            right = self.parse_pipe()
            return InExpr(left, right)
        if (self.current().type == ExprToken.NOT
                and self.pos + 1 < len(self.tokens)
                and self.tokens[self.pos].type == ExprToken.IN):
            self.advance()
            self.advance()
            right = self.parse_pipe()
            return NotExpr(InExpr(left, right))
        return left

    def parse_pipe(self):
        node = self.parse_add()
        while self.current().type == ExprToken.PIPE:
            self.advance()
            name_token = self.expect(ExprToken.NAME)
            args = []
            if self.current().type == ExprToken.LPAREN:
                self.advance()
                if self.current().type != ExprToken.RPAREN:
                    args.append(self.parse_or())
                    while self.current().type == ExprToken.COMMA:
                        self.advance()
                        args.append(self.parse_or())
                self.expect(ExprToken.RPAREN)
            node = FilterExpr(node, name_token.value, args)
        return node

    def parse_add(self):
        left = self.parse_mul()
        while self.current().type in (ExprToken.PLUS, ExprToken.MINUS):
            op = '+' if self.current().type == ExprToken.PLUS else '-'
            self.advance()
            right = self.parse_mul()
            left = BinOpExpr(op, left, right)
        return left

    def parse_mul(self):
        left = self.parse_unary()
        while self.current().type in (ExprToken.STAR, ExprToken.SLASH):
            op = '*' if self.current().type == ExprToken.STAR else '/'
            self.advance()
            right = self.parse_unary()
            left = BinOpExpr(op, left, right)
        return left

    def parse_unary(self):
        if self.current().type == ExprToken.MINUS:
            self.advance()
            node = self.parse_unary()
            return BinOpExpr('*', LiteralExpr(-1), node)
        return self.parse_primary()

    def parse_primary(self):
        token = self.current()

        if token.type == ExprToken.NAME:
            self.advance()
            node = NameExpr(token.value)
            return self._parse_trailer(node)

        if token.type == ExprToken.STRING:
            self.advance()
            return LiteralExpr(token.value)

        if token.type == ExprToken.NUMBER:
            self.advance()
            return LiteralExpr(token.value)

        if token.type == ExprToken.TRUE:
            self.advance()
            return LiteralExpr(True)

        if token.type == ExprToken.FALSE:
            self.advance()
            return LiteralExpr(False)

        if token.type == ExprToken.NONE:
            self.advance()
            return LiteralExpr(None)

        if token.type == ExprToken.LPAREN:
            self.advance()
            expr = self.parse_or()
            self.expect(ExprToken.RPAREN)
            return self._parse_trailer(expr)

        raise SyntaxError(
            f"Unexpected token in expression: {token.type} ({token.value!r})"
        )

    def _parse_trailer(self, node):
        while True:
            if self.current().type == ExprToken.DOT:
                self.advance()
                name = self.expect(ExprToken.NAME)
                node = GetAttrExpr(node, name.value)
            elif self.current().type == ExprToken.LBRACKET:
                self.advance()
                index = self.parse_or()
                self.expect(ExprToken.RBRACKET)
                node = GetItemExpr(node, index)
            else:
                break
        return node

from .nodes import (
    TemplateNode, TextNode, VariableNode, IfNode,
    ForNode, BlockNode, ExtendsNode, IncludeNode,
)
from .expr_parser import ExprParser
from .errors import TemplateSyntaxError


class Parser:
    TAG_IF = 'if'
    TAG_ELIF = 'elif'
    TAG_ELSE = 'else'
    TAG_ENDIF = 'endif'
    TAG_FOR = 'for'
    TAG_ENDFOR = 'endfor'
    TAG_BLOCK = 'block'
    TAG_ENDBLOCK = 'endblock'
    TAG_EXTENDS = 'extends'
    TAG_INCLUDE = 'include'

    BLOCK_TAGS = {
        TAG_IF, TAG_FOR, TAG_BLOCK,
    }

    def __init__(self):
        pass

    def parse(self, tokens):
        self._tokens = tokens
        self._pos = 0
        node = self._parse_body()
        return TemplateNode(children=node)

    def _current(self):
        if self._pos < len(self._tokens):
            return self._tokens[self._pos]
        return None

    def _advance(self):
        token = self._current()
        self._pos += 1
        return token

    def _parse_body(self, end_tags=None):
        nodes = []
        while True:
            token = self._current()
            if token is None:
                if end_tags:
                    raise TemplateSyntaxError(
                        f"Unexpected end of template, "
                        f"expected one of: {end_tags}"
                    )
                break

            if token.type == 'text':
                self._advance()
                nodes.append(TextNode(token.value, token.line))

            elif token.type == 'var_expr':
                self._advance()
                expr = ExprParser(token.value).parse()
                nodes.append(VariableNode(expr, token.line))

            elif token.type == 'tag_expr':
                tag_name = self._get_tag_name(token.value)
                if end_tags and tag_name in end_tags:
                    break
                node = self._parse_tag(token)
                if node is not None:
                    nodes.append(node)

            elif token.type == 'comment':
                self._advance()

            else:
                self._advance()

        return nodes

    def _get_tag_name(self, tag_content):
        parts = tag_content.split(None, 1)
        return parts[0] if parts else ''

    def _parse_tag(self, token):
        tag_content = token.value
        tag_name = self._get_tag_name(tag_content)
        tag_args = tag_content[len(tag_name):].strip()
        self._advance()

        if tag_name == self.TAG_IF:
            return self._parse_if(tag_args, token.line)
        elif tag_name == self.TAG_FOR:
            return self._parse_for(tag_args, token.line)
        elif tag_name == self.TAG_BLOCK:
            return self._parse_block(tag_args, token.line)
        elif tag_name == self.TAG_EXTENDS:
            return self._parse_extends(tag_args, token.line)
        elif tag_name == self.TAG_INCLUDE:
            return self._parse_include(tag_args, token.line)
        else:
            raise TemplateSyntaxError(
                f"Unknown tag: {tag_name}", line=token.line
            )

    def _parse_if(self, condition_text, line):
        branches = []
        condition = ExprParser(condition_text).parse()
        body = self._parse_body(
            end_tags={self.TAG_ELIF, self.TAG_ELSE, self.TAG_ENDIF}
        )
        branches.append((condition, body))

        while True:
            token = self._current()
            if token is None or token.type != 'tag_expr':
                raise TemplateSyntaxError(
                    "Unclosed if tag", line=line
                )
            tag_name = self._get_tag_name(token.value)
            if tag_name == self.TAG_ELIF:
                tag_args = token.value[len(self.TAG_ELIF):].strip()
                self._advance()
                condition = ExprParser(tag_args).parse()
                body = self._parse_body(
                    end_tags={
                        self.TAG_ELIF, self.TAG_ELSE, self.TAG_ENDIF
                    }
                )
                branches.append((condition, body))
            elif tag_name == self.TAG_ELSE:
                self._advance()
                else_body = self._parse_body(
                    end_tags={self.TAG_ENDIF}
                )
                self._expect_tag(self.TAG_ENDIF)
                return IfNode(branches=branches, else_body=else_body,
                             line=line)
            elif tag_name == self.TAG_ENDIF:
                self._advance()
                return IfNode(branches=branches, line=line)
            else:
                raise TemplateSyntaxError(
                    f"Unexpected tag in if block: {tag_name}",
                    line=token.line
                )

    def _parse_for(self, args_text, line):
        if ' in ' not in args_text:
            raise TemplateSyntaxError(
                "For tag requires 'in' keyword", line=line
            )
        parts = args_text.split(' in ', 1)
        var_name = parts[0].strip()
        iterable_text = parts[1].strip()

        if not var_name or not var_name.isidentifier():
            raise TemplateSyntaxError(
                f"Invalid loop variable name: {var_name!r}", line=line
            )

        iterable_expr = ExprParser(iterable_text).parse()
        body = self._parse_body(end_tags={self.TAG_ENDFOR})
        self._expect_tag(self.TAG_ENDFOR)

        return ForNode(var_name=var_name, iterable_expr=iterable_expr,
                       body=body, line=line)

    def _parse_block(self, name, line):
        if not name or not name.isidentifier():
            raise TemplateSyntaxError(
                f"Invalid block name: {name!r}", line=line
            )
        body = self._parse_body(end_tags={self.TAG_ENDBLOCK})
        self._expect_tag(self.TAG_ENDBLOCK)
        return BlockNode(name=name, body=body, line=line)

    def _parse_extends(self, name, line):
        parent_name = self._extract_string_arg(name, 'extends', line)
        return ExtendsNode(parent_name=parent_name, line=line)

    def _parse_include(self, name, line):
        template_name = self._extract_string_arg(name, 'include', line)
        return IncludeNode(template_name=template_name, line=line)

    def _extract_string_arg(self, text, tag_name, line):
        text = text.strip()
        if (text.startswith('"') and text.endswith('"')) or \
           (text.startswith("'") and text.endswith("'")):
            return text[1:-1]
        raise TemplateSyntaxError(
            f"{tag_name} requires a string argument", line=line
        )

    def _expect_tag(self, expected_name):
        token = self._current()
        if token is None or token.type != 'tag_expr':
            raise TemplateSyntaxError(
                f"Expected {expected_name} tag"
            )
        tag_name = self._get_tag_name(token.value)
        if tag_name != expected_name:
            raise TemplateSyntaxError(
                f"Expected {expected_name}, got {tag_name}",
                line=token.line
            )
        self._advance()

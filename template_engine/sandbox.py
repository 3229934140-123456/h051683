from .errors import SecurityError


class Sandbox:
    ALLOWED_FILTERS = frozenset({
        'upper', 'lower', 'capitalize', 'title',
        'strip', 'lstrip', 'rstrip', 'truncate',
        'length', 'first', 'last', 'join', 'sort', 'reverse',
        'default', 'default_if_none', 'replace',
        'escape', 'e', 'safe', 'string', 'int', 'float',
        'abs', 'round', 'batch', 'date', 'number', 'currency',
        'urlencode', 'wordcount', 'trim', 'center', 'count',
    })

    BLOCKED_ATTR_PREFIXES = ('_',)

    BLOCKED_ATTRS = frozenset({
        '__class__', '__mro__', '__bases__', '__subclasses__',
        '__globals__', '__code__', '__func__', '__self__',
        '__module__', '__dict__', '__weakref__',
        '__init__', '__new__', '__del__',
        '__import__', '__builtins__',
    })

    def __init__(self, enabled=True):
        self.enabled = enabled
        self._extra_filters = set()

    def allow_filter(self, name):
        if self.enabled and name.startswith('__') and name.endswith('__'):
            raise SecurityError(
                f"Cannot allow dangerous filter name: {name!r}"
            )
        self._extra_filters.add(name)

    def check_filter(self, name):
        if not self.enabled:
            return
        if name.startswith('__') and name.endswith('__'):
            raise SecurityError(
                f"Filter {name!r} is not allowed in sandbox mode"
            )
        if name not in self.ALLOWED_FILTERS and name not in self._extra_filters:
            raise SecurityError(
                f"Filter {name!r} is not allowed in sandbox mode"
            )

    def check_attribute_access(self, obj, attr):
        if not self.enabled:
            return
        if attr in self.BLOCKED_ATTRS:
            raise SecurityError(
                f"Access to attribute {attr!r} is not allowed"
            )
        for prefix in self.BLOCKED_ATTR_PREFIXES:
            if attr.startswith(prefix) and attr not in ('_length',):
                raise SecurityError(
                    f"Access to attribute {attr!r} starting with "
                    f"{prefix!r} is not allowed"
                )

    def check_tag(self, tag_name):
        if not self.enabled:
            return
        allowed_tags = {
            'if', 'elif', 'else', 'endif',
            'for', 'endfor',
            'block', 'endblock',
            'extends', 'include',
        }
        if tag_name not in allowed_tags:
            raise SecurityError(
                f"Tag {tag_name!r} is not allowed in sandbox mode"
            )

    def check_expression(self, expr_node):
        if not self.enabled:
            return
        from .nodes import (
            NameExpr, GetAttrExpr, GetItemExpr, FilterExpr,
            LiteralExpr, CompareExpr, BoolOpExpr, NotExpr,
            InExpr, BinOpExpr,
        )
        if isinstance(expr_node, NameExpr):
            if expr_node.name.startswith('__'):
                raise SecurityError(
                    f"Access to name {expr_node.name!r} is not allowed"
                )
        elif isinstance(expr_node, GetAttrExpr):
            self.check_attribute_access(None, expr_node.attr)
            self.check_expression(expr_node.obj)
        elif isinstance(expr_node, GetItemExpr):
            self.check_expression(expr_node.obj)
            self.check_expression(expr_node.index)
        elif isinstance(expr_node, FilterExpr):
            self.check_filter(expr_node.name)
            self.check_expression(expr_node.node)
            for arg in expr_node.args:
                self.check_expression(arg)
        elif isinstance(expr_node, CompareExpr):
            self.check_expression(expr_node.left)
            self.check_expression(expr_node.right)
        elif isinstance(expr_node, BoolOpExpr):
            self.check_expression(expr_node.left)
            if expr_node.right:
                self.check_expression(expr_node.right)
        elif isinstance(expr_node, NotExpr):
            self.check_expression(expr_node.node)
        elif isinstance(expr_node, InExpr):
            self.check_expression(expr_node.item)
            self.check_expression(expr_node.container)
        elif isinstance(expr_node, BinOpExpr):
            self.check_expression(expr_node.left)
            self.check_expression(expr_node.right)

    def validate_ast(self, ast):
        if not self.enabled:
            return
        from .nodes import (
            TemplateNode, TextNode, VariableNode, IfNode,
            ForNode, BlockNode, ExtendsNode, IncludeNode,
        )
        self._validate_node(ast)

    def _validate_node(self, node):
        from .nodes import (
            TemplateNode, TextNode, VariableNode, IfNode,
            ForNode, BlockNode, ExtendsNode, IncludeNode,
        )
        if isinstance(node, TemplateNode):
            for child in node.children:
                self._validate_node(child)
        elif isinstance(node, VariableNode):
            self.check_expression(node.expression)
        elif isinstance(node, IfNode):
            for cond, body in node.branches:
                self.check_expression(cond)
                for child in body:
                    self._validate_node(child)
            for child in node.else_body:
                self._validate_node(child)
        elif isinstance(node, ForNode):
            self.check_expression(node.iterable_expr)
            for child in node.body:
                self._validate_node(child)
        elif isinstance(node, BlockNode):
            for child in node.body:
                self._validate_node(child)
        elif isinstance(node, IncludeNode):
            pass
        elif isinstance(node, ExtendsNode):
            pass

class Node:
    pass


class TemplateNode(Node):
    def __init__(self, children=None):
        self.children = children or []


class TextNode(Node):
    def __init__(self, text, line=0):
        self.text = text
        self.line = line


class VariableNode(Node):
    def __init__(self, expression, line=0):
        self.expression = expression
        self.line = line


class IfNode(Node):
    def __init__(self, branches=None, else_body=None, line=0):
        self.branches = branches or []
        self.else_body = else_body or []
        self.line = line


class ForNode(Node):
    def __init__(self, var_name, iterable_expr, body=None, line=0):
        self.var_name = var_name
        self.iterable_expr = iterable_expr
        self.body = body or []
        self.line = line


class BlockNode(Node):
    def __init__(self, name, body=None, line=0):
        self.name = name
        self.body = body or []
        self.line = line


class ExtendsNode(Node):
    def __init__(self, parent_name, line=0):
        self.parent_name = parent_name
        self.line = line


class IncludeNode(Node):
    def __init__(self, template_name, line=0):
        self.template_name = template_name
        self.line = line


class ExprNode(Node):
    pass


class NameExpr(ExprNode):
    def __init__(self, name):
        self.name = name


class GetAttrExpr(ExprNode):
    def __init__(self, obj, attr):
        self.obj = obj
        self.attr = attr


class GetItemExpr(ExprNode):
    def __init__(self, obj, index):
        self.obj = obj
        self.index = index


class FilterExpr(ExprNode):
    def __init__(self, node, name, args=None):
        self.node = node
        self.name = name
        self.args = args or []


class LiteralExpr(ExprNode):
    def __init__(self, value):
        self.value = value


class CompareExpr(ExprNode):
    def __init__(self, left, op, right):
        self.left = left
        self.op = op
        self.right = right


class BoolOpExpr(ExprNode):
    def __init__(self, op, left, right=None):
        self.op = op
        self.left = left
        self.right = right


class NotExpr(ExprNode):
    def __init__(self, node):
        self.node = node


class InExpr(ExprNode):
    def __init__(self, item, container):
        self.item = item
        self.container = container


class BinOpExpr(ExprNode):
    def __init__(self, op, left, right):
        self.op = op
        self.left = left
        self.right = right

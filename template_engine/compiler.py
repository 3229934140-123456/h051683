from .nodes import (
    TemplateNode, TextNode, VariableNode, IfNode,
    ForNode, BlockNode, ExtendsNode, IncludeNode,
    NameExpr, GetAttrExpr, GetItemExpr, FilterExpr,
    LiteralExpr, CompareExpr, BoolOpExpr, NotExpr, InExpr,
    BinOpExpr,
)
from .ir import (
    IRText, IRVariable, IRIf, IRFor, IRBlock,
    IRExtends, IRInclude, CompiledTemplate,
)
from .errors import TemplateSyntaxError


class Compiler:
    def __init__(self, environment=None):
        self.environment = environment
        self._blocks = {}
        self._parent_name = None

    def compile(self, ast, source_name=None):
        self._blocks = {}
        self._parent_name = None
        ir_nodes = self._compile_children(ast.children)
        return CompiledTemplate(
            ir=ir_nodes,
            blocks=self._blocks,
            parent_name=self._parent_name,
            source_name=source_name,
        )

    def _compile_children(self, children):
        result = []
        for node in children:
            compiled = self._compile_node(node)
            if compiled is not None:
                if isinstance(compiled, list):
                    result.extend(compiled)
                else:
                    result.append(compiled)
        return result

    def _compile_node(self, node):
        if isinstance(node, TextNode):
            return IRText(node.text)

        if isinstance(node, VariableNode):
            return self._compile_variable(node)

        if isinstance(node, IfNode):
            return self._compile_if(node)

        if isinstance(node, ForNode):
            return self._compile_for(node)

        if isinstance(node, BlockNode):
            return self._compile_block(node)

        if isinstance(node, ExtendsNode):
            self._parent_name = node.parent_name
            return None

        if isinstance(node, IncludeNode):
            return IRInclude(node.template_name)

        raise TemplateSyntaxError(f"Unknown AST node: {type(node).__name__}")

    def _compile_variable(self, node):
        path, filters = self._compile_expression(node.expression)
        return IRVariable(path=path, filters=filters)

    def _compile_expression(self, expr):
        path = self._extract_path(expr)
        filters = self._extract_filters(expr)
        return path, filters

    def _extract_path(self, expr):
        if isinstance(expr, NameExpr):
            return (expr.name,)
        if isinstance(expr, GetAttrExpr):
            parent_path = self._extract_path(expr.obj)
            if parent_path is not None:
                return parent_path + (expr.attr,)
            return (expr.attr,)
        if isinstance(expr, GetItemExpr):
            if isinstance(expr.index, LiteralExpr):
                parent_path = self._extract_path(expr.obj)
                if parent_path is not None:
                    return parent_path + (expr.index.value,)
            return ('__complex__', expr)
        if isinstance(expr, LiteralExpr):
            return ('__literal__', expr.value)
        return ('__expr__', expr)

    def _extract_filters(self, expr):
        filters = []
        current = expr
        while isinstance(current, FilterExpr):
            compiled_args = []
            for arg in current.args:
                if isinstance(arg, LiteralExpr):
                    compiled_args.append(arg.value)
                else:
                    compiled_args.append(('__expr__', arg))
            filters.insert(0, (current.name, compiled_args))
            current = current.node
        return filters

    def _compile_if(self, node):
        branches = []
        for condition, body in node.branches:
            cond_path, cond_filters = self._compile_expression(condition)
            compiled_body = self._compile_children(body)
            branches.append((cond_path, cond_filters, compiled_body))

        else_body = self._compile_children(node.else_body) if node.else_body else []

        return IRIf(branches=branches, else_body=else_body)

    def _compile_for(self, node):
        iterable_path, iterable_filters = self._compile_expression(
            node.iterable_expr
        )
        compiled_body = self._compile_children(node.body)
        return IRFor(
            var_name=node.var_name,
            iterable_path=iterable_path,
            body=compiled_body,
        )

    def _compile_block(self, node):
        compiled_body = self._compile_children(node.body)
        self._blocks[node.name] = compiled_body
        return IRBlock(name=node.name, body=compiled_body)

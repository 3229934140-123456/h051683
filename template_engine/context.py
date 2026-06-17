from .safestring import SafeString


_UNDEFINED = object()


class Context:
    def __init__(self, data=None):
        self._stack = [data or {}]
        self._block_overrides = {}

    def push(self, data=None):
        self._stack.append(data or {})

    def pop(self):
        if len(self._stack) <= 1:
            raise RuntimeError("Cannot pop the root context")
        return self._stack.pop()

    def resolve(self, path):
        if not path:
            return None

        if path[0] == '__literal__':
            return path[1]

        if path[0] == '__expr__':
            return self._evaluate_expression(path[1])

        if path[0] == '__complex__':
            return self._evaluate_complex(path[1])

        var_name = path[0]
        value = self._lookup(var_name)

        if value is _UNDEFINED:
            return None

        for key in path[1:]:
            value = self._traverse(value, key)
            if value is _UNDEFINED:
                return None

        return value

    def _lookup(self, name):
        for scope in reversed(self._stack):
            if name in scope:
                return scope[name]
        return _UNDEFINED

    def _traverse(self, obj, key):
        if obj is None:
            return _UNDEFINED

        if isinstance(obj, dict):
            if key in obj:
                return obj[key]
            return _UNDEFINED

        if isinstance(key, (int, float)):
            try:
                int_key = int(key)
                if hasattr(obj, '__getitem__') and len(obj) > int_key:
                    return obj[int_key]
            except (TypeError, ValueError, IndexError):
                pass

        if isinstance(key, str):
            if hasattr(obj, key):
                try:
                    return getattr(obj, key)
                except AttributeError:
                    pass

        return _UNDEFINED

    def set(self, key, value):
        self._stack[-1][key] = value

    def set_block_override(self, name, body_ir):
        self._block_overrides[name] = body_ir

    def get_block_override(self, name):
        return self._block_overrides.get(name)

    def _evaluate_expression(self, expr):
        from .nodes import (
            NameExpr, GetAttrExpr, GetItemExpr, LiteralExpr,
            CompareExpr, BoolOpExpr, NotExpr, InExpr, BinOpExpr,
            FilterExpr,
        )

        if isinstance(expr, NameExpr):
            value = self._lookup(expr.name)
            return None if value is _UNDEFINED else value

        if isinstance(expr, GetAttrExpr):
            obj = self._evaluate_expression(expr.obj)
            result = self._traverse(obj, expr.attr)
            return None if result is _UNDEFINED else result

        if isinstance(expr, GetItemExpr):
            obj = self._evaluate_expression(expr.obj)
            index = self._evaluate_expression(expr.index)
            result = self._traverse(obj, index)
            return None if result is _UNDEFINED else result

        if isinstance(expr, LiteralExpr):
            return expr.value

        if isinstance(expr, CompareExpr):
            left = self._evaluate_expression(expr.left)
            right = self._evaluate_expression(expr.right)
            return self._compare(left, expr.op, right)

        if isinstance(expr, BoolOpExpr):
            left = self._evaluate_expression(expr.left)
            if expr.op == 'and':
                if not self._is_truthy(left):
                    return left
                return self._evaluate_expression(expr.right)
            elif expr.op == 'or':
                if self._is_truthy(left):
                    return left
                return self._evaluate_expression(expr.right)

        if isinstance(expr, NotExpr):
            value = self._evaluate_expression(expr.node)
            return not self._is_truthy(value)

        if isinstance(expr, InExpr):
            item = self._evaluate_expression(expr.item)
            container = self._evaluate_expression(expr.container)
            try:
                return item in container
            except TypeError:
                return False

        if isinstance(expr, BinOpExpr):
            left = self._evaluate_expression(expr.left)
            right = self._evaluate_expression(expr.right)
            return self._binop(expr.op, left, right)

        if isinstance(expr, FilterExpr):
            value = self._evaluate_expression(expr.node)
            return value

        return None

    def _evaluate_complex(self, expr):
        return self._evaluate_expression(expr)

    def _compare(self, left, op, right):
        try:
            if op == '==':
                return left == right
            if op == '!=':
                return left != right
            if op == '<':
                return left < right
            if op == '>':
                return left > right
            if op == '<=':
                return left <= right
            if op == '>=':
                return left >= right
        except TypeError:
            return False
        return False

    def _binop(self, op, left, right):
        try:
            if op == '+':
                return left + right
            if op == '-':
                return left - right
            if op == '*':
                return left * right
            if op == '/':
                return left / right
        except (TypeError, ZeroDivisionError):
            return 0
        return 0

    @staticmethod
    def _is_truthy(value):
        if value is None:
            return False
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return value != 0
        if isinstance(value, str):
            return len(value) > 0
        if isinstance(value, (list, tuple, dict, set)):
            return len(value) > 0
        return True

    def is_truthy(self, value):
        return self._is_truthy(value)

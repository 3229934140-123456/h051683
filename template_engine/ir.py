class IRNode:
    pass


class IRText(IRNode):
    __slots__ = ('text',)

    def __init__(self, text):
        self.text = text


class IRVariable(IRNode):
    __slots__ = ('path', 'filters')

    def __init__(self, path, filters=None):
        self.path = path
        self.filters = filters or []


class IRIf(IRNode):
    __slots__ = ('branches', 'else_body')

    def __init__(self, branches=None, else_body=None):
        self.branches = branches or []
        self.else_body = else_body or []


class IRFor(IRNode):
    __slots__ = ('var_name', 'iterable_path', 'body')

    def __init__(self, var_name, iterable_path, body=None):
        self.var_name = var_name
        self.iterable_path = iterable_path
        self.body = body or []


class IRBlock(IRNode):
    __slots__ = ('name', 'body')

    def __init__(self, name, body=None):
        self.name = name
        self.body = body or []


class IRExtends(IRNode):
    __slots__ = ('parent_name',)

    def __init__(self, parent_name):
        self.parent_name = parent_name


class IRInclude(IRNode):
    __slots__ = ('template_name',)

    def __init__(self, template_name):
        self.template_name = template_name


class CompiledTemplate:
    __slots__ = ('ir', 'blocks', 'parent_name', 'source_name')

    def __init__(self, ir, blocks=None, parent_name=None, source_name=None):
        self.ir = ir
        self.blocks = blocks or {}
        self.parent_name = parent_name
        self.source_name = source_name

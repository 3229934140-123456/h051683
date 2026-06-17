import os
from .lexer import Lexer
from .parser import Parser
from .compiler import Compiler
from .filters import FilterRegistry
from .sandbox import Sandbox
from .errors import TemplateNotFoundError, SecurityError


class DictLoader:
    def __init__(self, templates):
        self.templates = templates

    def load(self, name):
        self._validate_path(name)
        if name in self.templates:
            return self.templates[name]
        raise TemplateNotFoundError(name)

    def _validate_path(self, name):
        pass


class FileSystemLoader:
    def __init__(self, search_paths, encoding='utf-8'):
        if isinstance(search_paths, str):
            search_paths = [search_paths]
        self.search_paths = [os.path.abspath(p) for p in search_paths]
        self.encoding = encoding

    def _validate_path(self, name):
        if os.path.isabs(name):
            raise SecurityError(
                f"Absolute paths are not allowed in template "
                f"references: {name!r}"
            )
        if '..' in name.split(os.sep):
            raise SecurityError(
                f"Parent directory references are not allowed in "
                f"template references: {name!r}"
            )
        if '..' in name.split('/'):
            raise SecurityError(
                f"Parent directory references are not allowed in "
                f"template references: {name!r}"
            )

    def load(self, name):
        self._validate_path(name)
        for path in self.search_paths:
            full_path = os.path.normpath(os.path.join(path, name))
            if not os.path.abspath(full_path).startswith(os.path.abspath(path)):
                raise SecurityError(
                    f"Template path escapes the configured template "
                    f"directory: {name!r}"
                )
            if os.path.isfile(full_path):
                with open(full_path, 'r', encoding=self.encoding) as f:
                    return f.read()
        raise TemplateNotFoundError(name)


class ChainLoader:
    def __init__(self, loaders):
        self.loaders = loaders

    def load(self, name):
        for loader in self.loaders:
            try:
                return loader.load(name)
            except TemplateNotFoundError:
                continue
        raise TemplateNotFoundError(name)


class Environment:
    def __init__(self, loader=None, sandbox=None, auto_escape=True,
                 filter_registry=None):
        self.loader = loader or DictLoader({})
        self.sandbox = sandbox or Sandbox(enabled=True)
        self.auto_escape = auto_escape
        self.filter_registry = filter_registry or FilterRegistry()
        self._cache = {}
        self._lexer = Lexer()
        self._parser = Parser()
        self._compiler = Compiler(self)

    def get_template(self, name):
        if name in self._cache:
            return self._cache[name]
        source = self.loader.load(name)
        compiled = self._compile_source(source, source_name=name)
        self._cache[name] = compiled
        return compiled

    def compile_string(self, source, source_name='<string>'):
        return self._compile_source(source, source_name=source_name)

    def _compile_source(self, source, source_name=None):
        tokens = self._lexer.tokenize(source)
        ast = self._parser.parse(tokens)
        self.sandbox.validate_ast(ast)
        compiled = self._compiler.compile(ast, source_name=source_name)
        return compiled

    def clear_cache(self):
        self._cache = {}

    def add_filter(self, name, func):
        self.filter_registry.register(name, func)
        self.sandbox.allow_filter(name)

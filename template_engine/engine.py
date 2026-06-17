from .context import Context
from .environment import Environment, DictLoader, FileSystemLoader, ChainLoader
from .formatter import get_output_format, HtmlOutputFormat, PlainTextOutputFormat
from .renderer import Renderer
from .sandbox import Sandbox
from .safestring import SafeString, mark_safe
from .errors import (
    TemplateSyntaxError, TemplateRuntimeError,
    TemplateNotFoundError, SecurityError,
)


class Engine:
    def __init__(self, loader=None, output_format='html', sandbox_enabled=True,
                 auto_escape=True, custom_filters=None):
        self.sandbox = Sandbox(enabled=sandbox_enabled)
        self.environment = Environment(
            loader=loader or DictLoader({}),
            sandbox=self.sandbox,
            auto_escape=auto_escape,
        )
        self._output_format_name = output_format
        self._output_format = get_output_format(output_format)

        if custom_filters:
            for name, func in custom_filters.items():
                self.environment.add_filter(name, func)

    def render(self, template_name, data=None):
        compiled = self.environment.get_template(template_name)
        context = Context(data)
        renderer = Renderer(
            self.environment,
            self._output_format,
            self.environment.filter_registry,
        )
        return renderer.render(compiled, context)

    def render_string(self, source, data=None):
        compiled = self.environment.compile_string(source)
        context = Context(data)
        renderer = Renderer(
            self.environment,
            self._output_format,
            self.environment.filter_registry,
        )
        return renderer.render(compiled, context)

    def render_with_format(self, template_name, data=None, output_format='html'):
        compiled = self.environment.get_template(template_name)
        context = Context(data)
        fmt = get_output_format(output_format)
        renderer = Renderer(
            self.environment,
            fmt,
            self.environment.filter_registry,
        )
        return renderer.render(compiled, context)

    def render_string_with_format(self, source, data=None, output_format='html'):
        compiled = self.environment.compile_string(source)
        context = Context(data)
        fmt = get_output_format(output_format)
        renderer = Renderer(
            self.environment,
            fmt,
            self.environment.filter_registry,
        )
        return renderer.render(compiled, context)

    def add_filter(self, name, func):
        self.environment.add_filter(name, func)

    def add_template(self, name, source):
        if isinstance(self.environment.loader, DictLoader):
            self.environment.loader.templates[name] = source
            self.environment.clear_cache()
        else:
            raise RuntimeError(
                "add_template only works with DictLoader"
            )

    def compile(self, source):
        return self.environment.compile_string(source)

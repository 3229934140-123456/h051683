from .ir import (
    IRText, IRVariable, IRIf, IRFor, IRBlock,
    IRExtends, IRInclude, CompiledTemplate,
)
from .context import Context
from .filters import FilterRegistry
from .formatter import OutputFormat, HtmlOutputFormat
from .errors import TemplateRuntimeError, TemplateNotFoundError


class Renderer:
    def __init__(self, environment, output_format=None, filter_registry=None):
        self.environment = environment
        self.output_format = output_format or HtmlOutputFormat()
        self.filter_registry = filter_registry or FilterRegistry()

    def render(self, compiled_template, context):
        if compiled_template.parent_name:
            return self._render_with_inheritance(compiled_template, context)
        return self._render_nodes(compiled_template.ir, context)

    def _render_with_inheritance(self, compiled_template, context):
        for name, body in compiled_template.blocks.items():
            context.set_block_override(name, body)

        parent = self.environment.get_template(compiled_template.parent_name)
        return self._render_with_blocks(parent, context)

    def _render_with_blocks(self, compiled_template, context):
        if compiled_template.parent_name:
            for name, body in compiled_template.blocks.items():
                if context.get_block_override(name) is None:
                    context.set_block_override(name, body)
            parent = self.environment.get_template(
                compiled_template.parent_name
            )
            return self._render_with_blocks(parent, context)

        return self._render_nodes(compiled_template.ir, context)

    def _render_nodes(self, nodes, context):
        output = []
        for node in nodes:
            result = self._render_node(node, context)
            if result is not None:
                output.append(result)
        return ''.join(output)

    def _render_node(self, node, context):
        if isinstance(node, IRText):
            return self.output_format.format_raw(node.text)

        if isinstance(node, IRVariable):
            return self._render_variable(node, context)

        if isinstance(node, IRIf):
            return self._render_if(node, context)

        if isinstance(node, IRFor):
            return self._render_for(node, context)

        if isinstance(node, IRBlock):
            return self._render_block(node, context)

        if isinstance(node, IRInclude):
            return self._render_include(node, context)

        raise TemplateRuntimeError(
            f"Unknown IR node: {type(node).__name__}"
        )

    def _render_variable(self, node, context):
        value = context.resolve(node.path)
        if node.filters:
            value = self.filter_registry.apply_chain(value, node.filters)
        return self.output_format.format_value(value)

    def _render_if(self, node, context):
        for cond_path, cond_filters, body in node.branches:
            value = context.resolve(cond_path)
            if cond_filters:
                value = self.filter_registry.apply_chain(
                    value, cond_filters
                )
            if context.is_truthy(value):
                return self._render_nodes(body, context)

        if node.else_body:
            return self._render_nodes(node.else_body, context)

        return ''

    def _render_for(self, node, context):
        iterable = context.resolve(node.iterable_path)
        if iterable is None:
            return ''

        if not hasattr(iterable, '__iter__'):
            return ''

        items = list(iterable)
        if not items:
            return ''

        output = []
        for i, item in enumerate(items):
            context.push({
                node.var_name: item,
                'loop': {
                    'index': i + 1,
                    'index0': i,
                    'first': i == 0,
                    'last': i == len(items) - 1,
                    'length': len(items),
                    'revindex': len(items) - i,
                    'revindex0': len(items) - i - 1,
                },
            })
            output.append(self._render_nodes(node.body, context))
            context.pop()

        return ''.join(output)

    def _render_block(self, node, context):
        override = context.get_block_override(node.name)
        if override is not None:
            return self._render_nodes(override, context)
        return self._render_nodes(node.body, context)

    def _render_include(self, node, context):
        included = self.environment.get_template(node.template_name)
        return self._render_nodes(included.ir, context)

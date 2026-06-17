import unittest
import datetime
from template_engine import (
    Engine, Context, DictLoader, SafeString, mark_safe, is_safe,
    Lexer, Token, Parser, Compiler, Renderer,
    FilterRegistry, Sandbox,
    HtmlOutputFormat, PlainTextOutputFormat, get_output_format,
    TemplateSyntaxError, SecurityError, TemplateNotFoundError,
)
from template_engine.ir import (
    IRText, IRVariable, IRIf, IRFor, IRBlock,
    IRInclude, CompiledTemplate,
)
from template_engine.expr_lexer import ExprLexer, ExprToken
from template_engine.expr_parser import ExprParser


class TestLexer(unittest.TestCase):
    def setUp(self):
        self.lexer = Lexer()

    def test_plain_text(self):
        tokens = self.lexer.tokenize('Hello World')
        self.assertEqual(len(tokens), 1)
        self.assertEqual(tokens[0].type, Token.TEXT)
        self.assertEqual(tokens[0].value, 'Hello World')

    def test_variable(self):
        tokens = self.lexer.tokenize('Hello {{ name }}!')
        self.assertEqual(len(tokens), 3)
        self.assertEqual(tokens[0].type, Token.TEXT)
        self.assertEqual(tokens[0].value, 'Hello ')
        self.assertEqual(tokens[1].type, Token.VAR_EXPR)
        self.assertEqual(tokens[1].value, 'name')
        self.assertEqual(tokens[2].type, Token.TEXT)
        self.assertEqual(tokens[2].value, '!')

    def test_tag(self):
        tokens = self.lexer.tokenize('{% if x %}yes{% endif %}')
        self.assertEqual(len(tokens), 3)
        self.assertEqual(tokens[0].type, Token.TAG_EXPR)
        self.assertEqual(tokens[0].value, 'if x')
        self.assertEqual(tokens[1].type, Token.TEXT)
        self.assertEqual(tokens[1].value, 'yes')
        self.assertEqual(tokens[2].type, Token.TAG_EXPR)
        self.assertEqual(tokens[2].value, 'endif')

    def test_comment(self):
        tokens = self.lexer.tokenize('before{# comment #}after')
        self.assertEqual(len(tokens), 2)
        self.assertEqual(tokens[0].type, Token.TEXT)
        self.assertEqual(tokens[0].value, 'before')
        self.assertEqual(tokens[1].type, Token.TEXT)
        self.assertEqual(tokens[1].value, 'after')

    def test_mixed(self):
        source = 'Hello {{ name | upper }}, {% if show %}visible{% endif %}'
        tokens = self.lexer.tokenize(source)
        types = [t.type for t in tokens]
        self.assertIn(Token.VAR_EXPR, types)
        self.assertIn(Token.TAG_EXPR, types)
        self.assertIn(Token.TEXT, types)

    def test_unclosed_variable(self):
        with self.assertRaises(SyntaxError):
            self.lexer.tokenize('{{ name')

    def test_unclosed_tag(self):
        with self.assertRaises(SyntaxError):
            self.lexer.tokenize('{% if x')

    def test_unclosed_comment(self):
        with self.assertRaises(SyntaxError):
            self.lexer.tokenize('{# comment')

    def test_multiple_variables(self):
        tokens = self.lexer.tokenize('{{ a }} and {{ b }}')
        var_tokens = [t for t in tokens if t.type == Token.VAR_EXPR]
        self.assertEqual(len(var_tokens), 2)
        self.assertEqual(var_tokens[0].value, 'a')
        self.assertEqual(var_tokens[1].value, 'b')


class TestExprLexer(unittest.TestCase):
    def test_simple_name(self):
        tokens = ExprLexer('name').tokenize()
        self.assertEqual(tokens[0].type, ExprToken.NAME)
        self.assertEqual(tokens[0].value, 'name')

    def test_dot_access(self):
        tokens = ExprLexer('user.name').tokenize()
        self.assertEqual(tokens[0].type, ExprToken.NAME)
        self.assertEqual(tokens[1].type, ExprToken.DOT)
        self.assertEqual(tokens[2].type, ExprToken.NAME)

    def test_pipe_filter(self):
        tokens = ExprLexer('name | upper').tokenize()
        self.assertEqual(tokens[0].type, ExprToken.NAME)
        self.assertEqual(tokens[1].type, ExprToken.PIPE)
        self.assertEqual(tokens[2].type, ExprToken.NAME)

    def test_string_literal(self):
        tokens = ExprLexer('"hello"').tokenize()
        self.assertEqual(tokens[0].type, ExprToken.STRING)
        self.assertEqual(tokens[0].value, 'hello')

    def test_number_literal(self):
        tokens = ExprLexer('42').tokenize()
        self.assertEqual(tokens[0].type, ExprToken.NUMBER)
        self.assertEqual(tokens[0].value, 42)

    def test_float_literal(self):
        tokens = ExprLexer('3.14').tokenize()
        self.assertEqual(tokens[0].type, ExprToken.NUMBER)
        self.assertEqual(tokens[0].value, 3.14)

    def test_operators(self):
        tokens = ExprLexer('a == b').tokenize()
        self.assertEqual(tokens[1].type, ExprToken.EQ)

    def test_boolean_keywords(self):
        tokens = ExprLexer('a and b or not c').tokenize()
        self.assertEqual(tokens[1].type, ExprToken.AND)
        self.assertEqual(tokens[3].type, ExprToken.OR)
        self.assertEqual(tokens[4].type, ExprToken.NOT)

    def test_in_keyword(self):
        tokens = ExprLexer('item in items').tokenize()
        self.assertEqual(tokens[1].type, ExprToken.IN)

    def test_bracket_access(self):
        tokens = ExprLexer('items[0]').tokenize()
        self.assertEqual(tokens[1].type, ExprToken.LBRACKET)
        self.assertEqual(tokens[2].type, ExprToken.NUMBER)
        self.assertEqual(tokens[3].type, ExprToken.RBRACKET)

    def test_filter_with_args(self):
        tokens = ExprLexer('value | default("N/A")').tokenize()
        self.assertEqual(tokens[0].type, ExprToken.NAME)
        self.assertEqual(tokens[1].type, ExprToken.PIPE)
        self.assertEqual(tokens[2].type, ExprToken.NAME)
        self.assertEqual(tokens[3].type, ExprToken.LPAREN)
        self.assertEqual(tokens[4].type, ExprToken.STRING)


class TestExprParser(unittest.TestCase):
    def test_simple_name(self):
        expr = ExprParser('name').parse()
        from template_engine.nodes import NameExpr
        self.assertIsInstance(expr, NameExpr)
        self.assertEqual(expr.name, 'name')

    def test_dot_access(self):
        expr = ExprParser('user.name').parse()
        from template_engine.nodes import GetAttrExpr
        self.assertIsInstance(expr, GetAttrExpr)
        self.assertEqual(expr.attr, 'name')

    def test_filter(self):
        expr = ExprParser('name | upper').parse()
        from template_engine.nodes import FilterExpr
        self.assertIsInstance(expr, FilterExpr)
        self.assertEqual(expr.name, 'upper')

    def test_chained_filters(self):
        expr = ExprParser('name | strip | upper').parse()
        from template_engine.nodes import FilterExpr
        self.assertIsInstance(expr, FilterExpr)
        self.assertEqual(expr.name, 'upper')
        self.assertIsInstance(expr.node, FilterExpr)
        self.assertEqual(expr.node.name, 'strip')

    def test_filter_with_arg(self):
        expr = ExprParser('text | truncate(20)').parse()
        from template_engine.nodes import FilterExpr, LiteralExpr
        self.assertIsInstance(expr, FilterExpr)
        self.assertEqual(expr.name, 'truncate')
        self.assertEqual(len(expr.args), 1)
        self.assertIsInstance(expr.args[0], LiteralExpr)
        self.assertEqual(expr.args[0].value, 20)

    def test_comparison(self):
        expr = ExprParser('age > 18').parse()
        from template_engine.nodes import CompareExpr
        self.assertIsInstance(expr, CompareExpr)
        self.assertEqual(expr.op, '>')

    def test_bool_and(self):
        expr = ExprParser('a and b').parse()
        from template_engine.nodes import BoolOpExpr
        self.assertIsInstance(expr, BoolOpExpr)
        self.assertEqual(expr.op, 'and')

    def test_bool_or(self):
        expr = ExprParser('a or b').parse()
        from template_engine.nodes import BoolOpExpr
        self.assertIsInstance(expr, BoolOpExpr)
        self.assertEqual(expr.op, 'or')

    def test_not(self):
        expr = ExprParser('not disabled').parse()
        from template_engine.nodes import NotExpr
        self.assertIsInstance(expr, NotExpr)

    def test_in_expr(self):
        expr = ExprParser('item in items').parse()
        from template_engine.nodes import InExpr
        self.assertIsInstance(expr, InExpr)

    def test_literal_true(self):
        expr = ExprParser('True').parse()
        from template_engine.nodes import LiteralExpr
        self.assertIsInstance(expr, LiteralExpr)
        self.assertEqual(expr.value, True)

    def test_literal_false(self):
        expr = ExprParser('False').parse()
        from template_engine.nodes import LiteralExpr
        self.assertIsInstance(expr, LiteralExpr)
        self.assertEqual(expr.value, False)

    def test_literal_none(self):
        expr = ExprParser('None').parse()
        from template_engine.nodes import LiteralExpr
        self.assertIsInstance(expr, LiteralExpr)
        self.assertIsNone(expr.value)

    def test_string_literal(self):
        expr = ExprParser('"hello"').parse()
        from template_engine.nodes import LiteralExpr
        self.assertIsInstance(expr, LiteralExpr)
        self.assertEqual(expr.value, 'hello')

    def test_number_literal(self):
        expr = ExprParser('42').parse()
        from template_engine.nodes import LiteralExpr
        self.assertIsInstance(expr, LiteralExpr)
        self.assertEqual(expr.value, 42)


class TestContext(unittest.TestCase):
    def test_simple_resolve(self):
        ctx = Context({'name': 'Alice'})
        self.assertEqual(ctx.resolve(('name',)), 'Alice')

    def test_nested_resolve(self):
        ctx = Context({'user': {'name': 'Bob', 'age': 30}})
        self.assertEqual(ctx.resolve(('user', 'name')), 'Bob')
        self.assertEqual(ctx.resolve(('user', 'age')), 30)

    def test_deep_nesting(self):
        ctx = Context({'a': {'b': {'c': {'d': 'deep'}}}})
        self.assertEqual(ctx.resolve(('a', 'b', 'c', 'd')), 'deep')

    def test_missing_key(self):
        ctx = Context({'name': 'Alice'})
        self.assertIsNone(ctx.resolve(('missing',)))

    def test_missing_nested_key(self):
        ctx = Context({'user': {'name': 'Bob'}})
        self.assertIsNone(ctx.resolve(('user', 'missing',)))

    def test_scope_push_pop(self):
        ctx = Context({'x': 1})
        self.assertEqual(ctx.resolve(('x',)), 1)
        ctx.push({'x': 2})
        self.assertEqual(ctx.resolve(('x',)), 2)
        ctx.pop()
        self.assertEqual(ctx.resolve(('x',)), 1)

    def test_scope_isolation(self):
        ctx = Context({'x': 1})
        ctx.push({'y': 2})
        self.assertEqual(ctx.resolve(('x',)), 1)
        self.assertEqual(ctx.resolve(('y',)), 2)
        ctx.pop()
        self.assertIsNone(ctx.resolve(('y',)))

    def test_set_in_current_scope(self):
        ctx = Context({})
        ctx.set('key', 'value')
        self.assertEqual(ctx.resolve(('key',)), 'value')

    def test_literal_path(self):
        ctx = Context({})
        self.assertEqual(ctx.resolve(('__literal__', 42)), 42)
        self.assertEqual(ctx.resolve(('__literal__', 'hello')), 'hello')

    def test_list_index_access(self):
        ctx = Context({'items': ['a', 'b', 'c']})
        self.assertEqual(ctx.resolve(('items', 0)), 'a')
        self.assertEqual(ctx.resolve(('items', 2)), 'c')

    def test_is_truthy(self):
        ctx = Context({})
        self.assertFalse(ctx.is_truthy(None))
        self.assertFalse(ctx.is_truthy(False))
        self.assertFalse(ctx.is_truthy(0))
        self.assertFalse(ctx.is_truthy(''))
        self.assertFalse(ctx.is_truthy([]))
        self.assertTrue(ctx.is_truthy(True))
        self.assertTrue(ctx.is_truthy(1))
        self.assertTrue(ctx.is_truthy('hello'))
        self.assertTrue(ctx.is_truthy([1]))

    def test_block_overrides(self):
        ctx = Context({})
        self.assertIsNone(ctx.get_block_override('header'))
        ctx.set_block_override('header', ['some_ir'])
        self.assertEqual(ctx.get_block_override('header'), ['some_ir'])


class TestFilterRegistry(unittest.TestCase):
    def setUp(self):
        self.registry = FilterRegistry()

    def test_builtin_upper(self):
        self.assertEqual(self.registry.get('upper')('hello'), 'HELLO')

    def test_builtin_lower(self):
        self.assertEqual(self.registry.get('lower')('HELLO'), 'hello')

    def test_builtin_capitalize(self):
        self.assertEqual(self.registry.get('capitalize')('hello world'), 'Hello world')

    def test_builtin_title(self):
        self.assertEqual(self.registry.get('title')('hello world'), 'Hello World')

    def test_builtin_strip(self):
        self.assertEqual(self.registry.get('strip')('  hello  '), 'hello')

    def test_builtin_truncate(self):
        result = self.registry.get('truncate')('a' * 300, 20)
        self.assertTrue(len(result) <= 23)
        self.assertTrue(result.endswith('...'))

    def test_builtin_length(self):
        self.assertEqual(self.registry.get('length')([1, 2, 3]), 3)
        self.assertEqual(self.registry.get('length')('hello'), 5)

    def test_builtin_join(self):
        self.assertEqual(
            self.registry.get('join')(['a', 'b', 'c'], ', '),
            'a, b, c'
        )

    def test_builtin_default(self):
        self.assertEqual(self.registry.get('default')(None, 'N/A'), 'N/A')
        self.assertEqual(self.registry.get('default')('value', 'N/A'), 'value')

    def test_builtin_replace(self):
        self.assertEqual(
            self.registry.get('replace')('hello world', 'world', 'earth'),
            'hello earth'
        )

    def test_builtin_safe(self):
        result = self.registry.get('safe')('<b>bold</b>')
        self.assertIsInstance(result, SafeString)

    def test_builtin_escape(self):
        result = self.registry.get('escape')('<script>alert(1)</script>')
        self.assertNotIn('<script>', result)
        self.assertIn('&lt;script&gt;', result)

    def test_builtin_sort(self):
        self.assertEqual(self.registry.get('sort')([3, 1, 2]), [1, 2, 3])

    def test_builtin_reverse(self):
        self.assertEqual(self.registry.get('reverse')([1, 2, 3]), [3, 2, 1])

    def test_builtin_first(self):
        self.assertEqual(self.registry.get('first')([1, 2, 3]), 1)

    def test_builtin_last(self):
        self.assertEqual(self.registry.get('last')([1, 2, 3]), 3)

    def test_builtin_number(self):
        self.assertEqual(self.registry.get('number')(1234567), '1,234,567')

    def test_builtin_currency(self):
        result = self.registry.get('currency')(1234.5)
        self.assertIn('$', result)
        self.assertIn('1,234.50', result)

    def test_builtin_date(self):
        dt = datetime.datetime(2024, 1, 15)
        result = self.registry.get('date')(dt, '%Y-%m-%d')
        self.assertEqual(result, '2024-01-15')

    def test_builtin_abs(self):
        self.assertEqual(self.registry.get('abs')(-5), 5)
        self.assertEqual(self.registry.get('abs')(5), 5)

    def test_builtin_round(self):
        self.assertEqual(self.registry.get('round')(3.14159, 2), 3.14)

    def test_builtin_batch(self):
        result = self.registry.get('batch')([1, 2, 3, 4, 5], 2)
        self.assertEqual(result, [[1, 2], [3, 4], [5]])

    def test_builtin_wordcount(self):
        self.assertEqual(self.registry.get('wordcount')('hello world foo'), 3)

    def test_apply_chain(self):
        value = '  hello  '
        result = self.registry.apply_chain(value, [('strip', []), ('upper', [])])
        self.assertEqual(result, 'HELLO')

    def test_apply_chain_with_args(self):
        value = 'hello world'
        result = self.registry.apply_chain(value, [('truncate', [8, '...'])])
        self.assertEqual(result, 'hello...')

    def test_unknown_filter(self):
        with self.assertRaises(ValueError):
            self.registry.apply_chain('x', [('nonexistent', [])])

    def test_custom_filter(self):
        self.registry.register('exclaim', lambda v: str(v) + '!')
        self.assertEqual(self.registry.get('exclaim')('hello'), 'hello!')

    def test_has_filter(self):
        self.assertTrue(self.registry.has('upper'))
        self.assertFalse(self.registry.has('nonexistent'))


class TestOutputFormats(unittest.TestCase):
    def test_html_escape(self):
        fmt = HtmlOutputFormat()
        self.assertEqual(fmt.escape('<b>'), '&lt;b&gt;')
        self.assertEqual(fmt.escape('"x"'), '&quot;x&quot;')
        self.assertEqual(fmt.escape("a'b"), 'a&#x27;b')

    def test_html_format_value_safe(self):
        fmt = HtmlOutputFormat()
        safe = mark_safe('<b>bold</b>')
        self.assertEqual(fmt.format_value(safe), '<b>bold</b>')

    def test_html_format_value_unsafe(self):
        fmt = HtmlOutputFormat()
        self.assertEqual(
            fmt.format_value('<script>alert(1)</script>'),
            '&lt;script&gt;alert(1)&lt;/script&gt;'
        )

    def test_html_format_value_none(self):
        fmt = HtmlOutputFormat()
        self.assertEqual(fmt.format_value(None), '')

    def test_html_format_value_number(self):
        fmt = HtmlOutputFormat()
        self.assertEqual(fmt.format_value(42), '42')
        self.assertEqual(fmt.format_value(3.14), '3.14')

    def test_plain_text_no_escape(self):
        fmt = PlainTextOutputFormat()
        self.assertEqual(fmt.escape('<b>'), '<b>')
        self.assertEqual(fmt.format_value('hello'), 'hello')
        self.assertEqual(fmt.format_value(None), '')

    def test_plain_text_strip_html(self):
        fmt = PlainTextOutputFormat()
        result = fmt._html_to_text('<p>Hello</p>')
        self.assertNotIn('<p>', result)
        self.assertIn('Hello', result)

    def test_get_output_format(self):
        self.assertIsInstance(get_output_format('html'), HtmlOutputFormat)
        self.assertIsInstance(get_output_format('text'), PlainTextOutputFormat)
        self.assertIsInstance(get_output_format('plain'), PlainTextOutputFormat)

        with self.assertRaises(ValueError):
            get_output_format('unknown')


class TestSafeString(unittest.TestCase):
    def test_safe_string_is_str(self):
        s = SafeString('hello')
        self.assertIsInstance(s, str)
        self.assertEqual(s, 'hello')

    def test_mark_safe(self):
        s = mark_safe('<b>bold</b>')
        self.assertIsInstance(s, SafeString)
        self.assertEqual(s, '<b>bold</b>')

    def test_is_safe(self):
        safe = SafeString('hello')
        regular = 'hello'
        self.assertTrue(is_safe(safe))
        self.assertFalse(is_safe(regular))

    def test_safe_not_double_escaped(self):
        fmt = HtmlOutputFormat()
        safe = mark_safe('<em>text</em>')
        result = fmt.format_value(safe)
        self.assertEqual(result, '<em>text</em>')


class TestSandbox(unittest.TestCase):
    def setUp(self):
        self.sandbox = Sandbox(enabled=True)
        self.disabled_sandbox = Sandbox(enabled=False)

    def test_allowed_filter(self):
        self.sandbox.check_filter('upper')

    def test_blocked_filter(self):
        with self.assertRaises(SecurityError):
            self.sandbox.check_filter('__import__')

    def test_blocked_attribute(self):
        with self.assertRaises(SecurityError):
            self.sandbox.check_attribute_access(None, '__class__')

    def test_blocked_private_attribute(self):
        with self.assertRaises(SecurityError):
            self.sandbox.check_attribute_access(None, '_private')

    def test_allowed_tag(self):
        self.sandbox.check_tag('if')
        self.sandbox.check_tag('for')

    def test_blocked_tag(self):
        with self.assertRaises(SecurityError):
            self.sandbox.check_tag('exec')

    def test_disabled_sandbox_allows_all(self):
        self.disabled_sandbox.check_filter('__import__')
        self.disabled_sandbox.check_attribute_access(None, '__class__')


class TestCompiler(unittest.TestCase):
    def setUp(self):
        self.lexer = Lexer()
        self.parser = Parser()
        self.compiler = Compiler()

    def _compile(self, source):
        tokens = self.lexer.tokenize(source)
        ast = self.parser.parse(tokens)
        return self.compiler.compile(ast)

    def test_text_node(self):
        compiled = self._compile('Hello')
        self.assertEqual(len(compiled.ir), 1)
        self.assertIsInstance(compiled.ir[0], IRText)
        self.assertEqual(compiled.ir[0].text, 'Hello')

    def test_variable_node(self):
        compiled = self._compile('{{ name }}')
        self.assertEqual(len(compiled.ir), 1)
        self.assertIsInstance(compiled.ir[0], IRVariable)
        self.assertEqual(compiled.ir[0].path, ('name',))

    def test_variable_with_dot(self):
        compiled = self._compile('{{ user.name }}')
        self.assertIsInstance(compiled.ir[0], IRVariable)
        self.assertEqual(compiled.ir[0].path, ('user', 'name'))

    def test_variable_with_filter(self):
        compiled = self._compile('{{ name | upper }}')
        self.assertIsInstance(compiled.ir[0], IRVariable)
        self.assertEqual(len(compiled.ir[0].filters), 1)
        self.assertEqual(compiled.ir[0].filters[0][0], 'upper')

    def test_variable_with_chained_filters(self):
        compiled = self._compile('{{ name | strip | upper }}')
        self.assertEqual(len(compiled.ir[0].filters), 2)

    def test_if_node(self):
        compiled = self._compile('{% if x %}yes{% endif %}')
        self.assertEqual(len(compiled.ir), 1)
        self.assertIsInstance(compiled.ir[0], IRIf)

    def test_if_else_node(self):
        compiled = self._compile('{% if x %}yes{% else %}no{% endif %}')
        self.assertIsInstance(compiled.ir[0], IRIf)
        self.assertEqual(len(compiled.ir[0].else_body), 1)

    def test_if_elif_else_node(self):
        source = '{% if x %}a{% elif y %}b{% else %}c{% endif %}'
        compiled = self._compile(source)
        self.assertIsInstance(compiled.ir[0], IRIf)
        self.assertEqual(len(compiled.ir[0].branches), 2)
        self.assertEqual(len(compiled.ir[0].else_body), 1)

    def test_for_node(self):
        compiled = self._compile('{% for item in items %}{{ item }}{% endfor %}')
        self.assertEqual(len(compiled.ir), 1)
        self.assertIsInstance(compiled.ir[0], IRFor)
        self.assertEqual(compiled.ir[0].var_name, 'item')

    def test_block_node(self):
        compiled = self._compile('{% block content %}default{% endblock %}')
        self.assertEqual(len(compiled.ir), 1)
        self.assertIsInstance(compiled.ir[0], IRBlock)
        self.assertEqual(compiled.ir[0].name, 'content')
        self.assertIn('content', compiled.blocks)

    def test_extends_node(self):
        compiled = self._compile('{% extends "base.tpl" %}')
        self.assertEqual(compiled.parent_name, 'base.tpl')

    def test_include_node(self):
        compiled = self._compile('{% include "header.tpl" %}')
        self.assertEqual(len(compiled.ir), 1)
        self.assertIsInstance(compiled.ir[0], IRInclude)
        self.assertEqual(compiled.ir[0].template_name, 'header.tpl')


class TestEngineBasic(unittest.TestCase):
    def setUp(self):
        self.engine = Engine(output_format='html')

    def test_simple_variable(self):
        result = self.engine.render_string('Hello {{ name }}!', {'name': 'World'})
        self.assertEqual(result, 'Hello World!')

    def test_nested_variable(self):
        result = self.engine.render_string(
            '{{ user.name }} is {{ user.age }}',
            {'user': {'name': 'Alice', 'age': 30}}
        )
        self.assertEqual(result, 'Alice is 30')

    def test_missing_variable(self):
        result = self.engine.render_string('Hello {{ name }}!', {})
        self.assertEqual(result, 'Hello !')

    def test_literal_text(self):
        result = self.engine.render_string('Just text')
        self.assertEqual(result, 'Just text')

    def test_empty_template(self):
        result = self.engine.render_string('')
        self.assertEqual(result, '')


class TestEngineFilters(unittest.TestCase):
    def setUp(self):
        self.engine = Engine(output_format='text')

    def test_filter_upper(self):
        result = self.engine.render_string('{{ name | upper }}', {'name': 'alice'})
        self.assertEqual(result, 'ALICE')

    def test_filter_lower(self):
        result = self.engine.render_string('{{ name | lower }}', {'name': 'ALICE'})
        self.assertEqual(result, 'alice')

    def test_filter_capitalize(self):
        result = self.engine.render_string('{{ name | capitalize }}', {'name': 'hello world'})
        self.assertEqual(result, 'Hello world')

    def test_filter_strip(self):
        result = self.engine.render_string('{{ name | strip }}', {'name': '  hello  '})
        self.assertEqual(result, 'hello')

    def test_filter_length(self):
        result = self.engine.render_string('{{ items | length }}', {'items': [1, 2, 3]})
        self.assertEqual(result, '3')

    def test_filter_default(self):
        result = self.engine.render_string('{{ name | default("N/A") }}', {})
        self.assertEqual(result, 'N/A')

    def test_filter_default_with_value(self):
        result = self.engine.render_string(
            '{{ name | default("N/A") }}', {'name': 'Alice'}
        )
        self.assertEqual(result, 'Alice')

    def test_filter_join(self):
        result = self.engine.render_string(
            '{{ items | join(", ") }}', {'items': ['a', 'b', 'c']}
        )
        self.assertEqual(result, 'a, b, c')

    def test_filter_replace(self):
        result = self.engine.render_string(
            '{{ text | replace("world", "earth") }}',
            {'text': 'hello world'}
        )
        self.assertEqual(result, 'hello earth')

    def test_chained_filters(self):
        result = self.engine.render_string(
            '{{ name | strip | upper }}', {'name': '  alice  '}
        )
        self.assertEqual(result, 'ALICE')

    def test_filter_truncate(self):
        result = self.engine.render_string(
            '{{ text | truncate(8) }}', {'text': 'hello world'}
        )
        self.assertEqual(result, 'hello...')

    def test_filter_first(self):
        result = self.engine.render_string(
            '{{ items | first }}', {'items': [10, 20, 30]}
        )
        self.assertEqual(result, '10')

    def test_filter_last(self):
        result = self.engine.render_string(
            '{{ items | last }}', {'items': [10, 20, 30]}
        )
        self.assertEqual(result, '30')

    def test_filter_sort(self):
        result = self.engine.render_string(
            '{{ items | sort | join(", ") }}', {'items': [3, 1, 2]}
        )
        self.assertEqual(result, '1, 2, 3')

    def test_filter_number(self):
        result = self.engine.render_string(
            '{{ amount | number }}', {'amount': 1234567}
        )
        self.assertEqual(result, '1,234,567')

    def test_filter_currency(self):
        result = self.engine.render_string(
            '{{ price | currency }}', {'price': 99.95}
        )
        self.assertEqual(result, '$99.95')


class TestEngineConditionals(unittest.TestCase):
    def setUp(self):
        self.engine = Engine(output_format='text')

    def test_if_true(self):
        result = self.engine.render_string(
            '{% if show %}visible{% endif %}', {'show': True}
        )
        self.assertEqual(result, 'visible')

    def test_if_false(self):
        result = self.engine.render_string(
            '{% if show %}visible{% endif %}', {'show': False}
        )
        self.assertEqual(result, '')

    def test_if_else_true(self):
        result = self.engine.render_string(
            '{% if show %}yes{% else %}no{% endif %}', {'show': True}
        )
        self.assertEqual(result, 'yes')

    def test_if_else_false(self):
        result = self.engine.render_string(
            '{% if show %}yes{% else %}no{% endif %}', {'show': False}
        )
        self.assertEqual(result, 'no')

    def test_if_elif(self):
        result = self.engine.render_string(
            '{% if x == 1 %}one{% elif x == 2 %}two{% else %}other{% endif %}',
            {'x': 2}
        )
        self.assertEqual(result, 'two')

    def test_if_comparison_eq(self):
        result = self.engine.render_string(
            '{% if x == 5 %}equal{% endif %}', {'x': 5}
        )
        self.assertEqual(result, 'equal')

    def test_if_comparison_ne(self):
        result = self.engine.render_string(
            '{% if x != 5 %}not equal{% endif %}', {'x': 3}
        )
        self.assertEqual(result, 'not equal')

    def test_if_comparison_gt(self):
        result = self.engine.render_string(
            '{% if x > 5 %}greater{% endif %}', {'x': 10}
        )
        self.assertEqual(result, 'greater')

    def test_if_comparison_lt(self):
        result = self.engine.render_string(
            '{% if x < 5 %}less{% endif %}', {'x': 3}
        )
        self.assertEqual(result, 'less')

    def test_if_and(self):
        result = self.engine.render_string(
            '{% if x and y %}both{% endif %}', {'x': True, 'y': True}
        )
        self.assertEqual(result, 'both')

    def test_if_or(self):
        result = self.engine.render_string(
            '{% if x or y %}either{% endif %}', {'x': False, 'y': True}
        )
        self.assertEqual(result, 'either')

    def test_if_not(self):
        result = self.engine.render_string(
            '{% if not disabled %}enabled{% endif %}', {'disabled': False}
        )
        self.assertEqual(result, 'enabled')

    def test_if_in(self):
        result = self.engine.render_string(
            '{% if item in items %}found{% endif %}',
            {'item': 'a', 'items': ['a', 'b', 'c']}
        )
        self.assertEqual(result, 'found')

    def test_nested_if(self):
        result = self.engine.render_string(
            '{% if a %}{% if b %}both{% endif %}{% endif %}',
            {'a': True, 'b': True}
        )
        self.assertEqual(result, 'both')

    def test_if_with_string_variable(self):
        result = self.engine.render_string(
            '{% if name %}has name{% endif %}', {'name': 'Alice'}
        )
        self.assertEqual(result, 'has name')

    def test_if_with_empty_string(self):
        result = self.engine.render_string(
            '{% if name %}has name{% endif %}', {'name': ''}
        )
        self.assertEqual(result, '')


class TestEngineLoops(unittest.TestCase):
    def setUp(self):
        self.engine = Engine(output_format='text')

    def test_basic_for(self):
        result = self.engine.render_string(
            '{% for item in items %}{{ item }}{% endfor %}',
            {'items': ['a', 'b', 'c']}
        )
        self.assertEqual(result, 'abc')

    def test_for_with_text(self):
        result = self.engine.render_string(
            '{% for item in items %}{{ item }},{% endfor %}',
            {'items': ['a', 'b', 'c']}
        )
        self.assertEqual(result, 'a,b,c,')

    def test_for_with_nested_access(self):
        result = self.engine.render_string(
            '{% for user in users %}{{ user.name }} {% endfor %}',
            {'users': [{'name': 'Alice'}, {'name': 'Bob'}]}
        )
        self.assertEqual(result, 'Alice Bob ')

    def test_for_empty_list(self):
        result = self.engine.render_string(
            '{% for item in items %}{{ item }}{% endfor %}',
            {'items': []}
        )
        self.assertEqual(result, '')

    def test_for_none_iterable(self):
        result = self.engine.render_string(
            '{% for item in items %}{{ item }}{% endfor %}',
            {'items': None}
        )
        self.assertEqual(result, '')

    def test_for_loop_variable_index(self):
        result = self.engine.render_string(
            '{% for item in items %}{{ loop.index }}{% endfor %}',
            {'items': ['a', 'b', 'c']}
        )
        self.assertEqual(result, '123')

    def test_for_loop_variable_first(self):
        result = self.engine.render_string(
            '{% for item in items %}{% if loop.first %}*{% endif %}{{ item }}{% endfor %}',
            {'items': ['a', 'b', 'c']}
        )
        self.assertEqual(result, '*abc')

    def test_for_loop_variable_last(self):
        result = self.engine.render_string(
            '{% for item in items %}{{ item }}{% if loop.last %}!{% endif %}{% endfor %}',
            {'items': ['a', 'b', 'c']}
        )
        self.assertEqual(result, 'abc!')

    def test_for_loop_variable_length(self):
        result = self.engine.render_string(
            '{% for item in items %}{{ loop.length }}{% endfor %}',
            {'items': ['a', 'b', 'c']}
        )
        self.assertEqual(result, '333')

    def test_nested_for(self):
        result = self.engine.render_string(
            '{% for row in matrix %}{% for col in row %}{{ col }}{% endfor %};{% endfor %}',
            {'matrix': [[1, 2], [3, 4]]}
        )
        self.assertEqual(result, '12;34;')

    def test_for_with_filter(self):
        result = self.engine.render_string(
            '{% for item in items %}{{ item | upper }}{% endfor %}',
            {'items': ['a', 'b', 'c']}
        )
        self.assertEqual(result, 'ABC')


class TestEngineHtmlEscaping(unittest.TestCase):
    def setUp(self):
        self.engine = Engine(output_format='html')

    def test_auto_escape(self):
        result = self.engine.render_string(
            '{{ content }}', {'content': '<script>alert(1)</script>'}
        )
        self.assertNotIn('<script>', result)
        self.assertIn('&lt;script&gt;', result)

    def test_safe_filter_bypass(self):
        result = self.engine.render_string(
            '{{ content | safe }}', {'content': '<b>bold</b>'}
        )
        self.assertEqual(result, '<b>bold</b>')

    def test_escape_filter(self):
        result = self.engine.render_string(
            '{{ content | escape }}', {'content': '<b>bold</b>'}
        )
        self.assertIn('&lt;b&gt;', result)

    def test_html_ampersand(self):
        result = self.engine.render_string(
            '{{ content }}', {'content': 'a & b'}
        )
        self.assertEqual(result, 'a &amp; b')

    def test_html_quotes(self):
        result = self.engine.render_string(
            '{{ content }}', {'content': '"hello"'}
        )
        self.assertEqual(result, '&quot;hello&quot;')


class TestEnginePlainText(unittest.TestCase):
    def setUp(self):
        self.engine = Engine(output_format='text')

    def test_no_escape(self):
        result = self.engine.render_string(
            '{{ content }}', {'content': '<b>bold</b>'}
        )
        self.assertEqual(result, '<b>bold</b>')

    def test_ampersand_not_escaped(self):
        result = self.engine.render_string(
            '{{ content }}', {'content': 'a & b'}
        )
        self.assertEqual(result, 'a & b')


class TestEngineInheritance(unittest.TestCase):
    def test_simple_inheritance(self):
        templates = {
            'base.tpl': '<html>{% block content %}default{% endblock %}</html>',
            'child.tpl': '{% extends "base.tpl" %}{% block content %}child content{% endblock %}',
        }
        engine = Engine(loader=DictLoader(templates), output_format='text')
        result = engine.render('child.tpl', {})
        self.assertEqual(result, '<html>child content</html>')

    def test_inheritance_default_block(self):
        templates = {
            'base.tpl': '<html>{% block content %}default{% endblock %}</html>',
            'child.tpl': '{% extends "base.tpl" %}',
        }
        engine = Engine(loader=DictLoader(templates), output_format='text')
        result = engine.render('child.tpl', {})
        self.assertEqual(result, '<html>default</html>')

    def test_multi_block_inheritance(self):
        templates = {
            'base.tpl': '{% block header %}H{% endblock %}|{% block body %}B{% endblock %}',
            'child.tpl': '{% extends "base.tpl" %}{% block header %}CustomH{% endblock %}{% block body %}CustomB{% endblock %}',
        }
        engine = Engine(loader=DictLoader(templates), output_format='text')
        result = engine.render('child.tpl', {})
        self.assertEqual(result, 'CustomH|CustomB')

    def test_inheritance_partial_override(self):
        templates = {
            'base.tpl': '{% block header %}DEFAULT_HEADER{% endblock %}|{% block body %}DEFAULT_BODY{% endblock %}',
            'child.tpl': '{% extends "base.tpl" %}{% block body %}CUSTOM_BODY{% endblock %}',
        }
        engine = Engine(loader=DictLoader(templates), output_format='text')
        result = engine.render('child.tpl', {})
        self.assertEqual(result, 'DEFAULT_HEADER|CUSTOM_BODY')


class TestEngineInclusion(unittest.TestCase):
    def test_simple_include(self):
        templates = {
            'main.tpl': 'Hello {% include "greeting.tpl" %}!',
            'greeting.tpl': 'World',
        }
        engine = Engine(loader=DictLoader(templates), output_format='text')
        result = engine.render('main.tpl', {})
        self.assertEqual(result, 'Hello World!')

    def test_include_with_data(self):
        templates = {
            'main.tpl': '{% include "user.tpl" %}',
            'user.tpl': '{{ name }}',
        }
        engine = Engine(loader=DictLoader(templates), output_format='text')
        result = engine.render('main.tpl', {'name': 'Alice'})
        self.assertEqual(result, 'Alice')


class TestEngineComplex(unittest.TestCase):
    def setUp(self):
        self.engine = Engine(output_format='text')

    def test_for_inside_if(self):
        result = self.engine.render_string(
            '{% if show %}{% for item in items %}{{ item }}{% endfor %}{% endif %}',
            {'show': True, 'items': ['a', 'b']}
        )
        self.assertEqual(result, 'ab')

    def test_if_inside_for(self):
        result = self.engine.render_string(
            '{% for item in items %}{% if item.active %}{{ item.name }}{% endif %}{% endfor %}',
            {'items': [{'name': 'A', 'active': True}, {'name': 'B', 'active': False}]}
        )
        self.assertEqual(result, 'A')

    def test_complex_report(self):
        result = self.engine.render_string(
            'Report: {{ title }}\n'
            '{% for item in items %}'
            '- {{ item.name }}: {{ item.value | currency }}\n'
            '{% endfor %}'
            'Total: {{ total | currency }}',
            {
                'title': 'Sales Report',
                'items': [
                    {'name': 'Product A', 'value': 99.95},
                    {'name': 'Product B', 'value': 149.50},
                ],
                'total': 249.45,
            }
        )
        self.assertIn('Sales Report', result)
        self.assertIn('Product A', result)
        self.assertIn('$99.95', result)
        self.assertIn('$249.45', result)

    def test_report_with_conditionals(self):
        result = self.engine.render_string(
            '{% for item in items %}'
            '{% if item.price > 100 %}'
            'EXPENSIVE: {{ item.name }}\n'
            '{% else %}'
            'AFFORDABLE: {{ item.name }}\n'
            '{% endif %}'
            '{% endfor %}',
            {
                'items': [
                    {'name': 'Pen', 'price': 5},
                    {'name': 'Laptop', 'price': 999},
                ]
            }
        )
        self.assertIn('AFFORDABLE: Pen', result)
        self.assertIn('EXPENSIVE: Laptop', result)


class TestEngineCustomFilters(unittest.TestCase):
    def test_custom_filter(self):
        engine = Engine(output_format='text', custom_filters={
            'rot13': lambda v: ''.join(
                chr((ord(c) - ord('a') + 13) % 26 + ord('a'))
                if c.isalpha() and c.islower() else c
                for c in str(v)
            )
        })
        result = engine.render_string('{{ name | rot13 }}', {'name': 'hello'})
        self.assertEqual(result, 'uryyb')

    def test_add_filter_after_creation(self):
        engine = Engine(output_format='text')
        engine.add_filter('double', lambda v: str(v) * 2)
        result = engine.render_string('{{ name | double }}', {'name': 'ha'})
        self.assertEqual(result, 'haha')


class TestEngineMultiFormat(unittest.TestCase):
    def test_same_template_different_formats(self):
        source = '{{ content }}'
        data = {'content': '<b>bold</b>'}

        engine_html = Engine(output_format='html')
        html_result = engine_html.render_string(source, data)
        self.assertIn('&lt;b&gt;', html_result)

        engine_text = Engine(output_format='text')
        text_result = engine_text.render_string(source, data)
        self.assertEqual(text_result, '<b>bold</b>')

    def test_render_with_format(self):
        engine = Engine(output_format='html')
        data = {'content': '<script>x</script>'}

        html = engine.render_string_with_format('{{ content }}', data, 'html')
        self.assertIn('&lt;script&gt;', html)

        text = engine.render_string_with_format('{{ content }}', data, 'text')
        self.assertEqual(text, '<script>x</script>')


class TestEngineReusability(unittest.TestCase):
    def test_compiled_template_reuse(self):
        engine = Engine(output_format='text')
        compiled = engine.compile('Hello {{ name }}!')

        from template_engine.context import Context
        from template_engine.renderer import Renderer

        renderer = Renderer(
            engine.environment,
            engine._output_format,
            engine.environment.filter_registry,
        )

        ctx1 = Context({'name': 'Alice'})
        result1 = renderer.render(compiled, ctx1)

        ctx2 = Context({'name': 'Bob'})
        result2 = renderer.render(compiled, ctx2)

        self.assertEqual(result1, 'Hello Alice!')
        self.assertEqual(result2, 'Hello Bob!')


class TestEngineSecurity(unittest.TestCase):
    def test_sandbox_blocks_dangerous_filter(self):
        engine = Engine(output_format='text', sandbox_enabled=True)
        with self.assertRaises(SecurityError):
            engine.add_filter('__dangerous__', lambda v: v)

    def test_sandbox_disabled_allows_custom(self):
        engine = Engine(output_format='text', sandbox_enabled=False)
        engine.add_filter('__custom__', lambda v: str(v).upper())
        result = engine.render_string('{{ name | __custom__ }}', {'name': 'test'})
        self.assertEqual(result, 'TEST')

    def test_html_auto_escape_prevents_xss(self):
        engine = Engine(output_format='html')
        malicious = '<img src=x onerror=alert(1)>'
        result = engine.render_string('{{ content }}', {'content': malicious})
        self.assertNotIn('<img', result)
        self.assertIn('&lt;img', result)


class TestEngineDictLoader(unittest.TestCase):
    def test_dict_loader(self):
        templates = {
            'hello.tpl': 'Hello {{ name }}!',
        }
        engine = Engine(loader=DictLoader(templates), output_format='text')
        result = engine.render('hello.tpl', {'name': 'World'})
        self.assertEqual(result, 'Hello World!')

    def test_template_not_found(self):
        engine = Engine(loader=DictLoader({}), output_format='text')
        with self.assertRaises(TemplateNotFoundError):
            engine.render('missing.tpl', {})

    def test_add_template(self):
        engine = Engine(output_format='text')
        engine.add_template('greeting.tpl', 'Hi {{ name }}!')
        result = engine.render('greeting.tpl', {'name': 'Alice'})
        self.assertEqual(result, 'Hi Alice!')


class TestEngineReportGeneration(unittest.TestCase):
    def test_full_report(self):
        templates = {
            'report.tpl': (
                '=== {{ title }} ===\n'
                'Date: {{ date }}\n'
                '\n'
                '{% if summary %}Summary: {{ summary }}\n{% endif %}'
                '\n'
                'Items:\n'
                '{% for item in items %}'
                '  {{ loop.index }}. {{ item.name }} - {{ item.price | currency }}\n'
                '{% endfor %}'
                '\n'
                'Total: {{ total | currency }}\n'
                '{% if total > 1000 %}'
                'Status: HIGH VALUE\n'
                '{% else %}'
                'Status: NORMAL\n'
                '{% endif %}'
            ),
        }
        engine = Engine(loader=DictLoader(templates), output_format='text')
        result = engine.render('report.tpl', {
            'title': 'Q4 Sales Report',
            'date': '2024-12-31',
            'summary': 'End of year results',
            'items': [
                {'name': 'Widget A', 'price': 299.99},
                {'name': 'Widget B', 'price': 499.99},
                {'name': 'Widget C', 'price': 399.99},
            ],
            'total': 1199.97,
        })
        self.assertIn('Q4 Sales Report', result)
        self.assertIn('Widget A', result)
        self.assertIn('$299.99', result)
        self.assertIn('$1,199.97', result)
        self.assertIn('HIGH VALUE', result)
        self.assertIn('End of year results', result)


if __name__ == '__main__':
    unittest.main()

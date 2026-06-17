import unittest
import os
import tempfile
import shutil
from template_engine import (
    Engine, DictLoader, FileSystemLoader, SecurityError,
    Context,
)


class TestFilterDynamicParameters(unittest.TestCase):
    def setUp(self):
        self.engine = Engine(output_format='text')

    def test_truncate_length_from_data(self):
        result = self.engine.render_string(
            '{{ text | truncate(max_len) }}',
            {'text': 'hello world this is a long text', 'max_len': 8}
        )
        self.assertEqual(result, 'hello...')

    def test_default_value_from_data(self):
        result = self.engine.render_string(
            '{{ value | default(fallback) }}',
            {'value': None, 'fallback': 'N/A'}
        )
        self.assertEqual(result, 'N/A')

    def test_currency_symbol_from_data(self):
        result = self.engine.render_string(
            '{{ price | currency(symbol) }}',
            {'price': 99.5, 'symbol': '€'}
        )
        self.assertEqual(result, '€99.50')

    def test_currency_symbol_and_separator_from_data(self):
        result = self.engine.render_string(
            '{{ price | currency(symbol, 2, sep) }}',
            {'price': 1234.5, 'symbol': '¥', 'sep': ' '}
        )
        self.assertIn('¥', result)
        self.assertIn('1 234.50', result)

    def test_number_separator_from_data(self):
        result = self.engine.render_string(
            '{{ amount | number(sep) }}',
            {'amount': 1234567, 'sep': '.'}
        )
        self.assertEqual(result, '1.234.567')

    def test_replace_args_from_data(self):
        result = self.engine.render_string(
            '{{ text | replace(old, new) }}',
            {'text': 'hello world', 'old': 'world', 'new': 'earth'}
        )
        self.assertEqual(result, 'hello earth')

    def test_join_separator_from_data(self):
        result = self.engine.render_string(
            '{{ items | join(sep) }}',
            {'items': ['a', 'b', 'c'], 'sep': ' - '}
        )
        self.assertEqual(result, 'a - b - c')

    def test_nested_data_field_as_parameter(self):
        result = self.engine.render_string(
            '{{ value | default(config.fallback) }}',
            {'value': None, 'config': {'fallback': 'UNKNOWN'}}
        )
        self.assertEqual(result, 'UNKNOWN')

    def test_invalid_param_does_not_crash(self):
        result = self.engine.render_string(
            '{{ text | truncate(not_a_number) }}',
            {'text': 'hello', 'not_a_number': 'oops'}
        )
        self.assertEqual(result, 'hello')

    def test_missing_param_uses_filter_default(self):
        result = self.engine.render_string(
            '{{ value | default(missing_field) }}',
            {'value': None}
        )
        self.assertEqual(result, '')

    def test_chain_with_dynamic_params(self):
        result = self.engine.render_string(
            '{{ text | strip | truncate(limit) | upper }}',
            {'text': '  hello world this is long  ', 'limit': 8}
        )
        self.assertEqual(result, 'HELLO...')


class TestForLoopFilters(unittest.TestCase):
    def setUp(self):
        self.engine = Engine(output_format='text')

    def test_for_sort_ascending(self):
        result = self.engine.render_string(
            '{% for n in numbers | sort %}{{ n }},{% endfor %}',
            {'numbers': [3, 1, 4, 1, 5, 9]}
        )
        self.assertEqual(result, '1,1,3,4,5,9,')

    def test_for_sort_descending(self):
        result = self.engine.render_string(
            '{% for n in numbers | sort(True) %}{{ n }},{% endfor %}',
            {'numbers': [3, 1, 4, 1, 5, 9]}
        )
        self.assertEqual(result, '9,5,4,3,1,1,')

    def test_for_reverse(self):
        result = self.engine.render_string(
            '{% for n in numbers | reverse %}{{ n }},{% endfor %}',
            {'numbers': [1, 2, 3, 4]}
        )
        self.assertEqual(result, '4,3,2,1,')

    def test_for_batch(self):
        result = self.engine.render_string(
            '{% for row in items | batch(2) %}[{{ row | join(",") }}]{% endfor %}',
            {'items': ['a', 'b', 'c', 'd', 'e']}
        )
        self.assertEqual(result, '[a,b][c,d][e]')

    def test_for_sort_then_reverse(self):
        result = self.engine.render_string(
            '{% for n in numbers | sort | reverse %}{{ n }},{% endfor %}',
            {'numbers': [3, 1, 4, 1, 5, 9]}
        )
        self.assertEqual(result, '9,5,4,3,1,1,')

    def test_for_sort_reverse_then_truncate_body(self):
        result = self.engine.render_string(
            '{% for n in names | sort(True) %}{{ loop.index }}.{{ n }}\n{% endfor %}',
            {
                'names': ['zulu', 'alpha', 'mike']
            }
        )
        self.assertIn('1.zulu', result)
        self.assertIn('2.mike', result)
        self.assertIn('3.alpha', result)

    def test_for_filter_order_preserved(self):
        result = self.engine.render_string(
            '{% for n in numbers | reverse %}{{ loop.index }}:{{ n }};{% endfor %}',
            {'numbers': [10, 20, 30]}
        )
        self.assertEqual(result, '1:30;2:20;3:10;')

    def test_for_empty_after_filter(self):
        result = self.engine.render_string(
            '{% for n in numbers | reverse %}{{ n }}{% endfor %}',
            {'numbers': []}
        )
        self.assertEqual(result, '')

    def test_for_loop_index_reflects_filtered_order(self):
        result = self.engine.render_string(
            '{% for n in numbers | sort %}{% if loop.first %}FIRST={{ n }}{% endif %}{% if loop.last %}LAST={{ n }}{% endif %}{% endfor %}',
            {'numbers': [5, 3, 8, 1]}
        )
        self.assertIn('FIRST=1', result)
        self.assertIn('LAST=8', result)

    def test_for_dynamic_batch_size(self):
        result = self.engine.render_string(
            '{% for row in items | batch(size) %}{{ row | length }},{% endfor %}',
            {'items': list(range(10)), 'size': 3}
        )
        self.assertEqual(result, '3,3,3,1,')


class TestSandboxAttributeBlocking(unittest.TestCase):
    def setUp(self):
        self.engine = Engine(output_format='text', sandbox_enabled=True)

    def test_dot_dunder_class_blocked(self):
        with self.assertRaises(SecurityError):
            self.engine.render_string(
                '{{ obj.__class__ }}',
                {'obj': 'hello'}
            )

    def test_dot_private_attr_blocked(self):
        with self.assertRaises(SecurityError):
            self.engine.render_string(
                '{{ obj._secret }}',
                {'obj': {}}
            )

    def test_dot_private_attr_ast_error(self):
        with self.assertRaises(SecurityError):
            self.engine.render_string(
                '{{ obj._private }}',
                {'obj': {}}
            )

    def test_dot_dunder_ast_error(self):
        with self.assertRaises(SecurityError):
            self.engine.render_string(
                '{{ x.__class__ }}',
                {'x': {}}
            )

    def test_index_dunder_class_blocked(self):
        with self.assertRaises(SecurityError):
            self.engine.render_string(
                '{{ obj["__class__"] }}',
                {'obj': 'hello'}
            )

    def test_index_private_key_blocked(self):
        with self.assertRaises(SecurityError):
            self.engine.render_string(
                '{{ data["_secret"] }}',
                {'data': {'_secret': 'value'}}
            )

    def test_dict_private_key_rendered_none(self):
        engine = Engine(output_format='text', sandbox_enabled=False)
        result = engine.render_string(
            '{{ data._secret | default("BLOCKED") }}',
            {'data': {'_secret': 'hidden'}}
        )
        self.assertEqual(result, 'BLOCKED')

    def test_obj_private_attr_rendered_none(self):
        class Foo:
            _internal = 'nope'
        engine = Engine(output_format='text', sandbox_enabled=False)
        result = engine.render_string(
            '{{ obj._internal | default("BLOCKED") }}',
            {'obj': Foo()}
        )
        self.assertEqual(result, 'BLOCKED')

    def test_index_to_string_dunder_blocked(self):
        with self.assertRaises(SecurityError):
            self.engine.render_string(
                '{{ data["__builtins__"] }}',
                {'data': {}}
            )

    def test_normal_public_attr_works(self):
        result = self.engine.render_string(
            '{{ user.name }}',
            {'user': {'name': 'Alice'}}
        )
        self.assertEqual(result, 'Alice')

    def test_normal_dict_key_works(self):
        result = self.engine.render_string(
            '{{ data["name"] }}',
            {'data': {'name': 'Alice'}}
        )
        self.assertEqual(result, 'Alice')

    def test_sandbox_disabled_allows_access(self):
        engine = Engine(output_format='text', sandbox_enabled=False)
        result = engine.render_string(
            '{{ data["name"] }}',
            {'data': {'name': 'ok'}}
        )
        self.assertEqual(result, 'ok')

    def test_eval_name_blocked_in_ast(self):
        with self.assertRaises(SecurityError):
            self.engine.render_string('{{ eval }}', {})

    def test_import_name_blocked_in_ast(self):
        with self.assertRaises(SecurityError):
            self.engine.render_string('{{ __import__ }}', {})


class TestFileSystemLoaderSecurity(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        with open(os.path.join(self.tmpdir, 'hello.tpl'), 'w', encoding='utf-8') as f:
            f.write('Hello {{ name }}!')

        subdir = os.path.join(self.tmpdir, 'sub')
        os.makedirs(subdir, exist_ok=True)
        with open(os.path.join(subdir, 'nested.tpl'), 'w', encoding='utf-8') as f:
            f.write('Nested: {{ value }}')

        outside = os.path.join(self.tmpdir, '..')
        outside_tpl_dir = os.path.abspath(os.path.join(self.tmpdir, '..'))
        with open(os.path.join(outside_tpl_dir, 'secret.tpl'), 'w', encoding='utf-8') as f:
            f.write('SECRET FILE')
        self._outside_secret = os.path.join(outside_tpl_dir, 'secret.tpl')

        self.loader = FileSystemLoader(self.tmpdir)
        self.engine = Engine(loader=self.loader, output_format='text')

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)
        if os.path.exists(self._outside_secret):
            try:
                os.remove(self._outside_secret)
            except OSError:
                pass

    def test_normal_template_works(self):
        result = self.engine.render('hello.tpl', {'name': 'World'})
        self.assertEqual(result, 'Hello World!')

    def test_subdirectory_template_works(self):
        result = self.engine.render('sub/nested.tpl', {'value': 'data'})
        self.assertEqual(result, 'Nested: data')

    def test_parent_dir_traversal_blocked(self):
        with self.assertRaises(SecurityError):
            self.engine.render('../secret.tpl', {})

    def test_parent_dir_in_middle_blocked(self):
        with self.assertRaises(SecurityError):
            self.engine.render('sub/../../secret.tpl', {})

    def test_absolute_path_blocked(self):
        with self.assertRaises(SecurityError):
            self.engine.render(self._outside_secret, {})

    def test_windows_absolute_path_blocked(self):
        with self.assertRaises(SecurityError):
            self.engine.render('C:\\Windows\\system32\\drivers\\etc\\hosts', {})

    def test_include_parent_blocked(self):
        with self.assertRaises(SecurityError):
            self.engine.render_string(
                '{% include "../secret.tpl" %}',
                {}
            )

    def test_extends_parent_blocked(self):
        with self.assertRaises(SecurityError):
            self.engine.render_string(
                '{% extends "../secret.tpl" %}',
                {}
            )

    def test_include_absolute_blocked(self):
        with self.assertRaises(SecurityError):
            self.engine.render_string(
                '{% include "' + self._outside_secret + '" %}',
                {}
            )

    def test_include_sub_works(self):
        result = self.engine.render('sub/nested.tpl', {'value': 'OK'})
        self.assertEqual(result, 'Nested: OK')

    def test_normpath_escape_blocked(self):
        tricky = os.path.join('sub', '..', '..', 'secret.tpl')
        with self.assertRaises(SecurityError):
            self.engine.render(tricky, {})


if __name__ == '__main__':
    unittest.main()

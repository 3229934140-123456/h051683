import re
import html as html_module
from .safestring import SafeString, mark_safe, is_safe


class FilterRegistry:
    def __init__(self):
        self._filters = {}
        self._register_builtins()

    def register(self, name, func):
        self._filters[name] = func

    def get(self, name):
        return self._filters.get(name)

    def has(self, name):
        return name in self._filters

    def apply_chain(self, value, filter_chain, context=None):
        for filter_name, args in filter_chain:
            func = self._filters.get(filter_name)
            if func is None:
                raise ValueError(f"Unknown filter: {filter_name!r}")
            if args:
                resolved_args = []
                for arg in args:
                    resolved_args.append(self._resolve_arg(arg, context))
                try:
                    value = func(value, *resolved_args)
                except (TypeError, ValueError, IndexError, KeyError, AttributeError):
                    return value
            else:
                value = func(value)
        return value

    def _resolve_arg(self, arg, context):
        if isinstance(arg, tuple) and len(arg) == 2 and arg[0] == '__expr__':
            if context is not None:
                return context.resolve(('__expr__', arg[1]))
            return None
        if isinstance(arg, tuple) and len(arg) >= 1 and arg[0] == '__ref__':
            if context is not None and len(arg) > 1:
                return context.resolve(arg[1])
            return None
        return arg

    def _register_builtins(self):
        self.register('upper', _filter_upper)
        self.register('lower', _filter_lower)
        self.register('capitalize', _filter_capitalize)
        self.register('title', _filter_title)
        self.register('strip', _filter_strip)
        self.register('lstrip', _filter_lstrip)
        self.register('rstrip', _filter_rstrip)
        self.register('truncate', _filter_truncate)
        self.register('length', _filter_length)
        self.register('first', _filter_first)
        self.register('last', _filter_last)
        self.register('join', _filter_join)
        self.register('sort', _filter_sort)
        self.register('reverse', _filter_reverse)
        self.register('default', _filter_default)
        self.register('default_if_none', _filter_default_if_none)
        self.register('replace', _filter_replace)
        self.register('escape', _filter_escape)
        self.register('e', _filter_escape)
        self.register('safe', _filter_safe)
        self.register('string', _filter_string)
        self.register('int', _filter_int)
        self.register('float', _filter_float)
        self.register('abs', _filter_abs)
        self.register('round', _filter_round)
        self.register('batch', _filter_batch)
        self.register('date', _filter_date)
        self.register('number', _filter_number)
        self.register('currency', _filter_currency)
        self.register('urlencode', _filter_urlencode)
        self.register('wordcount', _filter_wordcount)
        self.register('trim', _filter_strip)
        self.register('center', _filter_center)
        self.register('count', _filter_length)


def _filter_upper(value):
    return str(value).upper()


def _filter_lower(value):
    return str(value).lower()


def _filter_capitalize(value):
    return str(value).capitalize()


def _filter_title(value):
    return str(value).title()


def _filter_strip(value):
    return str(value).strip()


def _filter_lstrip(value):
    return str(value).lstrip()


def _filter_rstrip(value):
    return str(value).rstrip()


def _filter_truncate(value, length=255, end='...'):
    s = str(value)
    if len(s) > length:
        return s[:length - len(end)] + end
    return s


def _filter_length(value):
    try:
        return len(value)
    except TypeError:
        return 0


def _filter_first(value):
    try:
        return value[0] if value else None
    except (TypeError, IndexError):
        return None


def _filter_last(value):
    try:
        return value[-1] if value else None
    except (TypeError, IndexError):
        return None


def _filter_join(value, separator=', '):
    if isinstance(value, (list, tuple)):
        return separator.join(str(v) for v in value)
    return str(value)


def _filter_sort(value, reverse=False):
    try:
        return sorted(value, reverse=reverse)
    except (TypeError, ValueError):
        return value


def _filter_reverse(value):
    try:
        if isinstance(value, str):
            return value[::-1]
        return list(reversed(value))
    except TypeError:
        return value


def _filter_default(value, default_value=''):
    if value is None or value == '' or value is False:
        return default_value
    return value


def _filter_default_if_none(value, default_value=''):
    if value is None:
        return default_value
    return value


def _filter_replace(value, old, new):
    return str(value).replace(old, new)


def _filter_escape(value):
    if is_safe(value):
        return value
    return SafeString(html_module.escape(str(value)))


def _filter_safe(value):
    return mark_safe(str(value))


def _filter_string(value):
    return str(value)


def _filter_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _filter_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _filter_abs(value):
    try:
        return abs(value)
    except TypeError:
        return value


def _filter_round(value, precision=0):
    try:
        return round(value, precision)
    except TypeError:
        return value


def _filter_batch(value, size, fill=None):
    result = []
    if not isinstance(value, (list, tuple)):
        return result
    for i in range(0, len(value), size):
        chunk = value[i:i + size]
        if fill is not None and len(chunk) < size:
            chunk = list(chunk) + [fill] * (size - len(chunk))
        result.append(chunk)
    return result


def _filter_date(value, format_str='%Y-%m-%d'):
    import datetime
    if isinstance(value, datetime.datetime):
        return value.strftime(format_str)
    if isinstance(value, datetime.date):
        return value.strftime(format_str)
    return str(value)


def _filter_number(value, separator=','):
    try:
        num = int(value)
        if separator:
            return f"{num:,}".replace(',', separator)
        return str(num)
    except (TypeError, ValueError):
        return str(value)


def _filter_currency(value, symbol='$', decimals=2, separator=','):
    try:
        num = float(value)
        formatted = f"{num:,.{decimals}f}"
        if separator != ',':
            formatted = formatted.replace(',', separator)
        return f"{symbol}{formatted}"
    except (TypeError, ValueError):
        return str(value)


def _filter_urlencode(value):
    from urllib.parse import quote_plus
    return quote_plus(str(value))


def _filter_wordcount(value):
    return len(str(value).split())


def _filter_center(value, width=80):
    return str(value).center(width)

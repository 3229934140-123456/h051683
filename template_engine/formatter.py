import html as html_module
from .safestring import SafeString, is_safe


class OutputFormat:
    def escape(self, value):
        raise NotImplementedError

    def format_value(self, value):
        if value is None:
            return ''
        if is_safe(value):
            return str(value)
        return self.escape(str(value))

    def format_raw(self, text):
        return text


class HtmlOutputFormat(OutputFormat):
    def escape(self, value):
        return html_module.escape(value, quote=True)

    def format_value(self, value):
        if value is None:
            return ''
        if is_safe(value):
            return str(value)
        if isinstance(value, (int, float, bool)):
            return str(value)
        return self.escape(str(value))


class PlainTextOutputFormat(OutputFormat):
    def escape(self, value):
        return value

    def format_value(self, value):
        if value is None:
            return ''
        if is_safe(value):
            return self._html_to_text(str(value))
        return str(value)

    def format_raw(self, text):
        return text

    def _html_to_text(self, html):
        cleaned = html
        cleaned = cleaned.replace('<br>', '\n')
        cleaned = cleaned.replace('<br/>', '\n')
        cleaned = cleaned.replace('<br />', '\n')
        import re
        cleaned = re.sub(r'<p[^>]*>', '\n', cleaned)
        cleaned = re.sub(r'</p>', '\n', cleaned)
        cleaned = re.sub(r'<[^>]+>', '', cleaned)
        cleaned = cleaned.replace('&amp;', '&')
        cleaned = cleaned.replace('&lt;', '<')
        cleaned = cleaned.replace('&gt;', '>')
        cleaned = cleaned.replace('&quot;', '"')
        cleaned = cleaned.replace('&#39;', "'")
        cleaned = cleaned.replace('&nbsp;', ' ')
        return cleaned


class JsonOutputFormat(OutputFormat):
    def escape(self, value):
        import json
        return json.dumps(value)

    def format_value(self, value):
        import json
        if value is None:
            return 'null'
        if isinstance(value, bool):
            return 'true' if value else 'false'
        if isinstance(value, (int, float)):
            return str(value)
        if is_safe(value):
            return json.dumps(str(value))
        return self.escape(value)


FORMAT_MAP = {
    'html': HtmlOutputFormat,
    'text': PlainTextOutputFormat,
    'plain': PlainTextOutputFormat,
    'plaintext': PlainTextOutputFormat,
    'json': JsonOutputFormat,
}


def get_output_format(name):
    fmt_class = FORMAT_MAP.get(name)
    if fmt_class is None:
        raise ValueError(f"Unknown output format: {name!r}")
    return fmt_class()

class TemplateSyntaxError(Exception):
    def __init__(self, message, line=None, source_name=None):
        self.line = line
        self.source_name = source_name
        if line:
            message = f"Line {line}: {message}"
        if source_name:
            message = f"[{source_name}] {message}"
        super().__init__(message)


class TemplateRuntimeError(Exception):
    pass


class TemplateNotFoundError(Exception):
    def __init__(self, name):
        self.name = name
        super().__init__(f"Template not found: {name}")


class SecurityError(Exception):
    def __init__(self, message):
        super().__init__(f"Security violation: {message}")

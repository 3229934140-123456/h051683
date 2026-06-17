class SafeString(str):
    _is_safe = True

    def __new__(cls, value=''):
        return str.__new__(cls, value)


def mark_safe(value):
    if isinstance(value, SafeString):
        return value
    return SafeString(value)


def is_safe(value):
    return isinstance(value, SafeString)

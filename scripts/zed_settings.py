import json
import re

LOCAL_KEYS = {'ssh_connections', 'wsl_connections', 'language_models', 'context_servers', 'agent_servers'}
TOKEN = re.compile(
    r'"(?:[^"\\]|\\[\s\S])*"|//[^\n]*|/\*[\s\S]*?(?:\*/|\Z)|[,\[\]{}:]|\s+|[^"/,\[\]{}:\s]+|.'
)


def reject_constant(_):
    raise ValueError('non-finite JSON number')


def parse(text):
    parts = []
    previous = ''
    trailing_comma = None
    for match in TOKEN.finditer(text.lstrip('\ufeff')):
        token = match.group()
        if token.startswith(('//', '/*')):
            if token.startswith('/*') and (len(token) < 4 or not token.endswith('*/')):
                raise ValueError('unterminated JSONC comment')
            parts.append(' ')
            continue
        if token.isspace():
            parts.append(token)
            continue

        if trailing_comma is not None and token in ('}', ']'):
            parts[trailing_comma] = ''
        if token == ',' and previous not in ('', '[', '{', ',', ':'):
            trailing_comma = len(parts)
        else:
            trailing_comma = None
        parts.append(token)
        previous = token

    value = json.loads(''.join(parts), parse_constant=reject_constant)
    if not isinstance(value, dict):
        raise ValueError('Zed settings must be an object')
    return value


def merge(shared, current):
    return {**shared, **{key: value for key, value in current.items() if key in LOCAL_KEYS}}

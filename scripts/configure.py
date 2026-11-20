#!/usr/bin/env python3
"""Preview or apply configuration only. Never install tools or execute profiles."""
import argparse
import datetime
import json
import os
from pathlib import Path
import re
import shlex
import stat
import sys
import tempfile
from typing import NamedTuple, Optional

from layout import BEGIN, END, PLATFORM, ROOT, mise_config_path, powershell_profiles, zed_settings_path
from zed_settings import merge, parse

MANAGED_BLOCK = re.compile(r'^' + re.escape(BEGIN) + r'\r?\n.*?^' + re.escape(END) + r'(?:\r?\n|$)', re.M | re.S)


class Change(NamedTuple):
    target: Path
    original: Optional[bytes]
    content: bytes

    def check_original(self):
        if self.target.is_symlink() or self.target.exists() != (self.original is not None) or (
            self.original is not None and self.target.read_bytes() != self.original
        ):
            raise ValueError('Destination changed during preparation; preview again: ' + str(self.target))

    def write(self):
        self.check_original()
        self.target.parent.mkdir(parents=True, exist_ok=True)
        permissions = 0o600
        if self.original is not None:
            permissions = stat.S_IMODE(self.target.stat().st_mode)
            stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
            backup = self.target.with_name(self.target.name + '.dotfiles-backup-' + stamp)
            descriptor = os.open(backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, 'wb') as handle:
                handle.write(self.original)
            print('BACKUP', backup)
        handle = tempfile.NamedTemporaryFile(dir=self.target.parent, delete=False)
        temporary = Path(handle.name)
        try:
            with handle:
                handle.write(self.content)
            os.chmod(temporary, permissions)
            self.check_original()
            os.replace(temporary, self.target)
        finally:
            temporary.unlink(missing_ok=True)


def managed(old, body):
    newline = '\r\n' if '\r\n' in old else '\n'
    block = newline.join([BEGIN, *body.splitlines(), END]) + newline
    if BEGIN in old or END in old:
        if old.count(BEGIN) != 1 or old.count(END) != 1:
            raise ValueError('ambiguous managed markers; repair manually')
        if not MANAGED_BLOCK.search(old):
            raise ValueError('malformed managed block; repair manually')
        return MANAGED_BLOCK.sub(lambda _: block, old)
    return old + (newline if old and not old.endswith('\n') else '') + block


def ps_quote(value):
    return "'" + str(value).replace("'", "''") + "'"


def git_quote(value):
    return '"' + Path(value).as_posix().replace('\\', '\\\\').replace('"', '\\"') + '"'


def sources_bashrc(text):
    lexer = shlex.shlex(text, posix=True, punctuation_chars=';&|()\n')
    lexer.whitespace = ' \t\r'
    lexer.whitespace_split = True
    tokens = list(lexer)
    for index, token in enumerate(tokens[:-1]):
        previous = tokens[index - 1] if index else ''
        separator = index == 0 or previous in {'then', 'do', 'else'} or bool(previous) and set(previous) <= set(';&|()\n')
        if token in {'.', 'source'} and separator:
            if tokens[index + 1].endswith('/.bashrc') or tokens[index + 1] == '.bashrc':
                return True
    return False


def destinations(args, home):
    components = set(args.components)
    unix_shells = components & {'bash', 'zsh'}
    if args.platform == 'windows' and unix_shells:
        raise ValueError('use powershell on Windows; configure Unix shells inside their Unix environment')
    if args.platform != 'windows' and 'powershell' in components:
        raise ValueError('powershell profile placement requires --platform windows')
    changes = []
    if 'powershell' in components:
        body = '\n'.join([
            '$env:DOTFILES_ROOT = ' + ps_quote(ROOT),
            ". (Join-Path $env:DOTFILES_ROOT 'powershell/profile.ps1')",
        ])
        for profile in powershell_profiles(home, args.documents):
            changes.append((profile, body, 'block', True))
    for shell, target, source in [('bash', '.bashrc', 'bash/init.bash'), ('zsh', '.zshrc', 'zsh/init.zsh')]:
        if shell not in components:
            continue
        body = '\n'.join([
            'export DOTFILES_ROOT=' + shlex.quote(str(ROOT)),
            'export DOTFILES_PLATFORM=' + shlex.quote(args.platform),
            '. "$DOTFILES_ROOT/' + source + '"',
        ])
        changes.append((home / target, body, 'block', True))
    if 'bash' in components:
        # Bash reads only the first existing user login file.
        login = next((home / f for f in ['.bash_profile', '.bash_login', '.profile'] if (home / f).exists()), home / '.profile')
        text = login.read_text(encoding='utf-8') if login.exists() else ''
        if BEGIN in text or END in text or not sources_bashrc(text):
            body = '\n'.join([
                'if [ -n "${BASH_VERSION:-}" ] && [ -z "${DOTFILES_BASH_LOADED:-}" ]; then',
                '    [ ! -f "$HOME/.bashrc" ] || . "$HOME/.bashrc"',
                'fi',
            ])
            changes.append((login, body, 'block', False))
    if 'mise' in components:
        changes.append((mise_config_path(home), (ROOT / 'mise/tools.toml').read_text(), 'file', False))
    if 'git' in components:
        # Appended includes override portable behavior; local identity wins last.
        body = '[include]\n    path = ' + git_quote(ROOT / 'git/config') + '\n    path = ' + git_quote(ROOT / 'local/git.config')
        changes.append((home / '.gitconfig', body, 'block', False))
    if 'zed' in components:
        changes.append((zed_settings_path(home, args.platform), (ROOT / 'zed/settings.json').read_text(), 'zed', False))
    return changes


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--platform', choices=['macos', 'linux', 'windows'], default=PLATFORM)
    parser.add_argument('components', nargs='+', choices=['bash', 'zsh', 'powershell', 'git', 'zed', 'mise'])
    parser.add_argument('--home', type=Path, default=Path.home(), help='destination home; use a temporary directory for staging')
    parser.add_argument('--documents', help='Windows Documents folder override (supports redirected Documents)')
    parser.add_argument('--apply', action='store_true', help='write files; without this flag only preview')
    parser.add_argument('--allow-existing-hooks', action='store_true', help='acknowledge reviewed unmanaged shell initialization')
    args = parser.parse_args(argv)
    home = args.home.expanduser().absolute()
    plans = []
    blockers = []
    try:
        for target, body, mode, shell in destinations(args, home):
            if target.is_symlink():
                raise ValueError('refusing to replace a symlink: ' + str(target))
            if target.exists() and not target.is_file():
                raise ValueError('destination is not a regular file: ' + str(target))
            original = target.read_bytes() if target.exists() else None
            old_bytes = original or b''
            old = old_bytes.decode('utf-8-sig')
            if mode == 'zed':
                content = json.dumps(merge(parse(body), parse(old) if old.strip() else {}), indent=2) + '\n'
            else:
                content = managed(old, body) if mode == 'block' else body
            if shell and re.search(r'starship\s+init|direnv\s+hook|nvm\.sh|_bun|oh-my-zsh\.sh|zsh-autosuggestions|zsh-syntax-highlighting|\.dotfiles/zsh/', MANAGED_BLOCK.sub('', old)):
                print('REVIEW existing shell hooks:', target)
                if not args.allow_existing_hooks:
                    blockers.append(target)
            # PowerShell 5.1 requires a BOM for non-ASCII paths in UTF-8.
            encoding = 'utf-8-sig' if target.suffix == '.ps1' or old_bytes.startswith(b'\xef\xbb\xbf') else 'utf-8'
            encoded = content.encode(encoding)
            changed = encoded != old_bytes
            print(('UPDATE' if original is not None else 'CREATE') if changed else 'UNCHANGED', target)
            plans.append(Change(target, original, encoded))
    except (OSError, UnicodeError, ValueError) as error:
        print('Cannot prepare configuration:', error, file=sys.stderr)
        return 2
    if blockers:
        print('Review and reconcile existing hooks before apply. --allow-existing-hooks is an explicit acknowledgement.')
        if args.apply:
            return 2
    if not args.apply:
        print('Preview only. No files written.')
        return 0
    try:
        for change in plans:
            change.check_original()
        for change in plans:
            if change.content != (change.original or b''):
                change.write()
    except (OSError, ValueError) as error:
        print('Cannot apply configuration:', error, file=sys.stderr)
        return 2
    print('Configuration applied. No packages installed or shells changed.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

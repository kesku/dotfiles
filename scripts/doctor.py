#!/usr/bin/env python3
"""Read-only checks. Report presence and counts, never config/credential values."""
import argparse
import os
from pathlib import Path
import re
import shutil
import subprocess

from layout import BEGIN, PLATFORM, ROOT, powershell_profiles, zed_settings_path
from zed_settings import merge, parse


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home', type=Path, default=Path.home())
    parser.add_argument('--platform', choices=['macos', 'linux', 'windows'], default=PLATFORM)
    parser.add_argument('--documents', help='Windows Documents folder override')
    args = parser.parse_args()
    args.home = args.home.expanduser().absolute()
    print('Tool availability (current PATH only):')
    for command in ['git', 'starship', 'zsh', 'bash', 'pwsh', 'node', 'bun', 'python3', 'py', 'uv', 'cargo', 'mise', 'direnv']:
        print(' ', command + ':', 'available' if shutil.which(command) else 'not found')
    expected = (ROOT / 'starship/version').read_text().strip()
    if shutil.which('starship'):
        try:
            version = subprocess.run(['starship', '--version'], capture_output=True, text=True, timeout=10)
            match = re.match(r'^starship ([0-9]+\.[0-9]+\.[0-9]+)(?:\s|$)', version.stdout)
            actual = match.group(1) if match and version.returncode == 0 else 'unknown'
            print('Starship version:', actual, '(matches)' if actual == expected else '(expected ' + expected + ')')
        except (OSError, subprocess.TimeoutExpired):
            print('Starship version: unavailable; expected', expected)
    else:
        print('Starship version: not installed; expected', expected)
    entries = [os.path.normcase(p.rstrip('/\\')) for p in os.environ.get('PATH', '').split(os.pathsep) if p]
    print('Repeated PATH entries:', len(entries) - len(set(entries)))
    profiles = [args.home / name for name in ('.bashrc', '.zshrc', '.gitconfig')]
    if args.platform == 'windows':
        try:
            profiles.extend(powershell_profiles(args.home, args.documents))
        except ValueError as error:
            print('PowerShell profiles:', error)
    for file in profiles:
        if file.is_file():
            text = file.read_text(encoding='utf-8-sig', errors='replace')
            label = file.relative_to(args.home) if file.name != 'profile.ps1' else Path(file.parent.name) / file.name
            print(str(label) + ':', 'managed block present' if BEGIN in text else 'unmanaged')
            if file.name in ['.bashrc', '.zshrc']:
                for label, pattern in [('Starship initializers', r'starship\s+init'), ('direnv hooks', r'direnv\s+hook')]:
                    print(' ', label + ':', len(re.findall(pattern, text)))
    for relative in ['.cargo/env', '.nvm/nvm.sh', '.bun/_bun', '.nix-profile/share/nix-direnv/direnvrc']:
        print(relative + ':', 'present' if (args.home / relative).is_file() else 'absent (optional)')
    target = zed_settings_path(args.home, args.platform)
    if not target.is_file():
        print('Zed: settings absent')
    else:
        try:
            current = parse(target.read_text(encoding='utf-8-sig'))
            shared = parse((ROOT / 'zed/settings.json').read_text())
            print('Zed:', 'shared preferences match' if current == merge(shared, current) else 'shared preferences differ')
        except (ValueError, OSError):
            print('Zed: unable to parse settings')
    print('No profiles executed. Optional tool absence is informational.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

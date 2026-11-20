import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
BEGIN = '# BEGIN kesku/dotfiles'
END = '# END kesku/dotfiles'
PLATFORM = 'windows' if os.name == 'nt' else 'macos' if sys.platform == 'darwin' else 'linux'


def user_directory(home, variable, fallback):
    if home == Path.home() and variable in os.environ:
        return Path(os.environ[variable])
    return fallback


def zed_settings_path(home, platform):
    if platform == 'windows':
        return user_directory(home, 'APPDATA', home / 'AppData/Roaming') / 'Zed/settings.json'
    return user_directory(home, 'XDG_CONFIG_HOME', home / '.config') / 'zed/settings.json'


def mise_config_path(home):
    config_home = user_directory(home, 'XDG_CONFIG_HOME', home / '.config')
    return user_directory(home, 'MISE_CONFIG_DIR', config_home / 'mise') / 'conf.d/90-dotfiles.toml'


def powershell_profiles(home, override):
    documents = home / 'Documents'
    if override:
        documents = home / Path(override).expanduser()
    elif home == Path.home() and os.name == 'nt':
        import ctypes
        buffer = ctypes.create_unicode_buffer(32768)
        if ctypes.windll.shell32.SHGetFolderPathW(None, 5, None, 0, buffer) != 0:
            raise ValueError('cannot discover Documents; specify --documents')
        documents = Path(buffer.value)
    return [documents / edition / 'profile.ps1' for edition in ('WindowsPowerShell', 'PowerShell')]

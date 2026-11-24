import contextlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import configure


class ConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix='dotfiles-test-')
        self.home = Path(self.directory.name) / 'home with spaces'
        self.home.mkdir()
        self.checkout = Path(self.directory.name) / 'checkout with spaces'
        self.checkout.mkdir()
        for name in ['scripts', 'shell', 'zsh', 'bash', 'powershell', 'git', 'zed', 'mise', 'starship', 'agents']:
            shutil.copytree(ROOT / name, self.checkout / name, ignore=shutil.ignore_patterns('__pycache__', 'local.zsh'))

    def tearDown(self):
        self.directory.cleanup()

    def run_configure(self, *args, expected=0, components=('bash', 'zsh', 'git', 'zed')):
        result = subprocess.run([os.sys.executable, str(self.checkout / 'scripts/configure.py'), '--home', str(self.home), '--platform', 'linux', *args, *components], capture_output=True, text=True)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return result

    def test_preview_never_writes(self):
        self.run_configure()
        self.assertEqual(list(self.home.iterdir()), [])

    def test_preserve_backup_and_idempotency(self):
        original = b'# keep my shell\r\nalias mine=true\r\n'
        (self.home / '.bashrc').write_bytes(original)
        self.run_configure('--apply')
        self.assertTrue((self.home / '.bashrc').read_bytes().startswith(original))
        backup = list(self.home.glob('.bashrc.dotfiles-backup-*'))
        self.assertEqual(len(backup), 1)
        self.assertEqual(backup[0].read_bytes(), original)
        before = {p.relative_to(self.home): p.read_bytes() for p in self.home.rglob('*') if p.is_file()}
        self.run_configure('--apply')
        after = {p.relative_to(self.home): p.read_bytes() for p in self.home.rglob('*') if p.is_file()}
        self.assertEqual(before, after)

    def test_conflicting_hooks_block_entire_apply(self):
        original = 'eval "$(starship init bash)"\n'
        (self.home / '.bashrc').write_text(original)
        self.run_configure('--apply', expected=2)
        self.assertEqual((self.home / '.bashrc').read_text(), original)
        self.assertFalse((self.home / '.gitconfig').exists())
        self.run_configure('--apply', '--allow-existing-hooks')

    def test_symlink_refused_without_partial_writes(self):
        target = self.home / 'existing'
        target.write_text('keep')
        try:
            (self.home / '.gitconfig').symlink_to(target)
        except OSError as error:
            if getattr(error, 'winerror', None) == 1314:
                self.skipTest('Windows account cannot create symlinks')
            raise
        self.run_configure('--apply', expected=2)
        self.assertEqual(target.read_text(), 'keep')
        self.assertFalse((self.home / '.bashrc').exists())

    def test_malformed_markers_block_apply(self):
        (self.home / '.gitconfig').write_text(configure.BEGIN + '\n')
        self.run_configure('--apply', expected=2)
        self.assertFalse((self.home / '.bashrc').exists())

    def test_only_selected_components(self):
        self.run_configure('--apply', components=('bash', 'git'))
        self.assertTrue((self.home / '.bashrc').exists())
        self.assertFalse((self.home / '.zshrc').exists())
        self.assertFalse((self.home / '.config/zed').exists())

    def test_zed_preserves_local_connections_and_replaces_preferences(self):
        target = self.home / '.config/zed/settings.json'
        target.parent.mkdir(parents=True)
        target.write_text('// local settings\n{"theme":"Old", "ssh_connections":[{"host":"example.invalid"}], "wsl_connections":[], "show_edit_predictions":false,}\n')
        self.run_configure('--apply', components=('zed',))
        actual = json.loads(target.read_text())
        self.assertEqual(actual['ssh_connections'], [{'host': 'example.invalid'}])
        self.assertEqual(actual['wsl_connections'], [])
        self.assertEqual(actual['theme'], 'VSCode Dark Modern')
        self.assertNotIn('show_edit_predictions', actual)
        doctor = subprocess.run([os.sys.executable, str(self.checkout / 'scripts/doctor.py'), '--home', str(self.home), '--platform', 'linux'], capture_output=True, text=True)
        self.assertEqual(doctor.returncode, 0, doctor.stderr)
        self.assertIn('Zed: shared preferences match', doctor.stdout)
        self.run_configure('--apply', components=('zed',))
        self.assertEqual(len(list(target.parent.glob('settings.json.dotfiles-backup-*'))), 1)

    def test_invalid_zed_settings_stop_before_any_write(self):
        target = self.home / '.config/zed/settings.json'
        target.parent.mkdir(parents=True)
        target.write_text('{invalid')
        self.run_configure('--apply', components=('git', 'zed'), expected=2)
        self.assertFalse((self.home / '.gitconfig').exists())
        self.assertEqual(target.read_text(), '{invalid')

    def test_mise_component_places_only_configuration(self):
        self.run_configure('--apply', components=('mise',))
        config = self.home / '.config/mise/conf.d/90-dotfiles.toml'
        self.assertEqual(config.read_bytes(), (self.checkout / 'mise/tools.toml').read_bytes())
        self.assertFalse((self.home / '.bashrc').exists())
        self.assertFalse((self.home / '.local/bin/mise').exists())
        self.run_configure('--apply', components=('mise',))
        self.assertEqual(list(config.parent.glob('*.dotfiles-backup-*')), [])

    @unittest.skipIf(os.name == 'nt', 'Unix shell integration runs on Unix')
    def test_mise_shims_yield_to_nix(self):
        bin_dir = self.home / 'bin'
        bin_dir.mkdir()
        marker = self.home / 'mise-called'
        fake = bin_dir / 'mise'
        fake.write_text('#!/bin/sh\nprintf called > "$HOME/mise-called"\nprintf "export DOTFILES_TEST_MISE=active\\n"\n')
        fake.chmod(0o755)
        env = {'HOME': str(self.home), 'PATH': str(bin_dir) + ':/usr/bin:/bin', 'DOTFILES_ROOT': str(self.checkout), 'DOTFILES_ENABLE_MISE': '1', 'DOTFILES_SHELL': 'bash'}
        command = ['/bin/bash', '--noprofile', '--norc', '-c', '. "$DOTFILES_ROOT/shell/common.sh"']
        original_path = env['PATH']
        nix = subprocess.run(command[:-1] + [command[-1] + '; printf %s \"$PATH\"'], env=dict(env, IN_NIX_SHELL='1'), capture_output=True, text=True, check=True)
        self.assertEqual(nix.stdout, original_path)
        self.assertFalse(marker.exists())
        subprocess.run(command, env=env, capture_output=True, check=True)
        self.assertTrue(marker.exists())

    def test_bash_login_comment_or_echo_is_not_a_source(self):
        for text in ['   # source ~/.bashrc\n', "echo 'source ~/.bashrc'\n", 'export BASHRC=~/.bashrc\n']:
            self.assertFalse(configure.sources_bashrc(text))
        for text in ['export X=1\n. "$HOME/.bashrc"\n', 'if [ -f ~/.bashrc ]; then\n source ~/.bashrc\nfi\n']:
            self.assertTrue(configure.sources_bashrc(text))
        (self.home / '.profile').write_text('  # source ~/.bashrc\n')
        self.run_configure('--apply', components=('bash',))
        self.assertIn(configure.BEGIN, (self.home / '.profile').read_text())

    def test_relative_documents_path_stays_under_staging_home(self):
        self.run_configure('--platform', 'windows', '--documents', 'Documents Alternate', '--apply', components=('powershell',))
        self.assertTrue((self.home / 'Documents Alternate/WindowsPowerShell/profile.ps1').exists())
        doctor = subprocess.run([sys.executable, str(self.checkout / 'scripts/doctor.py'), '--home', str(self.home), '--platform', 'windows', '--documents', 'Documents Alternate'], capture_output=True, text=True, check=True)
        self.assertEqual(doctor.stdout.count('profile.ps1: managed block present'), 2)

    @unittest.skipIf(os.name == 'nt', 'Unix permissions')
    def test_backup_permissions_are_private(self):
        file = self.home / '.gitconfig'
        file.write_text('[user]\n name = Example\n')
        file.chmod(0o644)
        self.run_configure('--apply', components=('git',))
        backup = next(self.home.glob('.gitconfig.dotfiles-backup-*'))
        self.assertEqual(backup.stat().st_mode & 0o777, 0o600)
        self.assertEqual(file.stat().st_mode & 0o777, 0o644)

    def test_concurrent_destination_edit_is_not_overwritten(self):
        target = self.home / '.gitconfig'
        target.write_text('initial\n')
        original_managed = configure.managed
        def edit_during_preparation(old, body):
            target.write_text('concurrent edit\n')
            return original_managed(old, body)
        with patch.object(configure, 'destinations', return_value=[(target, '[push]\n autoSetupRemote=true', 'block', False)]), patch.object(configure, 'managed', side_effect=edit_during_preparation), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(configure.main(['git', '--home', str(self.home), '--apply']), 2)
        self.assertEqual(target.read_text(), 'concurrent edit\n')
        self.assertEqual(list(self.home.glob('*.dotfiles-backup-*')), [])

    def test_components_required_and_platform_mismatches_rejected(self):
        self.run_configure(components=(), expected=2)
        self.run_configure('--platform', 'windows', '--apply', components=('bash',), expected=2)
        self.run_configure('--apply', components=('powershell',), expected=2)
        self.assertEqual(list(self.home.iterdir()), [])

    @unittest.skipIf(os.name == 'nt', 'agents is Unix-only')
    def test_agents_links_skills_and_disables_impeccable_telemetry(self):
        config = self.home / '.impeccable/config.json'
        config.parent.mkdir()
        config.write_text('{"account": "kept"}\n')
        self.run_configure('--apply', components=('agents',))
        self.assertEqual(json.loads(config.read_text()), {'account': 'kept', 'telemetry': False})
        skill = self.home / '.agents/skills/pr-review-guide'
        self.assertEqual(os.readlink(skill), str(self.checkout.resolve() / 'agents/skills/pr-review-guide'))
        for agent in ['.claude', '.codex']:
            self.assertTrue((self.home / agent / 'skills/pr-review-guide/SKILL.md').is_file())
        self.assertEqual(os.readlink(self.home / '.codex/skills/impeccable'), '../../.agents/skills/impeccable')
        self.assertNotIn('LINK', self.run_configure('--apply', components=('agents',)).stdout)
        self.run_configure('--platform', 'windows', components=('agents',), expected=2)

    @unittest.skipIf(os.name == 'nt', 'agents is Unix-only')
    def test_agents_refuses_unmanaged_skill_without_partial_writes(self):
        (self.home / '.claude/skills/pr-review-guide').mkdir(parents=True)
        self.run_configure('--apply', components=('agents',), expected=2)
        self.assertFalse((self.home / '.impeccable').exists())
        self.assertFalse((self.home / '.agents').exists())

    def test_zsh_only_does_not_configure_bash_or_git(self):
        self.run_configure('--apply', components=('zsh',))
        self.assertTrue((self.home / '.zshrc').exists())
        self.assertFalse((self.home / '.bashrc').exists())
        self.assertFalse((self.home / '.profile').exists())
        self.assertFalse((self.home / '.gitconfig').exists())

    @unittest.skipIf(os.name == 'nt', 'Unix shell integration runs on Unix')
    def test_local_settings_control_runtime_initialization(self):
        root = self.home / 'checkout'
        (root / 'local').mkdir(parents=True)
        (root / 'shell').mkdir()
        shutil.copyfile(self.checkout / 'shell/common.sh', root / 'shell/common.sh')
        (self.home / '.nvm').mkdir()
        (self.home / '.nvm/nvm.sh').write_text('printf runtime-loaded')
        env = {'HOME': str(self.home), 'PATH': '/usr/bin:/bin', 'DOTFILES_ROOT': str(root)}
        command = ['/bin/bash', '--noprofile', '--norc', '-c', '. "$DOTFILES_ROOT/shell/common.sh"']
        result = subprocess.run(command, env=env, capture_output=True, text=True, check=True)
        self.assertEqual(result.stdout, '')
        (root / 'local/env.sh').write_text('DOTFILES_ENABLE_DEV_TOOLS=1')
        result = subprocess.run(command, env=env, capture_output=True, text=True, check=True)
        self.assertEqual(result.stdout, 'runtime-loaded')

    def test_windows_paths_and_both_profile_editions(self):
        self.run_configure('--platform', 'windows', '--apply', components=('powershell', 'git', 'zed'))
        for edition in ['PowerShell', 'WindowsPowerShell']:
            self.assertTrue((self.home / 'Documents' / edition / 'profile.ps1').exists())
        settings = json.loads((self.home / 'AppData/Roaming/Zed/settings.json').read_text())
        self.assertEqual(settings['theme'], 'VSCode Dark Modern')
        self.assertFalse((self.home / '.bashrc').exists())

    def test_windows_bom_redirected_documents_and_repeat_apply(self):
        documents = self.home / 'Redirected Documents'
        args = ['--platform', 'windows', '--documents', str(documents), '--apply']
        self.run_configure(*args, components=('powershell', 'git', 'zed'))
        profile = documents / 'WindowsPowerShell/profile.ps1'
        before = profile.read_bytes()
        self.assertTrue(before.startswith(b'\xef\xbb\xbf'))
        self.run_configure(*args, components=('powershell', 'git', 'zed'))
        self.assertEqual(profile.read_bytes(), before)
        self.assertEqual(list(documents.rglob('*.dotfiles-backup-*')), [])

    def test_git_preserves_identity_and_applies_shared_behavior(self):
        git = shutil.which('git')
        if not git:
            self.skipTest('git unavailable')
        original = '[user]\n    email = example@example.invalid\n[push]\n    autoSetupRemote = false\n'
        (self.home / '.gitconfig').write_text(original)
        self.run_configure('--apply', components=('git',))
        env = dict(os.environ, HOME=str(self.home), GIT_CONFIG_GLOBAL=str(self.home / '.gitconfig'), GIT_CONFIG_NOSYSTEM='1')
        for key, expected in [('user.email', 'example@example.invalid'), ('push.autoSetupRemote', 'true')]:
            result = subprocess.run([git, 'config', '--global', '--includes', '--get', key], env=env, capture_output=True, text=True)
            self.assertEqual(result.stdout.strip(), expected)

    def test_git_conditional_identity_include_is_preserved(self):
        git = shutil.which('git')
        if not git:
            self.skipTest('git unavailable')
        repository = self.home / 'project'
        subprocess.run([git, 'init', '--quiet', str(repository)], capture_output=True, check=True)
        identity = self.home / 'conditional.config'
        identity.write_text('[user]\n    email = alternate@example.invalid\n')
        prefix = str(repository.resolve()).replace('\\', '/') + '/'
        include = str(identity).replace('\\', '/')
        original = '[user]\n    email = default@example.invalid\n[includeIf "gitdir:' + prefix + '"]\n    path = "' + include + '"\n'
        (self.home / '.gitconfig').write_text(original)
        self.run_configure('--apply', components=('git',))
        self.assertTrue((self.home / '.gitconfig').read_text().startswith(original))
        self.assertEqual(identity.read_text(), '[user]\n    email = alternate@example.invalid\n')
        env = dict(os.environ, HOME=str(self.home), GIT_CONFIG_GLOBAL=str(self.home / '.gitconfig'), GIT_CONFIG_NOSYSTEM='1')
        result = subprocess.run([git, '-C', str(repository), 'config', '--includes', '--get', 'user.email'], env=env, capture_output=True, text=True)
        self.assertEqual(result.stdout.strip(), 'alternate@example.invalid')

    def test_existing_bash_login_order(self):
        (self.home / '.bash_login').write_text('# keep\n')
        self.run_configure('--apply', components=('bash',))
        self.assertIn('.bashrc', (self.home / '.bash_login').read_text())
        self.assertFalse((self.home / '.profile').exists())

    def test_existing_login_hook_is_preserved(self):
        original = '[ ! -f ~/.bashrc ] || . ~/.bashrc\n'
        (self.home / '.profile').write_text(original)
        self.run_configure('--apply', components=('bash',))
        self.assertEqual((self.home / '.profile').read_text(), original)

    @unittest.skipIf(os.name == 'nt', 'Unix shell integration runs on Unix')
    def test_login_profile_does_not_source_bashrc_twice(self):
        (self.home / '.bashrc').write_text("printf '%s\\n' loaded\n")
        (self.home / '.profile').write_text('export FOO=1 # inline comment\n. "$HOME/.bashrc"\n')
        self.run_configure('--apply', components=('bash',))
        env = {'HOME': str(self.home), 'PATH': '/usr/bin:/bin', 'TERM': 'dumb'}
        result = subprocess.run(
            ['/bin/bash', '--noprofile', '--norc', '-ic', '. "$HOME/.profile"'],
            env=env, capture_output=True, text=True, check=True,
        )
        self.assertEqual(result.stdout, 'loaded\n')

    def check_shell_startup(self, shell, profile, flags):
        binary = shutil.which(shell)
        if os.name == 'nt' or not binary:
            self.skipTest(f'{shell} unavailable in a Unix environment')
        self.run_configure('--apply', components=(shell,))
        local = self.checkout / 'local'
        local.mkdir()
        (local / (shell + 'rc')).write_text("printf '%s\\n' loaded\n")
        env = {'HOME': str(self.home), 'ZDOTDIR': str(self.home), 'PATH': '/usr/bin:/bin', 'TERM': 'dumb'}
        command = f'. "$HOME/{profile}"; . "$HOME/{profile}"; printf "%s" "$STARSHIP_CONFIG"'
        result = subprocess.run([binary, *flags, command], env=env, capture_output=True, text=True, check=True)
        loaded, config = result.stdout.splitlines()
        self.assertEqual(loaded, 'loaded')
        self.assertEqual(Path(config).resolve(), (self.checkout / 'starship/starship.toml').resolve())

    def test_bash_startup_loads_local_override_once(self):
        self.check_shell_startup('bash', '.bashrc', ['--noprofile', '--norc', '-ic'])

    def test_zsh_startup_loads_local_override_once(self):
        self.check_shell_startup('zsh', '.zshrc', ['-f', '-ic'])

    @unittest.skipIf(os.name == "nt", "Unix shell integration runs on Unix")
    def test_nix_shell_does_not_load_nvm(self):
        nvm = self.home / '.nvm'
        nvm.mkdir()
        (nvm / 'nvm.sh').write_text('echo SHOULD_NOT_LOAD\n')
        env = {'HOME': str(self.home), 'PATH': '/usr/bin:/bin', 'IN_NIX_SHELL': '1', 'DOTFILES_ROOT': str(self.checkout), 'DOTFILES_ENABLE_DEV_TOOLS': '1'}
        result = subprocess.run(['/bin/bash', '--noprofile', '--norc', '-c', '. "$DOTFILES_ROOT/shell/common.sh"'], env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, '')


if __name__ == '__main__':
    unittest.main()

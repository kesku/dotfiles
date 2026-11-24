# Kesku's dotfiles

I got into homelabbing and wanted to standardize my setup across machines

## Install

Requires Python 3.9+

Clone somewhere permanent since the installed configs reference the repo

On macOS/Linux:

```sh
git clone git@github.com:kesku/dotfiles.git ~/.dotfiles
cd ~/.dotfiles
./install.sh zsh git zed
```

On Windows:

```powershell
py -3 scripts/configure.py powershell git zed
```

Pick: `bash`, `zsh`, `powershell`, `git`, `zed`, `mise`, `agents`

Run shell setup in its own environment inc WSL

The installer previews changes first. If everything looks good, run the same command with `--apply`

It backs up changed files and only updates the relevant parts of your existing configs. It won't install packages or change your default shell

If it finds existing shell hooks, check them before applying. Only use `--allow-existing-hooks` if you've reviewed the overlap

If something fails during install, restore the affected files from their backups

Restart terminal when done!

## Local overrides

Machine-specific config or secrets go in `local/`, which is gitignored

| File | Purpose |
| --- | --- |
| `env.sh` | Bash/Zsh options |
| `env.ps1` | PowerShell options |
| `bashrc`, `zshrc`, `profile.ps1` | Shell customizations |
| `git.config` | Git overrides |

To enable mise or direnv in Bash/Zsh, add these to `local/env.sh`:

```sh
DOTFILES_ENABLE_MISE=1
DOTFILES_ENABLE_DIRENV=1
```

For PowerShell, add this to `local/env.ps1`:

```powershell
$env:DOTFILES_ENABLE_MISE = '1'
```

Leave these unset if the machine already handles them

Existing `zsh/local.zsh` configs still work. `DOTFILES_ENABLE_DEV_TOOLS=1` enables the older Bash/Zsh runtime hooks when mise is off

Mise shims step aside inside Nix shells

Git keeps machine-specific identity, auth, and signing settings. Zed keeps SSH/WSL connections and model/server settings while updating shared preferences

## Mise

Install the mise version from `mise/version` separately

Then:

```sh
./install.sh mise
./install.sh mise --apply
cd ~
mise install
```

This installs the tools defined in `mise/tools.toml`. Projects can still use their own version files

Rust uses separate Cargo and rustup directories and still needs a native linker

## Agents

Skills for Claude Code and Codex on macOS/Linux. Skills in `agents/skills/` link into `~/.agents/skills` and from there into `~/.claude/skills` and `~/.codex/skills`, so `git pull` updates them

Install [impeccable](https://github.com/pbakaus/impeccable) at the version in `agents/impeccable/version` separately, with its design hook:

```sh
DO_NOT_TRACK=1 npx -y impeccable@$(cat agents/impeccable/version) install -y --providers=claude,codex --scope=global
```

Then:

```sh
./install.sh agents
./install.sh agents --apply
```

This turns off impeccable telemetry and links its Codex skill into `~/.codex/skills`. In Codex, approve the impeccable hook in `/hooks`

## Checks

```sh
python3 -m unittest discover -s tests -v
python3 scripts/doctor.py
```

Tests run in temporary home directories

Doctor checks installed tools, shell configs, Starship versions, and Zed settings without loading your profiles

For more options:

```sh
./install.sh --help
```

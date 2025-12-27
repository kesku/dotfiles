# Kesku's dotfiles

I got into homelabbing and wanted to standardize my setup

## Install

On machine:

```sh
git clone git@github.com:kesku/dotfiles.git ~/.dotfiles
~/.dotfiles/install.sh
```

Restart terminal when done

## Structure

```text
.dotfiles/
├── zsh/
│   ├── env.zsh
│   ├── aliases.zsh
│   ├── tools.zsh
│   ├── completions.zsh
│   └── local.zsh      # gitignored
├── starship/
│   └── starship.toml
├── install.sh
└── .gitignore
```

## Local overrides

machine-specific config or secrets go in:

```sh
~/.dotfiles/zsh/local.zsh
```
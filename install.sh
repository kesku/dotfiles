#!/usr/bin/env bash
set -e

DOTFILES="$HOME/.dotfiles"

echo "Setting up dotfiles from $DOTFILES"

if ! command -v zsh >/dev/null 2>&1; then
  echo "Installing zsh"
  sudo apt update
  sudo apt install -y zsh
fi

if [ ! -d "$HOME/.oh-my-zsh" ]; then
  echo "Installing oh-my-zsh"
  RUNZSH=no CHSH=no sh -c \
    "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"
fi

if [ ! -f "$HOME/.zshrc" ]; then
  echo "Creating ~/.zshrc"
  cat > "$HOME/.zshrc" <<'EOF'
export ZSH="$HOME/.oh-my-zsh"

ZSH_THEME=""
plugins=(git)

source "$ZSH/oh-my-zsh.sh"

# Dotfiles
[ -f "$HOME/.dotfiles/zsh/env.zsh" ] && source "$HOME/.dotfiles/zsh/env.zsh"
[ -f "$HOME/.dotfiles/zsh/aliases.zsh" ] && source "$HOME/.dotfiles/zsh/aliases.zsh"
[ -f "$HOME/.dotfiles/zsh/tools.zsh" ] && source "$HOME/.dotfiles/zsh/tools.zsh"
[ -f "$HOME/.dotfiles/zsh/completions.zsh" ] && source "$HOME/.dotfiles/zsh/completions.zsh"
[ -f "$HOME/.dotfiles/zsh/local.zsh" ] && source "$HOME/.dotfiles/zsh/local.zsh"

# Starship
export STARSHIP_CONFIG="$HOME/.dotfiles/starship/starship.toml"
command -v starship >/dev/null 2>&1 && eval "$(starship init zsh)"
EOF
else
  echo "~/.zshrc already exists, skipping"
fi

if [ "$SHELL" != "$(command -v zsh)" ]; then
  echo "Setting zsh as default shell"
  chsh -s "$(command -v zsh)"
fi

echo "Dotfiles install complete"
echo "Restart terminal"

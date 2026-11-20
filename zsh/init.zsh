[[ -o interactive ]] || return
[[ -z "${DOTFILES_ZSH_LOADED:-}" ]] || return
DOTFILES_ZSH_LOADED=1
DOTFILES_SHELL=zsh
source "$DOTFILES_ROOT/shell/common.sh"
source "$DOTFILES_ROOT/zsh/completions.zsh"
source "$DOTFILES_ROOT/zsh/env.zsh"
source "$DOTFILES_ROOT/zsh/aliases.zsh"
if command -v starship >/dev/null 2>&1; then
    eval "$(starship init zsh)"
fi
if [[ "${DOTFILES_ENABLE_DIRENV:-0}" == 1 ]] && command -v direnv >/dev/null 2>&1; then
    eval "$(direnv hook zsh)"
fi
[[ ! -f "$DOTFILES_ROOT/local/zshrc" ]] || source "$DOTFILES_ROOT/local/zshrc"
# Compatibility with the previous ignored override location.
[[ ! -f "$DOTFILES_ROOT/zsh/local.zsh" ]] || source "$DOTFILES_ROOT/zsh/local.zsh"
source "$DOTFILES_ROOT/zsh/tools.zsh"

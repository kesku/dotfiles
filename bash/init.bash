case $- in *i*) ;; *) return ;; esac
[ -z "${DOTFILES_BASH_LOADED:-}" ] || return
DOTFILES_BASH_LOADED=1
DOTFILES_SHELL=bash
. "$DOTFILES_ROOT/shell/common.sh"
if dotfiles_legacy_tools_enabled; then
    if [ -z "${IN_NIX_SHELL:-}" ]; then
        [ ! -s "$NVM_DIR/bash_completion" ] || . "$NVM_DIR/bash_completion"
    fi
    [ ! -f "$HOME/.fzf.bash" ] || . "$HOME/.fzf.bash"
fi
if command -v starship >/dev/null 2>&1; then
    eval "$(starship init bash)"
fi
if [ "${DOTFILES_ENABLE_DIRENV:-0}" = 1 ] && command -v direnv >/dev/null 2>&1; then
    eval "$(direnv hook bash)"
fi
[ ! -f "$DOTFILES_ROOT/local/bashrc" ] || . "$DOTFILES_ROOT/local/bashrc"

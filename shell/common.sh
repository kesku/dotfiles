dotfiles_prepend_path() {
    [ -d "$1" ] || return 0
    case ":$PATH:" in
        *":$1:"*) ;;
        *) export PATH="$1:$PATH" ;;
    esac
}
dotfiles_legacy_tools_enabled() {
    [ "${DOTFILES_ENABLE_DEV_TOOLS:-0}" = 1 ] && [ "${DOTFILES_ENABLE_MISE:-0}" != 1 ]
}
[ "${DOTFILES_PLATFORM:-}" != macos ] || . "$DOTFILES_ROOT/shell/platform/macos.sh"
[ ! -f "$DOTFILES_ROOT/local/env.sh" ] || . "$DOTFILES_ROOT/local/env.sh"
alias cls='clear'
alias CLS='clear'
export STARSHIP_CONFIG="$DOTFILES_ROOT/starship/starship.toml"
if [ -z "${IN_NIX_SHELL:-}" ]; then
    dotfiles_prepend_path "$HOME/bin"
    dotfiles_prepend_path "$HOME/.local/bin"
fi
if dotfiles_legacy_tools_enabled; then
    export BUN_INSTALL="${BUN_INSTALL:-$HOME/.bun}"
    export PYENV_ROOT="${PYENV_ROOT:-$HOME/.pyenv}"
    dotfiles_prepend_path "$BUN_INSTALL/bin"
    dotfiles_prepend_path "$PYENV_ROOT/bin"
    dotfiles_prepend_path "$PYENV_ROOT/shims"
    dotfiles_prepend_path "$HOME/.npm-global/bin"
    [ ! -f "$HOME/.cargo/env" ] || . "$HOME/.cargo/env"
    export NVM_DIR="${NVM_DIR:-$HOME/.nvm}"
    if [ -z "${IN_NIX_SHELL:-}" ] && ! command -v nvm >/dev/null 2>&1; then
        [ ! -s "$NVM_DIR/nvm.sh" ] || . "$NVM_DIR/nvm.sh"
    fi
fi
if [ "${DOTFILES_ENABLE_MISE:-0}" = 1 ] && [ -z "${IN_NIX_SHELL:-}" ] && command -v mise >/dev/null 2>&1; then
    eval "$(mise activate "$DOTFILES_SHELL" --shims)"
fi

if [[ "${DOTFILES_ENABLE_DEV_TOOLS:-0}" == 1 && "${DOTFILES_ENABLE_MISE:-0}" != 1 && -z "${IN_NIX_SHELL:-}" ]]; then
    [[ ! -s "$NVM_DIR/bash_completion" ]] || source "$NVM_DIR/bash_completion"
fi
if [[ "${DOTFILES_ENABLE_DEV_TOOLS:-0}" == 1 && "${DOTFILES_ENABLE_MISE:-0}" != 1 && -s "$HOME/.bun/_bun" ]]; then
    source "$HOME/.bun/_bun"
fi

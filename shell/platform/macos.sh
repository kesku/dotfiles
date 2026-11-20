if ! command -v brew >/dev/null 2>&1; then
    for dotfiles_brew in /opt/homebrew/bin/brew /usr/local/bin/brew; do
        if [ -x "$dotfiles_brew" ]; then
            eval "$("$dotfiles_brew" shellenv)"
            break
        fi
    done
    unset dotfiles_brew
fi

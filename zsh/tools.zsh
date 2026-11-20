typeset -a dotfiles_plugin_roots
dotfiles_plugin_roots=(/usr/share)
if command -v brew >/dev/null 2>&1; then
    dotfiles_plugin_roots=("$(brew --prefix)/share" $dotfiles_plugin_roots)
fi
if (( ! $+functions[_zsh_autosuggest_start] )); then
    for dotfiles_plugin_root in $dotfiles_plugin_roots; do
        dotfiles_plugin="$dotfiles_plugin_root/zsh-autosuggestions/zsh-autosuggestions.zsh"
        if [[ -f "$dotfiles_plugin" ]]; then
            source "$dotfiles_plugin"
            break
        fi
    done
fi
# Highlighting loads last, after other hooks.
if (( ! $+functions[_zsh_highlight] )); then
    for dotfiles_plugin_root in $dotfiles_plugin_roots; do
        dotfiles_plugin="$dotfiles_plugin_root/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh"
        if [[ -f "$dotfiles_plugin" ]]; then
            source "$dotfiles_plugin"
            break
        fi
    done
fi
unset dotfiles_plugin_roots dotfiles_plugin_root dotfiles_plugin

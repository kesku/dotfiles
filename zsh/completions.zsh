# Oh My Zsh or the system may have initialized completion already.
if (( ! $+functions[compdef] )); then
    autoload -Uz compinit
    compinit
fi

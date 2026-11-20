if (Get-Variable -Name KeskuDotfilesLoaded -Scope Global -ValueOnly -ErrorAction SilentlyContinue) { return }
$global:KeskuDotfilesLoaded = $true
$env:STARSHIP_CONFIG = Join-Path $env:DOTFILES_ROOT 'starship/starship.toml'
$localEnv = Join-Path $env:DOTFILES_ROOT 'local/env.ps1'
if (Test-Path -LiteralPath $localEnv) { . $localEnv }
if ($env:DOTFILES_ENABLE_MISE -eq '1' -and -not $env:IN_NIX_SHELL) {
    $miseBin = Join-Path $env:DOTFILES_ROOT 'bin'
    if (Test-Path -LiteralPath (Join-Path $miseBin 'mise.exe')) {
        $env:Path = $miseBin + ';' + $env:Path
    }
    if (Get-Command mise -CommandType Application -ErrorAction SilentlyContinue) {
        Invoke-Expression (& mise activate pwsh --shims)
    }
}
if (Get-Command starship -CommandType Application -ErrorAction SilentlyContinue) {
    Invoke-Expression (& starship init powershell)
}
$localProfile = Join-Path $env:DOTFILES_ROOT 'local/profile.ps1'
if (Test-Path -LiteralPath $localProfile) { . $localProfile }

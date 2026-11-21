param([switch]$Check, [switch]$PolicyOnly)
$ErrorActionPreference = 'Stop'
$archive = Join-Path $PSScriptRoot 'garvnanda-anchor-ai-0.1.0-demo.1.tgz'
$digest = (Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.Substring(0,16)
$install = Join-Path $PSScriptRoot ".cache/showcase-$digest"
$cli = Join-Path $install 'node_modules/@garvnanda/anchor-ai/cli.mjs'
if (!(Test-Path -LiteralPath $cli)) {
    & npm.cmd install --prefix $install $archive --offline --no-audit --no-fund
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
$arguments = @('demo')
if (!$PolicyOnly) {
    if (!$env:ANCHOR_PYTHON) {
        $env:ANCHOR_PYTHON = Join-Path $PSScriptRoot '.cache/b7-verify/Scripts/python.exe'
    }
    if (!(Get-Command $env:ANCHOR_PYTHON -ErrorAction SilentlyContinue)) {
        throw 'Set ANCHOR_PYTHON to the prepared Qwen interpreter, or pass -PolicyOnly.'
    }
    $arguments += '--qwen'
}
if ($Check) { $arguments += '--check' }
& node $cli @arguments
exit $LASTEXITCODE

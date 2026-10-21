$ErrorActionPreference = 'Stop'
$kicadCli = 'C:/Program Files/KiCad/9.0/bin/kicad-cli.exe'
$boards = @('gf1002-reference', 'thomas-amplifier-carrier-reference')
$previews = @('preview', 'carrier-preview')
$zooms = @('0.5', '0.7')
for ($i = 0; $i -lt $boards.Count; $i++) {
    $boardPath = Join-Path $PSScriptRoot ($boards[$i] + '.kicad_pcb')
    & $kicadCli pcb export step --force --subst-models --user-origin '50x50mm' -o (Join-Path $PSScriptRoot ($boards[$i] + '.step')) $boardPath
    if ($LASTEXITCODE -ne 0) { throw 'STEP export failed' }
    & $kicadCli pcb render --width 1200 --height 850 --zoom $zooms[$i] --background opaque --rotate '325,0,335' -o (Join-Path $PSScriptRoot ($previews[$i] + '.png')) $boardPath
    if ($LASTEXITCODE -ne 0) { throw 'Top render failed' }
    & $kicadCli pcb render --width 1200 --height 850 --zoom $zooms[$i] --background opaque --side bottom --rotate '25,0,25' -o (Join-Path $PSScriptRoot ($previews[$i] + '-underside.png')) $boardPath
    if ($LASTEXITCODE -ne 0) { throw 'Underside render failed' }
}

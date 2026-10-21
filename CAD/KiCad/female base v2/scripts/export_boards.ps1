param([ValidateSet('female-base-v2','male-static-v2')][string]$Only)
$ErrorActionPreference = 'Stop'
$cadRoot = Split-Path (Split-Path $PSScriptRoot)
$kicadCli = 'C:/Program Files/KiCad/9.0/bin/kicad-cli.exe'
foreach ($entry in @(@('female base v2','female-base-v2'), @('male static v2','male-static-v2'))) {
    if ($Only -and $entry[1] -ne $Only) { continue }
    $folder = Join-Path $cadRoot $entry[0]
    $board = Join-Path $folder ($entry[1]+'.kicad_pcb')
    $schematic = Join-Path $folder ($entry[1]+'.kicad_sch')
    & $kicadCli sch erc --format json -o (Join-Path $folder 'reports/erc.json') $schematic
    if ($LASTEXITCODE -ne 0) { throw 'ERC failed' }
    & $kicadCli pcb drc --schematic-parity --format json -o (Join-Path $folder 'reports/drc.json') $board
    if ($LASTEXITCODE -ne 0) { throw 'DRC failed' }
    & $kicadCli pcb export step --force --subst-models --user-origin '25x20mm' -o (Join-Path $folder ($entry[1]+'.step')) $board
    if ($LASTEXITCODE -ne 0) { throw 'STEP export failed' }
    & $kicadCli pcb render --width 1300 --height 1000 --zoom .85 --background opaque --rotate '325,0,335' -o (Join-Path $folder 'preview.png') $board
    if ($LASTEXITCODE -ne 0) { throw 'Top render failed' }
    & $kicadCli pcb render --width 1300 --height 1000 --zoom .85 --background opaque --side bottom --rotate '25,0,25' -o (Join-Path $folder 'underside.png') $board
    if ($LASTEXITCODE -ne 0) { throw 'Underside render failed' }
    & $kicadCli sch export svg -o (Join-Path $folder 'reports/schematic/') $schematic
    if ($LASTEXITCODE -ne 0) { throw 'Schematic export failed' }
    & $kicadCli pcb export svg --layers 'F.Cu,F.Silkscreen,Edge.Cuts' -o (Join-Path $folder 'reports/assembly-front.svg') $board
    if ($LASTEXITCODE -ne 0) { throw 'Board export failed' }
}

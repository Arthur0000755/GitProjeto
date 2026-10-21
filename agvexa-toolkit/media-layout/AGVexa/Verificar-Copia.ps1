#Requires -Version 5.1
<#
.SYNOPSIS
    AG Vexa Toolkit - confere se a cópia do toolkit no HD está íntegra.

.DESCRIPTION
    Lê SHA256SUMS-AGVEXA.txt na raiz do HD e recalcula o SHA-256 de cada
    arquivo listado. Mostra AUSENTE ou FALHOU para cada problema e, no fim,
    "CÓPIA ÍNTEGRA" quando tudo confere.

    SOMENTE LEITURA: não altera, não apaga e não move nenhum arquivo.
    Normalmente é aberto pelo VERIFICAR-COPIA.cmd (duplo clique na raiz do HD).

.PARAMETER Raiz
    Pasta raiz da cópia (padrão: a pasta acima de AGVexa\).

.PARAMETER SemISOs
    Pula as imagens em ISO\ (conferência rápida dos demais arquivos).

.EXAMPLE
    powershell -NoProfile -ExecutionPolicy Bypass -File .\AGVexa\Verificar-Copia.ps1
#>
[CmdletBinding()]
param(
    [string]$Raiz = (Split-Path -Parent $PSScriptRoot),
    [switch]$SemISOs
)

Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'

Write-Host ''
Write-Host '  AG VEXA TOOLKIT - conferência da cópia' -ForegroundColor Cyan
Write-Host ('  Pasta: {0}' -f $Raiz) -ForegroundColor Gray
Write-Host ''

$lista = Join-Path $Raiz 'SHA256SUMS-AGVEXA.txt'
if (-not (Test-Path -LiteralPath $lista)) {
    Write-Host '  [ERRO] SHA256SUMS-AGVEXA.txt não encontrado nesta pasta.' -ForegroundColor Red
    Write-Host '         Execute a partir da raiz do HD do toolkit.' -ForegroundColor Red
    exit 2
}

$entradas = @()
foreach ($linha in [System.IO.File]::ReadAllLines($lista, [System.Text.Encoding]::UTF8)) {
    if (-not $linha.Trim()) { continue }
    $partes = $linha -split '  ', 2
    if ($partes.Count -ne 2 -or $partes[0] -notmatch '^[0-9a-fA-F]{64}$') {
        Write-Host ('  [AVISO] linha ignorada (formato inesperado): {0}' -f $linha) -ForegroundColor Yellow
        continue
    }
    if ($SemISOs -and $partes[1] -like 'ISO/*') { continue }
    $entradas += [pscustomobject]@{ Hash = $partes[0].ToLowerInvariant(); Nome = $partes[1] }
}

$total = $entradas.Count
$ok = 0; $ausentes = 0; $falhas = 0; $i = 0
foreach ($e in $entradas) {
    $i++
    Write-Progress -Activity 'Conferindo arquivos' -Status $e.Nome -PercentComplete ([int](100 * $i / [math]::Max(1, $total)))
    $caminho = Join-Path $Raiz ($e.Nome -replace '/', '\')
    if (-not (Test-Path -LiteralPath $caminho -PathType Leaf)) {
        Write-Host ('  [AUSENTE] {0}' -f $e.Nome) -ForegroundColor Red
        $ausentes++
        continue
    }
    $atual = (Get-FileHash -Algorithm SHA256 -LiteralPath $caminho).Hash.ToLowerInvariant()
    if ($atual -ne $e.Hash) {
        Write-Host ('  [FALHOU]  {0}' -f $e.Nome) -ForegroundColor Red
        $falhas++
    } else {
        $ok++
    }
}
Write-Progress -Activity 'Conferindo arquivos' -Completed

if (Test-Path -LiteralPath (Join-Path $Raiz '.agvexa-staging')) {
    Write-Host '  [AVISO] o arquivo .agvexa-staging ainda está na raiz: pode apagá-lo (é só um marcador).' -ForegroundColor Yellow
}

Write-Host ''
Write-Host ('  Conferidos: {0}   OK: {1}   Ausentes: {2}   Com diferença: {3}' -f $total, $ok, $ausentes, $falhas)
if ($SemISOs) { Write-Host '  (as ISOs foram puladas: rode sem -SemISOs para a conferência completa)' -ForegroundColor Gray }
Write-Host ''
if (($ausentes + $falhas) -eq 0) {
    Write-Host '  CÓPIA ÍNTEGRA' -ForegroundColor Green
    exit 0
}
Write-Host '  HÁ PROBLEMAS: copie de novo os arquivos listados e repita a conferência.' -ForegroundColor Red
exit 1

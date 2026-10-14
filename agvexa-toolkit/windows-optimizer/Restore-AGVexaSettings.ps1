#Requires -Version 5.1
<#
.SYNOPSIS
    AG Vexa Windows Optimizer - desfaz ajustes de uma sessão a partir do backup.

.DESCRIPTION
    Lê backup.json da sessão escolhida e restaura cada item, na ordem
    inversa da aplicação, verificando o resultado. Mostra o que será
    restaurado e pede confirmação. Aceita -WhatIf.

.PARAMETER Sessao
    Nome da sessão, caminho completo, ou 'ultima' (padrão): sessão mais
    recente que possui backup.

.PARAMETER Listar
    Apenas lista as sessões com backup disponíveis.

.PARAMETER Ajustes
    Restaura somente estes IDs (padrão: todos os itens do backup).

.EXAMPLE
    .\Restore-AGVexaSettings.ps1 -Listar
    .\Restore-AGVexaSettings.ps1 -Sessao ultima
    .\Restore-AGVexaSettings.ps1 -Sessao 20261014-153000-otimizacao-desempenho -WhatIf
#>
[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'High')]
param(
    [string]$Sessao = 'ultima',
    [switch]$Listar,
    [string[]]$Ajustes
)

Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'
if (-not (Get-Module -Name AGVexa.Common)) { Import-Module (Join-Path $PSScriptRoot 'lib\AGVexa.Common.psm1') -DisableNameChecking }

if (-not (Test-AGVexaWindows)) { Write-Error 'Este script deve ser executado no Windows.'; exit 3 }
Write-AGVexaHeader -Subtitle 'Desfazer alterações'

if ($Listar) {
    $found = 0
    foreach ($s in Get-AGVexaSessions) {
        $b = Join-Path $s.FullName 'backup.json'
        if (-not (Test-Path -LiteralPath $b)) { continue }
        $data = Read-AGVexaJson -Path $b
        $n = @($data.itens).Count
        $restored = Test-Path -LiteralPath (Join-Path $s.FullName 'reversao.json')
        Write-Host ("  {0}  ({1} item(ns){2})" -f $s.Name, $n, $(if ($restored) { ', já revertida' } else { '' }))
        $found++
    }
    if (-not $found) { Write-AGVexaStatus -Level 'INFO' -Message 'Nenhuma sessão com backup.' }
    return
}

try { $path = Resolve-AGVexaSessionPath -Session $Sessao }
catch { Write-AGVexaStatus -Level 'ERRO' -Message $_.Exception.Message; exit 1 }

$backupFile = Join-Path $path 'backup.json'
if (-not (Test-Path -LiteralPath $backupFile)) {
    Write-AGVexaStatus -Level 'ERRO' -Message ("Sessão sem backup.json: {0}" -f $path); exit 1
}
$data = Read-AGVexaJson -Path $backupFile
$items = @($data.itens)
if ($Ajustes) { $items = @($items | Where-Object { $_.id -in $Ajustes }) }
if (-not $items.Count) { Write-AGVexaStatus -Level 'INFO' -Message 'Nada para restaurar.'; return }
[array]::Reverse($items)

$catalog = Get-AGVexaAdjustmentCatalog
$titles = @{}
foreach ($a in $catalog.ajustes) { $titles[$a.id] = $a.titulo }

Write-Host ("  Sessão: {0}" -f (Split-Path -Leaf $path))
foreach ($it in $items) {
    $prev = $it.anterior
    if ($it.tipo -eq 'registro') { $prev = $(if ($it.anterior.existia) { $it.anterior.dado } else { '(valor ausente - será removido)' }) }
    Write-Host ("   - {0}: voltar para {1}" -f $titles[$it.id], $prev) -ForegroundColor Cyan
}

if (-not $WhatIfPreference) {
    if (-not (Read-AGVexaConfirmation -Prompt ("Restaurar {0} item(ns)?" -f $items.Count) -Word 'RESTAURAR')) {
        Write-AGVexaStatus -Level 'AVISO' -Message 'Cancelado. Nada foi alterado.'; return
    }
}

$session = New-AGVexaSession -Label 'reversao'
$results = New-Object System.Collections.Generic.List[object]
foreach ($it in $items) {
    $r = [ordered]@{ id = $it.id; titulo = $titles[$it.id]; resultado = $null; detalhe = '' }
    if ($PSCmdlet.ShouldProcess($titles[$it.id], 'Restaurar valor anterior')) {
        try {
            Restore-AGVexaAdjustment -Backup $it
            $r.resultado = 'RESTAURADO_E_VERIFICADO'
            Write-AGVexaStatus -Level 'OK' -Message $titles[$it.id]
        } catch {
            $r.resultado = 'FALHOU'; $r.detalhe = $_.Exception.Message
            Write-AGVexaStatus -Level 'ERRO' -Message ("{0}: {1}" -f $titles[$it.id], $_.Exception.Message)
        }
    } else { $r.resultado = 'WHATIF_NAO_RESTAURADO' }
    $results.Add([pscustomobject]$r)
}
$summary = [ordered]@{ sessaoOrigem = (Split-Path -Leaf $path); sessaoReversao = $session.Id
                       quando = (Get-Date).ToString('s'); resultados = $results.ToArray() }
Save-AGVexaJson -Object $summary -Path (Join-Path $session.Path 'reversao.json')
if (-not $WhatIfPreference) { Save-AGVexaJson -Object $summary -Path (Join-Path $path 'reversao.json') }

$failed = @($results | Where-Object { $_.resultado -eq 'FALHOU' }).Count
if ($failed) { Write-AGVexaStatus -Level 'AVISO' -Message ("{0} item(ns) não restaurados; veja {1}" -f $failed, $session.Log); exit 1 }
Write-AGVexaStatus -Level 'OK' -Message 'Reversão concluída. Alguns efeitos visuais podem exigir sair e entrar na sessão.'

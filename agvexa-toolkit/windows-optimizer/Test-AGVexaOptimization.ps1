#Requires -Version 5.1
<#
.SYNOPSIS
    AG Vexa Windows Optimizer - avaliação prévia dos ajustes (SOMENTE LEITURA).

.DESCRIPTION
    Para o perfil escolhido, mostra cada ajuste com: o que muda, benefício,
    riscos, se exige administrador, como reverter, valor atual, valor alvo e
    status (PROPOSTO, JA_APLICADO, NAO_APLICAVEL, RECOMENDACAO, ERRO).
    Nada é alterado. O plano é salvo em plano.json na sessão.

.PARAMETER Perfil
    Conservador (padrão), Desempenho ou Personalizado.

.PARAMETER Ajustes
    Para o perfil Personalizado: lista de IDs do catálogo (profiles\ajustes.json).

.PARAMETER Sessao
    Diretório de sessão existente. Se omitido, cria uma nova.

.PARAMETER Detalhado
    Exibe também "o que muda", riscos e reversão de cada item.

.EXAMPLE
    .\Test-AGVexaOptimization.ps1 -Perfil Desempenho -Detalhado

.EXAMPLE
    .\Test-AGVexaOptimization.ps1 -Perfil Personalizado -Ajustes visual.transparencia,visual.animacao-janelas
#>
[CmdletBinding()]
param(
    [ValidateSet('Conservador', 'Desempenho', 'Personalizado')][string]$Perfil = 'Conservador',
    [string[]]$Ajustes,
    [string]$Sessao,
    [switch]$Detalhado,
    [switch]$SemTela
)

Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'
if (-not (Get-Module -Name AGVexa.Common)) { Import-Module (Join-Path $PSScriptRoot 'lib\AGVexa.Common.psm1') -DisableNameChecking }

if (-not (Test-AGVexaWindows)) { Write-Error 'Este script deve ser executado no Windows.'; exit 3 }
if ($Perfil -eq 'Personalizado' -and -not $Ajustes) {
    Write-Error 'Perfil Personalizado exige -Ajustes com os IDs desejados (veja profiles\ajustes.json).'
    exit 64
}

if (-not $Sessao) { $Sessao = (New-AGVexaSession -Label ("avaliacao-{0}" -f $Perfil.ToLowerInvariant())).Path }
$catalog = Get-AGVexaAdjustmentCatalog
$selected = Get-AGVexaAdjustmentsForProfile -Perfil $Perfil -Ids $Ajustes -Catalog $catalog
$chassis = Get-AGVexaChassis
$isAdmin = Test-AGVexaAdmin

$plan = @(foreach ($a in $selected) {
    $st = Get-AGVexaAdjustmentState -Adjustment $a -Chassis $chassis -IsAdmin $isAdmin
    [pscustomobject][ordered]@{
        id = $a.id; titulo = $a.titulo; categoria = $a.categoria; tipo = $a.tipo
        requerAdmin = [bool]$a.requerAdmin; escopo = $a.escopo
        oQueMuda = $a.o_que_muda; beneficio = $a.beneficio; riscos = $a.riscos; reversao = $a.reversao
        referencia = $a.referencia; atual = $st.atual; alvo = $st.alvo; status = $st.status; motivo = $st.motivo
        acao = (Get-AGVexaField $a 'acao')
    }
})

$result = [ordered]@{
    perfil = $Perfil; equipamento = $chassis; administrador = $isAdmin
    avaliadoEm = (Get-Date).ToString('s'); itens = $plan
}
Save-AGVexaJson -Object $result -Path (Join-Path $Sessao 'plano.json')

if (-not $SemTela) {
    Write-AGVexaHeader -Subtitle ("Avaliação prévia - perfil {0} (nada será alterado)" -f $Perfil)
    Write-Host ("  Equipamento detectado: {0} | Administrador: {1}" -f $chassis, $isAdmin) -ForegroundColor Gray
    Write-Host ''
    $colors = @{ PROPOSTO = 'Cyan'; JA_APLICADO = 'Green'; NAO_APLICAVEL = 'DarkGray'; RECOMENDACAO = 'Yellow'; ERRO = 'Red' }
    $n = 0
    foreach ($p in $plan) {
        $n++
        Write-Host ("  {0,2}. [{1}] {2}" -f $n, $p.status, $p.titulo) -ForegroundColor $colors[$p.status]
        if ($p.status -in 'PROPOSTO', 'JA_APLICADO') {
            Write-Host ("      atual: {0}  ->  alvo: {1}" -f $p.atual, $p.alvo) -ForegroundColor Gray
        }
        if ($p.motivo) { Write-Host ("      {0}" -f $p.motivo) -ForegroundColor DarkGray }
        if ($Detalhado) {
            Write-Host ("      O que muda : {0}" -f $p.oQueMuda)
            Write-Host ("      Benefício  : {0}" -f $p.beneficio)
            Write-Host ("      Riscos     : {0}" -f $p.riscos) -ForegroundColor Yellow
            Write-Host ("      Admin      : {0}" -f $(if ($p.requerAdmin) { 'sim' } else { 'não' }))
            Write-Host ("      Reversão   : {0}" -f $p.reversao)
        }
    }
    $prop = @($plan | Where-Object { $_.status -eq 'PROPOSTO' }).Count
    Write-Host ''
    Write-AGVexaStatus -Level 'INFO' -Message ("{0} ajuste(s) proposto(s). Plano salvo em {1}" -f $prop, (Join-Path $Sessao 'plano.json'))
}

[pscustomobject]$result

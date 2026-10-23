#Requires -Version 5.1
<#
.SYNOPSIS
    AG Vexa Windows Optimizer - aplica ajustes APROVADOS, com backup e reversão.

.DESCRIPTION
    Sem -Aplicar, funciona só como simulação (equivale à avaliação prévia).
    Com -Aplicar, segue obrigatoriamente:
      1. verificar permissões            7. exibir alterações propostas
      2. verificar compatibilidade       8. pedir confirmação do técnico
      3. gerar diagnóstico inicial       9. aplicar só o que foi aprovado
      4. registrar configurações atuais 10. verificar cada resultado
      5. criar backup específico        11. gerar relatório
      6. tentar ponto de restauração    12. disponibilizar reversão
    Também aceita -WhatIf (nenhuma alteração; mostra o que seria feito).

    O script NUNCA desativa Defender, Firewall, Windows Update, UAC,
    BitLocker, paginação, restauração do sistema ou otimização de SSD, não
    remove aplicativos e não exclui arquivos. Itens do tipo "recomendação"
    nunca são aplicados automaticamente.

.PARAMETER Perfil
    Conservador (padrão), Desempenho ou Personalizado.

.PARAMETER Ajustes
    IDs do catálogo (obrigatório no Personalizado; nos demais, restringe o perfil).

.PARAMETER Aplicar
    Sem esta chave nada é alterado.

.PARAMETER SemPontoDeRestauracao
    Não tenta criar ponto de restauração (o backup específico continua sendo feito).

.EXAMPLE
    .\Invoke-AGVexaOptimization.ps1 -Perfil Conservador            # simulação
    .\Invoke-AGVexaOptimization.ps1 -Perfil Conservador -Aplicar   # aplica após confirmação
    .\Invoke-AGVexaOptimization.ps1 -Perfil Desempenho -Aplicar -WhatIf
#>
[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'High')]
param(
    [ValidateSet('Conservador', 'Desempenho', 'Personalizado')][string]$Perfil = 'Conservador',
    [string[]]$Ajustes,
    [switch]$Aplicar,
    [switch]$SemPontoDeRestauracao
)

Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'
if (-not (Get-Module -Name AGVexa.Common)) { Import-Module (Join-Path $PSScriptRoot 'lib\AGVexa.Common.psm1') -DisableNameChecking }

if (-not (Test-AGVexaWindows)) { Write-Error 'Este script deve ser executado no Windows.'; exit 3 }
if ($Perfil -eq 'Personalizado' -and -not $Ajustes) {
    Write-Error 'Perfil Personalizado exige -Ajustes.'; exit 64
}

$session = New-AGVexaSession -Label ("otimizacao-{0}" -f $Perfil.ToLowerInvariant())
Write-AGVexaHeader -Subtitle ("Otimização - perfil {0}{1}" -f $Perfil, $(if (-not $Aplicar) { ' [SIMULAÇÃO]' } elseif ($WhatIfPreference) { ' [WHATIF]' } else { '' }))

# 1. Permissões
$isAdmin = Test-AGVexaAdmin
Write-AGVexaStatus -Level 'PASSO' -Message ("1/12 Permissões: {0}" -f $(if ($isAdmin) { 'administrador' } else { 'usuário padrão (ajustes que exigem admin serão ignorados)' }))

# 2. Compatibilidade
$build = [Environment]::OSVersion.Version
if ($build.Major -lt 10) {
    Write-AGVexaStatus -Level 'ERRO' -Message 'Somente Windows 10 e 11 são suportados.'
    exit 3
}
Write-AGVexaStatus -Level 'PASSO' -Message ("2/12 Compatibilidade: Windows {0}.{1} build {2} | PowerShell {3}" -f $build.Major, $build.Minor, $build.Build, $PSVersionTable.PSVersion)

# 3. Diagnóstico inicial
Write-AGVexaStatus -Level 'PASSO' -Message '3/12 Diagnóstico inicial'
& (Join-Path $PSScriptRoot 'Get-AGVexaSystemInfo.ps1') -Sessao $session.Path -SemTela | Out-Null

# 4. Estado atual / plano
Write-AGVexaStatus -Level 'PASSO' -Message '4/12 Registrando configurações atuais'
$plan = & (Join-Path $PSScriptRoot 'Test-AGVexaOptimization.ps1') -Perfil $Perfil -Ajustes $Ajustes -Sessao $session.Path -SemTela
$catalog = Get-AGVexaAdjustmentCatalog
$byId = @{}
foreach ($a in $catalog.ajustes) { $byId[$a.id] = $a }
$todo = @($plan.itens | Where-Object { $_.status -eq 'PROPOSTO' })
$recs = @($plan.itens | Where-Object { $_.status -eq 'RECOMENDACAO' })

$execution = [ordered]@{ perfil = $Perfil; sessao = $session.Id; aplicar = [bool]$Aplicar; whatIf = [bool]$WhatIfPreference
                         pontoRestauracao = 'não tentado'; resultados = @() }

# 5. Backup específico: estado inicial de tudo o que pode mudar + registro
#    exato de cada item gravado imediatamente ANTES da respectiva alteração.
$backupPath = Join-Path $session.Path 'backup.json'
$backups = New-Object System.Collections.Generic.List[object]
$initialState = @($todo | ForEach-Object { [ordered]@{ id = $_.id; atual = $_.atual } })
$saveBackup = {
    param($record)
    $backups.Add($record)
    Save-AGVexaJson -Object ([ordered]@{ sessao = $session.Id; estadoInicial = $initialState; itens = $backups.ToArray() }) -Path $backupPath
}.GetNewClosure()
if ($Aplicar -and $todo.Count -and -not $WhatIfPreference) {
    Save-AGVexaJson -Object ([ordered]@{ sessao = $session.Id; estadoInicial = $initialState; itens = @() }) -Path $backupPath
    Write-AGVexaStatus -Level 'PASSO' -Message ("5/12 Backup específico preparado em {0}" -f $backupPath)
} else {
    Write-AGVexaStatus -Level 'PASSO' -Message '5/12 Backup: não necessário (nenhuma alteração será feita)'
}

# 6. Ponto de restauração (melhor esforço; não é a única garantia)
if (-not $Aplicar -or -not $todo.Count) {
    $execution.pontoRestauracao = 'não necessário'
} elseif ($SemPontoDeRestauracao) {
    $execution.pontoRestauracao = 'dispensado pelo técnico'
} elseif (-not $isAdmin) {
    $execution.pontoRestauracao = 'não criado: requer administrador'
} elseif ($WhatIfPreference) {
    $execution.pontoRestauracao = 'WhatIf: não criado'
} else {
    try {
        Checkpoint-Computer -Description ("AG Vexa Optimizer {0}" -f $session.Id) -RestorePointType 'MODIFY_SETTINGS'
        $execution.pontoRestauracao = 'solicitado ao Windows (que pode ignorar se já houver um recente)'
    } catch {
        $execution.pontoRestauracao = ("não criado: {0}. A Proteção do Sistema não foi alterada." -f $_.Exception.Message)
    }
}
Write-AGVexaStatus -Level 'PASSO' -Message ("6/12 Ponto de restauração: {0}" -f $execution.pontoRestauracao)

# 7. Exibir alterações propostas
Write-AGVexaStatus -Level 'PASSO' -Message '7/12 Alterações propostas'
if (-not $todo.Count) {
    Write-AGVexaStatus -Level 'OK' -Message 'Nenhuma alteração necessária (tudo já aplicado ou não aplicável).'
}
$i = 0
foreach ($t in $todo) {
    $i++
    Write-Host ("   {0}. {1}" -f $i, $t.titulo) -ForegroundColor Cyan
    Write-Host ("      {0}" -f $t.oQueMuda)
    Write-Host ("      Riscos: {0}" -f $t.riscos) -ForegroundColor Yellow
    Write-Host ("      Atual: {0} -> Alvo: {1} | Reversão: {2}" -f $t.atual, $t.alvo, $t.reversao) -ForegroundColor Gray
}
if ($recs.Count) {
    Write-Host ''
    Write-Host '   Recomendações para o técnico (não serão aplicadas automaticamente):' -ForegroundColor Yellow
    foreach ($r in $recs) { Write-Host ("    - {0}" -f $r.titulo) }
}

if (-not $Aplicar -or -not $todo.Count) {
    if (-not $Aplicar) { Write-AGVexaStatus -Level 'INFO' -Message 'Simulação concluída: nada foi alterado. Use -Aplicar para aplicar após revisar.' }
    Save-AGVexaJson -Object $execution -Path (Join-Path $session.Path 'execucao.json')
    & (Join-Path $PSScriptRoot 'New-AGVexaReport.ps1') -Sessao $session.Path -SemAbrir | Out-Null
    return
}

# 8. Confirmação explícita do técnico
Write-AGVexaStatus -Level 'PASSO' -Message '8/12 Confirmação'
if (-not $WhatIfPreference) {
    Write-Host ''
    if (-not (Read-AGVexaConfirmation -Prompt ("Aplicar os {0} ajuste(s) listados acima?" -f $todo.Count) -Word 'APLICAR')) {
        Write-AGVexaStatus -Level 'AVISO' -Message 'Cancelado pelo técnico. Nada foi alterado.'
        $execution.cancelado = $true
        Save-AGVexaJson -Object $execution -Path (Join-Path $session.Path 'execucao.json')
        return
    }
}

# 9 e 10. Aplicar e verificar
Write-AGVexaStatus -Level 'PASSO' -Message '9/12 Aplicando ajustes aprovados'
$results = New-Object System.Collections.Generic.List[object]
foreach ($t in $todo) {
    $adj = $byId[$t.id]
    $res = [ordered]@{ id = $t.id; titulo = $t.titulo; resultado = $null; detalhe = '' }
    if ($PSCmdlet.ShouldProcess($t.titulo, 'Aplicar ajuste')) {
        try {
            Invoke-AGVexaAdjustment -Adjustment $adj -SaveBackup $saveBackup
            $res.resultado = 'APLICADO_E_VERIFICADO'
            Write-AGVexaStatus -Level 'OK' -Message $t.titulo
        } catch {
            $res.resultado = 'FALHOU'
            $res.detalhe = $_.Exception.Message
            Write-AGVexaStatus -Level 'ERRO' -Message ("{0}: {1}" -f $t.titulo, $_.Exception.Message)
        }
    } else {
        $res.resultado = 'WHATIF_NAO_APLICADO'
    }
    $results.Add([pscustomobject]$res)
}
$execution.resultados = $results.ToArray()
Write-AGVexaStatus -Level 'PASSO' -Message '10/12 Verificação concluída'

# 11. Relatório
Save-AGVexaJson -Object $execution -Path (Join-Path $session.Path 'execucao.json')
& (Join-Path $PSScriptRoot 'New-AGVexaReport.ps1') -Sessao $session.Path -SemAbrir | Out-Null
Write-AGVexaStatus -Level 'PASSO' -Message ("11/12 Relatório em {0}" -f (Join-Path $session.Path 'relatorio.html'))

# 12. Reversão disponível
$failed = @($results | Where-Object { $_.resultado -eq 'FALHOU' }).Count
$applied = @($results | Where-Object { $_.resultado -eq 'APLICADO_E_VERIFICADO' }).Count
if ($applied) {
    Write-AGVexaStatus -Level 'PASSO' -Message ("12/12 Para desfazer: .\Restore-AGVexaSettings.ps1 -Sessao '{0}'" -f $session.Id)
} else {
    Write-AGVexaStatus -Level 'PASSO' -Message '12/12 Nada a desfazer: nenhum ajuste foi aplicado'
}
if ($failed) {
    Write-AGVexaStatus -Level 'AVISO' -Message ("{0} ajuste(s) falharam; veja o relatório. Nada foi declarado como sucesso sem verificação." -f $failed)
    exit 1
}

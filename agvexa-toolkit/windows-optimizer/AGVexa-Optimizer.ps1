#Requires -Version 5.1
<#
.SYNOPSIS
    AG Vexa Windows Optimizer - menu principal.

.DESCRIPTION
    Menu textual para preparação pós-formatação do Windows 10/11.
    Comportamento padrão: somente análise. Nenhuma alteração é feita sem
    a avaliação prévia, o backup e a confirmação explícita do técnico.

    Como iniciar (sem alterar a política de execução de forma permanente):
        powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\AGVexa-Optimizer.ps1

    O parâmetro -ExecutionPolicy Bypass vale apenas para este processo.

.PARAMETER Opcao
    Executa diretamente uma opção do menu (1 a 7) e sai. Útil em testes.
#>
[CmdletBinding()]
param(
    [ValidateRange(1, 8)][int]$Opcao
)

Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'
if (-not (Get-Module -Name AGVexa.Common)) { Import-Module (Join-Path $PSScriptRoot 'lib\AGVexa.Common.psm1') -DisableNameChecking }

if (-not (Test-AGVexaWindows)) { Write-Error 'Este script deve ser executado no Windows.'; exit 3 }

function Show-Menu {
    Clear-Host
    Write-AGVexaHeader
    $admin = Test-AGVexaAdmin
    Write-Host ('  Windows PowerShell {0} | Administrador: {1}' -f $PSVersionTable.PSVersion, $(if ($admin) { 'sim' } else { 'não' })) -ForegroundColor DarkGray
    Write-Host ''
    $items = @(
        @('1', 'Diagnóstico do computador', 'somente leitura'),
        @('2', 'Otimização conservadora', 'recomendada para clientes'),
        @('3', 'Otimização de desempenho', 'hardware limitado'),
        @('4', 'Personalizar ajustes', 'escolha item a item'),
        @('5', 'Programas de inicialização', 'revisão com o cliente'),
        @('6', 'Relatório técnico', 'HTML local'),
        @('7', 'Desfazer alterações', 'usa o backup da sessão'),
        @('8', 'Sair', '')
    )
    foreach ($i in $items) {
        Write-Host ('   {0} ' -f $i[0]) -ForegroundColor Cyan -NoNewline
        Write-Host ('— {0}' -f $i[1]) -ForegroundColor White -NoNewline
        if ($i[2]) { Write-Host ('  ({0})' -f $i[2]) -ForegroundColor DarkGray } else { Write-Host '' }
    }
    Write-Host ''
    if (-not $admin) {
        Write-Host '  Dica: sem administrador, itens como BitLocker, Secure Boot e TPM não são lidos.' -ForegroundColor DarkYellow
    }
}

function Wait-Key { Write-Host ''; [void](Read-Host '  Pressione ENTER para voltar ao menu') }

function Invoke-ProfileFlow([string]$perfil, [string[]]$ids) {
    # Sempre: avaliação prévia -> decisão -> aplicação com confirmação dentro do Invoke
    & (Join-Path $PSScriptRoot 'Test-AGVexaOptimization.ps1') -Perfil $perfil -Ajustes $ids -Detalhado | Out-Null
    Write-Host ''
    if (Read-AGVexaConfirmation -Prompt 'Deseja seguir para a aplicação (haverá backup e nova confirmação)?') {
        & (Join-Path $PSScriptRoot 'Invoke-AGVexaOptimization.ps1') -Perfil $perfil -Ajustes $ids -Aplicar
    } else {
        Write-AGVexaStatus -Level 'INFO' -Message 'Nada foi alterado.'
    }
}

function Select-CustomAdjustments {
    $catalog = Get-AGVexaAdjustmentCatalog
    $auto = @($catalog.ajustes | Where-Object { $_.tipo -ne 'recomendacao' })
    Write-Host ''
    Write-Host '  Ajustes disponíveis (recomendações não aparecem: são sempre manuais):' -ForegroundColor White
    for ($k = 0; $k -lt $auto.Count; $k++) {
        $a = $auto[$k]
        Write-Host ('   {0,2}. {1}' -f ($k + 1), $a.titulo) -ForegroundColor Cyan
        Write-Host ('       Muda: {0}' -f $a.o_que_muda)
        Write-Host ('       Benefício: {0}' -f $a.beneficio)
        Write-Host ('       Riscos: {0}' -f $a.riscos) -ForegroundColor Yellow
        Write-Host ('       Admin: {0} | Reversão: {1}' -f $(if ($a.requerAdmin) { 'sim' } else { 'não' }), $a.reversao) -ForegroundColor DarkGray
    }
    $answer = Read-Host '  Digite os números separados por vírgula (vazio cancela)'
    $ids = @()
    foreach ($part in ($answer -split '[,; ]+' | Where-Object { $_ })) {
        $n = 0
        if ([int]::TryParse($part, [ref]$n) -and $n -ge 1 -and $n -le $auto.Count) { $ids += $auto[$n - 1].id }
        else { Write-AGVexaStatus -Level 'AVISO' -Message ("Ignorado: {0}" -f $part) }
    }
    $ids | Select-Object -Unique
}

function Show-Startup {
    Write-AGVexaHeader -Subtitle 'Programas de inicialização (somente leitura)'
    $items = @(Get-AGVexaStartupItems)
    if (-not $items.Count) { Write-AGVexaStatus -Level 'INFO' -Message 'Nenhum item encontrado.'; return }
    $order = @{ 'Segurança - NÃO desabilitar' = 0; 'Driver/hardware - manter' = 1; 'Sincronização/backup - confirmar com o cliente' = 2; 'Revisar com o cliente' = 3; 'Opcional - candidato a desabilitar (com o cliente)' = 4 }
    foreach ($it in ($items | Sort-Object { $order[$_.Categoria] }, Nome)) {
        $color = switch -Wildcard ($it.Categoria) { 'Segurança*' { 'Green' } 'Driver*' { 'Green' } 'Opcional*' { 'Yellow' } default { 'Gray' } }
        Write-Host ('  - {0} [{1}]' -f $it.Nome, $it.Estado) -ForegroundColor White -NoNewline
        Write-Host ('  {0}' -f $it.Categoria) -ForegroundColor $color
        Write-Host ('      {0} | {1}' -f $it.Origem, $it.Comando) -ForegroundColor DarkGray
    }
    Write-Host ''
    Write-Host '  O script NÃO desabilita itens. Combine com o cliente e use:' -ForegroundColor Yellow
    Write-Host '    Gerenciador de Tarefas > Aplicativos de inicialização, ou Configurações > Aplicativos > Inicialização.'
    if (Read-AGVexaConfirmation -Prompt 'Abrir a tela de Inicialização das Configurações agora?') {
        Start-Process 'ms-settings:startupapps'
    }
}

function Invoke-Option([int]$choice) {
    switch ($choice) {
        1 { & (Join-Path $PSScriptRoot 'Get-AGVexaSystemInfo.ps1') | Out-Null }
        2 { Invoke-ProfileFlow 'Conservador' @() }
        3 {
            Write-Host '  Perfil Desempenho: inclui o Conservador e reduz efeitos visuais; energia conforme o tipo de equipamento.' -ForegroundColor Yellow
            Invoke-ProfileFlow 'Desempenho' @()
        }
        4 {
            $ids = @(Select-CustomAdjustments)
            if ($ids.Count) { Invoke-ProfileFlow 'Personalizado' $ids } else { Write-AGVexaStatus -Level 'INFO' -Message 'Nenhum ajuste escolhido.' }
        }
        5 { Show-Startup }
        6 {
            $os = Read-Host '  Número da ordem de serviço (opcional; letras, números, - e _)'
            if ($os -notmatch '^[A-Za-z0-9_-]*$') { Write-AGVexaStatus -Level 'AVISO' -Message 'Número inválido; ignorado.'; $os = '' }
            $tec = Read-Host '  Nome do técnico (opcional)'
            & (Join-Path $PSScriptRoot 'New-AGVexaReport.ps1') -OrdemServico $os -Tecnico $tec -Formato Ambos | Out-Null
        }
        7 {
            & (Join-Path $PSScriptRoot 'Restore-AGVexaSettings.ps1') -Listar
            $s = Read-Host "  Sessão a desfazer (ENTER = 'ultima')"
            if (-not $s) { $s = 'ultima' }
            & (Join-Path $PSScriptRoot 'Restore-AGVexaSettings.ps1') -Sessao $s
        }
    }
}

if ($Opcao) {
    if ($Opcao -ne 8) { Invoke-Option $Opcao }
    return
}

while ($true) {
    Show-Menu
    $raw = Read-Host '  Escolha uma opção [1-8]'
    $choice = 0
    if (-not [int]::TryParse($raw, [ref]$choice) -or $choice -lt 1 -or $choice -gt 8) {
        Write-AGVexaStatus -Level 'AVISO' -Message 'Opção inválida.'
        Start-Sleep -Seconds 1
        continue
    }
    if ($choice -eq 8) { break }
    try { Invoke-Option $choice }
    catch { Write-AGVexaStatus -Level 'ERRO' -Message $_.Exception.Message }
    Wait-Key
}
Write-Host '  Até logo. AG Vexa - Assistência Técnica.' -ForegroundColor DarkCyan

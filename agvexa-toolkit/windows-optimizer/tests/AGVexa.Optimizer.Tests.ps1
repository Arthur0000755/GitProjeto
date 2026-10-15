#Requires -Version 5.1
<#
.SYNOPSIS
    Testes Pester 5 do AG Vexa Windows Optimizer (unitários, com mocks).
.DESCRIPTION
    Não alteram o sistema: todas as leituras/gravações de SPI, registro e
    energia são simuladas com Mock. Requer Pester 5.x instalado na máquina
    de laboratório (o Windows traz Pester 3.4, que não é compatível):
        Invoke-Pester -Path .\tests\AGVexa.Optimizer.Tests.ps1 -Output Detailed
#>

BeforeAll {
    $root = Split-Path -Parent $PSScriptRoot
    Import-Module (Join-Path (Join-Path $root 'lib') 'AGVexa.Common.psm1') -Force -DisableNameChecking
    $script:catalog = Get-AGVexaAdjustmentCatalog
    function Get-Adj([string]$id) { $script:catalog.ajustes | Where-Object { $_.id -eq $id } }
}

Describe 'Catálogo e perfis' {
    It 'Personalizado sem IDs não retorna ajustes' {
        @(Get-AGVexaAdjustmentsForProfile -Perfil Personalizado).Count | Should -Be 0
    }
    It 'Personalizado rejeita ID desconhecido' {
        { Get-AGVexaAdjustmentsForProfile -Perfil Personalizado -Ids 'x.y' } | Should -Throw
    }
    It 'Conservador não inclui ajustes exclusivos de desempenho' {
        $ids = @(Get-AGVexaAdjustmentsForProfile -Perfil Conservador | ForEach-Object { $_.id })
        $ids | Should -Not -Contain 'visual.transparencia'
        $ids | Should -Not -Contain 'energia.alto-desempenho-desktop'
    }
    It 'Nenhum ajuste automático exige alterar segurança' {
        $script:catalog.ajustes | Where-Object { $_.tipo -eq 'registro' } | ForEach-Object {
            $_.chave | Should -Match '^HKCU:'
        }
    }
}

Describe 'Avaliação (Get-AGVexaAdjustmentState)' {
    It 'Recomendação nunca é proposta como alteração' {
        (Get-AGVexaAdjustmentState -Adjustment (Get-Adj 'inicializacao.revisar') -Chassis desktop -IsAdmin $false).status | Should -Be 'RECOMENDACAO'
    }
    It 'Marca JA_APLICADO quando valor atual = alvo (idempotência)' {
        Mock -ModuleName AGVexa.Common Get-AGVexaMinAnimate { 0 }
        (Get-AGVexaAdjustmentState -Adjustment (Get-Adj 'visual.animacao-janelas') -Chassis desktop -IsAdmin $false).status | Should -Be 'JA_APLICADO'
    }
    It 'Propõe quando valor atual difere do alvo' {
        Mock -ModuleName AGVexa.Common Get-AGVexaMinAnimate { 1 }
        (Get-AGVexaAdjustmentState -Adjustment (Get-Adj 'visual.animacao-janelas') -Chassis desktop -IsAdmin $false).status | Should -Be 'PROPOSTO'
    }
    It 'Plano de alto desempenho nunca é proposto em notebook' {
        Mock -ModuleName AGVexa.Common Get-AGVexaActivePowerScheme { '381b4222-f694-41f0-9685-ff5bb260df2e' }
        $r = Get-AGVexaAdjustmentState -Adjustment (Get-Adj 'energia.alto-desempenho-desktop') -Chassis notebook -IsAdmin $true
        $r.status | Should -Be 'NAO_APLICAVEL'
    }
    It 'Plano inexistente não é criado' {
        Mock -ModuleName AGVexa.Common Get-AGVexaActivePowerScheme { '381b4222-f694-41f0-9685-ff5bb260df2e' }
        Mock -ModuleName AGVexa.Common Get-AGVexaPowerSchemes { @([pscustomobject]@{ Guid = '381b4222-f694-41f0-9685-ff5bb260df2e'; Nome = 'Equilibrado' }) }
        (Get-AGVexaAdjustmentState -Adjustment (Get-Adj 'energia.alto-desempenho-desktop') -Chassis desktop -IsAdmin $true).status | Should -Be 'NAO_APLICAVEL'
    }
    It 'Erro de leitura vira status ERRO (não interrompe)' {
        Mock -ModuleName AGVexa.Common Get-AGVexaMinAnimate { throw 'falha simulada' }
        (Get-AGVexaAdjustmentState -Adjustment (Get-Adj 'visual.animacao-janelas') -Chassis desktop -IsAdmin $false).status | Should -Be 'ERRO'
    }
}

Describe 'Aplicação e reversão (Invoke/Restore-AGVexaAdjustment)' {
    BeforeEach {
        $script:state = 1
        $script:saved = @()
        Mock -ModuleName AGVexa.Common Get-AGVexaMinAnimate { $script:state }
        Mock -ModuleName AGVexa.Common Set-AGVexaMinAnimate { $script:state = $Value }
    }
    It 'Grava backup ANTES de alterar e verifica o resultado' {
        $save = { param($r) $script:saved += $r; if ($script:state -ne 1) { throw 'backup gravado tarde demais' } }
        Invoke-AGVexaAdjustment -Adjustment (Get-Adj 'visual.animacao-janelas') -SaveBackup $save
        $script:saved.Count | Should -Be 1
        $script:saved[0].anterior | Should -Be 1
        $script:state | Should -Be 0
    }
    It 'Falha de verificação gera exceção (não declara sucesso)' {
        Mock -ModuleName AGVexa.Common Set-AGVexaMinAnimate { }   # finge aplicar mas não muda
        { Invoke-AGVexaAdjustment -Adjustment (Get-Adj 'visual.animacao-janelas') -SaveBackup { param($r) } } | Should -Throw
    }
    It 'Reversão devolve o valor anterior' {
        $script:state = 0
        Restore-AGVexaAdjustment -Backup ([pscustomobject]@{ tipo = 'spi-animacao'; anterior = 1 })
        $script:state | Should -Be 1
    }
    It 'Tipo recomendação não pode ser aplicado' {
        { Invoke-AGVexaAdjustment -Adjustment (Get-Adj 'armazenamento.limpeza') -SaveBackup { param($r) } } | Should -Throw
    }
}

Describe 'Privacidade' {
    It 'Mascara caminhos de perfil de usuário' {
        ConvertTo-AGVexaPrivatePath 'C:\Users\Fulano\AppData\Local\app.exe' | Should -Not -Match 'Fulano'
    }
    It 'Classifica antivírus como item a não desabilitar' {
        Get-AGVexaStartupCategory -Name 'AvastUI' -Command 'x' | Should -BeLike 'Segurança*'
    }
}

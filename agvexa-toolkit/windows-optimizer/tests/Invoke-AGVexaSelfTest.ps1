#Requires -Version 5.1
<#
.SYNOPSIS
    Autoteste do AG Vexa Windows Optimizer, sem módulos externos.

.DESCRIPTION
    Etapas (todas seguras):
      1. Sintaxe: analisa todos os .ps1/.psm1 com o parser oficial do PowerShell.
      2. Codificação: arquivos com acentos precisam de UTF-8 com BOM (Windows PowerShell 5.1).
      3. Catálogo: profiles\ajustes.json válido e sem alvos proibidos.
      4. Funções puras: classificação de inicialização, máscara de caminhos.
      5. Registro: ciclo backup -> alterar -> restaurar numa chave PRÓPRIA de teste
         (HKCU:\Software\AGVexa\SelfTest), removida ao final.
      6. Somente análise: diagnóstico e avaliação prévia dos três perfis.
      7. WhatIf: Invoke e Restore com -WhatIf não alteram nada.
      8. (Opcional, -CicloReal, SOMENTE EM VM DE LABORATÓRIO) aplica o perfil
         Desempenho com confirmação e depois reverte, comparando os valores.

    -SyntaxOnly executa apenas as etapas 1 a 3 (funciona também no Linux com pwsh).

.PARAMETER SyntaxOnly
    Somente sintaxe, codificação e catálogo.

.PARAMETER CicloReal
    Executa o ciclo aplicar/reverter real. Use apenas em máquina de teste.
#>
[CmdletBinding()]
param([switch]$SyntaxOnly, [switch]$CicloReal)

Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$script:pass = 0; $script:fail = 0; $script:skip = 0

function Check([string]$name, [scriptblock]$test) {
    try {
        $ok = & $test
        if ($ok -eq $false) { throw 'condição falsa' }
        Write-Host ("  [PASSOU] {0}" -f $name) -ForegroundColor Green; $script:pass++
    } catch {
        Write-Host ("  [FALHOU] {0}: {1}" -f $name, $_.Exception.Message) -ForegroundColor Red; $script:fail++
    }
}
function Skip([string]$name, [string]$why) { Write-Host ("  [PULADO] {0}: {1}" -f $name, $why) -ForegroundColor Yellow; $script:skip++ }

Write-Host 'AG Vexa Windows Optimizer - autoteste' -ForegroundColor Cyan
Write-Host ("PowerShell {0} | {1}" -f $PSVersionTable.PSVersion, [Environment]::OSVersion.VersionString)

Write-Host "`n[1] Sintaxe"
$files = @(Get-ChildItem -LiteralPath $root -Recurse -Include *.ps1, *.psm1 -File)
foreach ($f in $files) {
    Check ("parse {0}" -f $f.Name) {
        $tokens = $null; $errors = $null
        [void][System.Management.Automation.Language.Parser]::ParseFile($f.FullName, [ref]$tokens, [ref]$errors)
        if ($errors.Count) { throw (($errors | ForEach-Object { '{0} (linha {1})' -f $_.Message, $_.Extent.StartLineNumber }) -join '; ') }
        $true
    }
}

Write-Host "`n[2] Codificação"
foreach ($f in $files) {
    Check ("UTF-8 com BOM quando há acentos: {0}" -f $f.Name) {
        $bytes = [System.IO.File]::ReadAllBytes($f.FullName)
        $hasBom = $bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF
        $nonAscii = @($bytes | Where-Object { $_ -gt 127 }).Count -gt 0
        (-not $nonAscii) -or $hasBom
    }
}

Write-Host "`n[3] Catálogo de ajustes"
$catalogPath = Join-Path (Join-Path $root 'profiles') 'ajustes.json'
$catalog = [System.IO.File]::ReadAllText($catalogPath, [System.Text.Encoding]::UTF8) | ConvertFrom-Json
Check 'schema' { $catalog.schema -eq 'agvexa-optimizer-ajustes/1' }
Check 'IDs únicos' { @($catalog.ajustes.id | Select-Object -Unique).Count -eq @($catalog.ajustes).Count }
Check 'campos obrigatórios' {
    foreach ($a in $catalog.ajustes) {
        foreach ($k in 'id', 'titulo', 'tipo', 'perfis', 'requerAdmin', 'o_que_muda', 'beneficio', 'riscos', 'reversao') {
            if (-not $a.PSObject.Properties[$k]) { throw ("{0} sem {1}" -f $a.id, $k) }
        }
    }
    $true
}
Check 'nenhuma chave de registro protegida' {
    foreach ($a in @($catalog.ajustes | Where-Object { $_.tipo -eq 'registro' })) {
        if ($a.chave -match '(?i)Defender|WindowsUpdate|Policies\\System|FVE|Firewall|Memory Management|SystemRestore') { throw $a.id }
        if ($a.chave -notmatch '^HKCU:') { throw ("{0}: somente HKCU é permitido nesta versão" -f $a.id) }
    }
    $true
}

if ($SyntaxOnly) {
    Write-Host ("`nResultado: {0} passou, {1} falhou, {2} pulado(s)" -f $script:pass, $script:fail, $script:skip)
    if ($script:fail) { exit 1 } else { exit 0 }
}

$isWindows = [System.Environment]::OSVersion.Platform -eq [System.PlatformID]::Win32NT
if (-not $isWindows) { Skip 'etapas 4 a 8' 'exigem Windows'; exit $(if ($script:fail) { 1 } else { 0 }) }

Import-Module (Join-Path (Join-Path $root 'lib') 'AGVexa.Common.psm1') -Force -DisableNameChecking

Write-Host "`n[4] Funções puras"
Check 'antivírus classificado como segurança' { (Get-AGVexaStartupCategory -Name 'SecurityHealth' -Command 'x') -like 'Segurança*' }
Check 'áudio classificado como driver' { (Get-AGVexaStartupCategory -Name 'RtkAudUService' -Command 'x') -like 'Driver*' }
Check 'OneDrive pede confirmação' { (Get-AGVexaStartupCategory -Name 'OneDrive' -Command 'x') -like 'Sincroniza*' }
Check 'máscara de perfil de usuário' { (ConvertTo-AGVexaPrivatePath 'C:\Users\Maria\AppData\x.exe') -notmatch 'Maria' }
Check 'perfil Personalizado exige IDs válidos' {
    try { Get-AGVexaAdjustmentsForProfile -Perfil Personalizado -Ids 'nao.existe' | Out-Null; $false } catch { $true }
}
Check 'Desempenho contém Conservador' {
    $c = @(Get-AGVexaAdjustmentsForProfile -Perfil Conservador | ForEach-Object { $_.id })
    $d = @(Get-AGVexaAdjustmentsForProfile -Perfil Desempenho | ForEach-Object { $_.id })
    -not @($c | Where-Object { $_ -notin $d }).Count
}

Write-Host "`n[5] Ciclo de registro em chave de teste"
$testKey = 'HKCU:\Software\AGVexa\SelfTest'
try {
    Check 'estado ausente -> alterar -> restaurar remove o valor' {
        $st = Get-AGVexaRegistryState -Key $testKey -Name 'Valor'
        if ($st.existia) { throw 'valor de teste já existia' }
        Set-AGVexaRegistryValue -Key $testKey -Name 'Valor' -Value 1 -Type DWord
        Restore-AGVexaRegistryState -State $st
        -not (Get-AGVexaRegistryState -Key $testKey -Name 'Valor').existia
    }
    Check 'estado existente -> alterar -> restaurar volta ao dado original' {
        Set-AGVexaRegistryValue -Key $testKey -Name 'Valor' -Value 7 -Type DWord
        $st = Get-AGVexaRegistryState -Key $testKey -Name 'Valor'
        Set-AGVexaRegistryValue -Key $testKey -Name 'Valor' -Value 0 -Type DWord
        $json = $st | ConvertTo-Json | ConvertFrom-Json   # simula backup em disco
        Restore-AGVexaRegistryState -State $json
        (Get-AGVexaRegistryState -Key $testKey -Name 'Valor').dado -eq 7
    }
} finally {
    if (Test-Path -LiteralPath $testKey) { Remove-Item -LiteralPath $testKey -Force }
    $parent = 'HKCU:\Software\AGVexa'
    if ((Test-Path -LiteralPath $parent) -and -not (Get-ChildItem -LiteralPath $parent) -and -not (Get-Item -LiteralPath $parent).GetValueNames()) {
        Remove-Item -LiteralPath $parent -Force
    }
}

Write-Host "`n[6] Somente análise"
$tmpRoot = Join-Path ([System.IO.Path]::GetTempPath()) ('agvexa-selftest-' + [guid]::NewGuid().ToString('N'))
$sess = New-AGVexaSession -Label 'autoteste' -Root $tmpRoot
Check 'diagnóstico gera diagnostico.json' {
    & (Join-Path $root 'Get-AGVexaSystemInfo.ps1') -Sessao $sess.Path -SemTela | Out-Null
    Test-Path -LiteralPath (Join-Path $sess.Path 'diagnostico.json')
}
Check 'diagnóstico não contém nome do computador nem do usuário' {
    $txt = [System.IO.File]::ReadAllText((Join-Path $sess.Path 'diagnostico.json'))
    ($txt -notmatch [regex]::Escape($env:COMPUTERNAME)) -and ($txt -notmatch [regex]::Escape($env:USERNAME))
}
$visualBefore = @{}
try { $visualBefore.min = Get-AGVexaMinAnimate; $visualBefore.client = Get-AGVexaSpiBool -Action 0x1042 } catch { }
foreach ($p in 'Conservador', 'Desempenho') {
    Check ("avaliação {0} não altera nada" -f $p) {
        $r = & (Join-Path $root 'Test-AGVexaOptimization.ps1') -Perfil $p -Sessao $sess.Path -SemTela
        @($r.itens).Count -gt 0
    }
}
Check 'avaliação manteve os valores visuais' {
    ((Get-AGVexaMinAnimate) -eq $visualBefore.min) -and ((Get-AGVexaSpiBool -Action 0x1042) -eq $visualBefore.client)
}
Check 'relatório HTML e Markdown' {
    $out = & (Join-Path $root 'New-AGVexaReport.ps1') -Sessao $sess.Path -Formato Ambos -SemAbrir
    @($out | Where-Object { Test-Path -LiteralPath $_ }).Count -eq 2
}

Write-Host "`n[7] WhatIf"
Check 'Invoke -Aplicar -WhatIf não altera valores' {
    & (Join-Path $root 'Invoke-AGVexaOptimization.ps1') -Perfil Desempenho -Aplicar -WhatIf -SemPontoDeRestauracao | Out-Null
    ((Get-AGVexaMinAnimate) -eq $visualBefore.min) -and ((Get-AGVexaSpiBool -Action 0x1042) -eq $visualBefore.client)
}
Check 'execução repetida da avaliação é estável' {
    $a = & (Join-Path $root 'Test-AGVexaOptimization.ps1') -Perfil Desempenho -Sessao $sess.Path -SemTela
    $b = & (Join-Path $root 'Test-AGVexaOptimization.ps1') -Perfil Desempenho -Sessao $sess.Path -SemTela
    (@($a.itens | ForEach-Object { $_.status }) -join ',') -eq (@($b.itens | ForEach-Object { $_.status }) -join ',')
}

if ($CicloReal) {
    Write-Host "`n[8] Ciclo real (VM de laboratório)" -ForegroundColor Yellow
    Write-Host '  Será pedida a confirmação APLICAR e depois RESTAURAR.' -ForegroundColor Yellow
    & (Join-Path $root 'Invoke-AGVexaOptimization.ps1') -Perfil Desempenho -Aplicar -SemPontoDeRestauracao
    Check 'segunda avaliação após aplicar mostra JA_APLICADO (idempotência)' {
        $r = & (Join-Path $root 'Test-AGVexaOptimization.ps1') -Perfil Desempenho -Sessao $sess.Path -SemTela
        -not @($r.itens | Where-Object { $_.status -eq 'PROPOSTO' }).Count
    }
    & (Join-Path $root 'Restore-AGVexaSettings.ps1') -Sessao ultima
    Check 'reversão devolveu os valores visuais originais' {
        ((Get-AGVexaMinAnimate) -eq $visualBefore.min) -and ((Get-AGVexaSpiBool -Action 0x1042) -eq $visualBefore.client)
    }
} else {
    Skip 'ciclo real aplicar/reverter' 'use -CicloReal somente em VM de laboratório'
}

if (Test-Path -LiteralPath $tmpRoot) { Remove-Item -LiteralPath $tmpRoot -Recurse -Force }
Write-Host ("`nResultado: {0} passou, {1} falhou, {2} pulado(s)" -f $script:pass, $script:fail, $script:skip)
if ($script:fail) { exit 1 }

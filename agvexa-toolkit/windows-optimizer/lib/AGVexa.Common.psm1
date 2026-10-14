#Requires -Version 5.1
<#
.SYNOPSIS
    Funções comuns do AG Vexa Windows Optimizer.
.DESCRIPTION
    Módulo interno: sessões, registro em log, confirmação, leitura do
    catálogo de ajustes, inventário do sistema e operações reversíveis
    (com backup específico antes de qualquer alteração).

    Compatível com Windows PowerShell 5.1 (Windows 10/11) e PowerShell 7.
    Não usa módulos externos, não acessa a internet e não envia dados.
#>

Set-StrictMode -Version 2.0

$script:AGVRoot = Split-Path -Parent $PSScriptRoot
$script:AGVVersion = '0.1.0-rc1'
$script:AGVProfiles = @('Conservador', 'Desempenho', 'Personalizado')

# ------------------------------------------------------------------ básicos

function Get-AGVexaVersion { $script:AGVVersion }

function Get-AGVexaDataRoot {
    <# Diretório local de sessões (no próprio computador, para permitir reversão). #>
    $base = $env:ProgramData
    if (-not $base) { $base = [System.IO.Path]::GetTempPath() }
    Join-Path (Join-Path $base 'AGVexa') 'Optimizer'
}

function Test-AGVexaWindows {
    [System.Environment]::OSVersion.Platform -eq [System.PlatformID]::Win32NT
}

function Test-AGVexaAdmin {
    if (-not (Test-AGVexaWindows)) { return $false }
    $id = [System.Security.Principal.WindowsIdentity]::GetCurrent()
    $p = New-Object System.Security.Principal.WindowsPrincipal($id)
    $p.IsInRole([System.Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Write-AGVexaHeader {
    param([string]$Subtitle = '')
    $line = ('=' * 62)
    Write-Host ''
    Write-Host $line -ForegroundColor DarkCyan
    Write-Host '  AG VEXA WINDOWS OPTIMIZER' -ForegroundColor Cyan -NoNewline
    Write-Host ("   v{0}" -f $script:AGVVersion) -ForegroundColor DarkGray
    Write-Host '  AG Vexa - Assistência Técnica' -ForegroundColor Gray
    if ($Subtitle) { Write-Host ("  {0}" -f $Subtitle) -ForegroundColor White }
    Write-Host $line -ForegroundColor DarkCyan
}

function Write-AGVexaStatus {
    param(
        [ValidateSet('OK', 'AVISO', 'ERRO', 'INFO', 'PASSO')][string]$Level,
        [string]$Message
    )
    $color = @{ OK = 'Green'; AVISO = 'Yellow'; ERRO = 'Red'; INFO = 'Gray'; PASSO = 'Cyan' }[$Level]
    Write-Host ("  [{0}] {1}" -f $Level, $Message) -ForegroundColor $color
    if ($script:AGVSession) { Write-AGVexaLog -Level $Level -Message $Message }
}

# ------------------------------------------------------------------ sessão

$script:AGVSession = $null

function New-AGVexaSession {
    <# Cria um diretório de sessão com carimbo de data/hora e passa a registrar o log nele. #>
    param([string]$Label = 'sessao', [string]$Root = (Get-AGVexaDataRoot))
    $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    $dir = Join-Path (Join-Path $Root 'sessoes') ("{0}-{1}" -f $stamp, $Label)
    New-Item -ItemType Directory -Path $dir -Force | Out-Null
    $script:AGVSession = [pscustomobject]@{
        Id        = Split-Path -Leaf $dir
        Path      = $dir
        Log       = Join-Path $dir 'log.txt'
        Started   = (Get-Date).ToString('s')
        IsAdmin   = (Test-AGVexaAdmin)
        Version   = $script:AGVVersion
    }
    Write-AGVexaLog -Level 'INFO' -Message ("Sessão {0} iniciada (admin={1})" -f $script:AGVSession.Id, $script:AGVSession.IsAdmin)
    $script:AGVSession
}

function Get-AGVexaSession { $script:AGVSession }

function Get-AGVexaSessions {
    param([string]$Root = (Get-AGVexaDataRoot))
    $dir = Join-Path $Root 'sessoes'
    if (-not (Test-Path -LiteralPath $dir)) { return @() }
    @(Get-ChildItem -LiteralPath $dir -Directory | Sort-Object Name -Descending)
}

function Resolve-AGVexaSessionPath {
    <# Aceita caminho completo, nome da sessão ou 'ultima' (sessão mais recente com backup). #>
    param([Parameter(Mandatory)][string]$Session, [string]$Root = (Get-AGVexaDataRoot))
    if (Test-Path -LiteralPath $Session -PathType Container) { return (Resolve-Path -LiteralPath $Session).Path }
    if ($Session -eq 'ultima') {
        foreach ($s in (Get-AGVexaSessions -Root $Root)) {
            if (Test-Path -LiteralPath (Join-Path $s.FullName 'backup.json')) { return $s.FullName }
        }
        throw 'Nenhuma sessão com backup encontrada.'
    }
    $candidate = Join-Path (Join-Path $Root 'sessoes') $Session
    if (Test-Path -LiteralPath $candidate -PathType Container) { return $candidate }
    throw ("Sessão não encontrada: {0}" -f $Session)
}

function Write-AGVexaLog {
    param([string]$Level = 'INFO', [string]$Message)
    if (-not $script:AGVSession) { return }
    $line = '{0} [{1}] {2}' -f (Get-Date -Format 's'), $Level, $Message
    Add-Content -LiteralPath $script:AGVSession.Log -Value $line -Encoding UTF8
}

function Save-AGVexaJson {
    param([Parameter(Mandatory)]$Object, [Parameter(Mandatory)][string]$Path)
    $json = $Object | ConvertTo-Json -Depth 8
    [System.IO.File]::WriteAllText($Path, $json, (New-Object System.Text.UTF8Encoding($true)))
}

function Read-AGVexaJson {
    param([Parameter(Mandatory)][string]$Path)
    $text = [System.IO.File]::ReadAllText($Path, [System.Text.Encoding]::UTF8)
    $text | ConvertFrom-Json
}

function Get-AGVexaField {
    <# Lê uma propriedade opcional sem erro sob Set-StrictMode. #>
    param($Object, [Parameter(Mandatory)][string]$Name, $Default = $null)
    if ($null -eq $Object) { return $Default }
    if ($Object -is [System.Collections.IDictionary]) {
        if ($Object.Contains($Name)) { return $Object[$Name] } else { return $Default }
    }
    $p = $Object.PSObject.Properties[$Name]
    if ($p) { $p.Value } else { $Default }
}

# ------------------------------------------------------------------ confirmação

function Read-AGVexaConfirmation {
    <#
    .SYNOPSIS
        Pede confirmação explícita. Padrão é NÃO. Com -Word, exige digitar a palavra.
    #>
    param([Parameter(Mandatory)][string]$Prompt, [string]$Word)
    if ($Word) {
        $answer = Read-Host ("  {0} Digite {1} para confirmar (qualquer outra coisa cancela)" -f $Prompt, $Word)
        return ($answer -ceq $Word)
    }
    $answer = Read-Host ("  {0} [s/N]" -f $Prompt)
    return ($answer -match '^(s|sim)$')
}

# ------------------------------------------------------------------ catálogo

function Get-AGVexaAdjustmentCatalog {
    param([string]$Path = (Join-Path (Join-Path $script:AGVRoot 'profiles') 'ajustes.json'))
    $data = Read-AGVexaJson -Path $Path
    if ($data.schema -ne 'agvexa-optimizer-ajustes/1') { throw 'Catálogo de ajustes com schema inesperado.' }
    $data
}

function Get-AGVexaAdjustmentsForProfile {
    param(
        [Parameter(Mandatory)][ValidateSet('Conservador', 'Desempenho', 'Personalizado')][string]$Perfil,
        [string[]]$Ids,
        $Catalog = (Get-AGVexaAdjustmentCatalog)
    )
    if ($Perfil -eq 'Personalizado') {
        if (-not $Ids) { return @() }
        $unknown = @($Ids | Where-Object { $_ -notin @($Catalog.ajustes | ForEach-Object { $_.id }) })
        if ($unknown.Count) { throw ("Ajuste(s) desconhecido(s): {0}" -f ($unknown -join ', ')) }
        return @($Catalog.ajustes | Where-Object { $_.id -in $Ids })
    }
    $list = @($Catalog.ajustes | Where-Object { $_.perfis -contains $Perfil })
    if ($Ids) { $list = @($list | Where-Object { $_.id -in $Ids }) }
    $list
}

# ------------------------------------------------------------------ SystemParametersInfo

function Initialize-AGVexaNative {
    if (-not (Test-AGVexaWindows)) { return $false }
    if (-not ('AGVexa.Native' -as [type])) {
        Add-Type -Language CSharp -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
namespace AGVexa {
    [StructLayout(LayoutKind.Sequential)]
    public struct ANIMATIONINFO { public uint cbSize; public int iMinAnimate; }
    public static class Native {
        public const uint SPIF_UPDATEINIFILE = 0x01;
        public const uint SPIF_SENDCHANGE = 0x02;
        [DllImport("user32.dll", EntryPoint = "SystemParametersInfoW", SetLastError = true)]
        public static extern bool SpiGetInt(uint action, uint param, ref int value, uint winIni);
        [DllImport("user32.dll", EntryPoint = "SystemParametersInfoW", SetLastError = true)]
        public static extern bool SpiSetPtr(uint action, uint param, IntPtr value, uint winIni);
        [DllImport("user32.dll", EntryPoint = "SystemParametersInfoW", SetLastError = true)]
        public static extern bool SpiAnim(uint action, uint param, ref ANIMATIONINFO value, uint winIni);
    }
}
'@
    }
    $true
}

function Get-AGVexaSpiBool {
    param([Parameter(Mandatory)][uint32]$Action)
    [void](Initialize-AGVexaNative)
    $v = 0
    if (-not [AGVexa.Native]::SpiGetInt($Action, 0, [ref]$v, 0)) { throw ("SystemParametersInfo 0x{0:X} falhou" -f $Action) }
    [bool]$v
}

function Set-AGVexaSpiBool {
    param([Parameter(Mandatory)][uint32]$Action, [Parameter(Mandatory)][bool]$Value)
    [void](Initialize-AGVexaNative)
    $flags = [AGVexa.Native]::SPIF_UPDATEINIFILE -bor [AGVexa.Native]::SPIF_SENDCHANGE
    $ptr = [IntPtr]([int]$Value)
    if (-not [AGVexa.Native]::SpiSetPtr($Action, 0, $ptr, $flags)) { throw ("SystemParametersInfo 0x{0:X} falhou" -f $Action) }
}

function Get-AGVexaMinAnimate {
    [void](Initialize-AGVexaNative)
    $ai = New-Object AGVexa.ANIMATIONINFO
    $ai.cbSize = 8
    if (-not [AGVexa.Native]::SpiAnim(0x0048, 8, [ref]$ai, 0)) { throw 'SPI_GETANIMATION falhou' }
    [int]$ai.iMinAnimate
}

function Set-AGVexaMinAnimate {
    param([Parameter(Mandatory)][int]$Value)
    [void](Initialize-AGVexaNative)
    $ai = New-Object AGVexa.ANIMATIONINFO
    $ai.cbSize = 8
    $ai.iMinAnimate = $Value
    $flags = [AGVexa.Native]::SPIF_UPDATEINIFILE -bor [AGVexa.Native]::SPIF_SENDCHANGE
    if (-not [AGVexa.Native]::SpiAnim(0x0049, 8, [ref]$ai, $flags)) { throw 'SPI_SETANIMATION falhou' }
}

# ------------------------------------------------------------------ registro

function Get-AGVexaRegistryState {
    <# Retorna o estado exato de um valor (existência, tipo e dado) para backup. #>
    param([Parameter(Mandatory)][string]$Key, [Parameter(Mandatory)][string]$Name)
    $state = [ordered]@{ chave = $Key; valor = $Name; existia = $false; tipo = $null; dado = $null }
    if (Test-Path -LiteralPath $Key) {
        $item = Get-Item -LiteralPath $Key
        if ($item.GetValueNames() -contains $Name) {
            $state.existia = $true
            $state.tipo = $item.GetValueKind($Name).ToString()
            $state.dado = $item.GetValue($Name, $null, 'DoNotExpandEnvironmentNames')
        }
    }
    [pscustomobject]$state
}

function Set-AGVexaRegistryValue {
    param([Parameter(Mandatory)][string]$Key, [Parameter(Mandatory)][string]$Name,
          [Parameter(Mandatory)]$Value, [string]$Type = 'DWord')
    if (-not (Test-Path -LiteralPath $Key)) { New-Item -Path $Key -Force | Out-Null }
    New-ItemProperty -LiteralPath $Key -Name $Name -Value $Value -PropertyType $Type -Force | Out-Null
}

function Restore-AGVexaRegistryState {
    param([Parameter(Mandatory)]$State)
    if ($State.existia) {
        Set-AGVexaRegistryValue -Key $State.chave -Name $State.valor -Value $State.dado -Type $State.tipo
    } elseif (Test-Path -LiteralPath $State.chave) {
        Remove-ItemProperty -LiteralPath $State.chave -Name $State.valor -ErrorAction SilentlyContinue
    }
}

# ------------------------------------------------------------------ energia

function Get-AGVexaActivePowerScheme {
    $out = & powercfg.exe /getactivescheme 2>$null
    $m = [regex]::Match(($out -join ' '), '[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}')
    if ($m.Success) { $m.Value.ToLowerInvariant() } else { $null }
}

function Get-AGVexaPowerSchemes {
    $out = & powercfg.exe /list 2>$null
    @($out | ForEach-Object {
        $m = [regex]::Match($_, '([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})\s+\((.+?)\)')
        if ($m.Success) { [pscustomobject]@{ Guid = $m.Groups[1].Value.ToLowerInvariant(); Nome = $m.Groups[2].Value } }
    })
}

function Set-AGVexaPowerScheme {
    param([Parameter(Mandatory)][ValidatePattern('^[0-9a-f-]{36}$')][string]$Guid)
    & powercfg.exe /setactive $Guid
    if ($LASTEXITCODE -ne 0) { throw ("powercfg /setactive {0} retornou {1}" -f $Guid, $LASTEXITCODE) }
}

# ------------------------------------------------------------------ inventário

function Get-AGVexaChassis {
    <# Classifica o equipamento em notebook / desktop / desconhecido, sem dados pessoais. #>
    $mobileChassis = @(8, 9, 10, 11, 12, 14, 18, 21, 30, 31, 32)
    $desktopChassis = @(3, 4, 5, 6, 7, 13, 15, 16, 24, 35, 36)
    $result = 'desconhecido'
    try {
        $cs = Get-CimInstance -ClassName Win32_ComputerSystem -ErrorAction Stop
        if ($cs.PCSystemType -eq 2) { return 'notebook' }
        $enc = Get-CimInstance -ClassName Win32_SystemEnclosure -ErrorAction Stop
        $types = @($enc | ForEach-Object { $_.ChassisTypes } | Where-Object { $_ })
        if ($types | Where-Object { $_ -in $mobileChassis }) { return 'notebook' }
        $bat = @(Get-CimInstance -ClassName Win32_Battery -ErrorAction SilentlyContinue)
        if ($bat.Count -gt 0) { return 'notebook' }
        if ($types | Where-Object { $_ -in $desktopChassis }) { $result = 'desktop' }
        elseif ($cs.PCSystemType -in 1, 3) { $result = 'desktop' }
    } catch {
        $result = 'desconhecido'
    }
    $result
}

function ConvertTo-AGVexaPrivatePath {
    <# Mascara o caminho do perfil do usuário para não registrar nomes de pessoas. #>
    param([string]$Text)
    if (-not $Text) { return $Text }
    $out = $Text
    foreach ($pair in @(@($env:USERPROFILE, '%USERPROFILE%'), @($env:LOCALAPPDATA, '%LOCALAPPDATA%'), @($env:APPDATA, '%APPDATA%'))) {
        if ($pair[0]) { $out = $out -replace [regex]::Escape($pair[0]), $pair[1] }
    }
    $out -replace '(?i)C:\\Users\\[^\\]+', 'C:\Users\<usuario>'
}

function Get-AGVexaStartupCategory {
    <# Classificação heurística: só orienta a conversa com o cliente; nunca decide sozinha. #>
    param([string]$Name, [string]$Command)
    $t = ('{0} {1}' -f $Name, $Command).ToLowerInvariant()
    if ($t -match 'securityhealth|defender|windows security|avast|avg|kaspersky|eset|norton|mcafee|bitdefender|avira|sophos|malwarebytes|trend ?micro|panda|webroot') { return 'Segurança - NÃO desabilitar' }
    if ($t -match 'realtek|rtkaud|rthdvcpl|synaptics|elan|alps|nvidia|nvcpl|amd|radeon|igfx|intel|conexant|dolby|waves|maxx|smartaudio|hotkey|fnkey|touchpad|bluetooth|wacom') { return 'Driver/hardware - manter' }
    if ($t -match 'onedrive|dropbox|googledrive|google drive|icloud|megasync|backup') { return 'Sincronização/backup - confirmar com o cliente' }
    if ($t -match 'teams|skype|discord|spotify|steam|epic|zoom|whatsapp|telegram|adobe|acrobat|update|updater|java|ccleaner|utorrent') { return 'Opcional - candidato a desabilitar (com o cliente)' }
    'Revisar com o cliente'
}

function Get-AGVexaStartupItems {
    $items = New-Object System.Collections.Generic.List[object]
    $runKeys = @(
        @{ Key = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run'; Escopo = 'Usuário'; Approved = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run' },
        @{ Key = 'HKLM:\Software\Microsoft\Windows\CurrentVersion\Run'; Escopo = 'Computador'; Approved = 'HKLM:\Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run' },
        @{ Key = 'HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Run'; Escopo = 'Computador (32 bits)'; Approved = 'HKLM:\Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run32' }
    )
    foreach ($rk in $runKeys) {
        if (-not (Test-Path -LiteralPath $rk.Key)) { continue }
        $key = Get-Item -LiteralPath $rk.Key
        foreach ($n in $key.GetValueNames()) {
            if (-not $n) { continue }
            $cmd = [string]$key.GetValue($n, $null, 'DoNotExpandEnvironmentNames')
            $items.Add([pscustomobject]@{
                Nome = $n; Origem = 'Registro (Run)'; Escopo = $rk.Escopo
                Comando = (ConvertTo-AGVexaPrivatePath $cmd)
                Estado = (Get-AGVexaStartupApprovedState -Key $rk.Approved -Name $n)
                Categoria = (Get-AGVexaStartupCategory -Name $n -Command $cmd)
            })
        }
    }
    $folders = @(
        @{ Path = [Environment]::GetFolderPath('Startup'); Escopo = 'Usuário'; Approved = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\StartupFolder' },
        @{ Path = [Environment]::GetFolderPath('CommonStartup'); Escopo = 'Computador'; Approved = 'HKLM:\Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\StartupFolder' }
    )
    foreach ($f in $folders) {
        if (-not $f.Path -or -not (Test-Path -LiteralPath $f.Path)) { continue }
        foreach ($file in Get-ChildItem -LiteralPath $f.Path -File -ErrorAction SilentlyContinue) {
            if ($file.Name -eq 'desktop.ini') { continue }
            $items.Add([pscustomobject]@{
                Nome = $file.BaseName; Origem = 'Pasta Inicializar'; Escopo = $f.Escopo
                Comando = (ConvertTo-AGVexaPrivatePath $file.FullName)
                Estado = (Get-AGVexaStartupApprovedState -Key $f.Approved -Name $file.Name)
                Categoria = (Get-AGVexaStartupCategory -Name $file.BaseName -Command $file.Name)
            })
        }
    }
    $items.ToArray()
}

function Get-AGVexaStartupApprovedState {
    <# Somente leitura do estado mostrado pelo Gerenciador de Tarefas. O script não grava aqui. #>
    param([string]$Key, [string]$Name)
    try {
        if (-not (Test-Path -LiteralPath $Key)) { return 'Habilitado' }
        $k = Get-Item -LiteralPath $Key
        if ($k.GetValueNames() -notcontains $Name) { return 'Habilitado' }
        $bytes = [byte[]]$k.GetValue($Name)
        if ($bytes -and $bytes.Length -gt 0 -and ($bytes[0] -band 1)) { return 'Desabilitado' }
        'Habilitado'
    } catch { 'Desconhecido' }
}

function Invoke-AGVexaSafely {
    <# Executa um bloco de coleta; em caso de erro devolve objeto com a mensagem (não interrompe o diagnóstico). #>
    param([Parameter(Mandatory)][scriptblock]$Script, [string]$What)
    try { & $Script }
    catch {
        Write-AGVexaLog -Level 'AVISO' -Message ("Falha ao coletar {0}: {1}" -f $What, $_.Exception.Message)
        [pscustomobject]@{ Indisponivel = $true; Motivo = $_.Exception.Message }
    }
}

# ------------------------------------------------------------------ motor de ajustes

function Get-AGVexaAdjustmentState {
    <#
    .SYNOPSIS
        Avalia um ajuste SEM alterar nada. Retorna estado atual, alvo e se é aplicável.
    .OUTPUTS
        Status: PROPOSTO | JA_APLICADO | NAO_APLICAVEL | RECOMENDACAO | ERRO
    #>
    param([Parameter(Mandatory)]$Adjustment, [string]$Chassis = (Get-AGVexaChassis), [bool]$IsAdmin = (Test-AGVexaAdmin))
    $r = [ordered]@{
        id = $Adjustment.id; titulo = $Adjustment.titulo; tipo = $Adjustment.tipo
        requerAdmin = [bool]$Adjustment.requerAdmin; atual = $null; alvo = (Get-AGVexaField $Adjustment 'valorAlvo')
        status = 'PROPOSTO'; motivo = ''
    }
    try {
        switch ($Adjustment.tipo) {
            'recomendacao' { $r.status = 'RECOMENDACAO'; $r.motivo = 'Orientação manual; nada é alterado.' }
            'spi-animacao' { $r.atual = Get-AGVexaMinAnimate }
            'spi-bool' { $r.atual = Get-AGVexaSpiBool -Action ([uint32]$Adjustment.spiGet) }
            'registro' {
                $st = Get-AGVexaRegistryState -Key $Adjustment.chave -Name $Adjustment.valor
                $r.atual = if ($st.existia) { $st.dado } else { '(ausente = padrão do Windows)' }
            }
            'plano-energia' {
                $cond = Get-AGVexaField $Adjustment 'condicao'
                $r.atual = Get-AGVexaActivePowerScheme
                if ($cond -and $cond -ne $Chassis) {
                    $r.status = 'NAO_APLICAVEL'; $r.motivo = ("Somente para {0}; equipamento detectado: {1}." -f $cond, $Chassis)
                } elseif (-not (@(Get-AGVexaPowerSchemes) | Where-Object { $_.Guid -eq $Adjustment.planoGuid })) {
                    $r.status = 'NAO_APLICAVEL'; $r.motivo = 'Plano não existe neste Windows (ex.: Modern Standby). Nada será criado.'
                }
            }
            default { $r.status = 'ERRO'; $r.motivo = ("Tipo de ajuste desconhecido: {0}" -f $Adjustment.tipo) }
        }
        if ($r.status -eq 'PROPOSTO') {
            if ([string]$r.atual -eq [string]$r.alvo) { $r.status = 'JA_APLICADO'; $r.motivo = 'Valor atual já é o desejado (idempotente).' }
            elseif ($r.requerAdmin -and -not $IsAdmin) { $r.status = 'NAO_APLICAVEL'; $r.motivo = 'Requer PowerShell como administrador.' }
        }
    } catch {
        $r.status = 'ERRO'; $r.motivo = $_.Exception.Message
    }
    [pscustomobject]$r
}

function Invoke-AGVexaAdjustment {
    <#
    .SYNOPSIS
        Aplica UM ajuste aprovado. Antes de alterar, devolve/grava o registro de backup.
        Lança exceção em caso de falha (nunca declara sucesso sem verificar).
    #>
    param([Parameter(Mandatory)]$Adjustment, [Parameter(Mandatory)][scriptblock]$SaveBackup)
    $backup = [ordered]@{ id = $Adjustment.id; tipo = $Adjustment.tipo; quando = (Get-Date).ToString('s'); anterior = $null }
    switch ($Adjustment.tipo) {
        'spi-animacao' {
            $backup.anterior = Get-AGVexaMinAnimate
            & $SaveBackup ([pscustomobject]$backup)
            Set-AGVexaMinAnimate -Value ([int]$Adjustment.valorAlvo)
            if ((Get-AGVexaMinAnimate) -ne [int]$Adjustment.valorAlvo) { throw 'Verificação pós-ajuste falhou.' }
        }
        'spi-bool' {
            $backup.anterior = Get-AGVexaSpiBool -Action ([uint32]$Adjustment.spiGet)
            $backup.spiSet = [uint32]$Adjustment.spiSet
            $backup.spiGet = [uint32]$Adjustment.spiGet
            & $SaveBackup ([pscustomobject]$backup)
            Set-AGVexaSpiBool -Action ([uint32]$Adjustment.spiSet) -Value ([bool]$Adjustment.valorAlvo)
            if ((Get-AGVexaSpiBool -Action ([uint32]$Adjustment.spiGet)) -ne [bool]$Adjustment.valorAlvo) { throw 'Verificação pós-ajuste falhou.' }
        }
        'registro' {
            $backup.anterior = Get-AGVexaRegistryState -Key $Adjustment.chave -Name $Adjustment.valor
            & $SaveBackup ([pscustomobject]$backup)
            Set-AGVexaRegistryValue -Key $Adjustment.chave -Name $Adjustment.valor -Value $Adjustment.valorAlvo -Type $Adjustment.tipoValor
            $after = Get-AGVexaRegistryState -Key $Adjustment.chave -Name $Adjustment.valor
            if (-not $after.existia -or [string]$after.dado -ne [string]$Adjustment.valorAlvo) { throw 'Verificação pós-ajuste falhou.' }
        }
        'plano-energia' {
            $backup.anterior = Get-AGVexaActivePowerScheme
            if (-not $backup.anterior) { throw 'Não foi possível ler o plano de energia atual; nada alterado.' }
            & $SaveBackup ([pscustomobject]$backup)
            Set-AGVexaPowerScheme -Guid $Adjustment.planoGuid
            if ((Get-AGVexaActivePowerScheme) -ne $Adjustment.planoGuid) { throw 'Verificação pós-ajuste falhou.' }
        }
        default { throw ("Tipo não aplicável automaticamente: {0}" -f $Adjustment.tipo) }
    }
}

function Restore-AGVexaAdjustment {
    <# Restaura um registro de backup e verifica o resultado. #>
    param([Parameter(Mandatory)]$Backup)
    switch ($Backup.tipo) {
        'spi-animacao' {
            Set-AGVexaMinAnimate -Value ([int]$Backup.anterior)
            if ((Get-AGVexaMinAnimate) -ne [int]$Backup.anterior) { throw 'Verificação da reversão falhou.' }
        }
        'spi-bool' {
            Set-AGVexaSpiBool -Action ([uint32]$Backup.spiSet) -Value ([bool]$Backup.anterior)
            if ((Get-AGVexaSpiBool -Action ([uint32]$Backup.spiGet)) -ne [bool]$Backup.anterior) { throw 'Verificação da reversão falhou.' }
        }
        'registro' {
            Restore-AGVexaRegistryState -State $Backup.anterior
            $now = Get-AGVexaRegistryState -Key $Backup.anterior.chave -Name $Backup.anterior.valor
            if ([bool]$now.existia -ne [bool]$Backup.anterior.existia) { throw 'Verificação da reversão falhou.' }
        }
        'plano-energia' {
            Set-AGVexaPowerScheme -Guid $Backup.anterior
            if ((Get-AGVexaActivePowerScheme) -ne $Backup.anterior) { throw 'Verificação da reversão falhou.' }
        }
        default { throw ("Tipo de backup desconhecido: {0}" -f $Backup.tipo) }
    }
}

Export-ModuleMember -Function *-AGVexa*

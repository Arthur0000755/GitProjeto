#Requires -Version 5.1
<#
.SYNOPSIS
    AG Vexa Windows Optimizer - diagnóstico do computador (SOMENTE LEITURA).

.DESCRIPTION
    Coleta informações técnicas para o atendimento, sem alterar nada:
    versão/edição do Windows, processador, memória, armazenamento,
    ativação (via WMI/CIM SoftwareLicensingProduct), segurança (Defender,
    antivírus registrado, firewall, UAC, Secure Boot, BitLocker, TPM),
    energia, programas de inicialização e itens para análise manual.

    Privacidade: por padrão NÃO registra nome do computador, nome de usuário,
    número de série nem chave do produto. Caminhos do perfil do usuário são
    mascarados. Use -IncluirIdentificadores apenas se o cliente autorizar.

    Algumas informações (BitLocker, Secure Boot, TPM, TRIM) exigem
    administrador; sem privilégio, aparecem como "indisponível".

.PARAMETER Sessao
    Diretório da sessão onde salvar diagnostico.json. Se omitido, cria uma sessão nova.

.PARAMETER IncluirIdentificadores
    Inclui nome do computador e número de série (somente com autorização do cliente).

.PARAMETER SemTela
    Não imprime o resumo na tela (uso interno pelos outros scripts).

.EXAMPLE
    powershell -NoProfile -ExecutionPolicy Bypass -File .\Get-AGVexaSystemInfo.ps1

.NOTES
    Compatível com Windows PowerShell 5.1 e PowerShell 7 no Windows 10/11.
#>
[CmdletBinding()]
param(
    [string]$Sessao,
    [switch]$IncluirIdentificadores,
    [switch]$SemTela
)

Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'
if (-not (Get-Module -Name AGVexa.Common)) { Import-Module (Join-Path $PSScriptRoot 'lib\AGVexa.Common.psm1') -DisableNameChecking }

if (-not (Test-AGVexaWindows)) {
    Write-Error 'Este script deve ser executado no Windows.'
    exit 3
}

if ($Sessao) {
    $session = [pscustomobject]@{ Path = $Sessao }
} else {
    $session = New-AGVexaSession -Label 'diagnostico'
}
$isAdmin = Test-AGVexaAdmin

$info = [ordered]@{
    ferramenta  = 'AG Vexa Windows Optimizer'
    versao      = Get-AGVexaVersion
    coletadoEm  = (Get-Date).ToString('s')
    administrador = $isAdmin
}

$info.sistema = Invoke-AGVexaSafely -What 'sistema' -Script {
    $os = Get-CimInstance -ClassName Win32_OperatingSystem
    $cv = Get-ItemProperty -LiteralPath 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion'
    [ordered]@{
        nome          = $os.Caption
        edicao        = (Get-AGVexaField $cv 'EditionID')
        versaoExibida = (Get-AGVexaField $cv 'DisplayVersion' (Get-AGVexaField $cv 'ReleaseId'))
        versao        = $os.Version
        build         = ('{0}.{1}' -f $os.BuildNumber, (Get-AGVexaField $cv 'UBR' 0))
        arquitetura   = $os.OSArchitecture
        instaladoEm   = $os.InstallDate.ToString('yyyy-MM-dd')
        ultimoBoot    = $os.LastBootUpTime.ToString('s')
        reinicioPendente = [bool](
            (Test-Path -LiteralPath 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Component Based Servicing\RebootPending') -or
            (Test-Path -LiteralPath 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\WindowsUpdate\Auto Update\RebootRequired'))
    }
}

$info.hardware = Invoke-AGVexaSafely -What 'hardware' -Script {
    $cs = Get-CimInstance -ClassName Win32_ComputerSystem
    $cpu = @(Get-CimInstance -ClassName Win32_Processor)
    $hw = [ordered]@{
        fabricante   = $cs.Manufacturer
        modelo       = $cs.Model
        tipo         = Get-AGVexaChassis
        processador  = ($cpu | Select-Object -First 1).Name.Trim()
        nucleos      = ($cpu | Measure-Object -Property NumberOfCores -Sum).Sum
        threads      = ($cpu | Measure-Object -Property NumberOfLogicalProcessors -Sum).Sum
        memoriaGB    = [math]::Round($cs.TotalPhysicalMemory / 1GB, 1)
    }
    if ($IncluirIdentificadores) {
        $hw.nomeComputador = $env:COMPUTERNAME
        $hw.numeroSerie = (Get-CimInstance -ClassName Win32_BIOS).SerialNumber
    }
    $hw
}

$info.armazenamento = Invoke-AGVexaSafely -What 'armazenamento' -Script {
    $disks = @()
    if (Get-Command -Name Get-PhysicalDisk -ErrorAction SilentlyContinue) {
        $disks = @(Get-PhysicalDisk | ForEach-Object {
            [ordered]@{ modelo = $_.FriendlyName; midia = [string]$_.MediaType; barramento = [string]$_.BusType
                        tamanhoGB = [math]::Round($_.Size / 1GB, 0); saude = [string]$_.HealthStatus }
        })
    }
    $vols = @(Get-CimInstance -ClassName Win32_LogicalDisk -Filter 'DriveType=3' | ForEach-Object {
        $pct = if ($_.Size) { [math]::Round(100 * $_.FreeSpace / $_.Size, 1) } else { 0 }
        [ordered]@{ unidade = $_.DeviceID; sistemaArquivos = $_.FileSystem
                    tamanhoGB = [math]::Round($_.Size / 1GB, 1); livreGB = [math]::Round($_.FreeSpace / 1GB, 1); livrePct = $pct }
    })
    $trim = 'indisponível (requer administrador)'
    if ($isAdmin) {
        $q = (& fsutil.exe behavior query DisableDeleteNotify 2>$null) -join ' '
        if ($q -match 'NTFS DisableDeleteNotify = 0') { $trim = 'habilitado (NTFS)' }
        elseif ($q -match 'NTFS DisableDeleteNotify = 1') { $trim = 'DESABILITADO (NTFS) - investigar' }
        elseif ($q) { $trim = $q.Trim() }
    }
    [ordered]@{ discos = $disks; volumes = $vols; trim = $trim }
}

$info.ativacao = Invoke-AGVexaSafely -What 'ativação' -Script {
    $map = @{ 0 = 'Não licenciado'; 1 = 'Licenciado (ativado)'; 2 = 'Período de carência inicial'; 3 = 'Carência adicional';
              4 = 'Não original'; 5 = 'Notificação'; 6 = 'Carência estendida' }
    $prod = @(Get-CimInstance -ClassName SoftwareLicensingProduct `
        -Filter "ApplicationID='55c92734-d682-4d71-983e-d6ec3f16059f' AND PartialProductKey IS NOT NULL")
    if (-not $prod.Count) { return [ordered]@{ estado = 'Sem chave instalada' } }
    $p = $prod | Select-Object -First 1
    # Chave do produto (mesmo parcial) não é registrada.
    [ordered]@{ estado = $map[[int]$p.LicenseStatus]; canal = (Get-AGVexaField $p 'ProductKeyChannel' '') }
}

$info.seguranca = Invoke-AGVexaSafely -What 'segurança' -Script {
    $sec = [ordered]@{}
    $sec.defender = Invoke-AGVexaSafely -What 'Defender' -Script {
        $m = Get-MpComputerStatus
        [ordered]@{ servico = $m.AMServiceEnabled; antivirus = $m.AntivirusEnabled; tempoReal = $m.RealTimeProtectionEnabled
                    assinaturas = $m.AntivirusSignatureLastUpdated.ToString('yyyy-MM-dd') }
    }
    $sec.antivirusRegistrados = Invoke-AGVexaSafely -What 'antivírus' -Script {
        ,@(Get-CimInstance -Namespace 'root/SecurityCenter2' -ClassName AntiVirusProduct | ForEach-Object { $_.displayName })
    }
    $sec.firewall = Invoke-AGVexaSafely -What 'firewall' -Script {
        ,@(Get-NetFirewallProfile | ForEach-Object { [ordered]@{ perfil = $_.Name; ativo = [bool]$_.Enabled } })
    }
    $sec.uac = Invoke-AGVexaSafely -What 'UAC' -Script {
        $v = Get-ItemProperty -LiteralPath 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System'
        if ((Get-AGVexaField $v 'EnableLUA' 1) -eq 1) { 'ativo' } else { 'DESATIVADO - corrigir' }
    }
    $sec.secureBoot = if ($isAdmin) {
        Invoke-AGVexaSafely -What 'Secure Boot' -Script { if (Confirm-SecureBootUEFI) { 'ativo' } else { 'desativado' } }
    } else { 'indisponível (requer administrador)' }
    $sec.bitlocker = if ($isAdmin -and (Get-Command -Name Get-BitLockerVolume -ErrorAction SilentlyContinue)) {
        Invoke-AGVexaSafely -What 'BitLocker' -Script {
            ,@(Get-BitLockerVolume | ForEach-Object { [ordered]@{ unidade = $_.MountPoint; protecao = [string]$_.ProtectionStatus; estado = [string]$_.VolumeStatus } })
        }
    } else { 'indisponível (requer administrador ou edição sem BitLocker)' }
    $sec.tpm = if ($isAdmin -and (Get-Command -Name Get-Tpm -ErrorAction SilentlyContinue)) {
        Invoke-AGVexaSafely -What 'TPM' -Script { $t = Get-Tpm; [ordered]@{ presente = $t.TpmPresent; pronto = $t.TpmReady } }
    } else { 'indisponível (requer administrador)' }
    $sec.windowsUpdate = Invoke-AGVexaSafely -What 'Windows Update' -Script {
        $s = Get-Service -Name wuauserv
        [ordered]@{ servico = [string]$s.Status; inicializacao = [string]$s.StartType }
    }
    $sec
}

$info.energia = Invoke-AGVexaSafely -What 'energia' -Script {
    $active = Get-AGVexaActivePowerScheme
    $schemes = @(Get-AGVexaPowerSchemes)
    $bat = @(Get-CimInstance -ClassName Win32_Battery -ErrorAction SilentlyContinue)
    $bateria = [ordered]@{ presente = $false }
    if ($bat.Count) { $bateria = [ordered]@{ presente = $true; cargaPct = ($bat | Select-Object -First 1).EstimatedChargeRemaining } }
    [ordered]@{
        planoAtivo = (@($schemes | Where-Object { $_.Guid -eq $active } | ForEach-Object { $_.Nome }) + @($active))[0]
        planoAtivoGuid = $active
        planosDisponiveis = @($schemes | ForEach-Object { $_.Nome })
        bateria = $bateria
    }
}

$info.inicializacao = Invoke-AGVexaSafely -What 'inicialização' -Script { ,@(Get-AGVexaStartupItems) }

$info.analiseManual = Invoke-AGVexaSafely -What 'serviços e tarefas' -Script {
    $svc = @(Get-CimInstance -ClassName Win32_Service -Filter "StartMode='Auto'" |
        Where-Object { $_.PathName -and $_.PathName -notmatch '(?i)\\Windows\\' } |
        ForEach-Object { [ordered]@{ nome = $_.Name; exibicao = $_.DisplayName; estado = $_.State } })
    $tasks = @()
    if (Get-Command -Name Get-ScheduledTask -ErrorAction SilentlyContinue) {
        $tasks = @(Get-ScheduledTask | Where-Object { $_.TaskPath -notlike '\Microsoft\*' -and [string]$_.State -ne 'Disabled' } |
            ForEach-Object { [ordered]@{ tarefa = ('{0}{1}' -f $_.TaskPath, $_.TaskName); estado = [string]$_.State } })
    }
    $apps = @()
    if (Get-Command -Name Get-AppxPackage -ErrorAction SilentlyContinue) {
        $apps = @(Get-AppxPackage | Where-Object { -not $_.IsFramework -and [string]$_.SignatureKind -eq 'Store' } |
            Sort-Object Name | ForEach-Object { $_.Name })
    }
    [ordered]@{ servicosTerceiros = $svc; tarefasTerceiros = $tasks; appsLoja = $apps }
}

$outFile = Join-Path $session.Path 'diagnostico.json'
Save-AGVexaJson -Object $info -Path $outFile
Write-AGVexaLog -Level 'OK' -Message "Diagnóstico salvo em $outFile"

if (-not $SemTela) {
    Write-AGVexaHeader -Subtitle 'Diagnóstico do computador (somente leitura)'
    $s = $info.sistema; $h = $info.hardware; $e = $info.energia
    Write-Host ''
    Write-Host ('  Windows      : {0} {1} (build {2})' -f (Get-AGVexaField $s 'nome' '?'), (Get-AGVexaField $s 'versaoExibida' ''), (Get-AGVexaField $s 'build' '?'))
    Write-Host ('  Equipamento  : {0} {1} ({2})' -f (Get-AGVexaField $h 'fabricante' '?'), (Get-AGVexaField $h 'modelo' ''), (Get-AGVexaField $h 'tipo' '?'))
    Write-Host ('  Processador  : {0}' -f (Get-AGVexaField $h 'processador' '?'))
    Write-Host ('  Memória      : {0} GB' -f (Get-AGVexaField $h 'memoriaGB' '?'))
    foreach ($v in @(Get-AGVexaField $info.armazenamento 'volumes' @())) {
        $color = if ($v.livrePct -lt 15) { 'Yellow' } else { 'Gray' }
        Write-Host ('  Volume {0}    : {1} GB livres de {2} GB ({3}%)' -f $v.unidade, $v.livreGB, $v.tamanhoGB, $v.livrePct) -ForegroundColor $color
    }
    foreach ($d in @(Get-AGVexaField $info.armazenamento 'discos' @())) {
        Write-Host ('  Disco        : {0} - {1}/{2}, saúde {3}' -f $d.modelo, $d.midia, $d.barramento, $d.saude)
    }
    Write-Host ('  Ativação     : {0}' -f (Get-AGVexaField $info.ativacao 'estado' 'indisponível'))
    Write-Host ('  Energia      : {0}' -f (Get-AGVexaField $e 'planoAtivo' '?'))
    Write-Host ('  Reinício pendente: {0}' -f (Get-AGVexaField $s 'reinicioPendente' '?'))
    $startup = @($info.inicializacao)
    Write-Host ('  Inicialização: {0} item(ns) - use a opção 5 do menu para revisar' -f $startup.Count)
    Write-Host ''
    Write-AGVexaStatus -Level 'OK' -Message ("Diagnóstico salvo em {0}" -f $outFile)
    if (-not $isAdmin) { Write-AGVexaStatus -Level 'AVISO' -Message 'Sem administrador: Secure Boot, BitLocker, TPM e TRIM não foram lidos.' }
}

[pscustomobject]$info

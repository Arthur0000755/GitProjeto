#Requires -Version 5.1
<#
.SYNOPSIS
    AG Vexa Windows Optimizer - gera relatório técnico local (HTML e/ou Markdown).

.DESCRIPTION
    Monta o relatório a partir dos arquivos da sessão (diagnostico.json,
    plano.json, execucao.json). Tudo é local: nada é enviado para a internet.
    O relatório não inclui nome de usuário, nome do computador, número de
    série nem chave do produto, a menos que o diagnóstico tenha sido feito
    com -IncluirIdentificadores (autorização do cliente).

.PARAMETER Sessao
    Caminho/nome da sessão ou 'ultima' (padrão: sessão mais recente).

.PARAMETER OrdemServico
    Número da ordem de serviço AG Vexa (opcional).

.PARAMETER Tecnico
    Nome do técnico responsável (opcional).

.PARAMETER Formato
    Html (padrão), Markdown ou Ambos.

.PARAMETER CopiarPara
    Pasta adicional para copiar o relatório (ex.: pasta de relatórios no HD do toolkit).

.PARAMETER SemAbrir
    Não abre o relatório ao final.
#>
[CmdletBinding()]
param(
    [string]$Sessao,
    [ValidatePattern('^[A-Za-z0-9_-]*$')][string]$OrdemServico = '',
    [string]$Tecnico = '',
    [ValidateSet('Html', 'Markdown', 'Ambos')][string]$Formato = 'Html',
    [string]$CopiarPara,
    [switch]$SemAbrir
)

Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'
if (-not (Get-Module -Name AGVexa.Common)) { Import-Module (Join-Path $PSScriptRoot 'lib\AGVexa.Common.psm1') -DisableNameChecking }

if (-not $Sessao) {
    $last = @(Get-AGVexaSessions) | Select-Object -First 1
    if (-not $last) { Write-Error 'Nenhuma sessão encontrada. Execute o diagnóstico primeiro.'; exit 1 }
    $path = $last.FullName
} else {
    $path = Resolve-AGVexaSessionPath -Session $Sessao
}

function Read-Optional([string]$name) {
    $f = Join-Path $path $name
    if (Test-Path -LiteralPath $f) { Read-AGVexaJson -Path $f } else { $null }
}
function ConvertTo-AGVexaHtml([object]$text) { [System.Net.WebUtility]::HtmlEncode([string]$text) }

$diag = Read-Optional 'diagnostico.json'
$plan = Read-Optional 'plano.json'
$exec = Read-Optional 'execucao.json'
$now = Get-Date -Format 'dd/MM/yyyy HH:mm'
$version = Get-AGVexaVersion

# ---------------------------------------------------------------- linhas de conteúdo
$rows = New-Object System.Collections.Generic.List[object]   # (seção, rótulo, valor, nivel)
function Add-Row($sec, $label, $value, $level = '') { $rows.Add(@($sec, $label, $value, $level)) }

if ($diag) {
    $s = Get-AGVexaField $diag 'sistema'; $h = Get-AGVexaField $diag 'hardware'
    Add-Row 'Equipamento' 'Windows' ('{0} {1} (build {2})' -f (Get-AGVexaField $s 'nome' '?'), (Get-AGVexaField $s 'versaoExibida' ''), (Get-AGVexaField $s 'build' '?'))
    Add-Row 'Equipamento' 'Fabricante / modelo' ('{0} {1}' -f (Get-AGVexaField $h 'fabricante' '?'), (Get-AGVexaField $h 'modelo' ''))
    Add-Row 'Equipamento' 'Tipo' (Get-AGVexaField $h 'tipo' '?')
    Add-Row 'Equipamento' 'Processador' (Get-AGVexaField $h 'processador' '?')
    Add-Row 'Equipamento' 'Memória RAM' ('{0} GB' -f (Get-AGVexaField $h 'memoriaGB' '?'))
    $st = Get-AGVexaField $diag 'armazenamento'
    foreach ($d in @(Get-AGVexaField $st 'discos' @())) {
        $lvl = if ([string]$d.saude -ne 'Healthy') { 'alerta' } else { '' }
        Add-Row 'Armazenamento' ('Disco {0}' -f $d.modelo) ('{0} / {1} - {2} GB - saúde: {3}' -f $d.midia, $d.barramento, $d.tamanhoGB, $d.saude) $lvl
    }
    foreach ($v in @(Get-AGVexaField $st 'volumes' @())) {
        $lvl = if ([double]$v.livrePct -lt 15) { 'alerta' } else { '' }
        Add-Row 'Armazenamento' ('Volume {0}' -f $v.unidade) ('{0} GB livres de {1} GB ({2}%)' -f $v.livreGB, $v.tamanhoGB, $v.livrePct) $lvl
    }
    Add-Row 'Armazenamento' 'TRIM' (Get-AGVexaField $st 'trim' 'não verificado')
    Add-Row 'Segurança' 'Ativação do Windows' (Get-AGVexaField (Get-AGVexaField $diag 'ativacao') 'estado' 'indisponível')
    $sec = Get-AGVexaField $diag 'seguranca'
    $def = Get-AGVexaField $sec 'defender'
    Add-Row 'Segurança' 'Microsoft Defender (tempo real)' (Get-AGVexaField $def 'tempoReal' 'indisponível')
    Add-Row 'Segurança' 'Antivírus registrados' ((@(Get-AGVexaField $sec 'antivirusRegistrados' @()) | Where-Object { $_ -is [string] }) -join ', ')
    foreach ($fw in @(Get-AGVexaField $sec 'firewall' @())) {
        $on = Get-AGVexaField $fw 'ativo'
        if ($null -ne $on) { Add-Row 'Segurança' ('Firewall ({0})' -f $fw.perfil) $(if ($on) { 'ativo' } else { 'DESATIVADO' }) $(if ($on) { '' } else { 'alerta' }) }
    }
    $uac = Get-AGVexaField $sec 'uac' '?'
    Add-Row 'Segurança' 'Controle de Conta de Usuário (UAC)' $uac $(if ([string]$uac -eq 'ativo') { '' } else { 'alerta' })
    Add-Row 'Segurança' 'Secure Boot' (Get-AGVexaField $sec 'secureBoot' '?')
    $en = Get-AGVexaField $diag 'energia'
    Add-Row 'Energia' 'Plano ativo' (Get-AGVexaField $en 'planoAtivo' '?')
    foreach ($it in @(Get-AGVexaField $diag 'inicializacao' @())) {
        if ($null -eq (Get-AGVexaField $it 'Nome')) { continue }
        Add-Row 'Inicialização' $it.Nome ('{0} - {1} ({2})' -f $it.Categoria, $it.Estado, $it.Escopo)
    }
}
if ($plan) {
    foreach ($p in @($plan.itens)) {
        $lvl = switch ($p.status) { 'ERRO' { 'alerta' } 'RECOMENDACAO' { 'info' } default { '' } }
        Add-Row ('Avaliação (perfil {0})' -f $plan.perfil) $p.titulo ('{0}{1}' -f $p.status, $(if ($p.motivo) { ' - ' + $p.motivo } else { '' })) $lvl
    }
}
if ($exec) {
    Add-Row 'Execução' 'Modo' $(if ($exec.aplicar) { 'aplicação com confirmação' } else { 'simulação (nada alterado)' })
    Add-Row 'Execução' 'Ponto de restauração' $exec.pontoRestauracao
    foreach ($r in @($exec.resultados)) {
        if ($null -eq $r) { continue }
        Add-Row 'Execução' $r.titulo ('{0} {1}' -f $r.resultado, $r.detalhe) $(if ($r.resultado -eq 'FALHOU') { 'alerta' } else { '' })
    }
    if ($exec.aplicar) { Add-Row 'Execução' 'Como desfazer' (".\Restore-AGVexaSettings.ps1 -Sessao '{0}'" -f (Split-Path -Leaf $path)) }
}

$sid = Split-Path -Leaf $path
$header = [ordered]@{ 'Ordem de serviço' = $(if ($OrdemServico) { $OrdemServico } else { '(não informada)' })
                      'Técnico' = $(if ($Tecnico) { $Tecnico } else { '(não informado)' })
                      'Data' = $now; 'Sessão' = $sid; 'Ferramenta' = ('AG Vexa Windows Optimizer {0}' -f $version) }

$written = @()
if ($Formato -in 'Html', 'Ambos') {
    $sb = New-Object System.Text.StringBuilder
    [void]$sb.Append(@'
<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Relatório técnico AG Vexa</title><style>
:root{--bg:#0B1220;--bg2:#111C30;--azul:#38BDF8;--azul2:#2563EB;--txt:#0F172A;--sec:#475569;--al:#B45309}
body{font-family:Segoe UI,Arial,sans-serif;margin:0;color:var(--txt);background:#F8FAFC}
header{background:var(--bg);color:#F8FAFC;padding:24px 32px;border-bottom:4px solid var(--azul)}
header small{color:var(--azul);letter-spacing:.2em;font-weight:600}
header img.logo{height:64px;display:block;margin-bottom:10px}
header h1{margin:6px 0 2px;font-size:24px}header p{margin:0;color:#94A3B8}
main{padding:24px 32px;max-width:980px}
table{border-collapse:collapse;width:100%;margin:8px 0 24px;font-size:14px}
th,td{border-bottom:1px solid #E2E8F0;padding:7px 8px;text-align:left;vertical-align:top}
th{width:34%;color:var(--sec);font-weight:600}
h2{font-size:16px;color:var(--azul2);border-left:4px solid var(--azul);padding-left:8px;margin-top:28px}
tr.alerta td{color:var(--al);font-weight:600}tr.info td{color:var(--sec)}
.meta td,.meta th{border:0;padding:3px 8px}.ass{margin-top:48px;display:flex;gap:48px}
.ass div{flex:1;border-top:1px solid #94A3B8;padding-top:6px;color:var(--sec);font-size:13px}
footer{color:var(--sec);font-size:12px;padding:16px 32px}
@media print{header{-webkit-print-color-adjust:exact;print-color-adjust:exact}}
</style></head><body>
'@)
    # Logomarca oficial embutida no HTML (arquivo local; nada é buscado na internet)
    $logoPath = Join-Path (Join-Path $PSScriptRoot 'assets') 'agvexa-logo.png'
    $brand = '<small>AG VEXA</small>'
    $tagline = '<p>Assistência Técnica</p>'
    if (Test-Path -LiteralPath $logoPath) {
        $b64 = [Convert]::ToBase64String([System.IO.File]::ReadAllBytes($logoPath))
        $brand = '<img class="logo" alt="AG Vexa Assistência Técnica" src="data:image/png;base64,' + $b64 + '">'
        $tagline = ''   # a logo já traz "Assistência Técnica"
    }
    [void]$sb.AppendFormat('<header>{0}<h1>Relatório técnico - Windows Optimizer</h1>{1}</header><main>', $brand, $tagline)
    [void]$sb.Append('<table class="meta">')
    foreach ($k in $header.Keys) { [void]$sb.AppendFormat('<tr><th>{0}</th><td>{1}</td></tr>', (ConvertTo-AGVexaHtml $k), (ConvertTo-AGVexaHtml $header[$k])) }
    [void]$sb.Append('</table>')
    $current = $null
    foreach ($r in $rows) {
        if ($r[0] -ne $current) {
            if ($current) { [void]$sb.Append('</table>') }
            $current = $r[0]
            [void]$sb.AppendFormat('<h2>{0}</h2><table>', (ConvertTo-AGVexaHtml $current))
        }
        [void]$sb.AppendFormat('<tr class="{0}"><th>{1}</th><td>{2}</td></tr>', $r[3], (ConvertTo-AGVexaHtml $r[1]), (ConvertTo-AGVexaHtml $r[2]))
    }
    if ($current) { [void]$sb.Append('</table>') }
    [void]$sb.Append('<h2>Observações do técnico</h2><p>&nbsp;</p><p>&nbsp;</p>')
    [void]$sb.Append('<div class="ass"><div>Técnico responsável</div><div>Cliente (ciente das alterações)</div></div></main>')
    [void]$sb.AppendFormat('<footer>Gerado localmente por AG Vexa Windows Optimizer {0}. Nenhum dado foi enviado para a internet.</footer></body></html>', (ConvertTo-AGVexaHtml $version))
    $html = Join-Path $path 'relatorio.html'
    [System.IO.File]::WriteAllText($html, $sb.ToString(), (New-Object System.Text.UTF8Encoding($true)))
    $written += $html
}
if ($Formato -in 'Markdown', 'Ambos') {
    $md = New-Object System.Text.StringBuilder
    [void]$md.AppendLine('# Relatório técnico - AG Vexa Windows Optimizer').AppendLine()
    foreach ($k in $header.Keys) { [void]$md.AppendLine(('- **{0}:** {1}' -f $k, $header[$k])) }
    $current = $null
    foreach ($r in $rows) {
        if ($r[0] -ne $current) { $current = $r[0]; [void]$md.AppendLine().AppendLine('## ' + $current).AppendLine().AppendLine('| Item | Resultado |').AppendLine('|---|---|') }
        $mark = if ($r[3] -eq 'alerta') { ' ⚠' } else { '' }
        [void]$md.AppendLine(('| {0} | {1}{2} |' -f ([string]$r[1] -replace '\|', '/'), ([string]$r[2] -replace '\|', '/'), $mark))
    }
    [void]$md.AppendLine().AppendLine('## Observações do técnico').AppendLine().AppendLine('______________________________')
    $mdFile = Join-Path $path 'relatorio.md'
    [System.IO.File]::WriteAllText($mdFile, $md.ToString(), (New-Object System.Text.UTF8Encoding($true)))
    $written += $mdFile
}

if ($CopiarPara) {
    if (-not (Test-Path -LiteralPath $CopiarPara -PathType Container)) { New-Item -ItemType Directory -Path $CopiarPara -Force | Out-Null }
    foreach ($w in $written) {
        $dest = Join-Path $CopiarPara ('{0}-{1}{2}' -f $(if ($OrdemServico) { 'OS-' + $OrdemServico } else { $sid }), 'relatorio', [IO.Path]::GetExtension($w))
        Copy-Item -LiteralPath $w -Destination $dest
        $written += $dest
    }
}
foreach ($w in $written) { Write-AGVexaStatus -Level 'OK' -Message ("Relatório: {0}" -f $w) }
if (-not $SemAbrir -and $written.Count) { Invoke-Item -LiteralPath $written[0] }
$written

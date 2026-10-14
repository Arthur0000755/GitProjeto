#!/usr/bin/env bash
# AG Vexa Toolkit - verificação do ambiente de desenvolvimento (SOMENTE LEITURA)
set -uo pipefail
. "$(dirname "$0")/lib/common.sh"

usage() {
    cat <<EOF
Uso: scripts/preflight.sh [--help] [--quiet]

Verifica, sem alterar nada, se o ambiente está pronto para trabalhar no
AG Vexa Toolkit:
  - sistema operacional, CPU, memória e carga atual;
  - ferramentas obrigatórias e opcionais;
  - espaço livre no diretório do projeto;
  - estado dos diretórios do projeto e do Git (apenas deste projeto).

Este script NÃO lista discos, NÃO acessa dispositivos de bloco, NÃO usa
sudo e NÃO consulta Docker ou serviços do servidor.

Opções:
  --quiet   mostra apenas avisos e erros
  --help    mostra esta ajuda

Códigos de saída: 0 pronto | 2 pronto com avisos | 1 falta item obrigatório | 64 uso incorreto
EOF
}

QUIET=0
while [ $# -gt 0 ]; do
    case "$1" in
        -h|--help) usage; exit 0 ;;
        --quiet) QUIET=1 ;;
        *) agv_die_usage "opção desconhecida: $1" ;;
    esac
    shift
done

ERRORS=0; WARNS=0
ok()   { [ "$QUIET" = 1 ] || agv_ok "$@"; }
warn() { agv_warn "$@"; WARNS=$((WARNS+1)); }
err()  { agv_err "$@"; ERRORS=$((ERRORS+1)); }
info() { [ "$QUIET" = 1 ] || agv_info "$@"; }

[ "$QUIET" = 1 ] || agv_banner "verificação do ambiente (somente leitura)"

echo "${C_BOLD}[1] Sistema${C_RESET}"
if [ -r /etc/os-release ]; then
    # shellcheck disable=SC1091
    . /etc/os-release
    info "SO: ${PRETTY_NAME:-desconhecido}"
else
    warn "não foi possível ler /etc/os-release"
fi
info "Kernel: $(uname -sr) ($(uname -m))"
CPUS="$(getconf _NPROCESSORS_ONLN 2>/dev/null || echo 1)"
CPU_MODEL="$(awk -F': ' '/model name/{print $2; exit}' /proc/cpuinfo 2>/dev/null)"
info "CPU: ${CPU_MODEL:-desconhecida} (${CPUS} núcleo(s))"
MEM_KB="$(awk '/MemTotal/{print $2}' /proc/meminfo 2>/dev/null || echo 0)"
AVAIL_KB="$(awk '/MemAvailable/{print $2}' /proc/meminfo 2>/dev/null || echo 0)"
info "Memória: $((MEM_KB/1024)) MiB total, $((AVAIL_KB/1024)) MiB disponível"
LOAD1="$(cut -d' ' -f1 /proc/loadavg 2>/dev/null || echo 0)"
info "Carga (1 min): $LOAD1"
if awk -v l="$LOAD1" -v c="$CPUS" 'BEGIN{exit !(l > c)}'; then
    warn "carga acima do número de núcleos: evite testes pesados (QEMU) agora"
fi
if [ "$AVAIL_KB" -lt 1572864 ]; then
    warn "menos de 1,5 GiB de RAM livre: testes em máquina virtual podem afetar os serviços"
fi
[ "$(id -u)" = 0 ] && warn "executando como root: não é necessário para nenhum script do toolkit"

echo; echo "${C_BOLD}[2] Ferramentas obrigatórias${C_RESET}"
for t in bash python3 sha256sum; do
    if command -v "$t" >/dev/null 2>&1; then ok "$t: $(command -v "$t")"; else err "$t ausente"; fi
done
if command -v python3 >/dev/null 2>&1; then
    PYV="$(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
    if python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)'; then
        ok "Python $PYV"
    else
        err "Python $PYV: é necessário 3.8 ou superior"
    fi
fi

echo; echo "${C_BOLD}[3] Ferramentas opcionais${C_RESET}"
opt() { # nome comando finalidade
    if command -v "$2" >/dev/null 2>&1; then ok "$1: disponível ($3)"; else warn "$1 ausente: $3"; fi
}
if python3 -c 'import PIL' 2>/dev/null; then ok "Pillow: disponível (regerar imagens do tema)"
else warn "Pillow ausente: as imagens versionadas continuam válidas; só não é possível regerá-las"; fi
if python3 -c 'import yaml' 2>/dev/null; then ok "PyYAML: disponível (validar catalog/ferramentas.yaml)"
else warn "PyYAML ausente: catalog/ferramentas.yaml não será analisado"; fi
opt "git" git "versionamento"
opt "gpg" gpg "conferir assinaturas dos arquivos de checksums oficiais"
opt "file" file "identificação de tipos de arquivo"
opt "rsync" rsync "cópia futura do staging para o HD (cp -rL também serve)"
opt "shellcheck" shellcheck "análise estática dos scripts .sh"
opt "pwsh" pwsh "checar sintaxe do Windows Optimizer no Linux"
opt "qemu-system-x86_64" qemu-system-x86_64 "testes de boot virtuais"
OVMF=""
for f in /usr/share/OVMF/OVMF_CODE_4M.fd /usr/share/OVMF/OVMF_CODE.fd /usr/share/ovmf/OVMF.fd /usr/share/qemu/OVMF.fd; do
    [ -r "$f" ] && OVMF="$f" && break
done
if [ -n "$OVMF" ]; then ok "firmware UEFI de teste (OVMF): $OVMF"; else warn "OVMF ausente: testes UEFI virtuais indisponíveis"; fi
if [ -r /dev/kvm ] && [ -w /dev/kvm ]; then ok "KVM acessível (aceleração de VM)"; else info "KVM não acessível ao usuário: QEMU usaria emulação (lenta)"; fi

echo; echo "${C_BOLD}[4] Espaço em disco${C_RESET}"
FREE_KB="$(df -Pk "$AGV_ROOT" | awk 'NR==2{print $4}')"
info "Livre no volume do projeto: $((FREE_KB/1024/1024)) GiB"
if [ "$FREE_KB" -lt $((10*1024*1024)) ]; then
    warn "menos de 10 GiB livres: use --iso-mode link no staging e evite duplicar ISOs"
else
    ok "espaço suficiente para staging com links"
fi
if [ -d "$AGV_ROOT/isos" ]; then
    ISO_SIZE="$(du -sk "$AGV_ROOT/isos" 2>/dev/null | cut -f1)"
    info "Biblioteca de ISOs: $((ISO_SIZE/1024)) MiB em isos/"
fi

echo; echo "${C_BOLD}[5] Projeto${C_RESET}"
info "Raiz: $AGV_ROOT"
for d in docs branding ventoy catalog media-layout scripts tests templates windows-optimizer isos build reports; do
    if [ -d "$AGV_ROOT/$d" ]; then ok "diretório $d/"; else err "diretório $d/ ausente"; fi
done
if [ -f "$AGV_ROOT/catalog/isos-manifest.json" ]; then
    ok "manifesto real presente (catalog/isos-manifest.json)"
else
    warn "manifesto real ausente: copie catalog/isos-manifest.example.json quando baixar ISOs"
fi
if command -v git >/dev/null 2>&1 && git -C "$AGV_ROOT" rev-parse >/dev/null 2>&1; then
    CHG="$(git -C "$AGV_ROOT" status --porcelain -- . | wc -l)"
    info "Git: branch $(git -C "$AGV_ROOT" rev-parse --abbrev-ref HEAD), $CHG arquivo(s) alterado(s) neste projeto"
    TRACKED_BIG="$(git -C "$AGV_ROOT" ls-files -- . | grep -Ei '\.(iso|img|wim|esd|vhdx?)$' || true)"
    if [ -n "$TRACKED_BIG" ]; then err "imagens de disco versionadas no Git: $TRACKED_BIG"; else ok "nenhuma ISO/imagem versionada no Git"; fi
else
    warn "projeto fora de um repositório Git"
fi

echo
echo "Resumo: $ERRORS erro(s), $WARNS aviso(s)."
[ "$ERRORS" -gt 0 ] && exit "$AGV_EXIT_ERROR"
[ "$WARNS" -gt 0 ] && exit "$AGV_EXIT_WARN"
exit "$AGV_EXIT_OK"

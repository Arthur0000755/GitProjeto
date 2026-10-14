# shellcheck shell=bash
# Funções comuns dos scripts do AG Vexa Toolkit.
# Este arquivo é "sourced"; não executa nada sozinho.

# Raiz do projeto (independe do diretório atual)
AGV_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
AGV_VERSION="$(cat "$AGV_ROOT/VERSION" 2>/dev/null || echo desconhecida)"
AGV_PY="$AGV_ROOT/scripts/lib/agvexa.py"

# Códigos de saída padronizados (iguais aos de agvexa.py)
AGV_EXIT_OK=0
AGV_EXIT_ERROR=1
AGV_EXIT_WARN=2
AGV_EXIT_USAGE=64

if [ -t 1 ] && [ -z "${NO_COLOR:-}" ]; then
    C_RESET=$'\033[0m'; C_BOLD=$'\033[1m'; C_BLUE=$'\033[38;5;39m'
    C_OK=$'\033[32m'; C_WARN=$'\033[33m'; C_ERR=$'\033[31m'; C_DIM=$'\033[2m'
else
    C_RESET=""; C_BOLD=""; C_BLUE=""; C_OK=""; C_WARN=""; C_ERR=""; C_DIM=""
fi

agv_banner() {
    printf '%s%sAG VEXA TOOLKIT%s %s— %s%s\n' "$C_BOLD" "$C_BLUE" "$C_RESET" "$C_DIM" "$1" "$C_RESET"
    printf '%sversão %s%s\n\n' "$C_DIM" "$AGV_VERSION" "$C_RESET"
}

agv_ok()   { printf '  %s[OK]%s    %s\n' "$C_OK" "$C_RESET" "$*"; }
agv_warn() { printf '  %s[AVISO]%s %s\n' "$C_WARN" "$C_RESET" "$*"; }
agv_err()  { printf '  %s[ERRO]%s  %s\n' "$C_ERR" "$C_RESET" "$*" >&2; }
agv_info() { printf '  %s\n' "$*"; }

agv_die_usage() {
    agv_err "$1"
    echo "  Use --help para ver as opções." >&2
    exit "$AGV_EXIT_USAGE"
}

agv_require_python() {
    if ! command -v python3 >/dev/null 2>&1; then
        agv_err "python3 não encontrado (necessário para este script)."
        exit "$AGV_EXIT_ERROR"
    fi
}

# Recusa qualquer caminho que aponte para dispositivo de bloco ou
# pseudo-sistemas de arquivos. Usado por todos os scripts que recebem
# caminhos do usuário.
agv_refuse_device_path() {
    local p="$1"
    case "$p" in
        /dev/*|/proc/*|/sys/*|/run/*)
            agv_err "Caminho recusado por segurança: $p (scripts do toolkit não acessam dispositivos)."
            exit "$AGV_EXIT_USAGE" ;;
    esac
    if [ -e "$p" ] && [ -b "$p" ]; then
        agv_err "Caminho recusado: $p é um dispositivo de bloco."
        exit "$AGV_EXIT_USAGE"
    fi
}

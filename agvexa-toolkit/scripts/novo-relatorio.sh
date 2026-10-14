#!/usr/bin/env bash
# AG Vexa Toolkit - cria um relatório de atendimento a partir dos modelos (local)
set -uo pipefail
. "$(dirname "$0")/lib/common.sh"

TPL_DIR="$AGV_ROOT/templates/relatorios"

usage() {
    cat <<EOF
Uso: scripts/novo-relatorio.sh --tipo TIPO --os NUMERO [--tecnico NOME] [--dry-run]
     scripts/novo-relatorio.sh --listar

Cria em reports/ um relatório Markdown a partir de templates/relatorios/,
preenchendo data, número da ordem de serviço, técnico e versão do toolkit.
Tudo é local: nada é enviado para a internet ou para outros sistemas.

Não escreva no relatório dados pessoais além do necessário ao atendimento
(nome do cliente e contato ficam na ordem de serviço, não aqui).

Opções:
  --tipo TIPO     modelo a usar (veja --listar)
  --os NUMERO     número da ordem de serviço (letras, números, - e _)
  --tecnico NOME  nome do técnico responsável
  --listar        lista os modelos disponíveis
  --dry-run       mostra o arquivo que seria criado
  --help          mostra esta ajuda

Códigos de saída: 0 sucesso | 1 erro | 64 uso incorreto
EOF
}

TIPO=""; OS=""; TECNICO="(preencher)"; DRY=0; LIST=0
while [ $# -gt 0 ]; do
    case "$1" in
        -h|--help) usage; exit 0 ;;
        --tipo) [ $# -ge 2 ] || agv_die_usage "--tipo exige valor"; TIPO="$2"; shift ;;
        --os) [ $# -ge 2 ] || agv_die_usage "--os exige valor"; OS="$2"; shift ;;
        --tecnico) [ $# -ge 2 ] || agv_die_usage "--tecnico exige valor"; TECNICO="$2"; shift ;;
        --listar) LIST=1 ;;
        --dry-run) DRY=1 ;;
        *) agv_die_usage "opção desconhecida: $1" ;;
    esac
    shift
done

if [ "$LIST" = 1 ]; then
    for f in "$TPL_DIR"/*.md; do
        n="$(basename "$f" .md)"
        printf '  %-28s %s\n' "$n" "$(head -n1 "$f" | sed 's/^# *//')"
    done
    exit 0
fi

[ -n "$TIPO" ] || agv_die_usage "informe --tipo (ou --listar)"
[ -n "$OS" ] || agv_die_usage "informe --os"
case "$TIPO" in *[!a-z0-9-]*) agv_die_usage "tipo inválido: $TIPO" ;; esac
case "$OS" in *[!A-Za-z0-9_-]*) agv_die_usage "número de OS inválido: $OS" ;; esac
case "$TECNICO" in *'|'*|*'\'*) agv_die_usage "nome do técnico contém caracteres não permitidos" ;; esac
TPL="$TPL_DIR/$TIPO.md"
[ -f "$TPL" ] || agv_die_usage "modelo inexistente: $TIPO (use --listar)"

DATA="$(date +%Y-%m-%d)"
OUT="$AGV_ROOT/reports/OS-$OS-$TIPO-$DATA.md"
if [ -e "$OUT" ]; then
    agv_err "já existe: ${OUT#"$AGV_ROOT"/} (nada foi sobrescrito)"
    exit "$AGV_EXIT_ERROR"
fi
if [ "$DRY" = 1 ]; then
    agv_info "[dry-run] criaria ${OUT#"$AGV_ROOT"/} a partir de $TIPO.md"
    exit 0
fi
mkdir -p "$AGV_ROOT/reports"
TECNICO="${TECNICO//&/\\&}"
sed -e "s|{{DATA}}|$DATA|g" -e "s|{{OS}}|$OS|g" -e "s|{{TECNICO}}|$TECNICO|g" \
    -e "s|{{VERSAO}}|$AGV_VERSION|g" "$TPL" > "$OUT"
agv_ok "criado: ${OUT#"$AGV_ROOT"/}"

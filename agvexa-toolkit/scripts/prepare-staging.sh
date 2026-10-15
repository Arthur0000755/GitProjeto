#!/usr/bin/env bash
# AG Vexa Toolkit - preparação do staging (estrutura pronta para cópia futura ao HD)
set -uo pipefail
. "$(dirname "$0")/lib/common.sh"

usage() {
    cat <<EOF
Uso: scripts/prepare-staging.sh [opções]

Monta em build/staging/ uma cópia exata do que irá para a partição de
dados do HD Ventoy:
  ISO/<categoria>/...     somente ISOs VERIFICADAS (SHA-256 oficial)
  ventoy/ventoy.json      gerado com nomes amigáveis só das ISOs presentes
  ventoy/ventoy_grub.cfg  menu F6
  ventoy/themes/          temas agvexa e agvexa-lite
  AGVexa/                 documentação, modelos, Windows Optimizer, catálogo
  DRIVERS/ INSTALADORES/ FERRAMENTAS/ BIOS_FIRMWARE/
                          pastas de apoio (uso com o Windows aberto): LEIA-ME,
                          INVENTARIO.csv e os arquivos de extras/<PASTA>/
  SHA256SUMS-AGVEXA.txt   somas para conferência após a cópia

Segurança:
  - trabalha SOMENTE em diretórios comuns dentro de build/ do projeto;
  - recusa /dev, pontos de montagem, links simbólicos e diretórios que
    não tenham sido criados por este script (marcador .agvexa-staging);
  - não acessa discos, não formata, não instala Ventoy;
  - recusa extras/CLIENTES: dados de clientes nunca vão para a mídia.

Opções:
  --output DIR          destino dentro de build/ (padrão: build/staging)
  --manifest ARQ        manifesto (padrão: catalog/isos-manifest.json)
  --library DIR         biblioteca de ISOs (padrão: isos/)
  --extras DIR          arquivos das pastas de apoio (padrão: extras/)
  --iso-mode MODO       link (padrão, não duplica espaço) | copy | none
                        (vale também para os arquivos de extras/)
  --allow-unverified    inclui ISOs sem checksum oficial, marcadas
                        "[NÃO VERIFICADA]" no menu (use com critério)
  --ascii-menu          nomes do menu sem acentos (útil se usar modo texto)
  --rebuild-base        regenera ventoy/ventoy.json a partir de
                        catalog/categorias.json e encerra
  --dry-run             mostra o que seria feito, sem gravar nada
  --verbose             lista todas as ações
  --help                mostra esta ajuda

Códigos de saída: 0 sucesso | 1 erro | 64 uso incorreto/caminho recusado
EOF
}

ARGS=()
REBUILD=0
DRY=0
while [ $# -gt 0 ]; do
    case "$1" in
        -h|--help) usage; exit 0 ;;
        --output|--manifest|--library|--extras)
            [ $# -ge 2 ] || agv_die_usage "$1 exige um valor"
            agv_refuse_device_path "$2"
            ARGS+=("$1" "$2"); shift ;;
        --iso-mode)
            [ $# -ge 2 ] || agv_die_usage "--iso-mode exige link|copy|none"
            case "$2" in link|copy|none) ;; *) agv_die_usage "--iso-mode inválido: $2" ;; esac
            ARGS+=("$1" "$2"); shift ;;
        --allow-unverified|--ascii-menu|--verbose) ARGS+=("$1") ;;
        --dry-run) ARGS+=("$1"); DRY=1 ;;
        --rebuild-base) REBUILD=1 ;;
        *) agv_die_usage "opção desconhecida: $1" ;;
    esac
    shift
done

agv_require_python
if [ "$REBUILD" = 1 ]; then
    if [ "$DRY" = 1 ]; then
        python3 "$AGV_PY" build-base --dry-run
    else
        python3 "$AGV_PY" build-base
    fi
    exit $?
fi
python3 "$AGV_PY" stage "${ARGS[@]}"

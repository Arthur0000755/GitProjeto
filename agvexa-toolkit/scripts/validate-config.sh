#!/usr/bin/env bash
# AG Vexa Toolkit - validação da configuração (SOMENTE LEITURA)
set -uo pipefail
. "$(dirname "$0")/lib/common.sh"

usage() {
    cat <<EOF
Uso: scripts/validate-config.sh [--staging DIR] [--quiet] [--help]

Valida, sem alterar arquivos:
  - estrutura obrigatória do projeto e o arquivo VERSION;
  - ventoy/ventoy.json: JSON/UTF-8 sem BOM, plugins e opções documentados
    no Ventoy ${VENTOY_REF:-1.1.18}, caminhos absolutos, limites de tamanho,
    política de segurança (sem boot automático, sem bypass do Windows 11);
  - correspondência entre catalog/categorias.json e ventoy/ventoy.json;
  - temas (theme.txt): sintaxe, propriedades conhecidas, cores, imagens
    referenciadas, formato PNG aceito pelo GRUB, ícones e versão no rodapé;
  - menu F6 (ventoy_grub.cfg): apenas comandos informativos/energia;
  - catálogo de ferramentas e manifestos de ISOs.

Opções:
  --staging DIR  também valida um staging gerado (ex.: build/staging)
  --quiet        mostra apenas o resumo, avisos e erros
  --help         mostra esta ajuda

Importante: passar nesta validação NÃO garante que o boot funcione em
hardware real. Veja docs/plano-de-testes-boot.md.

Códigos de saída: 0 válido | 2 válido com avisos | 1 erros | 64 uso incorreto
EOF
}

ARGS=()
while [ $# -gt 0 ]; do
    case "$1" in
        -h|--help) usage; exit 0 ;;
        --staging)
            [ $# -ge 2 ] || agv_die_usage "--staging exige um diretório"
            agv_refuse_device_path "$2"
            ARGS+=(--staging "$2"); shift ;;
        --quiet) ARGS+=(--quiet) ;;
        *) agv_die_usage "opção desconhecida: $1" ;;
    esac
    shift
done

agv_require_python
python3 "$AGV_PY" validate "${ARGS[@]}"

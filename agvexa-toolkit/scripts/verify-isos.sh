#!/usr/bin/env bash
# AG Vexa Toolkit - verificação de integridade das ISOs (SOMENTE LEITURA nas ISOs)
set -uo pipefail
. "$(dirname "$0")/lib/common.sh"

usage() {
    cat <<EOF
Uso: scripts/verify-isos.sh [opções]

Confere cada item do manifesto de ISOs:
  - existência do arquivo na biblioteca;
  - extensão e tipo real (assinatura ISO 9660 ou tabela MBR/GPT);
  - tamanho (quando declarado no manifesto);
  - SHA-256 calculado x SHA-256 OFICIAL (campo "sha256" ou arquivo de
    checksums oficial indicado em "arquivo_checksums");
  - fonte oficial declarada (https://);
  - arquivos presentes na biblioteca mas ausentes do manifesto.

Status possíveis:
  VERIFICADA          SHA-256 confere com a fonte oficial
  NAO_VERIFICADA      sem checksum oficial registrado (integridade NÃO comprovada)
  DIVERGENTE          SHA-256 diferente do oficial: NÃO use o arquivo
  TIPO_INVALIDO       extensão/assinatura inesperada
  TAMANHO_DIVERGENTE  tamanho difere do declarado
  AUSENTE             arquivo não encontrado
  DESABILITADA        item desabilitado no manifesto
  NAO_CATALOGADA      arquivo na biblioteca sem entrada no manifesto

Opções:
  --manifest ARQ   manifesto (padrão: catalog/isos-manifest.json)
  --library DIR    biblioteca de ISOs (padrão: isos/)
  --report-dir DIR onde salvar o relatório JSON (padrão: reports/)
  --no-cache       recalcula todos os SHA-256 (o cache usa tamanho+data)
  --quiet          menos mensagens durante o cálculo
  --help           mostra esta ajuda

Os arquivos de ISO são apenas lidos. Este script nunca cria checksums
"esperados": eles devem vir da fonte oficial.

Códigos de saída: 0 tudo verificado | 2 há itens ausentes/não verificados
                  1 há divergências ou arquivos inválidos | 64 uso incorreto
EOF
}

ARGS=()
while [ $# -gt 0 ]; do
    case "$1" in
        -h|--help) usage; exit 0 ;;
        --manifest|--library|--report-dir)
            [ $# -ge 2 ] || agv_die_usage "$1 exige um valor"
            agv_refuse_device_path "$2"
            ARGS+=("$1" "$2"); shift ;;
        --no-cache|--quiet) ARGS+=("$1") ;;
        *) agv_die_usage "opção desconhecida: $1" ;;
    esac
    shift
done

agv_require_python
python3 "$AGV_PY" verify-isos "${ARGS[@]}"

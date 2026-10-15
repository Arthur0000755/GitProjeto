#!/usr/bin/env bash
# AG Vexa Toolkit - executa todos os testes automatizados disponíveis.
# Não usa sudo, não acessa dispositivos, não usa rede.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
. "$ROOT/scripts/lib/common.sh"

if [ "${1:-}" = "--help" ] || [ "${1:-}" = "-h" ]; then
    echo "Uso: tests/run-all.sh"
    echo "Executa: sintaxe bash, shellcheck (se houver), ajuda dos scripts,"
    echo "testes unitários Python (tests/unit), validação da configuração e,"
    echo "se pwsh estiver instalado, a análise sintática do Windows Optimizer."
    echo "Códigos de saída: 0 tudo passou | 1 alguma falha"
    exit 0
fi

PASS=0; FAIL=0; SKIP=0
pass() { agv_ok "$*"; PASS=$((PASS+1)); }
fail() { agv_err "$*"; FAIL=$((FAIL+1)); }
skip() { agv_warn "PULADO: $*"; SKIP=$((SKIP+1)); }

echo "${C_BOLD}[1] Sintaxe dos scripts bash${C_RESET}"
while IFS= read -r f; do
    if bash -n "$f" 2>/tmp/agv-bashn.$$; then pass "bash -n ${f#"$ROOT"/}"
    else fail "bash -n ${f#"$ROOT"/}: $(cat /tmp/agv-bashn.$$)"; fi
done < <(find "$ROOT/scripts" "$ROOT/tests" -name '*.sh' -type f | sort)
rm -f /tmp/agv-bashn.$$

echo; echo "${C_BOLD}[2] shellcheck${C_RESET}"
if command -v shellcheck >/dev/null 2>&1; then
    if shellcheck -x -S warning "$ROOT"/scripts/*.sh "$ROOT"/scripts/lib/common.sh "$ROOT"/tests/run-all.sh; then
        pass "shellcheck sem avisos"
    else fail "shellcheck encontrou problemas"; fi
else
    skip "shellcheck não instalado"
fi

echo; echo "${C_BOLD}[3] --help de todos os scripts${C_RESET}"
for s in preflight validate-config verify-isos prepare-staging test-boot novo-relatorio; do
    out="$(bash "$ROOT/scripts/$s.sh" --help 2>&1)"; rc=$?
    if [ $rc = 0 ] && printf '%s' "$out" | grep -q "Uso"; then pass "$s.sh --help"
    else fail "$s.sh --help (rc=$rc)"; fi
    bash "$ROOT/scripts/$s.sh" --opcao-inexistente >/dev/null 2>&1; rc=$?
    if [ $rc = 64 ]; then pass "$s.sh rejeita opção inválida (64)"; else fail "$s.sh com opção inválida retornou $rc"; fi
done

echo; echo "${C_BOLD}[4] Testes unitários (Python)${C_RESET}"
if python3 -m unittest discover -s "$ROOT/tests/unit" -t "$ROOT" -v 2>&1 | tee /tmp/agv-unit.$$ | tail -n 4; then
    if grep -q "^OK" /tmp/agv-unit.$$; then pass "unittest"; else fail "unittest (ver saída acima)"; fi
else
    fail "unittest"
fi
rm -f /tmp/agv-unit.$$

echo; echo "${C_BOLD}[5] Validação da configuração do projeto${C_RESET}"
bash "$ROOT/scripts/validate-config.sh" --quiet; rc=$?
if [ $rc = 0 ] || [ $rc = 2 ]; then pass "validate-config.sh (rc=$rc; 2 = apenas avisos)"
else fail "validate-config.sh (rc=$rc)"; fi

echo; echo "${C_BOLD}[6] PowerShell (Windows Optimizer)${C_RESET}"
if command -v pwsh >/dev/null 2>&1; then
    if pwsh -NoProfile -NonInteractive -File "$ROOT/windows-optimizer/tests/Invoke-AGVexaSelfTest.ps1" -SyntaxOnly; then
        pass "análise sintática com pwsh"
    else fail "análise sintática com pwsh"; fi
else
    skip "pwsh não instalado: sintaxe PowerShell só verificada estaticamente (tests/unit/test_powershell_static.py)"
fi

echo
echo "Resultado: $PASS passou, $FAIL falhou, $SKIP pulado(s)."
[ "$FAIL" = 0 ]

#!/usr/bin/env bash
# AG Vexa Toolkit - testes automatizados dos arquivos e teste de boot virtual opcional
set -uo pipefail
. "$(dirname "$0")/lib/common.sh"

usage() {
    cat <<EOF
Uso:
  scripts/test-boot.sh                 executa os testes automatizados dos arquivos
                                       (tests/run-all.sh) e informa se o teste
                                       virtual é possível neste computador
  scripts/test-boot.sh --check         só verifica dependências do teste virtual
  scripts/test-boot.sh --plan [--image ARQ]
                                       mostra (NÃO executa) o procedimento para
                                       criar uma imagem de disco Ventoy descartável
  scripts/test-boot.sh --vm --image ARQ [opções da VM]
                                       inicia a imagem em QEMU, isolada

Opções da VM:
  --firmware F    bios | uefi | uefi-sb (UEFI com Secure Boot, se houver OVMF .secboot)
  --bus B         usb (padrão, simula HD externo) | sata
  --memory MB     memória da VM (padrão 1024; mínimo 512, máximo 2048)
  --headless      sem janela; tira uma captura de tela após --delay segundos
  --delay S       espera antes da captura (padrão 25)
  --vnc           exibe via VNC somente em 127.0.0.1:5901 (use túnel SSH)
  --help          mostra esta ajuda

Garantias de segurança:
  - a imagem é aberta com -snapshot: NADA é gravado nela;
  - aceita somente ARQUIVO comum (.img/.raw); recusa /dev e dispositivos;
  - sem rede na VM (-nic none), 1 vCPU, prioridade baixa (nice);
  - não usa sudo. Criar a imagem Ventoy exige privilégios e por isso
    o procedimento é apenas exibido (--plan) para execução autorizada.

Resultados de VM são registrados em reports/ como PENDENTE_REVISAO_HUMANA:
uma VM que exibe o menu não prova o boot em hardware real.

Códigos de saída: 0 sucesso | 1 falha | 2 teste indisponível neste ambiente | 64 uso incorreto
EOF
}

MODE="files"; IMAGE=""; FIRMWARE="uefi"; BUS="usb"; MEM=1024; HEADLESS=0; DELAY=25; VNC=0
while [ $# -gt 0 ]; do
    case "$1" in
        -h|--help) usage; exit 0 ;;
        --check) MODE="check" ;;
        --plan) MODE="plan" ;;
        --vm) MODE="vm" ;;
        --image) [ $# -ge 2 ] || agv_die_usage "--image exige um arquivo"; IMAGE="$2"; shift ;;
        --firmware) [ $# -ge 2 ] || agv_die_usage "--firmware exige bios|uefi|uefi-sb"; FIRMWARE="$2"; shift ;;
        --bus) [ $# -ge 2 ] || agv_die_usage "--bus exige usb|sata"; BUS="$2"; shift ;;
        --memory) [ $# -ge 2 ] || agv_die_usage "--memory exige um número"; MEM="$2"; shift ;;
        --delay) [ $# -ge 2 ] || agv_die_usage "--delay exige segundos"; DELAY="$2"; shift ;;
        --headless) HEADLESS=1 ;;
        --vnc) VNC=1 ;;
        *) agv_die_usage "opção desconhecida: $1" ;;
    esac
    shift
done

case "$FIRMWARE" in bios|uefi|uefi-sb) ;; *) agv_die_usage "--firmware inválido: $FIRMWARE" ;; esac
case "$BUS" in usb|sata) ;; *) agv_die_usage "--bus inválido: $BUS" ;; esac
case "$MEM" in ''|*[!0-9]*) agv_die_usage "--memory deve ser número" ;; esac
case "$DELAY" in ''|*[!0-9]*) agv_die_usage "--delay deve ser número" ;; esac
[ "$MEM" -ge 512 ] && [ "$MEM" -le 2048 ] || agv_die_usage "--memory deve ficar entre 512 e 2048 (servidor compartilhado)"

find_ovmf() { # tipo -> "CODE VARS"
    local sb="$1" c v
    if [ "$sb" = 1 ]; then
        for c in /usr/share/OVMF/OVMF_CODE_4M.secboot.fd /usr/share/OVMF/OVMF_CODE.secboot.fd; do
            for v in /usr/share/OVMF/OVMF_VARS_4M.ms.fd /usr/share/OVMF/OVMF_VARS.ms.fd; do
                [ -r "$c" ] && [ -r "$v" ] && { echo "$c $v"; return 0; }
            done
        done
        return 1
    fi
    for c in /usr/share/OVMF/OVMF_CODE_4M.fd /usr/share/OVMF/OVMF_CODE.fd; do
        for v in /usr/share/OVMF/OVMF_VARS_4M.fd /usr/share/OVMF/OVMF_VARS.fd; do
            [ -r "$c" ] && [ -r "$v" ] && { echo "$c $v"; return 0; }
        done
    done
    return 1
}

check_deps() {
    local rc=0
    if command -v qemu-system-x86_64 >/dev/null 2>&1; then agv_ok "QEMU: $(command -v qemu-system-x86_64)"
    else agv_warn "QEMU ausente (instalação exige autorização: pacote qemu-system-x86)"; rc=2; fi
    if find_ovmf 0 >/dev/null; then agv_ok "OVMF (UEFI): $(find_ovmf 0)"
    else agv_warn "OVMF ausente: teste UEFI indisponível (pacote ovmf, requer autorização)"; fi
    if find_ovmf 1 >/dev/null; then agv_ok "OVMF Secure Boot: $(find_ovmf 1)"
    else agv_warn "OVMF com Secure Boot ausente: teste uefi-sb indisponível"; fi
    if [ -r /dev/kvm ] && [ -w /dev/kvm ]; then agv_ok "KVM disponível"
    else agv_warn "sem KVM: a VM será emulada (muito lenta no Pentium T4500)"; fi
    return $rc
}

print_plan() {
    local img="${IMAGE:-$AGV_ROOT/build/test-boot/ventoy-teste.img}"
    cat <<EOF
${C_BOLD}PROCEDIMENTO (NÃO EXECUTADO) - imagem de disco Ventoy descartável${C_RESET}

Objetivo: testar o menu em VM sem tocar em nenhum disco físico.
Exige: autorização do proprietário, sudo, pacote Ventoy oficial verificado,
suporte a exFAT no kernel. Recursos: ~8 GiB livres no SSD.

 1) Baixar Ventoy (linux.tar.gz) da página oficial de releases e conferir
    o SHA-256 publicado na página da release. Extrair em vendor/ (fora do Git).
 2) Criar arquivo esparso (não consome espaço até ser usado):
      mkdir -p "$(dirname "$img")"
      truncate -s 8G "$img"
 3) [SUDO] Associar a um dispositivo loop e ANOTAR o nome exibido:
      sudo losetup --find --show --partscan "$img"
      # saída esperada: /dev/loopN   <- use exatamente este nome
 4) [SUDO] Conferir que é o loop do arquivo correto antes de seguir:
      losetup -l | grep "$img"
 5) [SUDO] Instalar Ventoy no LOOP (nunca em /dev/sdX):
      sudo sh vendor/ventoy-<versão>/Ventoy2Disk.sh -i -g /dev/loopN
 6) [SUDO] Copiar o staging para a partição 1 e desmontar:
      sudo mkdir -p /mnt/agvexa-teste
      sudo mount /dev/loopNp1 /mnt/agvexa-teste
      sudo cp -rL "$AGV_ROOT/build/staging/." /mnt/agvexa-teste/
      sudo umount /mnt/agvexa-teste
      sudo losetup -d /dev/loopN
 7) Testar (sem sudo):
      scripts/test-boot.sh --vm --image "$img" --firmware uefi --headless
      scripts/test-boot.sh --vm --image "$img" --firmware bios --headless

Descartar depois: rm "$img"
EOF
}

run_vm() {
    [ -n "$IMAGE" ] || agv_die_usage "--vm exige --image ARQ"
    agv_refuse_device_path "$IMAGE"
    [ -f "$IMAGE" ] && [ ! -L "$IMAGE" ] || agv_die_usage "imagem deve ser um arquivo comum existente: $IMAGE"
    case "$IMAGE" in *.img|*.raw) ;; *) agv_die_usage "use imagem .img ou .raw" ;; esac
    command -v qemu-system-x86_64 >/dev/null 2>&1 || { agv_warn "QEMU indisponível; nada executado."; exit "$AGV_EXIT_WARN"; }

    local out stamp args=() accel="tcg"
    stamp="$(date +%Y%m%d-%H%M%S)"
    out="$AGV_ROOT/build/test-boot/$stamp-$FIRMWARE"
    mkdir -p "$out"
    [ -r /dev/kvm ] && [ -w /dev/kvm ] && accel="kvm"
    args+=(-machine "q35,accel=$accel" -m "$MEM" -smp 1 -nic none -snapshot)
    if [ "$FIRMWARE" != bios ]; then
        local pair code vars sb=0
        [ "$FIRMWARE" = uefi-sb ] && sb=1
        pair="$(find_ovmf "$sb")" || { agv_warn "OVMF necessário não encontrado; nada executado."; exit "$AGV_EXIT_WARN"; }
        code="${pair%% *}"; vars="${pair##* }"
        cp "$vars" "$out/OVMF_VARS.fd"   # cópia descartável das variáveis UEFI
        args+=(-drive "if=pflash,format=raw,readonly=on,file=$code" -drive "if=pflash,format=raw,file=$out/OVMF_VARS.fd")
    fi
    args+=(-drive "if=none,id=agvdisk,format=raw,file=$IMAGE")
    if [ "$BUS" = usb ]; then
        args+=(-device qemu-xhci -device "usb-storage,drive=agvdisk,bootindex=0")
    else
        args+=(-device ahci,id=ahci0 -device "ide-hd,drive=agvdisk,bus=ahci0.0,bootindex=0")
    fi
    local mon="$out/monitor.sock"
    if [ "$HEADLESS" = 1 ]; then
        args+=(-display none -monitor "unix:$mon,server=on,wait=off")
    elif [ "$VNC" = 1 ]; then
        args+=(-display none -vnc 127.0.0.1:1)
    fi

    agv_info "Iniciando VM ($FIRMWARE, $BUS, ${MEM} MiB, $accel). Imagem aberta em modo snapshot."
    printf '%q ' qemu-system-x86_64 "${args[@]}" > "$out/comando.txt"; echo >> "$out/comando.txt"
    if [ "$HEADLESS" = 1 ]; then
        nice -n 10 qemu-system-x86_64 "${args[@]}" > "$out/qemu.log" 2>&1 &
        local qpid=$!
        sleep "$DELAY"
        python3 - "$mon" "$out/tela.ppm" <<'PY' || true
import socket, sys, time
s = socket.socket(socket.AF_UNIX); s.connect(sys.argv[1]); s.settimeout(5)
for cmd in ("screendump %s\n" % sys.argv[2], "quit\n"):
    s.sendall(cmd.encode()); time.sleep(1.5)
s.close()
PY
        wait "$qpid" 2>/dev/null
        if [ -f "$out/tela.ppm" ] && python3 -c 'import PIL' 2>/dev/null; then
            python3 -c 'import sys; from PIL import Image; Image.open(sys.argv[1]).save(sys.argv[2])' "$out/tela.ppm" "$out/tela.png" && rm -f "$out/tela.ppm"
        fi
    else
        nice -n 10 qemu-system-x86_64 "${args[@]}" 2>&1 | tee "$out/qemu.log"
    fi

    local report="$AGV_ROOT/reports/teste-boot-vm-$stamp.txt"
    {
        echo "AG Vexa Toolkit $AGV_VERSION - teste de boot em VM"
        echo "data: $stamp"
        echo "imagem: $IMAGE (snapshot, não modificada)"
        echo "firmware: $FIRMWARE | barramento: $BUS | memória: $MEM MiB | aceleração: $accel"
        echo "artefatos: $out"
        echo "resultado: PENDENTE_REVISAO_HUMANA (abra a captura/tela e registre em docs/relatorio-de-validacao.md)"
    } > "$report"
    agv_ok "Registro salvo em ${report#"$AGV_ROOT"/}"
}

case "$MODE" in
    check) agv_banner "dependências do teste de boot virtual"; check_deps; exit $? ;;
    plan)  print_plan; exit 0 ;;
    vm)    agv_banner "teste de boot em máquina virtual"; run_vm; exit 0 ;;
    files)
        agv_banner "testes automatizados"
        bash "$AGV_ROOT/tests/run-all.sh"; rc=$?
        echo
        echo "${C_BOLD}Teste de boot virtual${C_RESET}"
        check_deps; vm_rc=$?
        if [ "$vm_rc" != 0 ]; then
            agv_info "Teste de boot virtual: NÃO TESTADO neste ambiente (dependências ausentes)."
            agv_info "Veja: scripts/test-boot.sh --plan"
        fi
        exit $rc ;;
esac

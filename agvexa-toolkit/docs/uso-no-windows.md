# Usando o AG Vexa Toolkit a partir do Windows

Estação de trabalho de referência: **Windows 10 Enterprise LTSC** (tem BitLocker completo).
Vale também para Windows 10/11 Pro.

## 1. Quem faz o quê

| Parte | Onde roda | Para quê |
|---|---|---|
| Scripts de preparação (`scripts/*.sh`) | **servidor Ubuntu** | verificar ISOs, montar a cópia (`build/staging`) |
| Instalação do Ventoy e cópia para o HD | **Windows da bancada** | preparar o HD de 320 GB |
| HD de 320 GB (boot + menu AG Vexa) | **computadores dos clientes** | diagnóstico, backup, recuperação, instalação |
| Windows Optimizer | **Windows dos clientes** (pós-formatação) | diagnóstico e ajustes seguros |
| HD de 1 TB criptografado | **bancada** | arquivo da empresa e backups de clientes (`hd-arquivo-1tb.md`) |

## 2. No servidor: preparar a cópia

```bash
git clone https://github.com/Arthur0000755/GitProjeto ~/GitProjeto
cd ~/GitProjeto/agvexa-toolkit
bash scripts/preflight.sh            # confere o ambiente (só lê)
bash scripts/test-boot.sh            # testes automatizados
```

Baixe as ISOs **somente dos sites oficiais** (`docs/ferramentas.md`) para `isos/<ferramenta>/`,
junto com os arquivos de checksum oficiais. Depois:

```bash
cp catalog/isos-manifest.example.json catalog/isos-manifest.json
nano catalog/isos-manifest.json      # arquivos, versões e SHA-256 OFICIAIS
bash scripts/verify-isos.sh          # todas precisam ficar VERIFICADA
bash scripts/prepare-staging.sh --iso-mode copy
bash scripts/validate-config.sh --staging build/staging
```

`--iso-mode copy` gera arquivos reais (não links), prontos para ir ao Windows.

## 3. Levar a cópia para o Windows

Copie a pasta `build/staging/` do servidor para o Windows, por exemplo:

- **WinSCP** (site oficial): conecte por SFTP ao servidor e arraste a pasta; ou
- pasta compartilhada já existente na rede da empresa.

Destino recomendado: HD de 1 TB, em `TOOLKIT-MESTRE\staging\` (cópia mestre).

## 4. Instalar o Ventoy no HD de 320 GB — **APAGA O HD**

Antes: confira o conteúdo do HD de 320 GB (salve o que precisar) e a saúde dele com o
CrystalDiskInfo (portátil, site oficial). Disco com "Cuidado"/"Ruim" → não use.

1. Baixe `ventoy-<versão>-windows.zip` da página oficial de releases do Ventoy e confira o
   SHA-256 publicado:
   ```powershell
   Get-FileHash -Algorithm SHA256 .\ventoy-<versão>-windows.zip
   ```
2. Extraia o zip numa pasta (não rode de dentro do zip).
3. **Desconecte o HD de 1 TB** e todos os outros pen drives/HDs externos. Fica só o de 320 GB.
4. Abra `Ventoy2Disk.exe`.
5. Menu **Option**:
   - **Partition Style → MBR**
   - **Secure Boot Support** → marcado
6. Em **Device**, confira: ~298 GB, marca/modelo do seu HD. Na dúvida, **pare**.
7. **Install** → confirme as duas perguntas.
8. Ao terminar, o Windows mostra uma unidade chamada **Ventoy** (exFAT).

## 5. Copiar o toolkit para o HD

1. Abra a pasta `staging` no Explorador de Arquivos.
2. Selecione **todo o conteúdo** (inclusive arquivos ocultos: menu *Exibir → Itens ocultos*) e
   copie para a raiz da unidade **Ventoy**.
3. Apague o arquivo `.agvexa-staging` da raiz do HD (marcador interno).

## 6. Conferir a cópia

No PowerShell (troque `F:` pela letra da unidade Ventoy):

```powershell
cd F:\
$falhas = 0
Get-Content .\SHA256SUMS-AGVEXA.txt | ForEach-Object {
    $hash, $arquivo = $_ -split '  ', 2
    if (-not (Test-Path -LiteralPath $arquivo)) { "AUSENTE: $arquivo"; $falhas++; return }
    if ((Get-FileHash -Algorithm SHA256 -LiteralPath $arquivo).Hash.ToLower() -ne $hash) {
        "FALHOU: $arquivo"; $falhas++
    }
}
if ($falhas -eq 0) { "CÓPIA ÍNTEGRA" } else { "$falhas problema(s): copie de novo os arquivos listados" }
```

ISOs grandes deixam a conferência demorada (minutos). É normal.

Para desconectar: **Remover hardware com segurança**.

## 7. Testar o boot (antes de usar em clientes)

Em um computador **seu**:

1. Conecte o HD de 320 GB, ligue e abra o menu de boot do firmware (F12, F11, F10, F8 ou Esc).
2. Escolha a entrada **UEFI** do HD.
3. Com Secure Boot ativo, o primeiro boot abre o **MokManager**: em equipamento seu, registre a
   chave (*Enroll key from disk* → VTOYEFI → `ENROLL_THIS_KEY_IN_MOKMANAGER.cer`).
4. Confira: tema AG Vexa, categorias que têm ferramentas, F6 (informações), F5 (tema leve).
5. Entre em cada ferramenta e veja se inicia.
6. Registre os resultados em `docs/relatorio-de-validacao.md` (Aprovado / Com ressalvas /
   Falhou / Não testado).

Roteiro completo: `docs/plano-de-testes-boot.md`.

## 8. Primeiro teste do Windows Optimizer na sua estação

O Optimizer ainda não foi executado em Windows real. O autoteste abaixo é seguro na sua
máquina: **só lê** configurações; cria e apaga uma chave de teste própria
(`HKCU\Software\AGVexa\SelfTest`) e grava uma sessão em `C:\ProgramData\AGVexa`.

```powershell
cd F:\AGVexa\windows-optimizer        # ou a pasta do projeto
powershell -NoProfile -ExecutionPolicy Bypass -File .\tests\Invoke-AGVexaSelfTest.ps1
```

- Rode uma vez como usuário comum e outra como administrador.
- **Não** use `-CicloReal` (só em máquina virtual de laboratório).
- Envie o resultado (as linhas `[FALHOU]`) para correção.

## 9. Atualizar o HD depois

1. No servidor: atualize ISOs/arquivos, rode `verify-isos.sh` e `prepare-staging.sh --iso-mode copy`.
2. No Windows: copie a nova `staging` por cima do conteúdo do HD (o Ventoy **não** precisa ser
   reinstalado) e repita a conferência da seção 6.
3. Atualizar o próprio Ventoy: `Ventoy2Disk.exe` → **Update** (preserva os arquivos; mantenha
   a cópia mestre no HD de 1 TB mesmo assim).

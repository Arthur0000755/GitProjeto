# Integração futura com o MAPOS (somente documentação)

**Nada foi implementado nem acessado nesta etapa.** O MAPOS e seus bancos de
dados não foram consultados; nenhuma credencial foi usada.

## Ideia

Associar relatórios do toolkit à ordem de serviço do MAPOS, sem digitação dupla.

## Princípios para quando for implementada

1. **Exportação manual primeiro:** o técnico anexa `relatorio.html`/`.md` à OS no MAPOS
   pela própria interface do MAPOS. Zero integração técnica, zero risco.
2. Se houver integração automática no futuro:
   - via API/recurso **documentado** do MAPOS, nunca escrevendo direto no banco;
   - credencial **própria e de menor privilégio** (não reutilizar credenciais de outros projetos);
   - executada no servidor, nunca a partir do HD do toolkit em computadores de clientes;
   - envio apenas de dados técnicos já presentes no relatório (sem identificadores pessoais extras);
   - registro de auditoria e possibilidade de desativar.
3. Campo de ligação: o número da OS já existe nos relatórios (`--os` / `-OrdemServico`).

## Pendência que exige decisão do proprietário

- Se e quando integrar; qual versão do MAPOS; quem administra a credencial.

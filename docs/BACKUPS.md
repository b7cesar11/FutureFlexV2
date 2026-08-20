# Future Flex V2 — Backup e restauração

## Objetivo

Os dados financeiros não devem depender de memória humana nem do disco do servidor web.

A política padrão do Future Flex usa:

- MongoDB como fonte primária;
- `mongodump --archive --gzip` para snapshot lógico consistente;
- criptografia AES-256-CBC com PBKDF2 **antes** do upload;
- object storage S3-compatible fora do provedor da aplicação;
- Cron Job diário independente do web service;
- rotação automática de restore points;
- teste de backup + restauração no CI usando MongoDB + MinIO isolados.

O `render.yaml` está preparado para Cloudflare R2, mas os scripts aceitam qualquer storage compatível com S3 que forneça endpoint, bucket e access keys.

## Agenda e retenção padrão

O Cron Job executa diariamente às `06:17 UTC` (`03:17` no horário de Brasília quando UTC-3).

Restore points mantidos:

- 14 backups diários;
- 8 backups semanais (domingo);
- 12 backups mensais (dia 1).

A rotação ocorre automaticamente após cada backup bem-sucedido.

## Secrets necessários no serviço de backup

Nunca coloque estes valores no Git:

```text
BACKUP_MONGO_URL=<URI do MongoDB com permissão de leitura do banco>
BACKUP_DB_NAME=futureflex_staging   # deve ser igual ao DB_NAME da API desse ambiente
BACKUP_BUCKET=<nome do bucket>
BACKUP_S3_ENDPOINT=<endpoint S3-compatible>
AWS_ACCESS_KEY_ID=<access key restrita ao bucket>
AWS_SECRET_ACCESS_KEY=<secret key>
AWS_DEFAULT_REGION=auto
BACKUP_ENCRYPTION_PASSPHRASE=<passphrase longa e única>
```

Guarde `BACKUP_ENCRYPTION_PASSPHRASE` em um gerenciador de senhas fora do Render e fora do GitHub. Se essa passphrase for perdida, os backups criptografados não poderão ser recuperados.

Para Cloudflare R2, crie um token com acesso somente ao bucket de backups. Não reutilize credenciais administrativas da conta Cloudflare.

## Estrutura dos objetos

```text
futureflex/
  daily/YYYY-MM-DD/<db>_<timestamp>.archive.gz.enc
  weekly/YYYY-MM-DD/<db>_<timestamp>.archive.gz.enc
  monthly/YYYY-MM-DD/<db>_<timestamp>.archive.gz.enc
```

Cada objeto recebe metadata com:

- SHA-256 do arquivo criptografado;
- nome do banco de origem;
- timestamp UTC de criação.

O job valida o tamanho remoto após o upload. Na restauração, o SHA-256 é conferido antes da descriptografia.

## Teste de restauração

A imagem de backup também contém `/usr/local/bin/futureflex-restore`.

Por segurança, a restauração recusa sobrescrever o banco de origem. O fluxo normal de teste deve restaurar para um banco isolado, por exemplo:

```text
BACKUP_DB_NAME=futureflex_staging
RESTORE_DB_NAME=futureflex_restore_test
```

Variáveis adicionais:

```text
BACKUP_OBJECT_KEY=futureflex/daily/.../arquivo.archive.gz.enc
RESTORE_MONGO_URL=<URI do MongoDB de destino>
RESTORE_DB_NAME=futureflex_restore_test
```

Nunca use `ALLOW_PRODUCTION_RESTORE=true` em testes. Essa flag existe somente para um procedimento consciente de disaster recovery.

## Disaster recovery real

Em caso de perda/corrupção do banco primário:

1. interromper escritas na API;
2. criar um banco/cluster de recuperação;
3. selecionar um restore point anterior ao incidente;
4. restaurar primeiro em banco com nome diferente;
5. validar usuários, contas, commitments, occurrences, transactions, invoices e projeção;
6. somente após validação decidir a troca da API para o banco recuperado;
7. manter o banco anterior preservado até confirmar a recuperação.

Não restaure diretamente sobre o banco primário como primeira tentativa.

## Monitoramento

Um backup só deve ser considerado válido quando o Cron Job termina com exit code `0`.

Após o deploy inicial:

- execute manualmente o Cron Job uma vez;
- confirme que um objeto aparece em `futureflex/daily/`;
- execute um restore drill para banco isolado;
- verifique o histórico de runs do Cron Job periodicamente;
- mantenha notificações de falha do provedor habilitadas.

## CI

O job `backup-restore-smoke` do GitHub Actions não acessa dados reais. Ele sobe:

- MongoDB temporário em replica set;
- MinIO temporário S3-compatible;
- um documento sintético;
- a imagem real de backup.

Depois executa:

```text
dump → criptografia → upload → checksum → download → descriptografia → restore → verificação do documento
```

Isso protege o mecanismo de backup contra regressões sem expor secrets ou dados financeiros reais.

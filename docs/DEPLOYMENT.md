# Future Flex V2 — Deploy

## Objetivo

O deploy de produção deve ser independente do Preview do Emergent e preservar as garantias financeiras do backend.

## Componentes mínimos

- frontend React servido por HTTPS;
- backend FastAPI servido por HTTPS;
- MongoDB com suporte a transações (replica set ou cluster gerenciado compatível);
- armazenamento persistente/backup do banco;
- variáveis de ambiente gerenciadas fora do Git;
- domínio estável;
- logs do backend e monitoramento de health check.

## Topologias recomendadas

### Mesmo domínio

Exemplo conceitual:

```text
https://app.exemplo.com/       → frontend
https://app.exemplo.com/api/*  → backend
```

Vantagens:

- `REACT_APP_BACKEND_URL` pode ficar vazio;
- cookies podem usar `SameSite=lax`;
- CORS pode ficar desabilitado;
- menor chance de erro de configuração.

### Domínios separados

```text
https://app.exemplo.com
https://api.exemplo.com
```

Nesse caso:

```env
# frontend
REACT_APP_BACKEND_URL=https://api.exemplo.com

# backend
CORS_ORIGINS=https://app.exemplo.com
COOKIE_SECURE=true
COOKIE_SAMESITE=none
```

Use `SameSite=none` somente quando realmente necessário e sempre com HTTPS.

## Variáveis obrigatórias do backend

```env
APP_ENV=production
MONGO_URL=...
DB_NAME=futureflex
JWT_SECRET=...
PROJECTION_WINDOW_MONTHS=24
REQUIRE_REPLICA_SET=true
ENABLE_DEMO_USER=false
COOKIE_SECURE=true
COOKIE_SAMESITE=lax
```

Se frontend/backend forem cross-site, ajuste `COOKIE_SAMESITE` e `CORS_ORIGINS` conforme a seção anterior.

## IA

Preferencial:

```env
OPENAI_API_KEY=...
AI_PROVIDER=openai
AI_MODEL=gpt-5.5
AI_DAILY_LIMIT=60
```

Sem chave configurada, endpoints de IA devem responder indisponibilidade; o motor financeiro deve continuar funcionando normalmente.

## MongoDB

O backend falha no startup por padrão se MongoDB não reportar replica set. Isso é intencional: pagamentos e outras ações multi-documento dependem de ACID.

Em desenvolvimento local use `docker-compose.dev.yml` ou o script legado `scripts/mongo_rs.sh` quando estiver em ambiente compatível.

Em produção, prefira um serviço MongoDB gerenciado que ofereça replica set/transações e backups automáticos.

## Health check

Use:

```text
GET /api/health
```

Resposta saudável deve indicar:

```json
{
  "status": "ok",
  "mongo": "ok",
  "replica_set": "...",
  "transactions_available": true
}
```

## Migração do ambiente legado

Antes de desligar definitivamente o ambiente do Emergent:

1. exporte/backup do banco se houver dados reais;
2. configure o novo MongoDB;
3. configure secrets no novo provedor;
4. suba backend e valide `/api/health`;
5. rode a regressão backend;
6. faça build e deploy do frontend;
7. valide login e onboarding com usuário novo;
8. valide um fluxo financeiro completo com conta de teste;
9. valide Google Login somente depois de migrar OAuth para credenciais próprias;
10. somente então comece a cadastrar dados financeiros reais.

## Backups

Antes do uso real, configure pelo menos:

- backup automático diário;
- retenção mínima definida pelo provedor;
- teste de restauração em ambiente não produtivo;
- acesso administrativo ao banco protegido por credenciais fortes e allow-list/rede privada quando disponível.

## Segredos

Nunca versionar:

- `JWT_SECRET`;
- `OPENAI_API_KEY`;
- credenciais Google OAuth;
- string MongoDB com senha;
- tokens de deploy.

Use o secret manager do provedor escolhido.

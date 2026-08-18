# Future Flex V2 — Deploy

## Objetivo

O deploy deve ser independente do antigo ambiente de Preview e preservar as garantias financeiras do backend. A estratégia escolhida para o Release Candidate é:

```text
GitHub (fonte + CI)
   ↓ checks verdes
Render Static Site  → frontend React
Render Web Service  → FastAPI
   ↓
MongoDB Atlas       → banco externo com replica set/transações
```

O arquivo `render.yaml` da raiz descreve o staging inicial. Ele **não contém segredos** e não provisiona MongoDB.

> Regra de segurança: staging não recebe dados financeiros pessoais reais. O primeiro deploy pode usar recursos de baixo custo apenas para smoke/QA. Antes do uso real, promova backend e banco para tiers adequados ao uso contínuo e valide backups/restauração.

## 1. Pré-requisito obrigatório: CI verde

Nunca faça deploy de produção a partir de um commit com checks falhando.

A CI atual valida:

- guards de configuração de produção;
- vínculo/expiração do `state` do Google OAuth;
- `render.yaml` sem segredos e com guards financeiros;
- regras financeiras centrais;
- valores dinâmicos;
- regressão E2E backend;
- build React com `yarn.lock` congelado;
- Playwright desktop e mobile, incluindo pagamento e cartão/fatura sem dupla contagem.

## 2. MongoDB Atlas — staging

Crie um projeto/cluster separado para staging. Não reutilize banco de produção nem banco legado de Preview.

Crie um usuário de banco exclusivo para o Future Flex e copie a connection string completa para `MONGO_URL` no Render. O backend não depende do nome local `rs0`; ele consulta `hello.setName` no startup e aceita o nome de replica set fornecido pelo cluster gerenciado.

Configuração do banco para staging:

```env
DB_NAME=futureflex_staging
REQUIRE_REPLICA_SET=true
```

No controle de acesso de rede do Atlas, prefira liberar somente os IPs de saída do serviço backend. Evite `0.0.0.0/0` em produção.

Depois que o backend subir, confirme:

```text
GET https://<api-staging>/api/health
```

Resposta esperada:

```json
{
  "status": "ok",
  "mongo": "ok",
  "replica_set": "<nome-do-replica-set>",
  "transactions_available": true
}
```

Se `transactions_available` for `false`, **não prossiga**.

## 3. Render Blueprint — staging

No Render, conecte o repositório `b7cesar11/FutureFlexV2` e crie os serviços a partir de `render.yaml`.

O Blueprint cria conceitualmente:

- `futureflex-api`: FastAPI;
- `futureflex-web`: static React.

O backend de staging já é configurado com:

```env
APP_ENV=production
PROJECTION_WINDOW_MONTHS=24
REQUIRE_REPLICA_SET=true
ENABLE_DEMO_USER=false
COOKIE_SECURE=true
COOKIE_SAMESITE=none
```

`APP_ENV=production` em staging é intencional: queremos testar os mesmos guards de segurança da produção.

### Variáveis que precisam ser preenchidas manualmente

No `futureflex-api`:

```env
MONGO_URL=<connection string Atlas>
FRONTEND_URL=https://<futureflex-web>.onrender.com
CORS_ORIGINS=https://<futureflex-web>.onrender.com
```

O `JWT_SECRET` é gerado pelo Blueprint.

No `futureflex-web`:

```env
REACT_APP_BACKEND_URL=https://<futureflex-api>.onrender.com
```

Não acrescente `/api` ao valor; o frontend adiciona esse prefixo.

Depois de alterar `REACT_APP_BACKEND_URL`, reconstrua/republique o frontend porque variáveis `REACT_APP_*` são incorporadas ao bundle no build.

## 4. Smoke obrigatório no staging

Use somente uma conta de teste descartável.

Valide nesta ordem:

1. `/api/health` com `transactions_available=true`;
2. cadastro por e-mail/senha;
3. onboarding e primeira conta;
4. reload sem reaparecer onboarding;
5. criar compromisso em conta — saldo não muda ao planejar;
6. pagar compromisso — exatamente uma transação e débito correto;
7. criar cartão;
8. criar compra parcelada — saldo bancário não muda;
9. confirmar que parcelas apenas compõem a fatura;
10. confirmar que o comprometido conta a fatura uma única vez;
11. pagar a fatura — apenas então a conta é debitada;
12. Dashboard e Compromissos permanecem coerentes;
13. navegação desktop e mobile;
14. nenhuma resposta HTTP 500 no fluxo.

Esses fluxos também estão automatizados no Playwright; o smoke externo confirma configuração real de rede/cookies/domínios.

## 5. OpenAI

A integração é opcional para o primeiro smoke do motor financeiro.

Quando for habilitar o Analista IA:

```env
OPENAI_API_KEY=<secret>
AI_MODEL=gpt-5.5
AI_DAILY_LIMIT=60
```

A chave entra somente no secret manager do backend. Nunca no frontend ou Git.

Sem chave, o motor financeiro continua funcionando; apenas recursos de IA ficam indisponíveis.

## 6. Google OAuth

E-mail/senha funciona sem Google OAuth. Configure Google somente depois que a URL final do backend estiver definida.

Crie um OAuth Client do tipo Web Application em um projeto Google Cloud sob seu controle e configure no backend:

```env
GOOGLE_CLIENT_ID=<secret/config>
GOOGLE_CLIENT_SECRET=<secret>
GOOGLE_REDIRECT_URI=https://<api>/api/auth/google/callback
```

A Redirect URI cadastrada no Google deve corresponder **exatamente** a `GOOGLE_REDIRECT_URI`.

O backend protege o fluxo com:

- `state` assinado e expirável;
- nonce;
- cookie HttpOnly temporário vinculado ao navegador iniciador;
- comparação segura no callback;
- validação do ID token e `email_verified`;
- proteção contra substituição silenciosa de `google_sub` já vinculado.

## 7. Promoção para produção

Antes de dados reais:

1. escolha tier de backend sem suspensão por inatividade e compatível com uso contínuo;
2. escolha tier MongoDB adequado a produção e política de backup desejada;
3. configure backup automático;
4. execute uma **restauração de teste** em banco não produtivo;
5. configure domínio próprio e HTTPS;
6. configure allow-list de rede do banco;
7. configure secrets de produção;
8. execute smoke completo com conta descartável;
9. só então libere cadastro/uso real.

### Topologia final recomendada

Prefira subdomínios sob o mesmo domínio registrável:

```text
https://app.seudominio.com  → frontend
https://api.seudominio.com  → backend
```

Nesse cenário, use:

```env
# frontend
REACT_APP_BACKEND_URL=https://api.seudominio.com

# backend
FRONTEND_URL=https://app.seudominio.com
CORS_ORIGINS=https://app.seudominio.com
COOKIE_SECURE=true
COOKIE_SAMESITE=lax
```

O staging com dois domínios `*.onrender.com` usa `SameSite=none` + `Secure` porque os sites são cross-site. Na topologia final sob o mesmo domínio registrável, volte para `SameSite=lax`.

## 8. Variáveis obrigatórias de produção

```env
APP_ENV=production
MONGO_URL=<secret>
DB_NAME=futureflex
JWT_SECRET=<secret aleatório 32+ caracteres>
PROJECTION_WINDOW_MONTHS=24
REQUIRE_REPLICA_SET=true
ENABLE_DEMO_USER=false
COOKIE_SECURE=true
COOKIE_SAMESITE=lax
FRONTEND_URL=https://app.seudominio.com
CORS_ORIGINS=https://app.seudominio.com
```

Opcionalmente:

```env
OPENAI_API_KEY=<secret>
AI_MODEL=gpt-5.5
AI_DAILY_LIMIT=60
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=<secret>
GOOGLE_REDIRECT_URI=https://api.seudominio.com/api/auth/google/callback
```

## 9. Backups

Antes do uso real, exija pelo menos:

- backup automático;
- retenção documentada;
- restauração testada em ambiente não produtivo;
- usuário de banco exclusivo da aplicação;
- credenciais fortes;
- acesso administrativo separado da aplicação;
- restrição de rede quando disponível.

Um backup que nunca foi restaurado ainda não é uma garantia operacional.

## 10. Segredos

Nunca versionar:

- `JWT_SECRET`;
- `OPENAI_API_KEY`;
- `GOOGLE_CLIENT_SECRET`;
- string MongoDB com senha;
- tokens de deploy.

Use sempre o secret manager do provedor.

## 11. Go / No-Go

**GO para staging:** CI verde + Atlas de teste + variáveis do Blueprint preenchidas.

**GO para dados reais:** staging verde + tier de produção definido + backup/restauração testados + domínio/HTTPS + smoke de produção verde + PR mergeado/tagueado.

Qualquer item ausente mantém o sistema em **NO-GO para dados financeiros reais**.

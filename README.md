# Future Flex V2

Future Flex V2 é uma aplicação de planejamento financeiro pessoal orientada ao futuro. O núcleo do produto é **Compromissos do Mês**: uma visão única do que já está financeiramente comprometido em cada competência, incluindo recorrências, parcelas, faturas, assinaturas, terceiros e atrasados — sem dupla contagem.

## Estado do projeto

O MVP funcional está implementado e está em **Release Candidate / hardening de produção**. O motor financeiro possui regressão automatizada para parcelamentos, cartões/faturas, pagamentos, valores dinâmicos, terceiros, congelamento, projeção, ownership e transações ACID. O frontend também possui Playwright desktop/mobile para cadastro, onboarding, pagamento e cartão/fatura com anti-dupla-contagem.

O projeto não depende mais do antigo ambiente de desenvolvimento para autenticação ou IA: Google OAuth usa credenciais próprias e o Analista IA usa a SDK oficial da OpenAI. O GitHub é a fonte de código/CI.

> Ainda não considere a aplicação liberada para dados financeiros pessoais reais até concluir o deploy de staging, backup/restauração, infraestrutura de produção e smoke pós-deploy descritos em `docs/DEPLOYMENT.md`.

## Arquitetura

```text
React
  ↓
FastAPI
  ↓
Application Services
  ↓
Domain
  ↓
Repositories
  ↓
MongoDB Replica Set
```

Modelo financeiro central:

```text
Commitment → Occurrence → Transaction
```

Regras que não podem ser quebradas:

- ocorrência futura é planejamento, não transação;
- status é derivado de data/pagamento;
- compra no cartão não debita conta bancária;
- somente o pagamento da fatura debita a conta escolhida;
- itens da fatura compõem a fatura e não somam novamente no comprometimento;
- pagamentos multi-documento são atômicos via MongoDB transaction/UnitOfWork;
- terceiro usando meu cartão gera obrigação na fatura + recebível do terceiro, sem segunda despesa;
- projeção padrão: 24 meses;
- simulações e IA são read-only.

Mais detalhes: `docs/ARCHITECTURE.md`.

## Pré-requisitos

- Python 3.11+
- Node.js 20+
- Yarn 1.22+
- Docker/Compose para o MongoDB local, ou MongoDB executando como replica set

## Configuração

### Backend

```bash
cp backend/.env.example backend/.env
```

Edite os valores obrigatórios:

```env
MONGO_URL=mongodb://127.0.0.1:27017/?replicaSet=rs0
DB_NAME=futureflex
JWT_SECRET=uma-chave-aleatoria-longa
```

Para IA:

```env
OPENAI_API_KEY=...
AI_MODEL=gpt-5.5
```

A conta demo é **opt-in**:

```env
ENABLE_DEMO_USER=true
```

Nunca habilite `ENABLE_DEMO_USER` em produção.

### Google Login

O login usa OAuth 2.0 diretamente com credenciais do seu próprio projeto Google Cloud. Configure um cliente OAuth do tipo Web Application e registre exatamente o callback do backend.

```env
FRONTEND_URL=http://localhost:3000
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GOOGLE_REDIRECT_URI=http://localhost:8001/api/auth/google/callback
```

Sem essas credenciais, cadastro/login por e-mail continuam funcionando e a rota de início do Google responde como integração não configurada.

### Frontend

```bash
cp frontend/.env.example frontend/.env
```

Quando frontend e backend estiverem no mesmo domínio, `REACT_APP_BACKEND_URL` pode ficar vazio e o frontend usará `/api`.

Quando estiverem separados:

```env
REACT_APP_BACKEND_URL=https://api.seudominio.com
```

## MongoDB replica set local

O Future Flex depende de transações ACID reais. Um MongoDB standalone não é suficiente para os fluxos financeiros multi-documento.

Suba o MongoDB portátil de desenvolvimento:

```bash
docker compose -f docker-compose.dev.yml up -d
```

O repositório também mantém `scripts/mongo_rs.sh` para compatibilidade com o ambiente legado.

## Executar o backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```

Health check:

```text
GET /api/health
```

## Executar o frontend

```bash
cd frontend
yarn install --frozen-lockfile
yarn start
```

Build de produção:

```bash
yarn install --frozen-lockfile
yarn build
```

`frontend/yarn.lock` é versionado. A CI falha se `package.json` e lockfile divergirem.

## Testes

Guards de segurança/release e Blueprint de deploy:

```bash
python -m pytest tests/test_release_security.py tests/test_deploy_config.py -v
```

Regras de negócio principais:

```bash
python -m pytest tests/test_business_rules.py -v
```

Valores dinâmicos:

```bash
python -m pytest tests/test_dynamic_amounts.py -v
```

Regressão E2E backend (requer backend em `localhost:8001` e conta demo habilitada):

```bash
python -m pytest backend/tests/backend_test.py -v
```

Smoke E2E de navegador (requer backend local em `localhost:8001`; o Playwright sobe o frontend):

```bash
cd frontend
yarn playwright install chromium
yarn test:e2e
```

A CI executa os fluxos de navegador em Chromium desktop e mobile. Entre os cenários críticos estão:

- cadastro → onboarding → Dashboard → reload idempotente;
- compromisso em conta não debita saldo antes da baixa e debita exatamente na baixa;
- compra parcelada no cartão não debita conta;
- parcela aparece como composição da fatura (`counts_in_total=false`);
- comprometido conta a fatura uma única vez;
- somente o pagamento da fatura debita a conta escolhida.

Há também scripts históricos das Etapas 3–6 na raiz usados durante a construção e QA do produto.

## Segurança de produção

- use `APP_ENV=production`;
- use `JWT_SECRET` aleatório com pelo menos 32 caracteres;
- mantenha `ENABLE_DEMO_USER=false`;
- mantenha `REQUIRE_REPLICA_SET=true`;
- use HTTPS e `COOKIE_SECURE=true`;
- configure `CORS_ORIGINS` com allow-list explícita quando necessário;
- não use `*` com credenciais;
- nunca versione `.env`, chaves ou credenciais;
- Google OAuth usa `state` assinado, expirável e vinculado ao navegador iniciador por cookie HttpOnly temporário.

## Funcionalidades principais

- cadastro/login e onboarding;
- contas e saldos;
- Compromissos do Mês;
- recorrências e valores mensais dinâmicos;
- cartões, parcelamentos e faturas;
- pagamentos e atrasados;
- terceiros;
- assinaturas;
- congelar/reativar compromissos;
- projeção de 24 meses;
- dinheiro livre;
- Health Score;
- simulador read-only;
- Analista IA read-only com contexto financeiro estruturado;
- PWA responsiva para mobile e desktop.

## Deploy / Release Candidate

A raiz contém `render.yaml` para o primeiro staging com frontend React + backend FastAPI. O MongoDB é externo e deve oferecer replica set/transações.

Fluxo de promoção:

```text
CI verde
→ staging sem dados pessoais
→ smoke externo
→ backup + restauração testada
→ infraestrutura/domínio de produção
→ smoke produção
→ merge/tag v1.0.0
→ uso real
```

Consulte:

- `docs/DEPLOYMENT.md` — configuração completa de staging/produção;
- `docs/RELEASE_CHECKLIST.md` — checklist Go/No-Go;
- `docs/ARCHITECTURE.md` — invariantes do motor financeiro.

## Compatibilidade legada

O backend ainda expõe temporariamente `POST /api/auth/google/session` apenas para responder de forma controlada a clientes antigos; ele não chama serviços externos legados. O frontend atual não usa esse endpoint. A IA utiliza diretamente a SDK oficial da OpenAI e exige `OPENAI_API_KEY` para responder.

# Future Flex V2

Future Flex V2 é uma aplicação de planejamento financeiro pessoal orientada ao futuro. O núcleo do produto é **Compromissos do Mês**: uma visão única do que já está financeiramente comprometido em cada competência, incluindo recorrências, parcelas, faturas, assinaturas, terceiros e atrasados — sem dupla contagem.

## Estado do projeto

O MVP funcional está implementado. O backend já possui regressão ampla para regras financeiras críticas (parcelamentos, cartões/faturas, pagamentos, valores dinâmicos, terceiros, congelamento, projeção, ownership e transações ACID). O trabalho atual é de **release hardening**: tornar execução, segurança, CI e deploy independentes do ambiente do Emergent.

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
- npm ou Yarn
- MongoDB 7+ executando como replica set (ex.: `rs0`)

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

Para IA, configure preferencialmente:

```env
OPENAI_API_KEY=...
AI_MODEL=gpt-5.5
```

A conta demo é **opt-in**:

```env
ENABLE_DEMO_USER=true
```

Nunca habilite `ENABLE_DEMO_USER` em produção.

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

O repositório contém `scripts/mongo_rs.sh` para o ambiente legado. Para desenvolvimento portátil, consulte `docs/DEPLOYMENT.md` e `docker-compose.dev.yml`.

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
npm install
npm start
```

Build de produção:

```bash
npm run build
```

## Testes

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
REACT_APP_BACKEND_URL=http://localhost:8001 python -m pytest backend/tests/backend_test.py -v
```

Há também scripts históricos das Etapas 3–6 na raiz usados durante a construção e QA do produto.

## Segurança de produção

- use `APP_ENV=production`;
- use `JWT_SECRET` aleatório com pelo menos 32 caracteres;
- mantenha `ENABLE_DEMO_USER=false`;
- mantenha `REQUIRE_REPLICA_SET=true`;
- use HTTPS e `COOKIE_SECURE=true`;
- configure `CORS_ORIGINS` somente quando frontend/backend estiverem em origens diferentes;
- não use `*` com credenciais;
- nunca versione `.env`, chaves ou credenciais.

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

## Release

Antes de uma versão ser marcada como pronta para produção, execute o checklist de `docs/RELEASE_CHECKLIST.md`.

## Observação sobre Google Login

O fluxo de Google Login existente foi originalmente integrado ao gateway OAuth do Emergent. Login por e-mail/senha é independente. A migração do Google OAuth para credenciais próprias é tratada como item explícito do hardening de release; não configure produção dependendo de uma URL temporária do Emergent.

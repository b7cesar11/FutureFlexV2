# Future Flex V2 — Release Checklist

Use este checklist antes de marcar uma versão como pronta para uso real.

## Ambiente

- [ ] `APP_ENV=production`
- [ ] `JWT_SECRET` forte (32+ caracteres aleatórios)
- [ ] `ENABLE_DEMO_USER=false`
- [ ] `REQUIRE_REPLICA_SET=true`
- [ ] MongoDB reporta replica set e transações disponíveis
- [ ] HTTPS ativo
- [ ] cookies configurados para a topologia de deploy
- [ ] `CORS_ORIGINS` explícito quando necessário
- [ ] `.env` e secrets fora do Git
- [ ] backup automático configurado
- [ ] restauração de backup testada

## Backend

- [ ] `GET /api/health` retorna saudável
- [ ] cadastro/login funcionam
- [ ] ownership entre usuários validado
- [ ] 1 pagamento gera exatamente 1 Transaction
- [ ] pagamento duplicado é bloqueado
- [ ] compra no cartão não debita conta
- [ ] pagamento da fatura debita apenas a conta escolhida
- [ ] multi-cartão cria faturas independentes no mesmo mês
- [ ] anti-dupla-contagem validada
- [ ] status continua derivado
- [ ] valores dinâmicos e overrides preservados
- [ ] ocorrência paga permanece imutável
- [ ] atrasado permanece na competência original
- [ ] congelar/reativar preserva histórico
- [ ] terceiro usando cartão não cria segunda despesa
- [ ] projeção retorna 24 competências sem duplicatas
- [ ] simulação continua read-only
- [ ] IA continua read-only

## Frontend

- [ ] login por e-mail/senha
- [ ] cadastro + onboarding de usuário novo
- [ ] onboarding não reaparece após conta criada
- [ ] Dashboard coerente com Compromissos
- [ ] pagamento pela UI
- [ ] edição de valor dinâmico pela UI
- [ ] dois cartões/faturas visivelmente separados
- [ ] assinaturas: pausar/cancelar/reativar
- [ ] terceiros
- [ ] congelar/reativar
- [ ] Saúde Financeira
- [ ] Projeção
- [ ] Simulador
- [ ] Analista IA
- [ ] estados loading/empty/error/success
- [ ] navegação mobile
- [ ] navegação desktop
- [ ] sem overflow crítico em 375/390/430 px
- [ ] sem quebra crítica em 1280/1440/1920 px
- [ ] console sem erros JavaScript críticos
- [ ] rede sem loops/500 recorrentes

## Build e regressão

- [ ] testes de regras de negócio passam
- [ ] testes de valores dinâmicos passam
- [ ] regressão E2E backend passa
- [ ] frontend build passa
- [ ] GitHub Actions passa

## Integrações

- [ ] OpenAI configurada com chave própria
- [ ] Google Login migrado para OAuth próprio ou explicitamente desabilitado até a migração
- [ ] nenhuma URL temporária de Preview é necessária em produção

## Release

- [ ] branch de release revisada
- [ ] PR aprovado/mergeado
- [ ] tag `v1.0.0` criada
- [ ] deploy de produção feito a partir do commit tagueado
- [ ] smoke test pós-deploy executado
- [ ] primeiro backup pós-deploy confirmado

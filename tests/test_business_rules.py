"""Testes de negocio do motor financeiro Future Flex V2.

Cobre os 12 cenarios exigidos antes de avancar de fase.
Executar: cd /app/backend && python -m pytest ../tests/test_business_rules.py -v
"""
import os
import time
from datetime import datetime, timezone

import pytest
import requests

BASE = "http://localhost:8001/api"


def competence_of(dt):
    return f"{dt.year:04d}-{dt.month:02d}"


CURRENT = competence_of(datetime.now(timezone.utc))


@pytest.fixture(scope="module")
def api():
    session = requests.Session()
    email = f"test.engine.{int(time.time())}@futureflex.dev"
    r = session.post(f"{BASE}/auth/register",
                     json={"email": email, "password": "Teste@123", "name": "Motor"})
    assert r.status_code == 200, r.text
    session.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
    return session


@pytest.fixture(scope="module")
def base_data(api):
    account = api.post(f"{BASE}/accounts",
                       json={"name": "Itaú", "type": "checking",
                             "opening_balance": 5000}).json()
    card = api.post(f"{BASE}/credit-cards",
                    json={"name": "Nubank", "limit": 8000, "closing_day": 28,
                          "due_day": 5}).json()
    person = api.post(f"{BASE}/people", json={"name": "Ana"}).json()
    return {"account": account, "card": card, "person": person}


def month(api, competence=CURRENT):
    r = api.get(f"{BASE}/months/{competence}")
    assert r.status_code == 200, r.text
    return r.json()


# ------------------------------------------------------------------ 1 / 11

def test_01_parcelamento_gera_12_parcelas_e_soma_exata(api, base_data):
    r = api.post(f"{BASE}/commitments", json={
        "type": "purchase_installment", "description": "iPhone 15",
        "total_amount": 3600, "installments_total": 12,
        "payment_method": "credit_card", "credit_card_id": base_data["card"]["id"]})
    assert r.status_code == 200, r.text
    commitment = r.json()
    detail = api.get(f"{BASE}/commitments/{commitment['id']}").json()
    occ = [o for o in detail["occurrences"]]
    assert len(occ) == 12
    assert round(sum(o["amount"] for o in occ), 2) == 3600.00
    assert occ[0]["sequence"] == 1 and occ[-1]["sequence"] == 12
    assert all(o["refs"]["invoice_id"] for o in occ), "parcelas devem estar vinculadas a faturas"
    base_data["iphone"] = commitment


def test_02_parcela_de_cartao_nao_conta_no_total_do_mes(api, base_data):
    view = month(api)
    cards_group = next(g for g in view["groups"] if g["key"] == "cards")
    installment_items = [i for i in
                         next(g for g in view["groups"] if g["key"] == "installments")["items"]]
    # a parcela existe, mas nao soma no total
    assert installment_items, "a parcela deve aparecer como composição"
    assert all(i["counts_in_total"] is False for i in installment_items)
    # o total de compromissos e igual ao total das faturas (nao o dobro)
    assert view["committed"] == cards_group["total"]
    assert cards_group["total"] == 300.00


def test_03_fatura_nao_soma_novamente_suas_parcelas(api, base_data):
    invoices = api.get(f"{BASE}/invoices",
                       params={"credit_card_id": base_data["card"]["id"]}).json()
    first = [i for i in invoices if i["total"] > 0][0]
    detail = api.get(f"{BASE}/invoices/{first['id']}").json()
    assert round(sum(i["amount"] for i in detail["items"]), 2) == first["total"]
    view = month(api, first["competence"])
    assert view["committed"] == first["total"], "fatura + parcelas nao pode dobrar o total"


def test_04_compra_no_cartao_nao_debita_conta(api, base_data):
    account = [a for a in api.get(f"{BASE}/accounts").json()
               if a["id"] == base_data["account"]["id"]][0]
    assert account["current_balance"] == 5000.00
    txs = api.get(f"{BASE}/transactions").json()
    assert txs == [], "compra no cartao nao pode gerar transacao"


def test_05_pagamento_de_fatura_debita_conta(api, base_data):
    invoices = api.get(f"{BASE}/invoices",
                       params={"credit_card_id": base_data["card"]["id"]}).json()
    invoice = [i for i in invoices if i["total"] > 0][0]
    r = api.post(f"{BASE}/invoices/{invoice['id']}/pay",
                 json={"account_id": base_data["account"]["id"]},
                 headers={"Idempotency-Key": "pay-invoice-1"})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["status"] == "paid"
    assert data["account_balance"] == round(5000 - invoice["total"], 2)
    txs = api.get(f"{BASE}/transactions").json()
    assert len(txs) == 1 and txs[0]["type"] == "invoice_payment"
    base_data["paid_invoice"] = invoice


def test_06_reprocessamento_nao_duplica_transactions(api, base_data):
    invoice = base_data["paid_invoice"]
    r = api.post(f"{BASE}/invoices/{invoice['id']}/pay",
                 json={"account_id": base_data["account"]["id"]},
                 headers={"Idempotency-Key": "pay-invoice-1"})
    assert r.status_code == 409
    assert len(api.get(f"{BASE}/transactions").json()) == 1


def test_07_despesa_fixa_gera_ocorrencias_futuras_24_meses(api, base_data):
    r = api.post(f"{BASE}/commitments", json={
        "type": "fixed_expense", "description": "Aluguel", "total_amount": 1800,
        "payment_method": "account", "day_of_month": 10,
        "default_account_id": base_data["account"]["id"]})
    assert r.status_code == 200, r.text
    detail = api.get(f"{BASE}/commitments/{r.json()['id']}").json()
    assert len(detail["occurrences"]) == 24
    base_data["aluguel"] = r.json()


def test_08_reprocessamento_nao_duplica_ocorrencias(api, base_data):
    before = len(api.get(f"{BASE}/commitments/{base_data['aluguel']['id']}").json()["occurrences"])
    api.post(f"{BASE}/commitments/materialize")
    api.post(f"{BASE}/commitments/materialize")
    after = len(api.get(f"{BASE}/commitments/{base_data['aluguel']['id']}").json()["occurrences"])
    assert before == after == 24


def test_09_ocorrencia_futura_nao_gera_transaction_automatica(api, base_data):
    occ = api.get(f"{BASE}/occurrences",
                  params={"competence": CURRENT, "group": "fixed"}).json()
    assert occ, "deve existir ocorrencia de despesa fixa no mes"
    assert all(o["status"] in ("future", "due", "overdue") for o in occ)
    assert all(not o["refs"]["transaction_ids"] for o in occ)
    # nenhuma transacao nova alem do pagamento da fatura
    assert len(api.get(f"{BASE}/transactions").json()) == 1


def test_10_pagamento_gera_transaction_com_a_conta_escolhida(api, base_data):
    occ = api.get(f"{BASE}/occurrences",
                  params={"competence": CURRENT, "group": "fixed"}).json()[0]
    other = api.post(f"{BASE}/accounts",
                     json={"name": "Nubank Conta", "type": "checking",
                           "opening_balance": 2000}).json()
    r = api.post(f"{BASE}/occurrences/{occ['id']}/pay",
                 json={"account_id": other["id"]},
                 headers={"Idempotency-Key": "pay-occ-1"})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["state"] == "paid"
    assert data["account_balance"] == round(2000 - occ["amount"], 2)
    tx = [t for t in api.get(f"{BASE}/transactions").json()
          if t["occurrence_id"] == occ["id"]]
    assert len(tx) == 1 and tx[0]["account_id"] == other["id"]
    # pagar de novo e bloqueado
    assert api.post(f"{BASE}/occurrences/{occ['id']}/pay",
                    json={"account_id": other["id"]}).status_code == 409


def test_11_terceiro_no_cartao_gera_obrigacao_e_recebivel(api, base_data):
    r = api.post(f"{BASE}/third-parties", json={
        "person_id": base_data["person"]["id"], "direction": "receivable",
        "description": "Compra no meu cartão", "total_amount": 600, "installments": 6,
        "credit_card_id": base_data["card"]["id"]})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["card_commitment_id"], "deve existir compromisso do cartao"
    card_c = api.get(f"{BASE}/commitments/{data['card_commitment_id']}").json()
    tp_c = api.get(f"{BASE}/commitments/{data['commitment_id']}").json()
    assert card_c["direction"] == "outflow" and tp_c["direction"] == "inflow"
    assert card_c["linked_commitment"]["id"] == tp_c["id"]
    assert tp_c["linked_commitment"]["id"] == card_c["id"]
    assert card_c["third_party_responsible"] is True
    assert len(card_c["occurrences"]) == 6 and len(tp_c["occurrences"]) == 6
    summary = api.get(f"{BASE}/third-parties").json()
    assert summary["total_receivable"] == 600.00
    assert summary["total_payable"] == 0.00


def test_12_recebivel_de_terceiro_nao_e_despesa(api, base_data):
    occ = api.get(f"{BASE}/occurrences", params={"group": "third_parties"}).json()
    assert occ and all(o["direction"] == "inflow" for o in occ)
    view = month(api)
    tp_group = next(g for g in view["groups"] if g["key"] == "third_parties")
    # entra como receita esperada, nunca somando em compromissos
    assert tp_group["total"] == 100.00
    assert view["income_expected"] >= 100.00


def test_13_congelamento_remove_dos_totais_ativos(api, base_data):
    before = month(api)["committed"]
    commitment_id = base_data["aluguel"]["id"]
    detail = api.get(f"{BASE}/commitments/{commitment_id}").json()
    monthly = detail["occurrences"][0]["amount"]
    next_comp = detail["occurrences"][1]["competence"]
    before_next = month(api, next_comp)["committed"]

    r = api.post(f"{BASE}/commitments/{commitment_id}/freeze")
    assert r.status_code == 200, r.text
    after_next = month(api, next_comp)
    assert after_next["committed"] == round(before_next - monthly, 2)
    assert after_next["frozen_total"] >= monthly
    frozen_items = [i for g in after_next["groups"] for i in g["items"] if i["frozen"]]
    assert frozen_items, "compromisso congelado continua visivel"
    assert all(i["status"] == "frozen" for i in frozen_items)

    api.post(f"{BASE}/commitments/{commitment_id}/unfreeze")
    assert month(api, next_comp)["committed"] == before_next


def test_14_projecao_de_24_meses(api, base_data):
    r = api.get(f"{BASE}/projection", params={"months": 24})
    assert r.status_code == 200, r.text
    data = r.json()
    assert len(data["rows"]) == 24
    assert data["rows"][0]["competence"] == CURRENT
    assert all("projected_balance" in row for row in data["rows"])
    # ocorrencias futuras alimentam a projecao sem virar transacao
    assert any(row["commitments"] > 0 for row in data["rows"][1:])


def test_15_dinheiro_livre(api, base_data):
    free = api.get(f"{BASE}/free-money").json()
    accounts = api.get(f"{BASE}/accounts").json()
    assert free["balance"] == round(sum(a["current_balance"] for a in accounts), 2)
    assert free["free_now"] == round(free["balance"] - free["pending_commitments"], 2)
    assert free["free_optimistic"] >= free["free_now"]


def test_16_simulacao_nao_altera_dados_reais(api, base_data):
    snapshot = {
        "month": month(api),
        "accounts": api.get(f"{BASE}/accounts").json(),
        "transactions": api.get(f"{BASE}/transactions").json(),
        "occurrences": api.get(f"{BASE}/occurrences").json(),
        "invoices": api.get(f"{BASE}/invoices").json(),
    }
    r = api.post(f"{BASE}/simulations", json={
        "add_installment_purchase": {"description": "Celular", "total_amount": 2400,
                                     "installments": 12},
        "monthly_income_delta": 500, "prepay_amount": 1000, "months": 24})
    assert r.status_code == 200, r.text
    sim = r.json()
    assert sim["read_only"] is True
    assert sim["impact"]["monthly_commitment_delta"] == 200.00
    assert len(sim["after"]["rows"]) == 24
    after = {
        "month": month(api),
        "accounts": api.get(f"{BASE}/accounts").json(),
        "transactions": api.get(f"{BASE}/transactions").json(),
        "occurrences": api.get(f"{BASE}/occurrences").json(),
        "invoices": api.get(f"{BASE}/invoices").json(),
    }
    assert after == snapshot, "simulacao nao pode alterar nenhum dado real"


def test_17_isolamento_entre_usuarios(base_data):
    other = requests.Session()
    r = other.post(f"{BASE}/auth/register",
                   json={"email": f"outro.{int(time.time())}@futureflex.dev",
                         "password": "Teste@123", "name": "Outro"})
    other.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
    assert other.get(f"{BASE}/occurrences").json() == []
    assert other.get(f"{BASE}/transactions").json() == []
    r = other.get(f"{BASE}/commitments/{base_data['aluguel']['id']}")
    assert r.status_code == 404
    r = other.post(f"{BASE}/occurrences/{base_data['aluguel']['id']}/pay",
                   json={"account_id": base_data["account"]["id"]})
    assert r.status_code in (403, 404)


def test_18_transferencia_preserva_soma_dos_saldos(api, base_data):
    accounts = api.get(f"{BASE}/accounts").json()
    total_before = round(sum(a["current_balance"] for a in accounts), 2)
    a, b = accounts[0], accounts[1]
    r = api.post(f"{BASE}/transactions", json={"type": "transfer", "amount": 250,
                                               "account_id": a["id"],
                                               "to_account_id": b["id"]})
    assert r.status_code == 200, r.text
    accounts_after = api.get(f"{BASE}/accounts").json()
    assert round(sum(x["current_balance"] for x in accounts_after), 2) == total_before


def test_19_split_de_parcelas_com_residuo(api, base_data):
    r = api.post(f"{BASE}/commitments", json={
        "type": "loan", "description": "Empréstimo", "total_amount": 1000,
        "installments_total": 3, "payment_method": "account"})
    detail = api.get(f"{BASE}/commitments/{r.json()['id']}").json()
    amounts = [o["amount"] for o in detail["occurrences"]]
    assert amounts == [333.34, 333.33, 333.33]
    assert round(sum(amounts), 2) == 1000.00


def test_20_dashboard_usa_a_mesma_fonte_do_mes(api, base_data):
    dash = api.get(f"{BASE}/dashboard").json()
    view = month(api)
    for key in ("committed", "paid", "pending", "income_expected", "progress_pct"):
        assert dash[key] == view[key], f"divergencia em {key}"
    free = api.get(f"{BASE}/free-money").json()
    assert dash["free_now"] == free["free_now"]

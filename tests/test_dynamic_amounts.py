"""Testes de valores dinamicos por occurrence (Etapa 3).

API-level (localhost:8001) — cobre os 3 modos, seguranca, imutabilidade de pagas,
preservacao de customizacoes, reflexo na fonte unica e regressao de materializacao.

Executar: cd /app/backend && python -m pytest ../tests/test_dynamic_amounts.py -v
"""
import time
from datetime import datetime, timezone

import pytest
import requests

BASE = "http://localhost:8001/api"


def competence_of(dt):
    return f"{dt.year:04d}-{dt.month:02d}"


def add_months(comp: str, n: int) -> str:
    y, m = map(int, comp.split("-"))
    idx = (y * 12 + (m - 1)) + n
    return f"{idx // 12:04d}-{idx % 12 + 1:02d}"


CURRENT = competence_of(datetime.now(timezone.utc))
C1 = add_months(CURRENT, 1)
C2 = add_months(CURRENT, 2)
C3 = add_months(CURRENT, 3)
C4 = add_months(CURRENT, 4)


def new_user():
    s = requests.Session()
    email = f"dyn.{int(time.time()*1000)}.{time.perf_counter_ns()}@futureflex.dev"
    r = s.post(f"{BASE}/auth/register",
               json={"email": email, "password": "Teste@123", "name": "Din"})
    assert r.status_code == 200, r.text
    s.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
    return s


@pytest.fixture(scope="module")
def api():
    return new_user()


@pytest.fixture(scope="module")
def account(api):
    return api.post(f"{BASE}/accounts",
                    json={"name": "Itaú", "type": "checking",
                          "opening_balance": 20000}).json()


def make_obra(api, amount=750):
    r = api.post(f"{BASE}/commitments", json={
        "type": "fixed_expense", "description": "Evolução de Obra",
        "total_amount": amount, "payment_method": "account", "day_of_month": 10})
    assert r.status_code == 200, r.text
    return r.json()


def occ_map(api, commitment_id):
    detail = api.get(f"{BASE}/commitments/{commitment_id}").json()
    return {o["competence"]: o for o in detail["occurrences"]}


def amt(api, commitment_id, competence):
    return round(occ_map(api, commitment_id)[competence]["amount"], 2)


def src(api, commitment_id, competence):
    return occ_map(api, commitment_id)[competence]["amount_source"]


def patch(api, occ_id, amount, mode):
    return api.patch(f"{BASE}/occurrences/{occ_id}", json={"amount": amount, "mode": mode})


# ------------------------------------------------------------------ setup / modelo

def test_01_recorrencia_cria_ocorrencias_no_valor_padrao(api, account):
    c = make_obra(api, 750)
    m = occ_map(api, c["id"])
    assert m[CURRENT]["amount"] == 750.0
    assert m[C1]["amount"] == 750.0 and m[C2]["amount"] == 750.0
    assert all(o["amount_source"] == "default" for o in m.values())
    # janela de 24 meses materializada
    assert len(m) >= 24


# ------------------------------------------------------------------ Teste A: somente este mes

def test_02_single_altera_somente_a_ocorrencia(api, account):
    c = make_obra(api, 750)
    r = patch(api, occ_map(api, c["id"])[C1]["id"], 950, "single")
    assert r.status_code == 200, r.text
    assert r.json()["affected_occurrences"] == 1
    assert amt(api, c["id"], CURRENT) == 750.0
    assert amt(api, c["id"], C1) == 950.0
    assert amt(api, c["id"], C2) == 750.0
    assert src(api, c["id"], C1) == "override"
    assert src(api, c["id"], C2) == "default"


# ------------------------------------------------------------------ Teste B: este mes e proximos

def test_03_this_and_future_altera_alvo_e_futuros(api, account):
    c = make_obra(api, 750)
    r = patch(api, occ_map(api, c["id"])[C1]["id"], 1000, "this_and_future")
    assert r.status_code == 200, r.text
    assert amt(api, c["id"], CURRENT) == 750.0        # anterior intacto
    assert amt(api, c["id"], C1) == 1000.0
    assert amt(api, c["id"], C2) == 1000.0
    assert amt(api, c["id"], C3) == 1000.0
    assert src(api, c["id"], C2) == "override"


def test_04_this_and_future_preserva_override_anterior(api, account):
    c = make_obra(api, 750)
    # customiza C3 isoladamente
    patch(api, occ_map(api, c["id"])[C3]["id"], 500, "single")
    # depois altera a partir de C1
    patch(api, occ_map(api, c["id"])[C1]["id"], 1100, "this_and_future")
    assert amt(api, c["id"], C1) == 1100.0
    assert amt(api, c["id"], C2) == 1100.0
    assert amt(api, c["id"], C3) == 500.0             # customizacao preservada
    assert amt(api, c["id"], C4) == 1100.0


# ------------------------------------------------------------------ Teste C: valor padrao

def test_05_default_afeta_futuros_nao_customizados_e_preserva_override(api, account):
    c = make_obra(api, 750)
    patch(api, occ_map(api, c["id"])[C2]["id"], 500, "single")   # override em C2
    r = patch(api, occ_map(api, c["id"])[C1]["id"], 820, "default")
    assert r.status_code == 200, r.text
    assert amt(api, c["id"], CURRENT) == 820.0        # futuro nao-customizado
    assert amt(api, c["id"], C1) == 820.0
    assert amt(api, c["id"], C2) == 500.0             # override preservado
    assert amt(api, c["id"], C3) == 820.0
    detail = api.get(f"{BASE}/commitments/{c['id']}").json()
    assert round(detail["total_amount"], 2) == 820.0


def test_06_default_rejeitado_para_parcelamento(api, account):
    card = api.post(f"{BASE}/credit-cards",
                    json={"name": "Nu", "limit": 9000, "closing_day": 28, "due_day": 5}).json()
    c = api.post(f"{BASE}/commitments", json={
        "type": "purchase_installment", "description": "Notebook",
        "total_amount": 1200, "installments_total": 12,
        "payment_method": "credit_card", "credit_card_id": card["id"]}).json()
    occ = api.get(f"{BASE}/commitments/{c['id']}").json()["occurrences"][0]
    r = patch(api, occ["id"], 200, "default")
    assert r.status_code == 422, r.text


# ------------------------------------------------------------------ imutabilidade de pagas

def test_07_ocorrencia_paga_nao_pode_ser_alterada(api, account):
    c = make_obra(api, 750)
    occ = occ_map(api, c["id"])[CURRENT]
    pay = api.post(f"{BASE}/occurrences/{occ['id']}/pay",
                   json={"account_id": account["id"]})
    assert pay.status_code == 200, pay.text
    r = patch(api, occ["id"], 900, "single")
    assert r.status_code == 409, r.text


# ------------------------------------------------------------------ seguranca / ownership

def test_08_outro_usuario_nao_acessa_ocorrencia(api, account):
    c = make_obra(api, 750)
    occ_id = occ_map(api, c["id"])[C1]["id"]
    intruder = new_user()
    r = intruder.patch(f"{BASE}/occurrences/{occ_id}", json={"amount": 10, "mode": "single"})
    assert r.status_code == 404, r.text
    # valor original intacto
    assert amt(api, c["id"], C1) == 750.0


# ------------------------------------------------------------------ validacoes

@pytest.mark.parametrize("bad", [0, -100, "abc", None])
def test_09_valores_invalidos_rejeitados(api, account, bad):
    c = make_obra(api, 750)
    occ_id = occ_map(api, c["id"])[C1]["id"]
    r = patch(api, occ_id, bad, "single")
    assert r.status_code == 422, r.text


# ------------------------------------------------------------------ reflexo na fonte unica

def test_10_alteracao_reflete_no_mes_e_no_dinheiro_livre(api, account):
    c = make_obra(api, 750)
    before_month = api.get(f"{BASE}/months/{CURRENT}").json()["committed"]
    before_free = api.get(f"{BASE}/free-money").json()["free_now"]
    patch(api, occ_map(api, c["id"])[CURRENT]["id"], 900, "single")  # +150
    after_month = api.get(f"{BASE}/months/{CURRENT}").json()["committed"]
    after_free = api.get(f"{BASE}/free-money").json()["free_now"]
    assert round(after_month - before_month, 2) == 150.0
    assert round(before_free - after_free, 2) == 150.0


def test_11_alteracao_reflete_na_projecao(api, account):
    c = make_obra(api, 750)
    before = {r["competence"]: r["commitments"]
              for r in api.get(f"{BASE}/projection").json()["rows"]}
    patch(api, occ_map(api, c["id"])[C1]["id"], 950, "single")  # +200 em C1
    after = {r["competence"]: r["commitments"]
             for r in api.get(f"{BASE}/projection").json()["rows"]}
    assert round(after[C1] - before[C1], 2) == 200.0


# ------------------------------------------------------------------ regressao: materializacao preserva override

def test_12_materialize_nao_sobrescreve_override(api, account):
    c = make_obra(api, 750)
    patch(api, occ_map(api, c["id"])[C1]["id"], 1234, "single")
    r = api.post(f"{BASE}/commitments/materialize")
    assert r.status_code == 200, r.text
    assert amt(api, c["id"], C1) == 1234.0             # NAO voltou para 750
    assert src(api, c["id"], C1) == "override"


# ------------------------------------------------------------------ ocorrencia inexistente

def test_13_ocorrencia_inexistente_retorna_404(api, account):
    r = api.patch(f"{BASE}/occurrences/000000000000000000000000",
                  json={"amount": 100, "mode": "single"})
    assert r.status_code == 404, r.text

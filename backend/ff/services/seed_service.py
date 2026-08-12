"""Seed de categorias padrao pt-BR por usuario (idempotente)."""
from ..core.db import db
from ..models.entities import Category
from bson import ObjectId

EXPENSE_CATEGORIES = [
    ("Moradia", "#F97316"), ("Alimentação", "#22C55E"), ("Transporte", "#3B82F6"),
    ("Saúde", "#EF4444"), ("Educação", "#8B5CF6"), ("Lazer", "#EC4899"),
    ("Assinaturas", "#06B6D4"), ("Cartão de crédito", "#A855F7"),
    ("Empréstimos", "#F59E0B"), ("Financiamentos", "#64748B"),
    ("Terceiros", "#14B8A6"), ("Outros", "#94A3B8"),
]
INCOME_CATEGORIES = [
    ("Salário", "#22D3A5"), ("Freelance", "#38BDF8"), ("Comissão", "#FBBF24"),
    ("Benefício", "#A3E635"), ("Renda extra", "#F472B6"), ("Outras receitas", "#94A3B8"),
]


async def seed_user_defaults(user_id: str, session=None) -> int:
    existing = await db.categories.count_documents({"user_id": ObjectId(user_id)},
                                                   session=session)
    if existing:
        return 0
    docs = []
    for name, color in EXPENSE_CATEGORIES:
        docs.append(Category(user_id=user_id, name=name, kind="expense", color=color,
                             is_system=True).to_mongo())
    for name, color in INCOME_CATEGORIES:
        docs.append(Category(user_id=user_id, name=name, kind="income", color=color,
                             is_system=True).to_mongo())
    await db.categories.insert_many(docs, session=session)
    return len(docs)

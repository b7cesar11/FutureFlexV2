"""Ownership/authorization equivalente a RLS: valida que cada referencia pertence ao usuario."""
from ..core.deps import DomainError
from ..repositories import registry as repo

REF_REPOS = {
    "account_id": repo.accounts,
    "to_account_id": repo.accounts,
    "credit_card_id": repo.credit_cards,
    "category_id": repo.categories,
    "person_id": repo.people,
    "commitment_id": repo.commitments,
    "occurrence_id": repo.occurrences,
    "invoice_id": repo.invoices,
}


async def assert_owned(user_id: str, refs: dict, session=None):
    for key, value in refs.items():
        if not value or key not in REF_REPOS:
            continue
        if not await REF_REPOS[key].exists(user_id, value, session=session):
            raise DomainError(f"Referência inválida ou de outro usuário: {key}", 403)

from ..models.entities import (Account, Category, Commitment, CreditCard, IncomeSource,
                               Invoice, Occurrence, Person, Subscription,
                               ThirdPartyRelationship, Transaction, User)
from .base import Repository

accounts = Repository("accounts", Account)
credit_cards = Repository("credit_cards", CreditCard)
categories = Repository("categories", Category)
people = Repository("people", Person)
commitments = Repository("commitments", Commitment)
occurrences = Repository("occurrences", Occurrence)
invoices = Repository("invoices", Invoice)
transactions = Repository("transactions", Transaction)
third_parties = Repository("third_party_relationships", ThirdPartyRelationship)
subscriptions = Repository("subscriptions", Subscription)
income_sources = Repository("income_sources", IncomeSource)
users = Repository("users", User)

CATALOG = {
    "accounts": (accounts, Account),
    "credit-cards": (credit_cards, CreditCard),
    "categories": (categories, Category),
    "people": (people, Person),
}

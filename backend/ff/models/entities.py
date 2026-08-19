from datetime import datetime
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field
from .base import BaseDocument, PyObjectId

class UserProfile(BaseModel):
    name: str = ""
    picture: Optional[str] = None

class UserPreferences(BaseModel):
    currency: str = "BRL"
    locale: str = "pt-BR"
    theme: str = "dark"
    projection_months: int = 24

class User(BaseDocument):
    email: str
    password_hash: Optional[str] = None
    google_sub: Optional[str] = None
    auth_providers: list[str] = Field(default_factory=list)
    role: str = "user"
    profile: UserProfile = Field(default_factory=UserProfile)
    preferences: UserPreferences = Field(default_factory=UserPreferences)

class Account(BaseDocument):
    user_id: PyObjectId
    name: str
    type: Literal["checking", "savings", "cash", "wallet", "other"] = "checking"
    institution: Optional[str] = None
    opening_balance: float = 0.0
    current_balance: float = 0.0
    color: str = "#22D3A5"
    archived: bool = False

class CreditCard(BaseDocument):
    user_id: PyObjectId
    name: str
    brand: Optional[str] = None
    limit: float = 0.0
    closing_day: int = 28
    due_day: int = 5
    default_account_id: Optional[PyObjectId] = None
    color: str = "#8B5CF6"
    archived: bool = False

class Category(BaseDocument):
    user_id: PyObjectId
    name: str
    kind: Literal["expense", "income"] = "expense"
    icon: Optional[str] = None
    color: str = "#94A3B8"
    is_system: bool = False

class Person(BaseDocument):
    user_id: PyObjectId
    name: str
    phone: Optional[str] = None
    notes: Optional[str] = None
    color: str = "#F59E0B"

CommitmentType = Literal[
    "purchase_installment", "fixed_expense", "subscription", "loan", "financing",
    "credit_card_invoice", "third_party_payable", "third_party_receivable",
    "recurring_income", "other",
]

class Recurrence(BaseModel):
    frequency: Literal["once", "monthly", "weekly", "yearly"] = "monthly"
    interval: int = 1
    day_of_month: int = 1
    start_competence: str = ""
    end_competence: Optional[str] = None

class Commitment(BaseDocument):
    user_id: PyObjectId
    type: CommitmentType
    direction: Literal["outflow", "inflow"] = "outflow"
    description: str
    total_amount: float = 0.0
    installments_total: Optional[int] = None
    installment_amount: float = 0.0
    recurrence: Optional[Recurrence] = None
    payment_method: Literal["credit_card", "account", "cash"] = "account"
    credit_card_id: Optional[PyObjectId] = None
    default_account_id: Optional[PyObjectId] = None
    category_id: Optional[PyObjectId] = None
    person_id: Optional[PyObjectId] = None
    linked_commitment_id: Optional[PyObjectId] = None
    source: dict = Field(default_factory=lambda: {"module": "manual", "ref_id": None})
    origin_group: str = "fixed"
    frozen: bool = False
    frozen_at: Optional[datetime] = None
    freeze_reason: Optional[str] = None
    status: Literal["active", "completed", "cancelled"] = "active"
    materialized_until: Optional[str] = None
    start_date: Optional[datetime] = None

class OccRefs(BaseModel):
    invoice_id: Optional[PyObjectId] = None
    credit_card_id: Optional[PyObjectId] = None
    account_id: Optional[PyObjectId] = None
    category_id: Optional[PyObjectId] = None
    person_id: Optional[PyObjectId] = None
    transaction_ids: list[PyObjectId] = Field(default_factory=list)

class OccMeta(BaseModel):
    materialized_by: str = "manual"
    generated_at: Optional[datetime] = None
    source_channel: str = "web"
    edited: bool = False
    version: int = 1

OccurrenceKind = Literal[
    "installment", "recurring_expense", "subscription_charge", "invoice",
    "third_party", "income", "loan", "financing", "other",
]

class Occurrence(BaseDocument):
    user_id: PyObjectId
    commitment_id: Optional[PyObjectId] = None
    kind: OccurrenceKind
    direction: Literal["outflow", "inflow"] = "outflow"
    competence: str
    due_date: datetime
    amount: float
    amount_source: Literal["default", "override"] = "default"
    paid_amount: float = 0.0
    paid_at: Optional[datetime] = None
    sequence: Optional[int] = None
    sequence_total: Optional[int] = None
    state: Literal["open", "paid", "cancelled"] = "open"
    frozen: bool = False
    refs: OccRefs = Field(default_factory=OccRefs)
    detail: dict = Field(default_factory=dict)
    label: str = ""
    origin_group: str = "fixed"
    meta: OccMeta = Field(default_factory=OccMeta)
    status: Optional[str] = Field(default=None, exclude=True)

class Invoice(BaseDocument):
    user_id: PyObjectId
    credit_card_id: PyObjectId
    period: dict
    competence: str
    closing_date: datetime
    due_date: datetime
    total: float = 0.0
    paid_amount: float = 0.0
    status: Literal["open", "closed", "partially_paid", "paid"] = "open"

class Transaction(BaseDocument):
    user_id: PyObjectId
    type: Literal["expense", "income", "transfer", "invoice_payment", "commitment_payment"]
    amount: float
    date: datetime
    competence: str
    account_id: Optional[PyObjectId] = None
    to_account_id: Optional[PyObjectId] = None
    category_id: Optional[PyObjectId] = None
    occurrence_id: Optional[PyObjectId] = None
    invoice_id: Optional[PyObjectId] = None
    credit_card_id: Optional[PyObjectId] = None
    person_id: Optional[PyObjectId] = None
    description: str = ""
    source: str = "manual"
    idempotency_key: Optional[str] = None

class ThirdPartyRelationship(BaseDocument):
    user_id: PyObjectId
    person_id: PyObjectId
    direction: Literal["receivable", "payable"]
    description: str
    total_amount: float
    installments: int = 1
    credit_card_id: Optional[PyObjectId] = None
    category_id: Optional[PyObjectId] = None
    start_date: Optional[datetime] = None
    commitment_id: Optional[PyObjectId] = None
    card_commitment_id: Optional[PyObjectId] = None
    status: Literal["open", "settled", "cancelled"] = "open"

class Subscription(BaseDocument):
    user_id: PyObjectId
    name: str
    description: Optional[str] = None
    amount: float
    periodicity: Literal["monthly", "yearly"] = "monthly"
    billing_day: int = 1
    payment_method: Literal["credit_card", "account"] = "credit_card"
    credit_card_id: Optional[PyObjectId] = None
    account_id: Optional[PyObjectId] = None
    category_id: Optional[PyObjectId] = None
    commitment_id: Optional[PyObjectId] = None
    start_competence: str = ""
    end_competence: Optional[str] = None
    status: Literal["active", "paused", "cancelled"] = "active"

class IncomeSource(BaseDocument):
    user_id: PyObjectId
    name: str
    amount: float
    day_of_month: int = 5
    account_id: Optional[PyObjectId] = None
    category_id: Optional[PyObjectId] = None
    commitment_id: Optional[PyObjectId] = None
    start_competence: str = ""
    end_competence: Optional[str] = None
    status: Literal["active", "paused", "cancelled"] = "active"

from datetime import datetime, timezone
from typing import Annotated, Any, Optional

from bson import ObjectId
from pydantic import BaseModel, BeforeValidator, ConfigDict, Field


def _as_str_id(v: Any) -> Any:
    if isinstance(v, ObjectId):
        return str(v)
    return v


PyObjectId = Annotated[str, BeforeValidator(_as_str_id)]


def _to_oid(value: Any) -> Any:
    if isinstance(value, str) and ObjectId.is_valid(value):
        return ObjectId(value)
    return value


def convert_ids(obj: Any, key: str | None = None) -> Any:
    if isinstance(obj, dict):
        return {k: convert_ids(v, k) for k, v in obj.items()}
    if isinstance(obj, list):
        if key and key.endswith("_ids"):
            return [_to_oid(v) for v in obj]
        return [convert_ids(v) for v in obj]
    if key and (key == "_id" or key == "id" or key.endswith("_id")):
        return _to_oid(obj)
    return obj


def stringify_ids(obj: Any) -> Any:
    """Converte ObjectId -> str recursivamente (campos dict livres como source/detail)."""
    if isinstance(obj, ObjectId):
        return str(obj)
    if isinstance(obj, dict):
        return {k: stringify_ids(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [stringify_ids(v) for v in obj]
    return obj


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class BaseDocument(BaseModel):
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True,
                             extra="ignore")

    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)

    def to_mongo(self) -> dict:
        doc = self.model_dump(by_alias=True)
        if doc.get("_id") is None:
            doc.pop("_id", None)
        return convert_ids(doc)

    @classmethod
    def from_mongo(cls, doc: dict | None):
        if not doc:
            return None
        return cls.model_validate(doc)

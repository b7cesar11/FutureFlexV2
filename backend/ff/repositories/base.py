from bson import ObjectId

from ..core.db import db
from ..models.base import convert_ids


class Repository:
    """Todo acesso ao Mongo passa por aqui. user_id e session sao obrigatorios por contrato."""

    def __init__(self, collection: str, model=None):
        self.collection = db[collection]
        self.model = model

    def _scope(self, user_id: str, extra: dict | None = None) -> dict:
        query = {"user_id": ObjectId(user_id)}
        if extra:
            query.update(convert_ids(extra))
        return query

    def _wrap(self, doc):
        if doc is None:
            return None
        return self.model.from_mongo(doc) if self.model else doc

    async def insert(self, model, session=None) -> str:
        doc = model.to_mongo()
        res = await self.collection.insert_one(doc, session=session)
        model.id = str(res.inserted_id)
        return model.id

    async def get(self, user_id: str, _id: str, session=None):
        doc = await self.collection.find_one(self._scope(user_id, {"_id": _id}), session=session)
        return self._wrap(doc)

    async def find(self, user_id: str, filters: dict | None = None, sort=None, limit: int = 0,
                   skip: int = 0, session=None):
        cursor = self.collection.find(self._scope(user_id, filters), session=session)
        if sort:
            cursor = cursor.sort(sort)
        if skip:
            cursor = cursor.skip(skip)
        if limit:
            cursor = cursor.limit(limit)
        docs = await cursor.to_list(length=limit or 5000)
        return [self._wrap(d) for d in docs]

    async def count(self, user_id: str, filters: dict | None = None, session=None) -> int:
        return await self.collection.count_documents(self._scope(user_id, filters), session=session)

    async def update(self, user_id: str, _id: str, changes: dict, session=None):
        await self.collection.update_one(self._scope(user_id, {"_id": _id}),
                                         {"$set": convert_ids(changes)}, session=session)

    async def update_many(self, user_id: str, filters: dict, changes: dict, session=None):
        return await self.collection.update_many(self._scope(user_id, filters),
                                                 {"$set": convert_ids(changes)}, session=session)

    async def inc(self, user_id: str, _id: str, changes: dict, session=None):
        await self.collection.update_one(self._scope(user_id, {"_id": _id}),
                                         {"$inc": changes}, session=session)

    async def delete(self, user_id: str, _id: str, session=None):
        await self.collection.delete_one(self._scope(user_id, {"_id": _id}), session=session)

    async def exists(self, user_id: str, _id: str, session=None) -> bool:
        return await self.collection.count_documents(self._scope(user_id, {"_id": _id}),
                                                     limit=1, session=session) > 0

"""
异步 MongoDB 测试替身。

生产环境使用 ``motor``（异步 PyMongo），测试环境使用 ``mongomock``（同步），
本模块把同步的 mongomock 集合包装成与 motor API 兼容的 awaitable 形式，
使得业务代码无需感知测试环境的差异。

只需覆盖业务代码实际使用到的方法；未覆盖的方法会抛出 ``NotImplementedError``，
从而在测试中显式暴露"新增了未适配的数据库调用"这一事实。
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

import mongomock


class AsyncCursorProxy:
    """兼容 ``motor`` 游标的 awaitable / async-iterable 包装。"""

    def __init__(self, cursor) -> None:
        self._cursor = cursor

    # --- await 支持：await db.coll.find({}) -> List[dict] ---
    def __await__(self):
        return self._collect().__await__()

    async def _collect(self) -> List[Dict[str, Any]]:
        return list(self._cursor)

    # --- async for 支持 ---
    def __aiter__(self):
        return self._aiter()

    async def _aiter(self):
        for doc in self._cursor:
            yield doc

    async def to_list(self, length: Optional[int] = None) -> List[Dict[str, Any]]:
        docs = list(self._cursor)
        return docs[:length] if length is not None else docs

    # 注意：motor 的 sort/limit/skip 是**同步**链式方法（返回自身），不是协程。
    # 这里必须保持同步语义，否则 `db.coll.find(...).sort(...).limit(...)` 会拿到协程对象。
    def sort(self, key_or_list, direction=None) -> "AsyncCursorProxy":
        self._cursor = self._cursor.sort(key_or_list, direction)
        return self

    def limit(self, count: int) -> "AsyncCursorProxy":
        self._cursor = self._cursor.limit(count)
        return self

    def skip(self, count: int) -> "AsyncCursorProxy":
        self._cursor = self._cursor.skip(count)
        return self

    async def count_documents(self, filter: Optional[Dict[str, Any]] = None) -> int:
        return self._cursor.count_documents(filter or {})

    async def distinct(self, key: str) -> List[Any]:
        return self._cursor.distinct(key)

    async def close(self) -> None:
        return None


class AsyncAggregateCursorProxy:
    """兼容 ``motor`` 聚合游标（``await coll.aggregate(...).to_list(None)``）。"""

    def __init__(self, cursor) -> None:
        self._cursor = cursor

    async def to_list(self, length: Optional[int] = None) -> List[Dict[str, Any]]:
        docs = list(self._cursor)
        return docs[:length] if length is not None else docs

    def __await__(self):
        return self.to_list().__await__()

    def __aiter__(self):
        async def _gen():
            for doc in self._cursor:
                yield doc

        return _gen()


class AsyncCollectionProxy:
    """兼容 ``motor`` 集合的异步代理。"""

    def __init__(self, collection) -> None:
        self._collection = collection

    # --- 读 ---
    async def find_one(self, filter=None, *args, **kwargs):
        return self._collection.find_one(filter or {}, *args, **kwargs)

    def find(self, filter=None, *args, **kwargs) -> AsyncCursorProxy:
        return AsyncCursorProxy(self._collection.find(filter or {}, *args, **kwargs))

    async def find_one_and_update(self, filter, update, *args, **kwargs):
        return self._collection.find_one_and_update(filter, update, *args, **kwargs)

    async def find_one_and_delete(self, filter, *args, **kwargs):
        return self._collection.find_one_and_delete(filter, *args, **kwargs)

    async def find_one_and_replace(self, filter, replacement, *args, **kwargs):
        return self._collection.find_one_and_replace(filter, replacement, *args, **kwargs)

    async def count_documents(self, filter=None, **kwargs) -> int:
        return self._collection.count_documents(filter or {}, **kwargs)

    async def estimated_document_count(self, **kwargs) -> int:
        return self._collection.estimated_document_count(**kwargs)

    async def distinct(self, key: str, filter=None, **kwargs) -> List[Any]:
        return self._collection.distinct(key, filter or {}, **kwargs)

    # --- 写 ---
    async def insert_one(self, document, **kwargs):
        return self._collection.insert_one(document, **kwargs)

    async def insert_many(self, documents, **kwargs):
        return self._collection.insert_many(documents, **kwargs)

    async def update_one(self, filter, update, **kwargs):
        return self._collection.update_one(filter, update, **kwargs)

    async def update_many(self, filter, update, **kwargs):
        return self._collection.update_many(filter, update, **kwargs)

    async def replace_one(self, filter, replacement, **kwargs):
        return self._collection.replace_one(filter, replacement, **kwargs)

    async def delete_one(self, filter, **kwargs):
        return self._collection.delete_one(filter, **kwargs)

    async def delete_many(self, filter, **kwargs):
        return self._collection.delete_many(filter, **kwargs)

    async def bulk_write(self, requests, **kwargs):
        return self._collection.bulk_write(requests, **kwargs)

    def aggregate(self, pipeline, **kwargs) -> AsyncAggregateCursorProxy:
        """聚合：motor 中 aggregate 是同步方法，返回可 await 的游标。"""
        return AsyncAggregateCursorProxy(self._collection.aggregate(pipeline, **kwargs))

    async def drop(self, **kwargs) -> None:
        self._collection.drop()

    # --- 索引 ---
    def create_index(self, keys, **kwargs):
        return self._collection.create_index(keys, **kwargs)

    def create_indexes(self, indexes, **kwargs):
        return self._collection.create_indexes(indexes, **kwargs)

    def index_information(self):
        return self._collection.index_information()

    def __getitem__(self, name: str) -> "AsyncCollectionProxy":
        return AsyncCollectionProxy(self._collection[name])

    def __getattr__(self, item: str) -> Any:
        # mongomock 的 Collection 通过 __getattr__ 返回子集合，同样需要异步包装。
        attr = getattr(self._collection, item)
        if isinstance(attr, mongomock.collection.Collection):
            return AsyncCollectionProxy(attr)
        return attr


class AsyncDatabaseProxy:
    """兼容 ``AsyncIOMotorDatabase`` 的异步代理。"""

    def __init__(self, database) -> None:
        self._database = database

    def __getitem__(self, name: str) -> AsyncCollectionProxy:
        return AsyncCollectionProxy(self._database[name])

    def get_collection(self, name: str, **kwargs) -> AsyncCollectionProxy:
        return AsyncCollectionProxy(self._database.get_collection(name, **kwargs))

    async def list_collection_names(self, **kwargs) -> List[str]:
        return list(self._database.list_collection_names())

    async def list_collections(self, **kwargs) -> List[Dict[str, Any]]:
        return list(self._database.list_collections())

    async def command(self, command, *args, **kwargs):
        return self._database.command(command, *args, **kwargs)

    async def create_collection(self, name: str, **kwargs):
        return self._database.create_collection(name, **kwargs)

    async def drop_collection(self, name: str, **kwargs) -> None:
        self._database.drop_collection(name)

    async def watch(self, *args, **kwargs):  # pragma: no cover - 测试不使用 change stream
        raise NotImplementedError("测试环境不支持 change stream")

    def __getattr__(self, item: str) -> Any:
        # mongomock 的 Database 通过 __getattr__ 为任意名字返回**同步**集合，
        # 必须重新包装成异步代理，否则 `await db.xxx.find_one()` 会炸。
        attr = getattr(self._database, item)
        if isinstance(attr, mongomock.collection.Collection):
            return AsyncCollectionProxy(attr)
        return attr


def make_async_mongo_client() -> mongomock.MongoClient:
    """创建同步 mongomock 客户端（供需要同步访问的代码使用）。"""
    return mongomock.MongoClient()


def make_async_database(sync_database) -> AsyncDatabaseProxy:
    """把同步 mongomock 数据库包装成 motor 兼容的异步数据库。"""
    return AsyncDatabaseProxy(sync_database)


def seed(collection_proxy: AsyncCollectionProxy, documents: Iterable[Dict[str, Any]]) -> None:
    """向集合中批量写入初始数据（同步写入，仅用于测试准备阶段）。"""
    docs = list(documents)
    if docs:
        collection_proxy._collection.insert_many(docs)

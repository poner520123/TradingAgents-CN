"""测试替身（fake）集合。"""

from tests.fakes.async_mongo import (
    AsyncCollectionProxy,
    AsyncCursorProxy,
    AsyncDatabaseProxy,
    make_async_database,
    make_async_mongo_client,
    seed,
)

__all__ = [
    "AsyncCollectionProxy",
    "AsyncCursorProxy",
    "AsyncDatabaseProxy",
    "make_async_database",
    "make_async_mongo_client",
    "seed",
]

from typing import Any
from contextlib import contextmanager


@contextmanager
def create_async_context():
    yield  # pragma: no cover

@contextmanager
def create_sync_context():
    yield  # pragma: no cover

@contextmanager
def create_generator_context():
    yield  # pragma: no cover


async_context = create_async_context()
sync_context = create_sync_context()
generator_context = create_generator_context()


def await_it(some_expression: Any) -> Any:
    pass

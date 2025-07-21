from typing import Any, NoReturn, Generator
from contextlib import contextmanager


@contextmanager
def create_async_context() -> Generator[NoReturn, None, None]:
    yield  # type: ignore[misc]  # pragma: no cover

@contextmanager
def create_sync_context() -> Generator[NoReturn, None, None]:
    yield  # type: ignore[misc]  # pragma: no cover

@contextmanager
def create_generator_context() -> Generator[NoReturn, None, None]:
    yield  # type: ignore[misc]  # pragma: no cover


async_context = create_async_context()
sync_context = create_sync_context()
generator_context = create_generator_context()


def await_it(some_expression: Any) -> Any:
    pass   # pragma: no cover

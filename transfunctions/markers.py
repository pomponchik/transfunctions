from typing import Any, NoReturn, Generator, Iterable, Optional
from contextlib import contextmanager

from transfunctions.typing import IterableWithResults


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

def yield_from_it(some_iterable: IterableWithResults) -> NoReturn:  # type: ignore[misc]
    for value in some_iterable:  # pragma: no cover
        return value  # type: ignore[misc]


@contextmanager
def variant_context(name: str) -> Generator[NoReturn, None, None]:
    """
    Marker-context for custom variants (N-branches).

    Usage:
        with variant_context("trio"):
            ...
    """
    yield  # type: ignore[misc]  # pragma: no cover


@contextmanager
def patch_context(name: str, *, variants: Optional[Iterable[str]] = None) -> Generator[NoReturn, None, None]:
    """
    Marker-context for optional patches (composition on top of variants).

    Usage:
        with patch_context("logging"):
            ...
        with patch_context("metrics", variants=["async", "trio"]):
            ...
    """
    yield  # type: ignore[misc]  # pragma: no cover

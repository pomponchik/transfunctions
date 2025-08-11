import sys
from typing import TypeVar
from collections.abc import Iterable

if sys.version_info >= (3, 10):
    from typing import ParamSpec
else:
    from typing_extensions import ParamSpec  # pragma: no cover

if sys.version_info <= (3, 10):
    from typing_extensions import TypeAlias  # pragma: no cover
else:
    from typing import TypeAlias

if sys.version_info <= (3, 9):
    from typing import Callable, Coroutine, Generator  # pragma: no cover
else:
    from collections.abc import Callable, Coroutine, Generator


ReturnType = TypeVar('ReturnType')
FunctionParams = ParamSpec('FunctionParams')
SomeClassInstance = TypeVar('SomeClassInstance')

if sys.version_info >= (3, 9):
    IterableWithResults = Iterable[ReturnType]
else:
    IterableWithResults = Iterable  # pragma: no cover

__all__ = ('ParamSpec', 'TypeAlias', 'Callable', 'Coroutine', 'Generator', 'ReturnType', 'FunctionParams', 'IterableWithResults', 'SomeClassInstance')

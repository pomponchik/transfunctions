import sys
from typing import TypeVar

if sys.version_info >= (3, 10):
    from typing import ParamSpec
else:
    from typing_extensions import ParamSpec

if sys.version_info <= (3, 10):
    from typing_extensions import TypeAlias
else:
    from typing import TypeAlias

if sys.version_info <= (3, 9):
    from typing import Callable, Coroutine, Generator
else:
    from collections.abc import Callable, Coroutine, Generator


ReturnType = TypeVar("ReturnType")
FunctionParams = ParamSpec("FunctionParams")

__all__ = ("ParamSpec", "TypeAlias", "Callable", "Coroutine", "Generator", "ReturnType", "FunctionParams")

import sys
from typing import TypeVar

if sys.version_info <= (3, 9):  # pragma: no cover

try:
    from typing import ParamSpec
except ImportError:  # pragma: no cover
    from typing_extensions import ParamSpec  # type: ignore[assignment]

try:
    from typing import Protocol
except ImportError:  # pragma: no cover
    from typing_extensions import Protocol  # type: ignore[assignment]


FunctionParameters = ParamSpec("FunctionParameters")
CallResult = TypeVar("CallResult")

class GeneratorAndCoroutineProtocol(Protocol):
    def __iter__(self):
        ...

    def __await__(self) -> Any:  # pragma: no cover
        ...

    def send(self, value: Any) -> Any:
        ...

    def throw(self, exception_type: Any, value: Any = None, traceback: Any = None) -> None:  # pragma: no cover
        ...

    def close(self) -> None:  # pragma: no cover
        ...

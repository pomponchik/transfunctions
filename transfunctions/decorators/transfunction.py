from inspect import currentframe
from typing import Optional, Sequence, overload

from transfunctions.transformer import FunctionTransformer
from transfunctions.typing import Callable, FunctionParams, ReturnType


@overload
def transfunction(
    function: Callable[FunctionParams, ReturnType],
) -> FunctionTransformer[FunctionParams, ReturnType]: ...


@overload
def transfunction(
    *,
    variants: Sequence[str],
) -> Callable[[Callable[FunctionParams, ReturnType]], FunctionTransformer[FunctionParams, ReturnType]]: ...


def transfunction(  # type: ignore[misc]
    function: Optional[Callable[FunctionParams, ReturnType]] = None,
    *,
    variants: Optional[Sequence[str]] = None,
) -> object:
    caller_frame = currentframe().f_back  # type: ignore[union-attr]
    decorator_lineno = caller_frame.f_lineno  # type: ignore[union-attr]

    def decorator(fn: Callable[FunctionParams, ReturnType]) -> FunctionTransformer[FunctionParams, ReturnType]:
        return FunctionTransformer(
            fn,
            decorator_lineno,
            "transfunction",
            caller_frame,
            variants=variants,
        )

    if function is not None:
        return decorator(function)

    return decorator

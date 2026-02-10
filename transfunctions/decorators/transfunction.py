from inspect import currentframe
from types import FrameType
from typing import Union, cast, overload

from transfunctions.transformer import FunctionTransformer
from transfunctions.typing import Callable, FunctionParams, ReturnType


@overload
def transfunction(function: Callable[FunctionParams, ReturnType]) -> FunctionTransformer[FunctionParams, ReturnType]: ...


@overload
def transfunction(
    *, check_decorators: bool = True,
) -> Callable[[Callable[FunctionParams, ReturnType]], FunctionTransformer[FunctionParams, ReturnType]]: ...


def transfunction(  # type: ignore[misc]
    *args: Callable[FunctionParams, ReturnType], check_decorators: bool = True,
) -> Union[Callable[[Callable[FunctionParams, ReturnType]], FunctionTransformer[FunctionParams, ReturnType]], FunctionTransformer[FunctionParams, ReturnType]]:
    frame = currentframe()

    def decorator(
        function: Callable[FunctionParams, ReturnType],
    ) -> FunctionTransformer[FunctionParams, ReturnType]:
        return FunctionTransformer(
            function,
            cast(FrameType, cast(FrameType, frame).f_back).f_lineno,
            "transfunction",
            cast(FrameType, cast(FrameType, frame).f_back),
            check_decorators,
        )

    if args:
        return decorator(args[0])

    return decorator

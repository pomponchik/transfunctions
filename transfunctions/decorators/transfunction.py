from inspect import currentframe
from types import FrameType
from typing import cast

from transfunctions.transformer import FunctionTransformer
from transfunctions.typing import Callable, FunctionParams, ReturnType


def transfunction(
    function: Callable[FunctionParams, ReturnType],
) -> FunctionTransformer[FunctionParams, ReturnType]:
    return FunctionTransformer(
        function,
        cast(FrameType, cast(FrameType, currentframe()).f_back).f_lineno,
        "transfunction",
        cast(FrameType, cast(FrameType, currentframe()).f_back),
        True,
    )

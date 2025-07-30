from inspect import currentframe

from transfunctions.errors import AmbiguousFrameSyntaxError
from transfunctions.transformer import FunctionTransformer
from transfunctions._typing import Callable, FunctionParams, ReturnType


def transfunction(
    function: Callable[FunctionParams, ReturnType],
) -> FunctionTransformer[FunctionParams, ReturnType]:

    current_frame = currentframe()

    if current_frame is None or current_frame.f_back is None:
        raise AmbiguousFrameSyntaxError(
            "No stack frame found. This is likely due to calling this code from dynamically evaluated contexts."
        )

    return FunctionTransformer(function, current_frame.f_back.f_lineno, "transfunction")

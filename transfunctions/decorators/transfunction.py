from inspect import currentframe
from typing import TypeVar

from transfunctions.errors import AmbiguousFrameSyntaxError
from transfunctions.transformer import FunctionTransformer
from transfunctions.typing_compat import Callable, ParamSpec

R = TypeVar("R")
P = ParamSpec("P")


def transfunction(function: Callable[P, R]) -> FunctionTransformer[P, R]:

    current_frame = currentframe()

    if current_frame is None or current_frame.f_back is None:
        raise AmbiguousFrameSyntaxError(
            "No stack frame found. This is likely due to calling this code from dynamically evaluated contexts."
        )

    return FunctionTransformer(function, current_frame.f_back.f_lineno, "transfunction")

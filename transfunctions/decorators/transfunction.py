from inspect import currentframe

from transfunctions.transformer import FunctionTransformer
from transfunctions._typing import Callable, FunctionParams, ReturnType


def transfunction(
    function: Callable[FunctionParams, ReturnType],
) -> FunctionTransformer[FunctionParams, ReturnType]:
    return FunctionTransformer(function, currentframe().f_back.f_lineno, "transfunction")

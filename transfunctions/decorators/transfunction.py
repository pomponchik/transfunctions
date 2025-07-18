from transfunctions.transformer import FunctionTransformer
from inspect import currentframe


def transfunction(function):
    return FunctionTransformer(function, currentframe().f_back.f_lineno, 'transfunction')

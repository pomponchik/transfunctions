import sys
import weakref
from ast import NodeTransformer, Return, AST
from inspect import currentframe
from functools import wraps
from typing import Dict, Any, Optional, Union, List
from collections.abc import Coroutine

if sys.version_info <= (3, 10):  # pragma: no cover
    from typing_extensions import TypeAlias
else:  # pragma: no cover
    from typing import TypeAlias

from displayhooks import not_display

from transfunctions.transformer import FunctionTransformer
from transfunctions.errors import WrongTransfunctionSyntaxError


if sys.version_info <= (3, 9):  # pragma: no cover
    CoroutineClass = Coroutine
else:  # pragma: no cover
    CoroutineClass: TypeAlias = Coroutine[Any, Any, None]

class UsageTracer(CoroutineClass):
    def __init__(self, args, kwargs, transformer) -> None:
        self.flags: Dict[str, bool] = {}
        self.args = args
        self.kwargs = kwargs
        self.transformer = transformer
        self.coroutine = self.async_sleep_option(self.flags, args, kwargs, transformer)
        self.finalizer = weakref.finalize(self, self.sync_sleep_option, self.flags, args, kwargs, transformer, self.coroutine)

    def __iter__(self):
        self.flags['used'] = True
        self.coroutine.close()
        generator_function = self.transformer.get_generator_function()
        generator = generator_function(*(self.args), **(self.kwargs))
        yield from generator

    def __await__(self) -> Any:  # pragma: no cover
        return self.coroutine.__await__()

    def __invert__(self):
        result = self.finalizer()
        return result

    def send(self, value: Any) -> Any:
        return self.coroutine.send(value)

    def throw(self, exception_type: Any, value: Any = None, traceback: Any = None) -> None:  # pragma: no cover
        pass

    def close(self) -> None:  # pragma: no cover
        pass

    @staticmethod
    def sync_sleep_option(flags: Dict[str, bool], args, kwargs, transformer, wrapped_coroutine: CoroutineClass) -> None:
        if not flags.get('used', False):
            wrapped_coroutine.close()
            return transformer.get_usual_function()(*args, **kwargs)

    @staticmethod
    async def async_sleep_option(flags: Dict[str, bool], args, kwargs, transformer) -> None:
        flags['used'] = True
        return await transformer.get_async_function()(*args, **kwargs)


not_display(UsageTracer)

def superfunction(function):
    class NoReturns(NodeTransformer):
        def visit_Return(self, node: Return) -> Optional[Union[AST, List[AST]]]:
            raise WrongTransfunctionSyntaxError('A superfunction cannot contain a return statement.')

    transformer = FunctionTransformer(
        function,
        currentframe().f_back.f_lineno,
        'superfunction',
        extra_transformers=[
            #NoReturns(),
        ],
    )

    @wraps(function)
    def wrapper(*args, **kwargs):
        return UsageTracer(args, kwargs, transformer)

    wrapper.__is_superfunction__ = True

    return wrapper

import sys
import weakref
from ast import NodeTransformer, Return, AST
from inspect import currentframe
from functools import wraps
from typing import Dict, Any, Optional, Union, List, Callable
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
    def __init__(self, args, kwargs, transformer, tilde_syntax: bool) -> None:
        self.flags: Dict[str, bool] = {}
        self.args = args
        self.kwargs = kwargs
        self.transformer = transformer
        self.tilde_syntax = tilde_syntax
        self.coroutine = self.async_option(self.flags, args, kwargs, transformer)
        self.finalizer = weakref.finalize(self, self.sync_option, self.flags, args, kwargs, transformer, self.coroutine, tilde_syntax)

    def __iter__(self):
        self.flags['used'] = True
        self.coroutine.close()
        generator_function = self.transformer.get_generator_function()
        generator = generator_function(*(self.args), **(self.kwargs))
        yield from generator

    def __await__(self) -> Any:  # pragma: no cover
        return self.coroutine.__await__()

    def __invert__(self):
        if not self.tilde_syntax:
            raise NotImplementedError('The syntax with ~ is disabled for this superfunction. Call it with simple breackets.')

        self.flags['used'] = True
        self.coroutine.close()
        return self.transformer.get_usual_function()(*(self.args), **(self.kwargs))

    def send(self, value: Any) -> Any:
        return self.coroutine.send(value)

    def throw(self, exception_type: Any, value: Any = None, traceback: Any = None) -> None:  # pragma: no cover
        pass

    def close(self) -> None:  # pragma: no cover
        pass

    @staticmethod
    def sync_option(flags: Dict[str, bool], args, kwargs, transformer, wrapped_coroutine: CoroutineClass, tilde_syntax: bool) -> None:
        if not flags.get('used', False):
            wrapped_coroutine.close()
            if not tilde_syntax:
                return transformer.get_usual_function()(*args, **kwargs)
            else:
                raise NotImplementedError(f'The tilde-syntax is enabled for the "{transformer.function.__name__}" function. Call it like this: ~{transformer.function.__name__}().')

    @staticmethod
    async def async_option(flags: Dict[str, bool], args, kwargs, transformer) -> None:
        flags['used'] = True
        return await transformer.get_async_function()(*args, **kwargs)


not_display(UsageTracer)

def superfunction(*args: Callable, tilde_syntax: bool = True):
    def decorator(function):
        transformer = FunctionTransformer(
            function,
            currentframe().f_back.f_lineno,
            'superfunction',
        )

        if not tilde_syntax:
            class NoReturns(NodeTransformer):
                def visit_Return(self, node: Return) -> Optional[Union[AST, List[AST]]]:
                    raise WrongTransfunctionSyntaxError('A superfunction cannot contain a return statement.')
            transformer.get_usual_function(addictional_transformers=[NoReturns()])

        @wraps(function)
        def wrapper(*args, **kwargs):
            return UsageTracer(args, kwargs, transformer, tilde_syntax)

        wrapper.__is_superfunction__ = True

        return wrapper

    if args:
        return decorator(args[0])
    return decorator

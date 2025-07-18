from transfunctions.transformer import FunctionTransformer
from inspect import currentframe


import sys
import weakref

from functools import wraps
from typing import Dict, Any
from collections.abc import Coroutine

if sys.version_info <= (3, 10):  # pragma: no cover
    from typing_extensions import TypeAlias
else:  # pragma: no cover
    from typing import TypeAlias

from displayhooks import not_display


if sys.version_info <= (3, 8):  # pragma: no cover
    CoroutineClass = Coroutine
else:  # pragma: no cover
    CoroutineClass: TypeAlias = Coroutine[Any, Any, None]

class UsageTracer(CoroutineClass):
    def __init__(self, args, kwargs, transformer) -> None:
        self.flags: Dict[str, bool] = {}
        self.coroutine = self.async_sleep_option(self.flags, args, kwargs, transformer)
        weakref.finalize(self, self.sync_sleep_option, self.flags, args, kwargs, transformer, self.coroutine)

    def __await__(self) -> Any:  # pragma: no cover
        return self.coroutine.__await__()

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
            transformer.get_usual_function()(*args, **kwargs)

    @staticmethod
    async def async_sleep_option(flags: Dict[str, bool], args, kwargs, transformer) -> None:
        flags['used'] = True
        await transformer.get_async_function()(*args, **kwargs)


not_display(UsageTracer)

def superfunction(function):
    transformer = FunctionTransformer(function, currentframe().f_back.f_lineno, 'superfunction')

    @wraps(function)
    def wrapper(*args, **kwargs):
        return UsageTracer(args, kwargs, transformer)

    return wrapper

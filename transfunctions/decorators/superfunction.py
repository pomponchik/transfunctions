import weakref
from ast import AST, NodeTransformer, Return
from functools import wraps
from inspect import currentframe
from typing import Any, Dict, Generic, List, Optional, Union, overload

from displayhooks import not_display

from transfunctions.errors import (
    AmbiguousFrameSyntaxError,
    WrongTransfunctionSyntaxError,
)
from transfunctions.transformer import FunctionTransformer
from transfunctions._typing import Callable, Coroutine, ReturnType, FunctionParams, Generator


class ParamSpecContainer(Generic[FunctionParams]):
    def __init__(self, *args: FunctionParams.args, **kwargs: FunctionParams.kwargs) -> None:
        self.args = args
        self.kwargs = kwargs

class UsageTracer(Generic[FunctionParams, ReturnType], Coroutine[Any, None, ReturnType]):
    def __init__(
        self,
        param_spec: ParamSpecContainer[FunctionParams],
        transformer: FunctionTransformer[FunctionParams, ReturnType],
        tilde_syntax: bool,
    ) -> None:
        self.flags: Dict[str, bool] = {}
        self.args = param_spec.args
        self.kwargs = param_spec.kwargs
        self.transformer = transformer
        self.tilde_syntax = tilde_syntax
        self.coroutine = self.async_option(self.flags, param_spec, transformer)
        self.finalizer = weakref.finalize(
            self,
            self.sync_option,
            self.flags,
            param_spec,
            transformer,
            self.coroutine,
            tilde_syntax,
        )

    def __iter__(self) -> Generator[ReturnType, None, None]:
        self.flags['used'] = True
        self.coroutine.close()
        generator_function = self.transformer.get_generator_function()
        generator = generator_function(*(self.args), **(self.kwargs))
        yield from generator

    def __await__(self) -> Generator[Any, None, ReturnType]:
        return self.coroutine.__await__()

    def __invert__(self) -> ReturnType:
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
    def sync_option(
        flags: Dict[str, bool],
        param_spec: ParamSpecContainer[FunctionParams],
        transformer: FunctionTransformer[FunctionParams, ReturnType],
        wrapped_coroutine: Coroutine[Any, Any, ReturnType],
        tilde_syntax: bool,
    ) -> Optional[ReturnType]:
        if not flags.get('used', False):
            wrapped_coroutine.close()
            if not tilde_syntax:
                return transformer.get_usual_function()(*param_spec.args, **param_spec.kwargs)
            else:
                raise NotImplementedError(f'The tilde-syntax is enabled for the "{transformer.function.__name__}" function. Call it like this: ~{transformer.function.__name__}().')
        return None

    @staticmethod
    async def async_option(
        flags: Dict[str, bool], param_spec: ParamSpecContainer[FunctionParams], transformer: FunctionTransformer[FunctionParams, ReturnType]) -> ReturnType:
        flags['used'] = True
        return await transformer.get_async_function()(*param_spec.args, **param_spec.kwargs)


not_display(UsageTracer)


@overload
def superfunction(function: Callable[FunctionParams, ReturnType]) -> Callable[FunctionParams, UsageTracer[FunctionParams, ReturnType]]: ...


@overload
def superfunction(
    *, tilde_syntax: bool = True
) -> Callable[[Callable[FunctionParams, ReturnType]], Callable[FunctionParams, UsageTracer[FunctionParams, ReturnType]]]: ...


def superfunction(
    function: Optional[Callable[FunctionParams, ReturnType]] = None, *, tilde_syntax: bool = True
) -> Union[
    Callable[FunctionParams, UsageTracer[FunctionParams, ReturnType]],
    Callable[[Callable[FunctionParams, ReturnType]], Callable[FunctionParams, UsageTracer[FunctionParams, ReturnType]]],
]:
    def decorator(function: Callable[FunctionParams, ReturnType]) -> Callable[FunctionParams, UsageTracer[FunctionParams, ReturnType]]:
        current_frame = currentframe()
        if current_frame is None or current_frame.f_back is None:
            raise AmbiguousFrameSyntaxError(
                "No stack frame found. This is likely due to calling this code from dynamically evaluated contexts."
            )

        transformer = FunctionTransformer(
            function,
            current_frame.f_back.f_lineno,
            "superfunction",
        )

        if not tilde_syntax:

            class NoReturns(NodeTransformer):
                def visit_Return(self, node: Return) -> Optional[Union[AST, List[AST]]]:
                    raise WrongTransfunctionSyntaxError('A superfunction cannot contain a return statement.')
            transformer.get_usual_function(addictional_transformers=[NoReturns()])

        @wraps(function)
        def wrapper(*args: FunctionParams.args, **kwargs: FunctionParams.kwargs) -> UsageTracer[FunctionParams, ReturnType]:
            return UsageTracer(ParamSpecContainer(*args, **kwargs), transformer, tilde_syntax)

        setattr(wrapper, "__is_superfunction__", True)

        return wrapper

    if function is not None:
        return decorator(function)

    return decorator

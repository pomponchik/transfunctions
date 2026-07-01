import asyncio
import sys
from contextlib import suppress

if sys.version_info <= (3, 11):
    from typing_extensions import reveal_type
else:
    from typing import reveal_type

import pytest

from transfunctions import (
    async_context,
    generator_context,
    superfunction,
    sync_context,
    yield_from_it,
)

"""
Что нужно проверить:

1. Что await_it, yield_from_it и yield_it типизированы.
2. Нельзя сохранять возвращаемое значение суперфункции в переменную.

Что проверено:

"""


@pytest.mark.mypy_testing
def test_superfunction_deduced_return_type_sync() -> None:
    """
    Ensure mypy infers a synchronous superfunction tilde call as the template's annotated return type.

    The check uses reveal_type on the sync call path and expects int, focusing on static return type deduction rather than runtime behavior.
    """
    @superfunction
    def typed_superfunction(arg: float, *, kwarg: int = 0) -> int:  # noqa: ARG001
        with sync_context:
            return 1
        with async_context:
            return 2

    reveal_type(~typed_superfunction(1.0)) # N: Revealed type is "builtins.int"


@pytest.mark.mypy_testing
def test_superfunction_deduced_return_type_async() -> None:
    """
    Locks down that async use of a @superfunction exposes the template's annotated return type.

    The check treats the decorated function call as a coroutine passed to asyncio.run and expects the revealed result type to remain int, while still allowing the forwarded positional argument.
    """
    @superfunction
    def typed_superfunction(arg: float, *, kwarg: int = 0) -> int:  # noqa: ARG001
        with sync_context:
            return 1
        with async_context:
            return 2

    reveal_type(asyncio.run(typed_superfunction(1.0))) # N: Revealed type is "builtins.int"


@pytest.mark.mypy_testing
def test_superfunction_param_spec_fail_on_incorrect_arg_type_sync() -> None:
    """
    Reject a synchronous tilde call to a superfunction when the first positional argument has the wrong type.

    The keyword argument is valid, so the checked failure is that None is not accepted where the original template requires a float.
    """
    @superfunction
    def typed_superfunction(arg: float, *, kwarg: int = 0) -> int:  # noqa: ARG001
        with sync_context:
            return 1
        with async_context:
            return 2

    ~typed_superfunction(None, kwarg=1) # E: Argument 1 to "typed_superfunction" has incompatible type "None"; expected "float"


@pytest.mark.mypy_testing
def test_superfunction_param_spec_fail_on_incorrect_kwarg_type_sync() -> None:
    """
    A @superfunction preserves keyword-only argument types for static checking in the synchronous tilde call path.

    The check verifies that mypy rejects passing None to an int parameter named kwarg.
    """
    @superfunction
    def typed_superfunction(arg: float, *, kwarg: int = 0) -> int:  # noqa: ARG001
        with sync_context:
            return 1
        with async_context:
            return 2

    ~typed_superfunction(1.0, kwarg=None) # E: Argument "kwarg" to "typed_superfunction" has incompatible type "None"; expected "int"


@pytest.mark.mypy_testing
def test_superfunction_param_spec_on_correct_args_types_sync() -> None:
    """
    A superfunction preserves its original parameter types for valid synchronous tilde calls.

    The check calls the decorated function with a float positional argument and an int keyword-only argument, matching the template signature, and expects static type checking to accept the call.
    """
    @superfunction
    def typed_superfunction(arg: float, *, kwarg: int = 0) -> int:  # noqa: ARG001
        with sync_context:
            return 1
        with async_context:
            return 2

    ~typed_superfunction(1.0, kwarg=1)


@pytest.mark.mypy_testing
def test_superfunction_param_spec_fail_on_incorrect_arg_type_async() -> None:
    """
    Ensure a superfunction keeps its ParamSpec when type checked through async-style invocation.

    The call is wrapped in asyncio.run, passes None for a parameter annotated as float, and supplies a valid keyword-only int so the expected mypy failure is limited to the first positional argument.
    """
    @superfunction
    def typed_superfunction(arg: float, *, kwarg: int = 0) -> int:  # noqa: ARG001
        with sync_context:
            return 1
        with async_context:
            return 2

    asyncio.run(typed_superfunction(None, kwarg=1)) # E: Argument 1 to "typed_superfunction" has incompatible type "None"; expected "float"


@pytest.mark.mypy_testing
def test_superfunction_param_spec_fail_on_incorrect_kwarg_type_async() -> None:
    """
    Ensure async superfunction calls preserve keyword-only parameter types for static checking.

    The test exercises coroutine consumption with asyncio.run and expects mypy to reject passing None to an int keyword-only argument.
    """
    @superfunction
    def typed_superfunction(arg: float, *, kwarg: int = 0) -> int:  # noqa: ARG001
        with sync_context:
            return 1
        with async_context:
            return 2

    asyncio.run(typed_superfunction(1.0, kwarg=None)) # E: Argument "kwarg" to "typed_superfunction" has incompatible type "None"; expected "int"


@pytest.mark.mypy_testing
def test_superfunction_param_spec_on_correct_args_types_async() -> None:
    """
    Ensures @superfunction keeps the template ParamSpec when called through async usage.

    The type check should accept asyncio.run on the decorated function with the required float positional argument and keyword-only int argument, with no expected mypy errors.
    """
    @superfunction
    def typed_superfunction(arg: float, *, kwarg: int = 0) -> int:  # noqa: ARG001
        with sync_context:
            return 1
        with async_context:
            return 2

    asyncio.run(typed_superfunction(1.0, kwarg=1))


@pytest.mark.mypy_testing
def test_superfunction_param_spec_fail_on_missing_args_sync() -> None:
    """
    Ensure type checking reports a missing-argument error for sync tilde calls to a superfunction without its required positional argument.

    The runtime TypeError is suppressed so the test can verify the inline type-checking expectation rather than fail during execution.
    """
    @superfunction
    def typed_superfunction(arg: float, *, kwarg: int = 0) -> int:  # noqa: ARG001
        with sync_context:
            return 1
        with async_context:
            return 2

    with suppress(TypeError):
        ~typed_superfunction() # E: Missing positional argument "arg" in call to "typed_superfunction"  [call-arg]


@pytest.mark.mypy_testing
@pytest.mark.xfail
def test_superfunction_param_spec_fail_on_extra_args_sync() -> None:
    """
    Track the xfailed extra-positional-argument case for sync tilde superfunction calls.

    The call uses unary ~ with the valid first argument, the keyword-only argument, and one additional positional value under suppress(TypeError).
    """
    @superfunction
    def typed_superfunction(arg: float, *, kwarg: int = 0) -> int:  # noqa: ARG001
        with sync_context:
            return 1
        with async_context:
            return 2

    with suppress(TypeError):
        ~typed_superfunction(1.0, 2.0, kwarg=1)


@pytest.mark.mypy_testing
@pytest.mark.xfail
def test_superfunction_param_spec_fail_on_extra_kwargs_sync() -> None:
    """
    Reject unexpected keyword arguments on synchronous tilde calls to a superfunction.

    The decorated function allows a float positional argument and the keyword-only kwarg, so passing kwarg2 should be a static call-shape error. Runtime TypeError is suppressed because the assertion is about typing.
    """
    @superfunction
    def typed_superfunction(arg: float, *, kwarg: int = 0) -> int:  # noqa: ARG001
        with sync_context:
            return 1
        with async_context:
            return 2

    with suppress(TypeError):
        ~typed_superfunction(1.0, kwarg=1, kwarg2=1)


@pytest.mark.mypy_testing
def test_superfunction_param_spec_fail_on_missing_args_async() -> None:
    """
    Mypy rejects asyncio.run calls to a superfunction that omit a required positional argument.

    Runtime TypeError is suppressed so the test can keep the focus on the preserved ParamSpec call-shape error for async-style consumption.
    """
    @superfunction
    def typed_superfunction(arg: float, *, kwarg: int = 0) -> int:  # noqa: ARG001
        with sync_context:
            return 1
        with async_context:
            return 2

    with suppress(TypeError):
        asyncio.run(typed_superfunction()) # E: Missing positional argument "arg" in call to "typed_superfunction"  [call-arg]


@pytest.mark.mypy_testing
@pytest.mark.xfail
def test_superfunction_param_spec_fail_on_extra_args_async() -> None:
    """
    Track the xfailed extra-positional-argument case for async-style superfunction calls.

    The call is wrapped in asyncio.run under suppress(TypeError), with a valid first argument, the keyword-only argument, and one additional positional value.
    """
    @superfunction
    def typed_superfunction(arg: float, *, kwarg: int = 0) -> int:  # noqa: ARG001
        with sync_context:
            return 1
        with async_context:
            return 2

    with suppress(TypeError):
        asyncio.run(typed_superfunction(1.0, 2.0, kwarg=1))


@pytest.mark.mypy_testing
@pytest.mark.xfail
def test_superfunction_param_spec_fail_on_extra_kwargs_async() -> None:
    """
    Async-style superfunction calls reject unexpected keyword arguments.

    The checked call is wrapped in asyncio.run under suppress(TypeError), supplies the valid positional and keyword-only arguments, then adds one extra keyword. The typing failure is expected to be about that unexpected keyword.
    """
    @superfunction
    def typed_superfunction(arg: float, *, kwarg: int = 0) -> int:  # noqa: ARG001
        with sync_context:
            return 1
        with async_context:
            return 2

    with suppress(TypeError):
        asyncio.run(typed_superfunction(1.0, kwarg=1, kwarg2=1))


@pytest.mark.mypy_testing
@pytest.mark.xfail  # it shouldn't work because typed_superfunction is a generator function, gut it's not returning a generator object according to it's typing.
def test_simple_using_of_generator_function_with_simple_yield_from() -> None:
    """
    Calling a typed superfunction in generator mode is expected to fail static typing when its generator branch uses native yield from.

    This locks down the known limitation that raw generator syntax makes the decorated template look like a generator function to mypy, even though list(...) is the intended generator-mode use at runtime.
    """
    @superfunction
    def typed_superfunction(arg: float, *, kwarg: int = 0) -> int:  # noqa: ARG001
        with sync_context:
            return 1
        with async_context:
            return 2
        with generator_context:
            yield from [1, 2, 3]

    list(typed_superfunction(1))


# TODO: we should understand why it works
@pytest.mark.xfail
@pytest.mark.mypy_testing
def test_wrong_using_of_generator_function_with_simple_yield_from() -> None:
    """
    Generator-style use of a superfunction still enforces the original positional argument type.

    This xfailed typing case checks that consuming the generator form does not hide that None is invalid for a float parameter, even when the template uses a plain yield from branch.
    """
    @superfunction
    def typed_superfunction(arg: float, *, kwarg: int = 0) -> int:  # noqa: ARG001
        with sync_context:
            return 1
        with async_context:
            return 2
        with generator_context:
            yield from [1, 2, 3]

    list(typed_superfunction(None))


@pytest.mark.mypy_testing
def test_simple_using_of_generator_function_with_yield_from_it_marker_function() -> None:
    """
    A @superfunction generator_context branch using yield_from_it type-checks when the generated function is consumed with list(...).

    The template body has separate sync_context, async_context, and generator_context blocks. The generator block calls yield_from_it with integer values, and the check calls the decorated object itself with a valid original argument and wraps that call in list(...).
    """
    @superfunction
    def typed_superfunction(arg: float, *, kwarg: int = 0) -> int:  # noqa: ARG001
        with sync_context:
            return 1
        with async_context:
            return 2
        with generator_context:
            yield_from_it([1, 2, 3])

    list(typed_superfunction(1))


# TODO: we should understand why it works
@pytest.mark.xfail
@pytest.mark.mypy_testing
def test_using_of_generator_function_with_yield_from_it_marker_function_with_wrong_return_value() -> None:
    """Documents the typing gap where yield_from_it can yield strings from a superfunction annotated to return int."""
    @superfunction
    def typed_superfunction(arg: float, *, kwarg: int = 0) -> int:  # noqa: ARG001
        with sync_context:
            return 1
        with async_context:
            return 2
        with generator_context:
            yield_from_it(['one', 'two'])

    list(typed_superfunction(1))

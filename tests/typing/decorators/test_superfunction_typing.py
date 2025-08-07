import sys
import asyncio
from contextlib import suppress

if sys.version_info <= (3, 11):
    from typing_extensions import reveal_type
else:
    from typing import reveal_type

import pytest

from transfunctions import superfunction, sync_context, async_context, generator_context, yield_from_it


"""
Что нужно проверить:

1. Что await_it, yield_from_it и yield_it типизированы.
2. Нельзя сохранять возвращаемое значение суперфункции в переменную.

Что проверено:

"""


@pytest.mark.mypy_testing
def test_superfunction_deduced_return_type_sync() -> None:
    @superfunction
    def typed_superfunction(arg: float, *, kwarg: int = 0) -> int:
        with sync_context:
            return 1
        with async_context:
            return 2

    reveal_type(~typed_superfunction(1.0)) # N: Revealed type is "builtins.int"


@pytest.mark.mypy_testing
def test_superfunction_deduced_return_type_async() -> None:
    @superfunction
    def typed_superfunction(arg: float, *, kwarg: int = 0) -> int:
        with sync_context:
            return 1
        with async_context:
            return 2

    reveal_type(asyncio.run(typed_superfunction(1.0))) # N: Revealed type is "builtins.int"


@pytest.mark.mypy_testing
def test_superfunction_param_spec_fail_on_incorrect_arg_type_sync() -> None:
    @superfunction
    def typed_superfunction(arg: float, *, kwarg: int = 0) -> int:
        with sync_context:
            return 1
        with async_context:
            return 2

    ~typed_superfunction(None, kwarg=1) # E: Argument 1 to "typed_superfunction" has incompatible type "None"; expected "float"


@pytest.mark.mypy_testing
def test_superfunction_param_spec_fail_on_incorrect_kwarg_type_sync() -> None:
    @superfunction
    def typed_superfunction(arg: float, *, kwarg: int = 0) -> int:
        with sync_context:
            return 1
        with async_context:
            return 2

    ~typed_superfunction(1.0, kwarg=None) # E: Argument "kwarg" to "typed_superfunction" has incompatible type "None"; expected "int"


@pytest.mark.mypy_testing
def test_superfunction_param_spec_on_correct_args_types_sync() -> None:
    @superfunction
    def typed_superfunction(arg: float, *, kwarg: int = 0) -> int:
        with sync_context:
            return 1
        with async_context:
            return 2

    ~typed_superfunction(1.0, kwarg=1)


@pytest.mark.mypy_testing
def test_superfunction_param_spec_fail_on_incorrect_arg_type_async() -> None:
    @superfunction
    def typed_superfunction(arg: float, *, kwarg: int = 0) -> int:
        with sync_context:
            return 1
        with async_context:
            return 2

    asyncio.run(typed_superfunction(None, kwarg=1)) # E: Argument 1 to "typed_superfunction" has incompatible type "None"; expected "float"


@pytest.mark.mypy_testing
def test_superfunction_param_spec_fail_on_incorrect_kwarg_type_async() -> None:
    @superfunction
    def typed_superfunction(arg: float, *, kwarg: int = 0) -> int:
        with sync_context:
            return 1
        with async_context:
            return 2

    asyncio.run(typed_superfunction(1.0, kwarg=None)) # E: Argument "kwarg" to "typed_superfunction" has incompatible type "None"; expected "int"


@pytest.mark.mypy_testing
def test_superfunction_param_spec_on_correct_args_types_async() -> None:
    @superfunction
    def typed_superfunction(arg: float, *, kwarg: int = 0) -> int:
        with sync_context:
            return 1
        with async_context:
            return 2

    asyncio.run(typed_superfunction(1.0, kwarg=1))


@pytest.mark.mypy_testing
def test_superfunction_param_spec_fail_on_missing_args_sync() -> None:
    @superfunction
    def typed_superfunction(arg: float, *, kwarg: int = 0) -> int:
        with sync_context:
            return 1
        with async_context:
            return 2

    with suppress(TypeError):
        ~typed_superfunction() # E: Missing positional argument "arg" in call to "typed_superfunction"  [call-arg]


@pytest.mark.mypy_testing
@pytest.mark.xfail
def test_superfunction_param_spec_fail_on_extra_args_sync() -> None:
    @superfunction
    def typed_superfunction(arg: float, *, kwarg: int = 0) -> int:
        with sync_context:
            return 1
        with async_context:
            return 2

    with suppress(TypeError):
        ~typed_superfunction(1.0, 2.0, kwarg=1)


@pytest.mark.mypy_testing
@pytest.mark.xfail
def test_superfunction_param_spec_fail_on_extra_kwargs_sync() -> None:
    @superfunction
    def typed_superfunction(arg: float, *, kwarg: int = 0) -> int:
        with sync_context:
            return 1
        with async_context:
            return 2

    with suppress(TypeError):
        ~typed_superfunction(1.0, kwarg=1, kwarg2=1)


@pytest.mark.mypy_testing
def test_superfunction_param_spec_fail_on_missing_args_async() -> None:
    @superfunction
    def typed_superfunction(arg: float, *, kwarg: int = 0) -> int:
        with sync_context:
            return 1
        with async_context:
            return 2

    with suppress(TypeError):
        asyncio.run(typed_superfunction()) # E: Missing positional argument "arg" in call to "typed_superfunction"  [call-arg]


@pytest.mark.mypy_testing
@pytest.mark.xfail
def test_superfunction_param_spec_fail_on_extra_args_async() -> None:
    @superfunction
    def typed_superfunction(arg: float, *, kwarg: int = 0) -> int:
        with sync_context:
            return 1
        with async_context:
            return 2

    with suppress(TypeError):
        asyncio.run(typed_superfunction(1.0, 2.0, kwarg=1))


@pytest.mark.mypy_testing
@pytest.mark.xfail
def test_superfunction_param_spec_fail_on_extra_kwargs_async() -> None:
    @superfunction
    def typed_superfunction(arg: float, *, kwarg: int = 0) -> int:
        with sync_context:
            return 1
        with async_context:
            return 2

    with suppress(TypeError):
        asyncio.run(typed_superfunction(1.0, kwarg=1, kwarg2=1))


@pytest.mark.mypy_testing
@pytest.mark.xfail  # it shouldn't work because typed_superfunction is a generator function, gut it's not returning a generator object according to it's typing.
def test_simple_using_of_generator_function_with_simple_yield_from() -> None:
    @superfunction
    def typed_superfunction(arg: float, *, kwarg: int = 0) -> int:
        with sync_context:
            return 1
        with async_context:
            return 2
        with generator_context:
            yield from [1, 2, 3]

    list(typed_superfunction(1))


# TODO: we should understand why it works
#@pytest.mark.xfail
@pytest.mark.mypy_testing
def test_wrong_using_of_generator_function_with_simple_yield_from() -> None:
    @superfunction
    def typed_superfunction(arg: float, *, kwarg: int = 0) -> int:
        with sync_context:
            return 1
        with async_context:
            return 2
        with generator_context:
            yield from [1, 2, 3]

    list(typed_superfunction(None))


@pytest.mark.mypy_testing
def test_simple_using_of_generator_function_with_yield_from_it_marker_function() -> None:
    @superfunction
    def typed_superfunction(arg: float, *, kwarg: int = 0) -> int:
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
    @superfunction
    def typed_superfunction(arg: float, *, kwarg: int = 0) -> int:
        with sync_context:
            return 1
        with async_context:
            return 2
        with generator_context:
            yield_from_it(['one', 'two'])

    list(typed_superfunction(1))

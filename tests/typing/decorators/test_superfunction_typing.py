import sys
import asyncio
from contextlib import suppress

if sys.version_info <= (3, 11):
    from typing_extensions import reveal_type
else:
    from typing import reveal_type

import pytest

from transfunctions import superfunction, sync_context, async_context


@superfunction
def typed_superfunction(arg: float, *, kwarg: int = 0) -> int:
    with sync_context:
        return 1
    with async_context:
        return 2
    # TODO: add test case for generator_context once there is a typing solution


@pytest.mark.mypy_testing
def test_superfunction_deduced_return_type_sync():
    reveal_type(~typed_superfunction(1.0)) # N: Revealed type is "builtins.int"


@pytest.mark.mypy_testing
def test_superfunction_deduced_return_type_async():
    reveal_type(asyncio.run(typed_superfunction(1.0))) # N: Revealed type is "builtins.int"


@pytest.mark.mypy_testing
def test_superfunction_param_spec_fail_on_incorrect_arg_type_sync():
    ~typed_superfunction(None, kwarg=1) # E: Argument 1 to "typed_superfunction" has incompatible type "None"; expected "float"


@pytest.mark.mypy_testing
def test_superfunction_param_spec_fail_on_incorrect_kwarg_type_sync():
    ~typed_superfunction(1.0, kwarg=None) # E: Argument "kwarg" to "typed_superfunction" has incompatible type "None"; expected "int"


@pytest.mark.mypy_testing
def test_superfunction_param_spec_on_correct_args_types_sync():
    ~typed_superfunction(1.0, kwarg=1)


@pytest.mark.mypy_testing
def test_superfunction_param_spec_fail_on_incorrect_arg_type_async():
    asyncio.run(typed_superfunction(None, kwarg=1)) # E: Argument 1 to "typed_superfunction" has incompatible type "None"; expected "float"


@pytest.mark.mypy_testing
def test_superfunction_param_spec_fail_on_incorrect_kwarg_type_async():
    asyncio.run(typed_superfunction(1.0, kwarg=None)) # E: Argument "kwarg" to "typed_superfunction" has incompatible type "None"; expected "int"


@pytest.mark.mypy_testing
def test_superfunction_param_spec_on_correct_args_types_async():
    asyncio.run(typed_superfunction(1.0, kwarg=1))


@pytest.mark.mypy_testing
def test_superfunction_param_spec_fail_on_missing_args_sync():
    with suppress(TypeError):
        ~typed_superfunction() # E: Missing positional argument "arg" in call to "typed_superfunction"  [call-arg]


@pytest.mark.mypy_testing
@pytest.mark.xfail
def test_superfunction_param_spec_fail_on_extra_args_sync():
    with suppress(TypeError):
        ~typed_superfunction(1.0, 2.0, kwarg=1)


@pytest.mark.mypy_testing
@pytest.mark.xfail
def test_superfunction_param_spec_fail_on_extra_kwargs_sync():
    with suppress(TypeError):
        ~typed_superfunction(1.0, kwarg=1, kwarg2=1)


@pytest.mark.mypy_testing
def test_superfunction_param_spec_fail_on_missing_args_async():
    with suppress(TypeError):
        asyncio.run(typed_superfunction()) # E: Missing positional argument "arg" in call to "typed_superfunction"  [call-arg]


@pytest.mark.mypy_testing
@pytest.mark.xfail
def test_superfunction_param_spec_fail_on_extra_args_async():
    with suppress(TypeError):
        asyncio.run(typed_superfunction(1.0, 2.0, kwarg=1))


@pytest.mark.mypy_testing
@pytest.mark.xfail
def test_superfunction_param_spec_fail_on_extra_kwargs_async():
    with suppress(TypeError):
        asyncio.run(typed_superfunction(1.0, kwarg=1, kwarg2=1))

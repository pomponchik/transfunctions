import asyncio
import sys
from contextlib import suppress

if sys.version_info <= (3, 11):
    from typing_extensions import reveal_type
else:
    from typing import reveal_type

import pytest

from transfunctions import async_context, sync_context, transfunction


@pytest.mark.mypy_testing
def test_transfunction_deduced_return_type_sync():
    """
    Verify that @transfunction preserves the annotated return type for a generated synchronous function.

    The type check calls the regular function returned by get_usual_function() and confirms that a template annotated to return int is inferred as int.
    """
    @transfunction
    def typed_transfunction(arg: float, *, kwarg: int = 0) -> int:  # noqa: ARG001
        with sync_context:
            return 1
        with async_context:
            return 2
    # TODO: add test case for generator_context once there is a typing solution

    reveal_type(typed_transfunction.get_usual_function()(1.0)) # N: Revealed type is "builtins.int"


@pytest.mark.mypy_testing
def test_transfunction_deduced_return_type_async():
    """
    Verify that the decorated object's get_async_function() method preserves the template return type after asyncio.run(...).

    The template is a regular @transfunction body with sync_context and async_context blocks, not an async def. The type check calls get_async_function() as a method on the decorated object, invokes the returned async callable, and consumes it through asyncio.run expecting the annotated int result.
    """
    @transfunction
    def typed_transfunction(arg: float, *, kwarg: int = 0) -> int:  # noqa: ARG001
        with sync_context:
            return 1
        with async_context:
            return 2

    reveal_type(asyncio.run(typed_transfunction.get_async_function()(1.0))) # N: Revealed type is "builtins.int"


@pytest.mark.mypy_testing
def test_transfunction_param_spec_fail_on_incorrect_arg_type_sync():
    """
    A transfunction-generated synchronous callable preserves the original positional argument type.

    The check passes None where a float is required while keeping the keyword-only argument valid, so the expected type failure is isolated to the first positional argument.
    """
    @transfunction
    def typed_transfunction(arg: float, *, kwarg: int = 0) -> int:  # noqa: ARG001
        with sync_context:
            return 1
        with async_context:
            return 2

    typed_transfunction.get_usual_function()(None, kwarg=1) # E: Argument 1 has incompatible type "None"; expected "float"


@pytest.mark.mypy_testing
def test_transfunction_param_spec_fail_on_incorrect_kwarg_type_sync():
    """
    @transfunction preserves keyword-only parameter types on the callable returned by get_usual_function().

    The check calls get_usual_function()(...) with a valid positional argument and an invalid keyword-only value, so the expected type failure is isolated to that keyword-only int parameter.
    """
    @transfunction
    def typed_transfunction(arg: float, *, kwarg: int = 0) -> int:  # noqa: ARG001
        with sync_context:
            return 1
        with async_context:
            return 2

    typed_transfunction.get_usual_function()(1.0, kwarg=None) # E: Argument "kwarg" has incompatible type "None"; expected "int"


@pytest.mark.mypy_testing
def test_transfunction_param_spec_fail_on_missing_args_sync():
    """
    The callable returned by a @transfunction object's get_usual_function() still requires the template's positional arguments.

    The template body uses with sync_context and with async_context blocks. The check calls get_usual_function() on the decorated object, then invokes that generated sync function with no arguments while suppressing runtime TypeError.
    """
    @transfunction
    def typed_transfunction(arg: float, *, kwarg: int = 0) -> int:  # noqa: ARG001
        with sync_context:
            return 1
        with async_context:
            return 2

    with suppress(TypeError):
        typed_transfunction.get_usual_function()() # E: Too few arguments


@pytest.mark.mypy_testing
@pytest.mark.xfail
def test_transfunction_param_spec_fail_on_extra_args_sync():
    """
    Reject extra positional arguments on the callable returned by get_usual_function().

    The xfailed check calls the generated sync function with the required float, the valid keyword-only int, and one unexpected positional value while suppressing runtime TypeError.
    """
    @transfunction
    def typed_transfunction(arg: float, *, kwarg: int = 0) -> int:  # noqa: ARG001
        with sync_context:
            return 1
        with async_context:
            return 2

    with suppress(TypeError):
        typed_transfunction.get_usual_function()(1.0, 2.0, kwarg=1)


@pytest.mark.mypy_testing
@pytest.mark.xfail
def test_transfunction_param_spec_fail_on_extra_kwargs_sync():
    """
    Reject unexpected keywords on the callable returned by get_usual_function().

    The xfailed check calls the generated sync function with valid arguments plus an unsupported keyword while suppressing runtime TypeError.
    """
    @transfunction
    def typed_transfunction(arg: float, *, kwarg: int = 0) -> int:  # noqa: ARG001
        with sync_context:
            return 1
        with async_context:
            return 2

    with suppress(TypeError):
        typed_transfunction.get_usual_function()(1.0, kwarg=1, kwarg2=1)


@pytest.mark.mypy_testing
def test_transfunction_param_spec_on_correct_args_types_sync():
    """
    A sync transfunction preserves the template ParamSpec so correctly typed arguments are accepted.

    This checks the positive mypy case for get_usual_function: a valid float positional argument and keyword-only int argument should type-check without an expected-error marker.
    """
    @transfunction
    def typed_transfunction(arg: float, *, kwarg: int = 0) -> int:  # noqa: ARG001
        with sync_context:
            return 1
        with async_context:
            return 2

    typed_transfunction.get_usual_function()(1.0, kwarg=1)


@pytest.mark.mypy_testing
def test_transfunction_param_spec_fail_on_incorrect_arg_type_async():
    """
    The async callable returned by get_async_function() preserves the template's positional parameter type.

    The check runs the generated coroutine with None where a float is required, while keeping the keyword-only argument valid.
    """
    @transfunction
    def typed_transfunction(arg: float, *, kwarg: int = 0) -> int:  # noqa: ARG001
        with sync_context:
            return 1
        with async_context:
            return 2

    asyncio.run(typed_transfunction.get_async_function()(None, kwarg=1)) # E: Argument 1 has incompatible type "None"; expected "float"


@pytest.mark.mypy_testing
def test_transfunction_param_spec_fail_on_incorrect_kwarg_type_async():
    """
    The async callable returned by get_async_function() preserves the template's keyword-only parameter type.

    The check runs the generated coroutine with a valid float and None for the keyword-only int argument.
    """
    @transfunction
    def typed_transfunction(arg: float, *, kwarg: int = 0) -> int:  # noqa: ARG001
        with sync_context:
            return 1
        with async_context:
            return 2

    asyncio.run(typed_transfunction.get_async_function()(1.0, kwarg=None)) # E: Argument "kwarg" has incompatible type "None"; expected "int"


@pytest.mark.mypy_testing
def test_transfunction_param_spec_fail_on_missing_args_async():
    """
    The async callable returned by get_async_function() still requires the template's positional argument.

    Runtime TypeError is suppressed so the inline mypy expectation can check the missing-argument error.
    """
    @transfunction
    def typed_transfunction(arg: float, *, kwarg: int = 0) -> int:  # noqa: ARG001
        with sync_context:
            return 1
        with async_context:
            return 2

    with suppress(TypeError):
        asyncio.run(typed_transfunction.get_async_function()()) # E: Too few arguments

@pytest.mark.mypy_testing
@pytest.mark.xfail
def test_transfunction_param_spec_fail_on_extra_args_async():
    """
    Document the current xfailed gap for extra positional arguments in the async-labeled transfunction case.

    The body calls get_usual_function() inside asyncio.run with one unexpected positional value, so this test does not actually cover get_async_function().
    """
    @transfunction
    def typed_transfunction(arg: float, *, kwarg: int = 0) -> int:  # noqa: ARG001
        with sync_context:
            return 1
        with async_context:
            return 2

    with suppress(TypeError):
        asyncio.run(typed_transfunction.get_usual_function()(1.0, 2.0, kwarg=1))


@pytest.mark.mypy_testing
@pytest.mark.xfail
def test_transfunction_param_spec_fail_on_extra_kwargs_async():
    """
    Document the current xfailed gap for unexpected keywords in the async-labeled transfunction case.

    The body calls get_usual_function() inside asyncio.run with an extra keyword, so this test does not actually cover get_async_function().
    """
    @transfunction
    def typed_transfunction(arg: float, *, kwarg: int = 0) -> int:  # noqa: ARG001
        with sync_context:
            return 1
        with async_context:
            return 2

    with suppress(TypeError):
        asyncio.run(typed_transfunction.get_usual_function()(1.0, kwarg=1, kwarg2=1))


@pytest.mark.mypy_testing
@pytest.mark.xfail
def test_transfunction_param_spec_on_correct_args_types_async():
    """
    Exercise the positive ParamSpec case for get_async_function().

    The generated async callable is run with a valid float positional argument and keyword-only int argument, and the call is expected to type-check successfully.
    """
    @transfunction
    def typed_transfunction(arg: float, *, kwarg: int = 0) -> int:  # noqa: ARG001
        with sync_context:
            return 1
        with async_context:
            return 2

    asyncio.run(typed_transfunction.get_async_function()(1.0, kwarg=1))

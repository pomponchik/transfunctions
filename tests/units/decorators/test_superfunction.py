import io
import sys
from asyncio import run
from contextlib import redirect_stdout

import pytest
from full_match import match

from transfunctions import (
    WrongDecoratorSyntaxError,
    WrongMarkerSyntaxError,
    WrongTransfunctionSyntaxError,
    async_context,
    await_it,
    generator_context,
    superfunction,
    sync_context,
    yield_from_it,
)

"""
Что нужно проверить:

3. Трейсбек исключения из п. 2 информативен (т.е. содержит конкретную строчку кода, и короткий). Но есть возможность увидеть полный "настоящий" трейсбек.
4. Базовые кейсы работают в глобальном скоупе.

Что проверено:

1. Все базово работает без аргументов и с аргументами, для обычных, асинк и генераторных функций.
5. С использованием синтаксиса ~ для вызова обычных функций можно возвращать значения, с аргументами и без.
2. При попытке вызвать без тильды суперфункцию, в которой есть return или raise, должно подниматься исключение.
6. С синтаксисом ~ нормально поднимаются исключения.
"""


global_variable = 123

def test_just_sync_call_without_breackets():
    """
    A bare @superfunction call evaluated with unary ~ runs only the sync_context branch.

    The template has sync and async branches that print different values plus a generator branch that would yield values. The check redirects stdout around ~function() and expects only the sync branch output.
    """
    @superfunction
    def function():
        with sync_context:
            print(1)  # noqa: T201
        with async_context:
            print(2)  # noqa: T201
        with generator_context:
            yield from [1, 2, 3]

    buffer = io.StringIO()
    with redirect_stdout(buffer):
        ~function()
    assert buffer.getvalue() == "1\n"


def test_just_sync_call_without_tilde_syntax():
    """
    A superfunction with tilde syntax disabled runs its sync branch when called with ordinary function-call syntax.

    The check discards the call result and verifies that only the sync marker code produces output, while async and generator marker branches stay inactive.
    """
    @superfunction(tilde_syntax=False)
    def function():
        with sync_context:
            print(1)  # noqa: T201
        with async_context:
            print(2)  # noqa: T201
        with generator_context:
            yield from [1, 2, 3]

    buffer = io.StringIO()
    with redirect_stdout(buffer):
        function()
    assert buffer.getvalue() == "1\n"


def test_just_sync_call_with_tilde_syntax():
    """
    Applying tilde to a superfunction call with tilde_syntax=True executes only the sync context.

    The stdout assertion distinguishes the sync branch from the async and generator branches.
    """
    @superfunction(tilde_syntax=True)
    def function():
        with sync_context:
            print(1)  # noqa: T201
        with async_context:
            print(2)  # noqa: T201
        with generator_context:
            yield from [1, 2, 3]

    buffer = io.StringIO()
    with redirect_stdout(buffer):
        ~function()
    assert buffer.getvalue() == "1\n"


def test_just_async_call():
    """
    Calling a superfunction as a coroutine runs only its async context branch.

    The assertion checks captured stdout after asyncio.run to confirm that the sync and generator branches were not executed.
    """
    @superfunction
    def function():
        with sync_context:
            print(1)  # noqa: T201
        with async_context:
            print(2)  # noqa: T201
        with generator_context:
            yield from [1, 2, 3]

    buffer = io.StringIO()
    with redirect_stdout(buffer):
        run(function())
    assert buffer.getvalue() == "2\n"


def test_just_generator_iteration():
    """
    Iterating a bare superfunction call selects and runs only its generator context.

    The test converts the call result to a list and checks that it yields [1, 2, 3] while captured stdout stays empty, proving the sync and async contexts did not execute.
    """
    @superfunction
    def function():
        with sync_context:
            print(1)  # noqa: T201
        with async_context:
            print(2)  # noqa: T201
        with generator_context:
            yield from [1, 2, 3]

    buffer = io.StringIO()
    with redirect_stdout(buffer):
        numbers = list(function())

    assert buffer.getvalue() == ""
    assert numbers == [1, 2, 3]


def test_just_sync_call_with_arguments():
    """
    A tilde call to a superfunction with positional arguments runs the synchronous branch with those arguments.

    The captured output confirms that only the sync path contributes and that the first positional argument is used.
    """
    @superfunction
    def function(a, b):
        with sync_context:
            print(a)  # noqa: T201
        with async_context:
            print(b)  # noqa: T201
        with generator_context:
            yield from [1, 2, 3]

    buffer = io.StringIO()
    with redirect_stdout(buffer):
        ~function(1, 2)
    assert buffer.getvalue() == "1\n"


def test_just_async_call_with_arguments():
    """
    Calling a parameterized superfunction as an async function runs only its async context with the original positional arguments.

    The captured output confirms the async branch receives the second argument while the sync and generator branches are skipped.
    """
    @superfunction
    def function(a, b):
        with sync_context:
            print(a)  # noqa: T201
        with async_context:
            print(b)  # noqa: T201
        with generator_context:
            yield from [1, 2, 3]

    buffer = io.StringIO()
    with redirect_stdout(buffer):
        run(function(1, 2))
    assert buffer.getvalue() == "2\n"


def test_just_generator_with_arguments_iteration():
    """
    Calling a superfunction with arguments and iterating the result selects its generator behavior.

    The generated iterator receives the original arguments and yields values from them, while the sync and async branches remain inactive.
    """
    @superfunction
    def function(a, b):
        with sync_context:
            print(a)  # noqa: T201
        with async_context:
            print(b)  # noqa: T201
        with generator_context:
            yield from [a, b, 3]

    buffer = io.StringIO()
    with redirect_stdout(buffer):
        numbers = list(function(1, 2))

    assert buffer.getvalue() == ""
    assert numbers == [1, 2, 3]


def test_tilda_syntax_for_function_call_without_arguments():
    """
    A no-argument default superfunction call returns its plain synchronous result when the call is evaluated with unary tilde.

    This checks the simplest tilde syntax path: no argument binding, alternate contexts, side effects, or exception handling are involved.
    """
    @superfunction
    def function():
        return 124

    assert ~function() == 124


def test_tilda_syntax_for_function_call_with_arguments():
    """
    Using tilde syntax on a superfunction call forwards positional arguments, default parameters, and keyword overrides to the regular synchronous function."""
    @superfunction
    def function(a, b, c=4, d=3):
        return 1 + a + b + c + d

    assert ~function(2, 3, d=5) == 15


def test_tilda_syntax_for_function_call_without_arguments_raise_exception():
    """
    Ensure a zero-argument superfunction propagates a ValueError when called with the default tilde syntax.

    The check invokes the function as ~function() and verifies that the original error message is preserved.
    """
    @superfunction
    def function():
        raise ValueError('some text')

    with pytest.raises(ValueError, match=match('some text')):
        ~function()


def test_tilda_syntax_for_function_call_with_arguments_raise_exception():
    """
    Unary tilde calls on a default superfunction pass positional and keyword arguments through and propagate the raised exception.

    The case uses mixed explicit and default arguments, then checks that the original exception type and message are preserved instead of being hidden by the call syntax.
    """
    @superfunction
    def function(a, b, c=4, d=3):  # noqa: ARG001
        raise ValueError('some text')

    with pytest.raises(ValueError, match=match('some text')):
        ~function(2, 3, d=5)


def test_return_value_from_async_simple_superfunction():
    """
    An async call to a no-argument superfunction returns the value from a plain body return.

    The check runs the decorated function as a coroutine and expects the returned value to be 1.
    """
    @superfunction
    def function():
        return 1

    assert run(function()) == 1


def test_return_awaited_value_from_async_simple_superfunction():
    """
    Awaiting a zero-argument superfunction returns the value produced by await_it on an inner coroutine.

    The check runs the decorated function through the async entry path and compares the result with a sentinel value from the coroutine.
    """
    async def another_one():
        return 1

    @superfunction
    def function():
        return await_it(another_one())

    assert run(function()) == 1


def test_return_value_from_async_superfunction_with_arguments():
    """
    A @superfunction call used as an async coroutine returns its template result after binding positional, keyword, and default arguments.

    The check runs the decorated function through asyncio.run with one positional argument, one keyword override, and one default value, proving the async path forwards arguments and propagates the return value.
    """
    @superfunction
    def function(a, b=5, c=10):
        return a + b + c

    assert run(function(2, b=3)) == 15


def test_return_awaited_value_from_async_superfunction_with_arguments():
    """Async superfunctions return the awaited result while forwarding positional arguments, keyword overrides, and defaults correctly."""
    async def another_one(a, b, c):
        return a + b + c

    @superfunction
    def function(a, b=5, c=10):
        return await_it(another_one(a, b, c))

    assert run(function(2, b=3)) == 15


def test_call_superfunction_with_tilda_multiple_times():
    """
    A regular superfunction can be invoked with the default tilde syntax repeatedly.

    Each check uses a fresh tilde call on the same decorated function and expects the original scalar return value every time.
    """
    @superfunction
    def function():
        return 4

    assert ~function() == 4
    assert ~function() == 4
    assert ~function() == 4


def test_async_call_superfunction_multiple_times():
    """
    A superfunction returns the same value across repeated independent async calls.

    The test uses separate calls through the async entry point to confirm repeatability without relying on reusing or re-awaiting the same coroutine object.
    """
    @superfunction
    def function():
        return 4

    assert run(function()) == 4
    assert run(function()) == 4
    assert run(function()) == 4


def test_generator_call_superfunction_multiple_times():
    """
    A generator @superfunction call can be repeated, producing the same yielded values each time.

    Each check calls the wrapper anew and consumes that fresh generator, so the test is about repeatable generator creation rather than reusing one iterator.
    """
    @superfunction
    def function():
        yield 4

    assert list(function()) == [4]
    assert list(function()) == [4]
    assert list(function()) == [4]


def test_combine_with_other_decorator_before():
    """
    Rejects a superfunction template when another decorator is applied before superfunction.

    The check uses tilde generation so the regular synchronous path must still enforce the direct decorator-stacking restriction.
    """
    def other_decorator(function):
        return function

    @superfunction
    @other_decorator
    def template():
        pass

    with pytest.raises(WrongDecoratorSyntaxError, match=match('The @superfunction decorator cannot be used in conjunction with other decorators.')):
        ~template()


def test_combine_with_other_decorator_after():
    """
    Stacking another decorator outside @superfunction is rejected when regular superfunction use is generated.

    The function can be defined, but applying tilde syntax must raise WrongDecoratorSyntaxError, confirming decorator-list validation happens during lazy regular-function creation.
    """
    def other_decorator(function):
        return function

    @other_decorator
    @superfunction
    def template():
        pass

    with pytest.raises(WrongDecoratorSyntaxError, match=match('The @superfunction decorator cannot be used in conjunction with other decorators.')):
        ~template()


def test_pass_coroutine_function_to_decorator():
    """
    Rejects an async function used directly as a @superfunction template during decoration.

    The check verifies that coroutine templates fail before the decorated function is called and that the error identifies regular or generator functions as the only allowed template forms.
    """
    with pytest.raises(ValueError, match=match("Only regular or generator functions can be used as a template for @superfunction. You can't use async functions.")):
        @superfunction
        async def function_maker():
            return 4


def test_pass_not_function_to_decorator():
    """
    Rejects direct use of superfunction when the template argument is not a regular or generator function.

    This locks down the generic validation path for invalid decorator input, before any wrapping behavior can occur.
    """
    with pytest.raises(ValueError, match=match("Only regular or generator functions can be used as a template for @superfunction.")):
        superfunction(1)


def test_try_to_pass_lambda_to_decorator():
    """
    Rejects a lambda passed directly as a superfunction template.

    The check confirms that lambda templates fail immediately with ValueError before any generated function is created or invoked.
    """
    with pytest.raises(ValueError, match=match("Only regular or generator functions can be used as a template for @superfunction. Don't use lambdas here.")):
        superfunction(lambda x: x)


def test_choose_tilde_syntax_off_and_use_tilde():
    """
    Disabled tilde syntax rejects calls made with unary tilde.

    The test decorates an empty superfunction with tilde_syntax=False and checks that using the tilde call form raises NotImplementedError with the disabled-tilde error message.
    """
    @superfunction(tilde_syntax=False)
    def function():
        pass

    with pytest.raises(NotImplementedError, match=match('The syntax with ~ is disabled for this superfunction. Call it with simple breackets.')):
        ~function()


def test_call_superfunction_without_tilde_syntax_whet_it_is_on_by_default():
    """
    Bare @superfunction callables reject plain function() calls while tilde syntax is enabled by default.

    The call leaves the tracer unused, so the test checks the resulting finalizer failure through the unraisable-exception hook rather than expecting the call itself to raise.
    """
    exception_message = None
    def temporary_hook(unraisable):
        nonlocal exception_message
        exception_message = str(unraisable.exc_value)
    old_hook = sys.unraisablehook
    sys.unraisablehook = temporary_hook

    @superfunction
    def function():
        pass

    function()

    assert exception_message == 'The tilde-syntax is enabled for the "function" function. Call it like this: ~function().'

    sys.unraisablehook = old_hook


def test_call_superfunction_without_tilde_syntax_whet_it_is_on():
    """
    Plain calls to a tilde-enabled superfunction are rejected instead of running synchronously.

    The test checks the unraisable exception path because this misuse is reported when the unused call result is finalized.
    """
    exception_message = None
    def temporary_hook(unraisable):
        nonlocal exception_message
        exception_message = str(unraisable.exc_value)
    old_hook = sys.unraisablehook
    sys.unraisablehook = temporary_hook

    @superfunction(tilde_syntax=True)
    def function():
        pass

    function()

    assert exception_message == 'The tilde-syntax is enabled for the "function" function. Call it like this: ~function().'

    sys.unraisablehook = old_hook


def test_there_is_exception_if_not_tilde_mode_and_in_function_is_empty_return_in_common_block():
    """
    Non-tilde superfunctions reject a bare return in the common body at decoration time.

    The check defines the decorated function inside the exception assertion, so the failure must happen during validation rather than during a later call.
    """
    with pytest.raises(WrongTransfunctionSyntaxError, match=match('A superfunction cannot contain a return statement.')):
        @superfunction(tilde_syntax=False)
        def function():
            return


def test_there_is_exception_if_not_tilde_mode_and_in_function_is_return_true_in_common_block():
    """
    Non-tilde superfunctions reject a value-returning return in the common body.

    The error is raised while the decorator is applied, before the function can be called.
    """
    with pytest.raises(WrongTransfunctionSyntaxError, match=match('A superfunction cannot contain a return statement.')):
        @superfunction(tilde_syntax=False)
        def function():
            return True


def test_there_is_exception_if_not_tilde_mode_and_in_function_is_empty_return_in_sync_block():
    """
    Decorating a no-tilde superfunction raises WrongTransfunctionSyntaxError for a bare return inside sync_context.

    The failure is checked during decoration, before the generated function is ever called.
    """
    with pytest.raises(WrongTransfunctionSyntaxError, match=match('A superfunction cannot contain a return statement.')):
        @superfunction(tilde_syntax=False)
        def function():
            with sync_context:
                return


def test_there_is_exception_if_not_tilde_mode_and_in_function_is_return_true_in_sync_block():
    """
    Non-tilde superfunctions reject value-returning returns inside a sync_context block.

    The error is expected while applying the decorator, before the function is ever called, because the sync block belongs to the normal generated function path where return values are not allowed.
    """
    with pytest.raises(WrongTransfunctionSyntaxError, match=match('A superfunction cannot contain a return statement.')):
        @superfunction(tilde_syntax=False)
        def function():
            with sync_context:
                return True


def test_there_are_no_exceptions_if_not_tilde_mode_and_in_function_is_empty_return_in_async_block():
    """
    Non-tilde superfunctions allow a bare return inside an async-only block.

    This locks down that definition-time validation succeeds when the return is confined to async context, without checking execution or returned values.
    """
    @superfunction(tilde_syntax=False)
    def function():
        with async_context:
            return


def test_there_are_no_exceptions_if_not_tilde_mode_and_in_function_is_return_true_in_async_block():
    """
    Plain-call superfunctions may be decorated when their only return value is inside an async_context block.

    The test checks definition-time validation only: the decorated function is not called, and no runtime async behavior is asserted.
    """
    @superfunction(tilde_syntax=False)
    def function():
        with async_context:
            return True


def test_there_are_no_exceptions_if_not_tilde_mode_and_in_function_is_empty_return_in_generator_block():
    """
    Allow non-tilde superfunctions to decorate a template with a bare return inside generator_context.

    The check is decoration-only: it locks down that the return restriction does not reject code removed from the generated sync function.
    """
    @superfunction(tilde_syntax=False)
    def function():
        with generator_context:
            return


def test_there_are_no_exceptions_if_not_tilde_mode_and_in_function_is_return_true_in_generator_block():
    """
    Non-tilde superfunctions allow a valued return inside a generator_context block without raising during decoration.

    This locks down that the allowed return is specific to the generator block, even when the return carries a truthy value.
    """
    @superfunction(tilde_syntax=False)
    def function():
        with generator_context:
            return True


def test_async_function_with_all_content_in_generator_context():
    """
    Awaiting a superfunction with only generator-context content returns None.

    The async path should discard the generator-only block entirely, including its return value, leaving the generated coroutine to complete without an explicit result.
    """
    @superfunction
    def function():
        with generator_context:
            return True

    assert run(function()) is None


def test_async_function_with_all_content_in_sync_context():
    """
    Async dispatch drops sync-only template content and completes with None.

    The test uses a superfunction whose only meaningful body is inside sync_context, then runs it as a coroutine and checks that the sync return value is ignored.
    """
    @superfunction
    def function():
        with sync_context:
            return True

    assert run(function()) is None


def test_usual_tilde_function_with_all_content_in_generator_context():
    """A tilde call ignores generator_context-only content and returns None when no synchronous body remains."""
    @superfunction
    def function():
        with generator_context:
            return True

    assert ~function() is None


def test_usual_tilde_function_with_all_content_in_async_context():
    """Ensure a usual tilde call returns None when a superfunction has only async-context content.

    This confirms that the synchronous variant ignores async-only content rather than running it.
    """
    @superfunction
    def function():
        with async_context:
            return True

    assert ~function() is None


def test_basic_yield_from_it():
    """
    @superfunction yields each item provided through yield_from_it inside generator_context.

    The check uses list(function()) to select the generated iterator behavior and confirms the literal iterable is forwarded as [1, 2, 3].
    """
    @superfunction
    def function():
        with generator_context:
            yield_from_it([1, 2, 3])

    assert list(function()) == [1, 2, 3]


def test_yield_from_it_with_function_call():
    """
    A superfunction generator expands yield_from_it(helper()) into the iterable returned by helper.

    This checks that the marker accepts a call expression and that iterating the decorated function uses the generator variant.
    """
    def some_other_function():
        return [1, 2, 3]

    @superfunction
    def function():

        with generator_context:
            yield_from_it(some_other_function())

    assert list(function()) == [1, 2, 3]


def test_await_it_with_two_arguments():
    """
    Reject await_it with two positional arguments in a superfunction async branch.

    The invalid marker is detected when the lazily generated async form is executed, so the check runs the template through asyncio.run and expects the single-positional-argument syntax error.
    """
    async def another_function():
        return None

    @superfunction
    def template():
        with async_context:
            return await_it(another_function(), another_function())

    with pytest.raises(WrongMarkerSyntaxError, match=match('The "await_it" marker can be used with only one positional argument.')):
        run(template())


def test_await_it_without_arguments():
    """
    Rejects a zero-argument await_it marker when a superfunction is invoked asynchronously.

    The check confirms that lazy async generation raises the marker syntax error instead of treating await_it() as a valid await expression.
    """
    @superfunction
    def template():
        with async_context:
            return await_it()

    with pytest.raises(WrongMarkerSyntaxError, match=match('The "await_it" marker can be used with only one positional argument.')):
        run(template())


def test_await_it_with_one_usual_and_one_named_arguments():
    """
    await_it rejects a positional awaitable combined with any keyword argument in a superfunction async branch.

    The test forces the async path and checks that this invalid marker shape raises the marker syntax error for using anything other than one positional argument.
    """
    async def another_function():
        return None

    @superfunction
    def template():
        with async_context:
            return await_it(another_function(), kek=another_function())

    with pytest.raises(WrongMarkerSyntaxError, match=match('The "await_it" marker can be used with only one positional argument.')):
        run(template())


def test_yield_from_it_with_two_arguments():
    """yield_from_it rejects multiple positional arguments in a generator-only superfunction template with a marker syntax error."""
    @superfunction
    def template():
        with generator_context:
            return yield_from_it([1, 2, 3], [1, 2, 3])

    with pytest.raises(WrongMarkerSyntaxError, match=match('The "yield_from_it" marker can be used with only one positional argument.')):
        list(template())


def test_yield_from_it_without_arguments():
    """
    yield_from_it without an argument is rejected in a superfunction generator context.

    The check forces the generated iterator path so validation happens during lazy generator variant selection, covering the zero-argument marker case.
    """
    @superfunction
    def template():
        with generator_context:
            return yield_from_it()

    with pytest.raises(WrongMarkerSyntaxError, match=match('The "yield_from_it" marker can be used with only one positional argument.')):
        list(template())


def test_yield_from_it_with_one_usual_and_one_named_arguments():
    """
    yield_from_it rejects keyword arguments even when it receives one positional iterable.

    The check is exercised by iterating the superfunction, which requests generator code generation and should raise WrongMarkerSyntaxError.
    """
    @superfunction
    def template():
        with generator_context:
            return yield_from_it([1, 2, 3], kek=[1, 2, 3])

    with pytest.raises(WrongMarkerSyntaxError, match=match('The "yield_from_it" marker can be used with only one positional argument.')):
        list(template())


def test_string_literal_default_value_for_usual_function_with_tilde():
    """
    Preserve a string literal default when a superfunction is called through tilde syntax.

    Calling the synchronous variant without arguments should still use the original default value.
    """
    @superfunction
    def function(string='kek'):
        return string

    assert ~function() == 'kek'


def test_int_literal_default_value_for_usual_function_with_tilde():
    """
    Preserve an integer literal default when invoking a superfunction's usual branch with tilde syntax.

    The check omits the argument and verifies that the synchronous call uses the generated function's default value.
    """
    @superfunction
    def function(number=123):
        return number

    assert ~function() == 123


def test_list_literal_default_value_for_usual_function_with_tilde():
    """Usual tilde calls to a superfunction reuse the same list literal default across invocations."""
    @superfunction
    def function(number, lst=[]):  # noqa: B006
        lst.append(number)
        return lst

    assert ~function(1) == [1]
    assert ~function(2) == [1, 2]


def test_list_literal_default_value_it_the_same_for_all_types_of_functions_when_usual_one_is_with_tilde():
    """
    Mutable list defaults are shared across the usual, async, and generator variants of one superfunction when the usual variant is called with tilde syntax.

    Each mode observes the accumulated mutations from the previous calls, proving that the generated variants do not receive separate default lists.
    """
    @superfunction
    def function(number, lst=[]):  # noqa: B006
        lst.append(number)
        with async_context:
            return lst
        with sync_context:
            return lst
        with generator_context:
            yield from lst

    assert ~function(1) == [1]
    assert ~function(2) == [1, 2]

    assert run(function(3)) == [1, 2, 3]
    assert run(function(4)) == [1, 2, 3, 4]

    assert list(function(5)) == [1, 2, 3, 4, 5]
    assert list(function(6)) == [1, 2, 3, 4, 5, 6]


def test_string_literal_default_value_for_async_function():
    """Async superfunction calls preserve string literal positional defaults when no argument is supplied."""
    @superfunction
    def function(string='kek'):
        return string

    assert run(function()) == 'kek'


def test_int_literal_default_value_for_async_function():
    """
    Async superfunctions preserve an int literal default when called without arguments.

    The check consumes the generated coroutine with asyncio.run and expects the default value to be returned.
    """
    @superfunction
    def function(number=123):
        return number

    assert run(function()) == 123


def test_list_literal_default_value_for_async_function():
    """
    Async superfunctions preserve normal Python identity semantics for mutable default arguments.

    The coroutine path is checked by running the same superfunction twice with a list literal default and confirming that appended values accumulate across invocations.
    """
    @superfunction
    def function(number, lst=[]):  # noqa: B006
        lst.append(number)
        return lst

    assert run(function(1)) == [1]
    assert run(function(2)) == [1, 2]


def test_string_literal_default_value_for_generator_function():
    """A superfunction used as a generator preserves a string literal default argument when called without arguments."""
    @superfunction
    def function(string='kek'):
        yield string

    assert list(function()) == ['kek']


def test_int_literal_default_value_for_generator_function():
    """
    A superfunction generator preserves an integer literal positional default when called without arguments.

    The check consumes the decorated function with list(...) and expects the yielded value to be 123, confirming generator mode uses the original default value.
    """
    @superfunction
    def function(number=123):
        yield number

    assert list(function()) == [123]


def test_list_literal_default_value_for_generator_function():
    """
    Generator-style superfunctions preserve and reuse a list literal default across calls.

    The test consumes two calls with list(...) so generator mode is selected and confirms the second result includes the mutation from the first call.
    """
    @superfunction
    def function(number, lst=[]):  # noqa: B006
        lst.append(number)
        yield from lst

    assert list(function(1)) == [1]
    assert list(function(2)) == [1, 2]


def test_nonlocal_variable_default_value_for_usual_function_with_tilde():
    """
    A usual superfunction call via tilde preserves a default argument value captured from an enclosing local variable.

    The check rebinds the enclosing name after decoration, then calls the generated ordinary function without an explicit argument and expects the original object to be returned unchanged.
    """
    original_variable = object()
    variable = original_variable

    @superfunction
    def function(number=variable):
        return number

    variable = object()

    assert ~function() is original_variable


def test_global_variable_default_value_for_usual_function_with_tilde():
    """
    A usual superfunction call with unary tilde preserves a default argument evaluated from a module-level global.

    The wrapped function returns that parameter directly, so calling it without an argument checks that generated usual-function execution keeps the original default value intact.
    """
    @superfunction
    def function(number=global_variable):
        return number

    assert ~function() == global_variable


def test_resetted_global_variable_default_value_for_usual_function_with_tilde():
    """
    A usual superfunction call through tilde keeps a default argument captured from a local name that shadows a global.

    The test verifies that calling without an explicit argument returns the local default value, not the module-level global value.
    """
    global_variable = 'kek'

    @superfunction
    def function(number=global_variable):
        return number

    assert ~function() == 'kek'


def test_nonlocal_variable_default_value_for_usual_function_without_tilde():
    """A usual function can use a nonlocal variable as a default value without tilde syntax."""
    container = []
    variable = 123

    @superfunction(tilde_syntax=False)
    def function(number=variable):
        container.append(number)

    function()

    assert container == [variable]


def test_global_variable_default_value_for_usual_function_without_tilde():
    """
    A no-tilde superfunction keeps a module global used as a normal function default.

    The test calls the usual function without passing that argument and checks that its side effect receives the global value.
    """
    container = []

    @superfunction(tilde_syntax=False)
    def function(number=global_variable):
        container.append(number)

    function()

    assert container == [global_variable]


def test_resetted_global_variable_default_value_for_usual_function_without_tilde():
    """
    A non-tilde superfunction call uses a default value captured from an enclosing local variable.

    The local variable named global_variable shadows the module global, and the side effect records that local default when the decorated function is called without arguments.
    """
    container = []
    global_variable = 'kek'

    @superfunction(tilde_syntax=False)
    def function(number=global_variable):
        container.append(number)

    function()

    assert container == ['kek']


def test_nonlocal_variable_default_value_for_async_function():
    """
    Preserves a default parameter value captured from an enclosing local variable when an async superfunction is executed.

    The test checks that calling the decorated function through the coroutine path returns the nonlocal default value when no explicit argument is supplied.
    """
    variable = 123

    @superfunction
    def function(number=variable):
        return number

    assert run(function()) == variable


def test_global_variable_default_value_for_async_function():
    """
    Async superfunction calls preserve parameter defaults that were bound from module globals.

    The check calls the decorated function through asyncio.run without arguments and expects the global-backed default value to be returned.
    """
    @superfunction
    def function(number=global_variable):
        return number

    assert run(function()) == global_variable


def test_resetted_global_variable_default_value_for_async_function():
    """
    Preserves a locally captured default argument when the superfunction is invoked as async.

    The default comes from a local variable that shadows a module global, so the generated async function must return the local value when called without an explicit argument.
    """
    global_variable = 'kek'

    @superfunction
    def function(number=global_variable):
        return number

    assert run(function()) == 'kek'


def test_nonlocal_variable_default_value_for_generator_function():
    """Generator superfunctions preserve default arguments captured from an enclosing local variable.

    The check calls the generated generator without arguments and confirms iteration yields the captured default value.
    """
    variable = 123

    @superfunction
    def function(number=variable):
        yield number

    assert list(function()) == [variable]


def test_global_variable_default_value_for_generator_function():
    """
    Generator superfunctions preserve module-level global default arguments when called without an explicit value.

    The call is consumed with list() to exercise the generator path selected by normal iteration, and the yielded value must match the original global default.
    """
    @superfunction
    def function(number=global_variable):
        yield number

    assert list(function()) == [global_variable]


def test_resetted_global_variable_default_value_for_generator_function():
    """
    Generator superfunctions preserve a default value captured from a local variable that shadows a module global.

    The local shadowing name is deleted before iteration, so the yielded value must come from the original default rather than from a later global-name lookup.
    """
    global_variable = 'kek'

    @superfunction
    def function(number=global_variable):
        yield number

    del global_variable

    assert list(function()) == ['kek']


def test_use_decorator_without_at():
    """
    Reject calling superfunction directly instead of applying it with decorator syntax.

    The wrapping call may succeed initially, but forcing the resulting sync, async, or generator form must raise the decorator-syntax error.
    """
    def template():
        pass

    function = superfunction(template)

    with pytest.raises(WrongDecoratorSyntaxError, match=match("The @superfunction decorator can only be used with the '@' symbol. Don't use it as a regular function. Also, don't rename it.")):
        ~function()

    with pytest.raises(WrongDecoratorSyntaxError, match=match("The @superfunction decorator can only be used with the '@' symbol. Don't use it as a regular function. Also, don't rename it.")):
        run(function())

    with pytest.raises(WrongDecoratorSyntaxError, match=match("The @superfunction decorator can only be used with the '@' symbol. Don't use it as a regular function. Also, don't rename it.")):
        list(function())

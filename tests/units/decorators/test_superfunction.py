import io
import sys
from asyncio import run
from contextlib import redirect_stdout

import pytest
import full_match

from transfunctions import superfunction, sync_context, async_context, generator_context, await_it, WrongDecoratorSyntaxError, WrongTransfunctionSyntaxError, WrongMarkerSyntaxError

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


def test_just_sync_call_without_breackets():
    @superfunction
    def function():
        with sync_context:
            print(1)
        with async_context:
            print(2)
        with generator_context:
            yield from [1, 2, 3]

    buffer = io.StringIO()
    with redirect_stdout(buffer):
        ~function()
    assert buffer.getvalue() == "1\n"


def test_just_sync_call_without_tilde_syntax():
    @superfunction(tilde_syntax=False)
    def function():
        with sync_context:
            print(1)
        with async_context:
            print(2)
        with generator_context:
            yield from [1, 2, 3]

    buffer = io.StringIO()
    with redirect_stdout(buffer):
        function()
    assert buffer.getvalue() == "1\n"


def test_just_sync_call_with_tilde_syntax():
    @superfunction(tilde_syntax=True)
    def function():
        with sync_context:
            print(1)
        with async_context:
            print(2)
        with generator_context:
            yield from [1, 2, 3]

    buffer = io.StringIO()
    with redirect_stdout(buffer):
        ~function()
    assert buffer.getvalue() == "1\n"


def test_just_async_call():
    @superfunction
    def function():
        with sync_context:
            print(1)
        with async_context:
            print(2)
        with generator_context:
            yield from [1, 2, 3]

    buffer = io.StringIO()
    with redirect_stdout(buffer):
        run(function())
    assert buffer.getvalue() == "2\n"


def test_just_generator_iteration():
    @superfunction
    def function():
        with sync_context:
            print(1)
        with async_context:
            print(2)
        with generator_context:
            yield from [1, 2, 3]

    buffer = io.StringIO()
    with redirect_stdout(buffer):
        numbers = list(function())

    assert buffer.getvalue() == ""
    assert numbers == [1, 2, 3]


def test_just_sync_call_with_arguments():
    @superfunction
    def function(a, b):
        with sync_context:
            print(a)
        with async_context:
            print(b)
        with generator_context:
            yield from [1, 2, 3]

    buffer = io.StringIO()
    with redirect_stdout(buffer):
        ~function(1, 2)
    assert buffer.getvalue() == "1\n"


def test_just_async_call_with_arguments():
    @superfunction
    def function(a, b):
        with sync_context:
            print(a)
        with async_context:
            print(b)
        with generator_context:
            yield from [1, 2, 3]

    buffer = io.StringIO()
    with redirect_stdout(buffer):
        run(function(1, 2))
    assert buffer.getvalue() == "2\n"


def test_just_generator_with_arguments_iteration():
    @superfunction
    def function(a, b):
        with sync_context:
            print(a)
        with async_context:
            print(b)
        with generator_context:
            yield from [a, b, 3]

    buffer = io.StringIO()
    with redirect_stdout(buffer):
        numbers = list(function(1, 2))

    assert buffer.getvalue() == ""
    assert numbers == [1, 2, 3]


def test_tilda_syntax_for_function_call_without_arguments():
    @superfunction
    def function():
        return 124

    assert ~function() == 124


def test_tilda_syntax_for_function_call_with_arguments():
    @superfunction
    def function(a, b, c=4, d=3):
        return 1 + a + b + c + d

    assert ~function(2, 3, d=5) == 15


def test_tilda_syntax_for_function_call_without_arguments_raise_exception():
    @superfunction
    def function():
        raise ValueError

    with pytest.raises(ValueError):
        ~function() == 124


def test_tilda_syntax_for_function_call_with_arguments_raise_exception():
    @superfunction
    def function(a, b, c=4, d=3):
        raise ValueError

    with pytest.raises(ValueError):
        ~function(2, 3, d=5)


def test_return_value_from_async_simple_superfunction():
    @superfunction
    def function():
        return 1

    assert run(function()) == 1


def test_return_awaited_value_from_async_simple_superfunction():
    async def another_one():
        return 1

    @superfunction
    def function():
        return await_it(another_one())

    assert run(function()) == 1


def test_return_value_from_async_superfunction_with_arguments():
    @superfunction
    def function(a, b=5, c=10):
        return a + b + c

    assert run(function(2, b=3)) == 15


def test_return_awaited_value_from_async_superfunction_with_arguments():
    async def another_one(a, b, c):
        return a + b + c

    @superfunction
    def function(a, b=5, c=10):
        return await_it(another_one(a, b, c))

    assert run(function(2, b=3)) == 15


def test_call_superfunction_with_tilda_multiple_times():
    @superfunction
    def function():
        return 4

    assert ~function() == 4
    assert ~function() == 4
    assert ~function() == 4


def test_async_call_superfunction_multiple_times():
    @superfunction
    def function():
        return 4

    assert run(function()) == 4
    assert run(function()) == 4
    assert run(function()) == 4


def test_generator_call_superfunction_multiple_times():
    @superfunction
    def function():
        yield 4

    assert list(function()) == [4]
    assert list(function()) == [4]
    assert list(function()) == [4]


def test_combine_with_other_decorator_before():
    def other_decorator(function):
        return function

    @superfunction
    @other_decorator
    def template():
        pass

    with pytest.raises(WrongDecoratorSyntaxError, match=full_match('The @superfunction decorator cannot be used in conjunction with other decorators.')):
        ~template()


def test_combine_with_other_decorator_after():
    def other_decorator(function):
        return function

    @other_decorator
    @superfunction
    def template():
        pass

    with pytest.raises(WrongDecoratorSyntaxError, match=full_match('The @superfunction decorator cannot be used in conjunction with other decorators.')):
        ~template()


def test_pass_coroutine_function_to_decorator():
    with pytest.raises(ValueError, match=full_match("Only regular or generator functions can be used as a template for @superfunction. You can't use async functions.")):
        @superfunction
        async def function_maker():
            return 4


def test_pass_not_function_to_decorator():
    with pytest.raises(ValueError, match=full_match("Only regular or generator functions can be used as a template for @superfunction.")):
        superfunction(1)


def test_try_to_pass_lambda_to_decorator():
    with pytest.raises(ValueError, match=full_match("Only regular or generator functions can be used as a template for @superfunction. Don't use lambdas here.")):
        superfunction(lambda x: x)


def test_choose_tilde_syntax_off_and_use_tilde():
    @superfunction(tilde_syntax=False)
    def function():
        pass

    with pytest.raises(NotImplementedError, match=full_match('The syntax with ~ is disabled for this superfunction. Call it with simple breackets.')):
        ~function()


def test_call_superfunction_without_tilde_syntax_whet_it_is_on_by_default():
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

    assert 'The tilde-syntax is enabled for the "function" function. Call it like this: ~function().' == exception_message

    sys.unraisablehook = old_hook


def test_call_superfunction_without_tilde_syntax_whet_it_is_on():
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

    assert 'The tilde-syntax is enabled for the "function" function. Call it like this: ~function().' == exception_message

    sys.unraisablehook = old_hook


def test_there_is_exception_if_not_tilde_mode_and_in_function_is_empty_return_in_common_block():
    with pytest.raises(WrongTransfunctionSyntaxError, match=full_match('A superfunction cannot contain a return statement.')):
        @superfunction(tilde_syntax=False)
        def function():
            return


def test_there_is_exception_if_not_tilde_mode_and_in_function_is_return_true_in_common_block():
    with pytest.raises(WrongTransfunctionSyntaxError, match=full_match('A superfunction cannot contain a return statement.')):
        @superfunction(tilde_syntax=False)
        def function():
            return True


def test_there_is_exception_if_not_tilde_mode_and_in_function_is_empty_return_in_sync_block():
    with pytest.raises(WrongTransfunctionSyntaxError, match=full_match('A superfunction cannot contain a return statement.')):
        @superfunction(tilde_syntax=False)
        def function():
            with sync_context:
                return


def test_there_is_exception_if_not_tilde_mode_and_in_function_is_return_true_in_sync_block():
    with pytest.raises(WrongTransfunctionSyntaxError, match=full_match('A superfunction cannot contain a return statement.')):
        @superfunction(tilde_syntax=False)
        def function():
            with sync_context:
                return True


def test_there_are_no_exceptions_if_not_tilde_mode_and_in_function_is_empty_return_in_async_block():
    @superfunction(tilde_syntax=False)
    def function():
        with async_context:
            return


def test_there_are_no_exceptions_if_not_tilde_mode_and_in_function_is_return_true_in_async_block():
    @superfunction(tilde_syntax=False)
    def function():
        with async_context:
            return True


def test_there_are_no_exceptions_if_not_tilde_mode_and_in_function_is_empty_return_in_generator_block():
    @superfunction(tilde_syntax=False)
    def function():
        with generator_context:
            return


def test_there_are_no_exceptions_if_not_tilde_mode_and_in_function_is_return_true_in_generator_block():
    @superfunction(tilde_syntax=False)
    def function():
        with generator_context:
            return True


def test_async_function_with_all_content_in_generator_context():
    @superfunction
    def function():
        with generator_context:
            return True

    assert run(function()) is None


def test_async_function_with_all_content_in_sync_context():
    @superfunction
    def function():
        with sync_context:
            return True

    assert run(function()) is None


def test_usual_tilde_function_with_all_content_in_generator_context():
    @superfunction
    def function():
        with generator_context:
            return True

    assert ~function() is None


def test_usual_tilde_function_with_all_content_in_async_context():
    @superfunction
    def function():
        with async_context:
            return True

    assert ~function() is None


def test_basic_yield_from_it():
    @superfunction
    def function():
        with generator_context:
            yield_from_it([1, 2, 3])

    assert list(function()) == [1, 2, 3]


def test_yield_from_it_with_function_call():
    def some_other_function():
        return [1, 2, 3]

    @superfunction
    def function():

        with generator_context:
            yield_from_it(some_other_function())

    assert list(function()) == [1, 2, 3]















def test_await_it_with_two_arguments():
    async def another_function():
        return None

    @superfunction
    def template():
        with async_context:
            return await_it(another_function(), another_function())

    with pytest.raises(WrongMarkerSyntaxError, match=full_match('The "await_it" marker can be used with only one positional argument.')):
        run(template())


def test_await_it_without_arguments():
    @superfunction
    def template():
        with async_context:
            return await_it()

    with pytest.raises(WrongMarkerSyntaxError, match=full_match('The "await_it" marker can be used with only one positional argument.')):
        run(template())


def test_await_it_with_one_usual_and_one_named_arguments():
    async def another_function():
        return None

    @superfunction
    def template():
        with async_context:
            return await_it(another_function(), kek=another_function())

    with pytest.raises(WrongMarkerSyntaxError, match=full_match('The "await_it" marker can be used with only one positional argument.')):
        run(template())


def test_yield_from_it_with_two_arguments():
    @superfunction
    def template():
        with generator_context:
            return yield_from_it([1, 2, 3], [1, 2, 3])

    with pytest.raises(WrongMarkerSyntaxError, match=full_match('The "yield_from_it" marker can be used with only one positional argument.')):
        list(template())


def test_yield_from_it_without_arguments():
    @superfunction
    def template():
        with generator_context:
            return yield_from_it()

    with pytest.raises(WrongMarkerSyntaxError, match=full_match('The "yield_from_it" marker can be used with only one positional argument.')):
        list(template())


def test_yield_from_it_with_one_usual_and_one_named_arguments():
    @superfunction
    def template():
        with generator_context:
            return yield_from_it([1, 2, 3], kek=[1, 2, 3])

    with pytest.raises(WrongMarkerSyntaxError, match=full_match('The "yield_from_it" marker can be used with only one positional argument.')):
        list(template())

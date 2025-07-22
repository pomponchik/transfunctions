import io
from asyncio import run
from contextlib import redirect_stdout

import pytest
import full_match

from transfunctions import superfunction, sync_context, async_context, generator_context, await_it, WrongDecoratorSyntaxError

"""
Что нужно проверить:

2. При попытке вызвать без тильды суперфункцию, в которой есть return или raise, должно подниматься исключение, причем .
3. Трейсбек исключения из п. 2 информативен (т.е. содержит конкретную строчку кода, и короткий). Но есть возможность увидеть полный "настоящий" трейсбек.
4. Базовые кейсы работают в глобальном скоупе.
6. С синтаксисом ~ нормально поднимаются исключения.

Что проверено:

1. Все базово работает без аргументов и с аргументами, для обычных, асинк и генераторных функций.
5. С использованием синтаксиса ~ для вызова обычных функций можно возвращать значения, с аргументами и без.
"""


def test_just_sync_call():
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
        function()
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
        function(1, 2)
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

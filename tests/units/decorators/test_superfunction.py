import io
from asyncio import run
from contextlib import redirect_stdout

import pytest

from transfunctions import superfunction, sync_context, async_context, generator_context, await_it

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

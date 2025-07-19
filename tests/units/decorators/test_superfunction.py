import io
from asyncio import run
from contextlib import redirect_stdout

import pytest
import full_match

from transfunctions import superfunction, sync_context, async_context, generator_context, WrongTransfunctionSyntaxError

"""
Что нужно проверить:


2. При попытке навесить декоратор @superfunction на функцию с return'ами будет исключение.
3. Трейсбек исключения с суперфункции при наличии в ней return'а информативен.

Что проверено:

1. Все базово работает без аргументов и с аргументами, для обычных, асинк и генераторных функций.
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

















def test_superfunction_with_return_nothing_in_common_code_before_specific_blocks_is_raising():
    import sys

    def new_excepthook(something):
        raise something.exc_value

    sys.unraisablehook = new_excepthook

    @superfunction
    def function(a, b):
        return 124
        with sync_context:
            print(a)
        with async_context:
            print(b)
        with generator_context:
            yield from [a, b, 3]

    ~function(1, 2)

    #with pytest.raises(WrongTransfunctionSyntaxError, match=full_match('A superfunction cannot contain a return statement.')):

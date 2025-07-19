import io
from asyncio import run
from contextlib import redirect_stdout

from transfunctions import superfunction, sync_context, async_context

"""
Что нужно проверить:

1. Все базово работает без аргументов и с аргументами, для обычных, асинк и генераторных функций.
2. При попытке навесить декоратор @superfunction на функцию с return'ами будет исключение.

Что проверено:

-
"""


def test_just_sync_call():
    @superfunction
    def function():
        with sync_context:
            print(1)
        with async_context:
            print(2)

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

    buffer = io.StringIO()
    with redirect_stdout(buffer):
        run(function())
    assert buffer.getvalue() == "2\n"

import io
from asyncio import run
from contextlib import redirect_stdout

from transfunctions import (
    async_context,
    generator_context,
    sync_context,
    transfunction,
)


def test_quick_start():
    @transfunction
    def template():
        print('so, ', end='')  # noqa: T201
        with sync_context:
            print("it's just usual function!")  # noqa: T201
        with async_context:
            print("it's an async function!")  # noqa: T201
        with generator_context:
            print("it's a generator function!")  # noqa: T201
            yield

    buffer = io.StringIO()
    function = template.get_usual_function()
    with redirect_stdout(buffer):
        function()
    assert buffer.getvalue() == "so, it's just usual function!\n"

    buffer = io.StringIO()
    async_function = template.get_async_function()
    with redirect_stdout(buffer):
        run(async_function())
    assert buffer.getvalue() == "so, it's an async function!\n"

    buffer = io.StringIO()
    generator_function = template.get_generator_function()
    with redirect_stdout(buffer):
        list(generator_function())
    assert buffer.getvalue() == "so, it's a generator function!\n"

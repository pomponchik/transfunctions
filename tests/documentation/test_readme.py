import io
from asyncio import run
from contextlib import redirect_stdout

from transfunctions import (
    transfunction,
    sync_context,
    async_context,
    generator_context,
)


def test_quick_start():
    @transfunction
    def template():
        print('so, ', end='')
        with sync_context:
            print("it's just usual function!")
        with async_context:
            print("it's an async function!")
        with generator_context:
            print("it's a generator function!")
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

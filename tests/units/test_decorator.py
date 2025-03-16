from inspect import isfunction, iscoroutinefunction, isgeneratorfunction
from asyncio import run

import pytest
import full_match

from transfunctions import transfunction, CallTransfunctionDirectlyError
from transfunctions.transformer import FunctionTransformer
from transfunctions import async_context, sync_context, generator_context


"""
Что нужно проверить:

1. Декоратор можно использовать с нулевым и с ненулевым индентом.
2. Декоратор работает для обычных, корутинных и генераторных функций. Как с аргументами (позиционными и именованными), так и без.
3. Исключения внутри всех видов функций корректно работают: в трейсбеке отображаются корректные номера строк и корректные строчки кода.

5. Нельзя использовать декоратор @transfunction без символа @.
6. Прочие декораторы срабатывают.
7. Декоратор @transfunction нельзя использовать дважды на одной функции.
8. Работают замыкания.
9. Работают чтение глобальных переменных.
10. Работает директива nonlocal.
11. Работает директива global.
12. Декоратор @transfunction можно использовать на методах (в т.ч. асинк и генераторных).

14. Все работает с любыми уровнями вложенности (попробовать объявить функцию внутри функции).
15. Сторонние контекстные менеджеры работают, как со скобками, так и без.
16. При попытке использовать маркерные контекстные менеджеры со скобками поднимается информативное исключение.
18. Нельзя навешивать декоратор @transfunction не первым, т.е. не сразу после объявления функции.
19. При попытке сгенерировать генераторную функцию без "yield" или "yield from" - поднимается исключение.

Что проверено:

13. В декоратор @transfunction нельзя скормить лямбду или число.

4. Нельзя навешивать декоратор на асинк-функции. При попытке это сделать вылетает информативное исключение.
17. Нельзя вызывать трансформер напрямую. При попытке это сделать вылетает информативное исключение, причем как при передаче аргументов, так и нет.
"""

@transfunction
def null_indentation_function():
    with sync_context:
        return 1
    with async_context:
        return 2
    with generator_context:
        yield 1
        yield 2
        yield 3


def test_result_is_transformer():
    @transfunction
    def function():
        pass

    assert isinstance(function, FunctionTransformer)


@pytest.mark.parametrize(
    ['args', 'kwargs'],
    [
        ((), {}),
        (('lol', 'kek'), {}),
        (('lol', 'kek'), {'lol': 'kek'}),
        ((), {'lol': 'kek'}),
    ],
)
def test_direct_call_or_transformer(args, kwargs):
    @transfunction
    def function_maker(*args, **kwargs):
        pass

    with pytest.raises(CallTransfunctionDirectlyError, match=full_match("You can't call a transfunction object directly, create a function, a generator function or a coroutine function from it.")):
        function_maker(*args, **kwargs)


def test_pass_coroutine_function_to_decorator():
    with pytest.raises(ValueError, match=full_match("Only regular or generator functions can be used as a template for @transfunction. You can't use async functions.")):
        @transfunction
        async def function_maker():
            return 4


def test_pass_not_function_to_decorator():
    with pytest.raises(ValueError, match=full_match("Only regular or generator functions can be used as a template for @transfunction.")):
        transfunction(1)


def test_create_usual_function_without_any_markers():
    @transfunction
    def function_maker():
        return 4

    function = function_maker.get_usual_function()

    assert isfunction(function)
    assert function() == 4


def test_create_usual_function_with_parameters_without_any_markers():
    @transfunction
    def function_maker(a, b, c=3):
        return a + b + c

    function = function_maker.get_usual_function()

    assert isfunction(function)
    assert function(1, 2, c=3) == 6


def test_null_indentation_usual_function():
    function = null_indentation_function.get_usual_function()

    assert function() == 1


def test_null_indentation_async_function():
    function = null_indentation_function.get_async_function()

    assert run(function()) == 2


def test_null_indentation_generator_function():
    function = null_indentation_function.get_generator_function()

    assert [x for x in function()] == [1, 2, 3]


def test_create_async_function_without_any_markers():
    @transfunction
    def function_maker():
        return 4

    function = function_maker.get_async_function()

    assert iscoroutinefunction(function)
    assert run(function()) == 4


def test_create_async_function_with_parameters_without_any_markers():
    @transfunction
    def function_maker(a, b, c=3):
        return a + b + c

    function = function_maker.get_async_function()

    assert iscoroutinefunction(function)
    assert run(function(1, 2, c=3)) == 6


def test_create_generator_function_without_any_markers():
    @transfunction
    def generator_maker():
        yield 1
        yield 2
        yield 3

    generator = generator_maker.get_generator_function()

    assert isgeneratorfunction(generator)
    assert [x for x in generator()] == [1, 2, 3]


def test_create_generator_function_with_parameters_without_any_markers():
    @transfunction
    def generator_maker(a, b, c=3):
        yield a
        yield b
        yield c

    generator = generator_maker.get_generator_function()

    assert isgeneratorfunction(generator)
    assert [x for x in generator(1, 2, c=3)] == [1, 2, 3]

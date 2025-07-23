import traceback
from inspect import isfunction, iscoroutinefunction, isgeneratorfunction, getsourcelines
from asyncio import run

import pytest
import full_match

from transfunctions import transfunction, CallTransfunctionDirectlyError, WrongDecoratorSyntaxError, DualUseOfDecoratorError
from transfunctions.transformer import FunctionTransformer
from transfunctions import async_context, sync_context, generator_context


SOME_GLOBAL = 777

"""
Что нужно проверить:

1 фаза:

23. Если использовать 'await_it' вне асинк блока, поднимется исключение.
14. Все работает с любыми уровнями вложенности (попробовать объявить функцию внутри функции).
15. Сторонние контекстные менеджеры работают, как со скобками, так и без.
16. При попытке использовать маркерные контекстные менеджеры со скобками поднимается информативное исключение.
18. При попытке сгенерировать генераторную функцию без "yield" или "yield from" - поднимается исключение.
19. При попытке сгенерировать обычную функцию, в которой есть "yield" или "yield from" - поднимется исключение.
20. При попытке сгенерировать асинк функцию, в которой есть "yield" или "yield from" - поднимется исключение.
22. При подмене имен переменных из списка все продолжает работать: 'transfunction', 'create_async_context', 'create_sync_context', 'create_generator_context', 'await_it'.
25. Кэширование работает.

2 фаза:

6. Нельзя ставить декораторы поверх @transfunction (2 фаза). Реализовывать через поиск через слабые ссылки функций, у которых в .__wrapped__ находится переданная ссылка, рекурсивно. См. https://stackoverflow.com/a/73769181/14522393
22. Декораторы ниже @transfunction - запрещены (2 фаза).
21. Декораторы ниже @transfunction работают (2 фаза).

Что проверено:

1. Декоратор можно использовать с нулевым и с ненулевым индентом.
3. Исключения внутри всех видов функций корректно работают: в трейсбеке отображаются корректные номера строк и корректные строчки кода.
2. Декоратор работает в базовом случае для обычных, корутинных и генераторных функций. Как с аргументами (позиционными и именованными), так и без.
4. Нельзя навешивать декоратор на асинк-функции. При попытке это сделать вылетает информативное исключение.
5. Нельзя использовать декоратор @transfunction без символа @.
13. В декоратор @transfunction нельзя скормить лямбду или число.
17. Нельзя вызывать трансформер напрямую. При попытке это сделать вылетает информативное исключение, причем как при передаче аргументов, так и нет.
7. Декоратор @transfunction нельзя использовать дважды на одной функции.
8. Работает чтение из замыканий (в том числе для функций с аргументами).
9. Работает чтение глобальных переменных.
10. Работает директива nonlocal.
11. Работает директива global.
24. Модуль у порождаемых функций такой же, как у шаблона-оригинала.
12. Декоратор @transfunction можно использовать на методах (в т.ч. асинк и генераторных).
26. Если функция-шаблон содержит исключительно sync_context блок, при генерации async функции в ее тело будет подставлено pass, и по аналогии с другими типами. Исключение - генераторы, там потом будет проверка на наличие yield.
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


def test_try_to_pass_lambda_to_decorator():
    with pytest.raises(ValueError, match=full_match("Only regular or generator functions can be used as a template for @transfunction. Don't use lambdas here.")):
        transfunction(lambda x: x)


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


def test_traceback_is_working_in_simple_usual_function():
    @transfunction
    def make():
        raise ValueError('message')

    function = make.get_usual_function()

    try:
        function()
        assert False
    except ValueError as e:
        certain_traceback = list(traceback.extract_tb(e.__traceback__))

    assert getsourcelines(make.function)[1] + 2 == certain_traceback[-1].lineno
    assert getsourcelines(make.function)[0][-1].strip() == certain_traceback[-1].line


def test_traceback_is_working_in_simple_async_function():
    @transfunction
    def make():
        raise ValueError('message')

    function = make.get_async_function()

    try:
        run(function())
        assert False
    except ValueError as e:
        certain_traceback = list(traceback.extract_tb(e.__traceback__))

    assert getsourcelines(make.function)[1] + 2 == certain_traceback[-1].lineno
    assert getsourcelines(make.function)[0][-1].strip() == certain_traceback[-1].line


def test_traceback_is_working_in_simple_generator_function():
    @transfunction
    def make():
        raise ValueError('message')
        yield 1

    function = make.get_generator_function()

    try:
        [x for x in function()]
        assert False
    except ValueError as e:
        certain_traceback = list(traceback.extract_tb(e.__traceback__))

    assert getsourcelines(make.function)[1] + 2 == certain_traceback[-1].lineno
    assert getsourcelines(make.function)[0][-2].strip() == certain_traceback[-1].line


def test_traceback_is_working_in_usual_function_with_marker():
    @transfunction
    def make():
        with sync_context:
            raise ValueError('message')

    function = make.get_usual_function()

    try:
        function()
        assert False
    except ValueError as e:
        certain_traceback = list(traceback.extract_tb(e.__traceback__))

    assert getsourcelines(make.function)[1] + 3 == certain_traceback[-1].lineno
    assert getsourcelines(make.function)[0][-1].strip() == certain_traceback[-1].line


def test_traceback_is_working_in_simple_async_function_with_marker():
    @transfunction
    def make():
        with async_context:
            raise ValueError('message')

    function = make.get_async_function()

    try:
        run(function())
        assert False
    except ValueError as e:
        certain_traceback = list(traceback.extract_tb(e.__traceback__))

    assert getsourcelines(make.function)[1] + 3 == certain_traceback[-1].lineno
    assert getsourcelines(make.function)[0][-1].strip() == certain_traceback[-1].line


def test_traceback_is_working_in_simple_generator_function_with_marker():
    @transfunction
    def make():
        with generator_context:
            raise ValueError('message')
            yield 1

    function = make.get_generator_function()

    try:
        [x for x in function()]
        assert False
    except ValueError as e:
        certain_traceback = list(traceback.extract_tb(e.__traceback__))

    assert getsourcelines(make.function)[1] + 3 == certain_traceback[-1].lineno
    assert getsourcelines(make.function)[0][-2].strip() == certain_traceback[-1].line


def test_try_to_use_transfunction_decorator_without_at_sign():
    def function():
        with generator_context:
            raise ValueError('message')
            yield 1

    make = transfunction(function)

    with pytest.raises(WrongDecoratorSyntaxError, match=full_match("The @transfunction decorator can only be used with the '@' symbol. Don't use it as a regular function. Also, don't rename it.")):
        function = make.get_generator_function()


def test_double_use_of_decorator():
    with pytest.raises(DualUseOfDecoratorError, match=full_match("You cannot use the 'transfunction' decorator twice for the same function.")):
        @transfunction
        @transfunction
        def make():
            pass


def test_read_closures_with_usual_function():
    nonlocal_variable = 1

    @transfunction
    def make():
        #nonlocal nonlocal_variable
        return nonlocal_variable

    function = make.get_usual_function()

    assert function() == 1


def test_read_closures_with_usual_function_with_arguments():
    nonlocal_variable = 1

    @transfunction
    def make(some_number):
        #nonlocal nonlocal_variable
        return nonlocal_variable + some_number

    function = make.get_usual_function()

    assert function(1) == 2
    assert function(2) == 3


def test_read_closures_with_async_function():
    nonlocal_variable = 1

    @transfunction
    def make():
        #nonlocal nonlocal_variable
        return nonlocal_variable

    function = make.get_async_function()

    assert run(function()) == 1


def test_read_closures_with_async_function_with_arguments():
    nonlocal_variable = 1

    @transfunction
    def make(some_number):
        #nonlocal nonlocal_variable
        return nonlocal_variable + some_number

    function = make.get_async_function()

    assert run(function(1)) == 2
    assert run(function(2)) == 3


def test_read_closures_with_generator_function():
    nonlocal_variable = 1

    @transfunction
    def make():
        #nonlocal nonlocal_variable
        yield nonlocal_variable

    function = make.get_generator_function()

    assert list(function()) == [1]


def test_read_closures_with_generator_function_with_arguments():
    nonlocal_variable = 1

    @transfunction
    def make(some_number):
        #nonlocal nonlocal_variable
        yield nonlocal_variable + some_number

    function = make.get_generator_function()

    assert list(function(1)) == [2]
    assert list(function(2)) == [3]


def test_read_globals_with_usual_function():
    @transfunction
    def make():
        return SOME_GLOBAL

    function = make.get_usual_function()

    assert function() == SOME_GLOBAL


def test_read_globals_with_usual_function_with_arguments():
    @transfunction
    def make(some_number):
        #nonlocal nonlocal_variable
        return SOME_GLOBAL + some_number

    function = make.get_usual_function()

    assert function(1) == SOME_GLOBAL + 1
    assert function(2) == SOME_GLOBAL + 2


def test_read_globals_with_async_function():
    @transfunction
    def make():
        return SOME_GLOBAL

    function = make.get_async_function()

    assert run(function()) == SOME_GLOBAL


def test_read_globals_with_async_function_with_arguments():
    @transfunction
    def make(some_number):
        return SOME_GLOBAL + some_number

    function = make.get_async_function()

    assert run(function(1)) == SOME_GLOBAL + 1
    assert run(function(2)) == SOME_GLOBAL + 2


def test_read_globals_with_generator_function():
    @transfunction
    def make():
        yield SOME_GLOBAL

    function = make.get_generator_function()

    assert list(function()) == [SOME_GLOBAL]


def test_read_globals_with_generator_function_with_arguments():
    @transfunction
    def make(some_number):
        yield SOME_GLOBAL + some_number

    function = make.get_generator_function()

    assert list(function(1)) == [SOME_GLOBAL + 1]
    assert list(function(2)) == [SOME_GLOBAL + 2]


def test_write_nonlocal_variable_from_usual_function_without_arguments():
    nonlocal_variable = 1

    @transfunction
    def make():
        nonlocal nonlocal_variable
        nonlocal_variable += 1

    function = make.get_usual_function()
    function()

    assert nonlocal_variable == 2


def test_write_nonlocal_variable_from_usual_function_with_arguments():
    nonlocal_variable = 1

    @transfunction
    def make(number):
        nonlocal nonlocal_variable
        nonlocal_variable += number

    function = make.get_usual_function()
    function(3)

    assert nonlocal_variable == 4


def test_write_nonlocal_variable_from_async_function_without_arguments():
    nonlocal_variable = 1

    @transfunction
    def make():
        nonlocal nonlocal_variable
        nonlocal_variable += 1

    function = make.get_async_function()
    run(function())

    assert nonlocal_variable == 2


def test_write_nonlocal_variable_from_async_function_with_arguments():
    nonlocal_variable = 1

    @transfunction
    def make(number):
        nonlocal nonlocal_variable
        nonlocal_variable += number

    function = make.get_async_function()
    run(function(3))

    assert nonlocal_variable == 4


def test_write_nonlocal_variable_from_generator_function_without_arguments():
    nonlocal_variable = 1

    @transfunction
    def make():
        nonlocal nonlocal_variable
        nonlocal_variable += 1
        yield nonlocal_variable

    function = make.get_generator_function()
    list(function())

    assert nonlocal_variable == 2


def test_write_nonlocal_variable_from_generator_function_with_arguments():
    nonlocal_variable = 1

    @transfunction
    def make(number):
        nonlocal nonlocal_variable
        nonlocal_variable += number
        yield nonlocal_variable

    function = make.get_generator_function()
    list(function(3))

    assert nonlocal_variable == 4


def test_write_global_variable_from_usual_function_without_arguments():
    @transfunction
    def make():
        global SOME_GLOBAL
        SOME_GLOBAL += 1

    global SOME_GLOBAL
    SOME_GLOBAL_BEFORE = SOME_GLOBAL
    function = make.get_usual_function()
    function()

    assert SOME_GLOBAL == SOME_GLOBAL_BEFORE + 1

    SOME_GLOBAL = SOME_GLOBAL_BEFORE


def test_write_global_variable_from_usual_function_with_arguments():
    @transfunction
    def make(number):
        global SOME_GLOBAL
        SOME_GLOBAL += number

    global SOME_GLOBAL
    SOME_GLOBAL_BEFORE = SOME_GLOBAL
    function = make.get_usual_function()
    function(3)

    assert SOME_GLOBAL == SOME_GLOBAL_BEFORE + 3

    SOME_GLOBAL = SOME_GLOBAL_BEFORE


def test_write_global_variable_from_async_function_without_arguments():
    @transfunction
    def make():
        global SOME_GLOBAL
        SOME_GLOBAL += 1

    global SOME_GLOBAL
    SOME_GLOBAL_BEFORE = SOME_GLOBAL
    function = make.get_async_function()
    run(function())

    assert SOME_GLOBAL == SOME_GLOBAL_BEFORE + 1

    SOME_GLOBAL = SOME_GLOBAL_BEFORE


def test_write_global_variable_from_async_function_with_arguments():
    @transfunction
    def make(number):
        global SOME_GLOBAL
        SOME_GLOBAL += number

    global SOME_GLOBAL
    SOME_GLOBAL_BEFORE = SOME_GLOBAL
    function = make.get_async_function()
    run(function(3))

    assert SOME_GLOBAL == SOME_GLOBAL_BEFORE + 3

    SOME_GLOBAL = SOME_GLOBAL_BEFORE


def test_write_global_variable_from_generator_function_without_arguments():
    @transfunction
    def make():
        global SOME_GLOBAL
        SOME_GLOBAL += 1
        yield None

    global SOME_GLOBAL
    SOME_GLOBAL_BEFORE = SOME_GLOBAL
    function = make.get_generator_function()
    list(function())

    assert SOME_GLOBAL == SOME_GLOBAL_BEFORE + 1

    SOME_GLOBAL = SOME_GLOBAL_BEFORE


def test_write_global_variable_from_generator_function_with_arguments():
    @transfunction
    def make(number):
        global SOME_GLOBAL
        SOME_GLOBAL += number
        yield None

    global SOME_GLOBAL
    SOME_GLOBAL_BEFORE = SOME_GLOBAL
    function = make.get_generator_function()
    list(function(3))

    assert SOME_GLOBAL == SOME_GLOBAL_BEFORE + 3

    SOME_GLOBAL = SOME_GLOBAL_BEFORE


def test_module_name():
    @transfunction
    def template():
        pass

    def usual_function():
        pass

    generated_functions = (
        template.get_usual_function(),
        template.get_async_function(),
        template.get_generator_function(),
    )

    for function in generated_functions:
        assert function.__module__ == usual_function.__module__


def test_it_works_with_simple_usual_method():
    class SomeClass:
        some_value = 1
        @transfunction
        def template(self):
            return self.some_value + 1

    some_class_instance = SomeClass()

    assert isinstance(some_class_instance.template, FunctionTransformer)
    assert some_class_instance.template.get_usual_function()() == 2


def test_it_works_with_simple_usual_method_with_parameters():
    class SomeClass:
        some_value = 1
        @transfunction
        def template(self, a, b=5):
            return self.some_value + 1 + a + b

    some_class_instance = SomeClass()

    assert isinstance(some_class_instance.template, FunctionTransformer)
    assert some_class_instance.template.get_usual_function()(2) == 9


def test_it_works_with_simple_async_method():
    class SomeClass:
        some_value = 1
        @transfunction
        def template(self):
            return self.some_value + 1

    some_class_instance = SomeClass()

    assert isinstance(some_class_instance.template, FunctionTransformer)
    assert run(some_class_instance.template.get_async_function()()) == 2


def test_it_works_with_simple_async_method_with_parameters():
    class SomeClass:
        some_value = 1
        @transfunction
        def template(self, a, b=5):
            return self.some_value + 1 + a + b

    some_class_instance = SomeClass()

    assert isinstance(some_class_instance.template, FunctionTransformer)
    assert run(some_class_instance.template.get_async_function()(2)) == 9


def test_it_works_with_simple_generator_method():
    class SomeClass:
        some_value = 1
        @transfunction
        def template(self):
            yield self.some_value + 1

    some_class_instance = SomeClass()

    assert isinstance(some_class_instance.template, FunctionTransformer)
    assert list(some_class_instance.template.get_generator_function()()) == [2]


def test_it_works_with_simple_generator_method_with_parameters():
    class SomeClass:
        some_value = 1
        @transfunction
        def template(self, a, b=5):
            yield self.some_value + 1 + a + b

    some_class_instance = SomeClass()

    assert isinstance(some_class_instance.template, FunctionTransformer)
    assert list(some_class_instance.template.get_generator_function()(2)) == [9]


def test_combine_with_other_decorator_before():
    def other_decorator(function):
        return function

    @transfunction
    @other_decorator
    def template():
        pass

    with pytest.raises(WrongDecoratorSyntaxError, match=full_match('The @transfunction decorator cannot be used in conjunction with other decorators.')):
        template.get_usual_function()


def test_combine_with_other_decorator_after():
    def other_decorator(function):
        return function

    @other_decorator
    @transfunction
    def template():
        pass

    with pytest.raises(WrongDecoratorSyntaxError, match=full_match('The @transfunction decorator cannot be used in conjunction with other decorators.')):
        template.get_usual_function()


def test_create_empty_usual_function_without_arguments():
    @transfunction
    def template():
        with async_context:
            pass

    function = template.get_usual_function()

    assert function() is None


def test_create_empty_usual_function_with_arguments():
    @transfunction
    def template(a, b):
        with async_context:
            return a + b

    function = template.get_usual_function()

    assert function(1, 2) is None


def test_create_empty_async_function_without_arguments():
    @transfunction
    def template():
        with sync_context:
            pass

    function = template.get_async_function()

    assert run(function()) is None


def test_create_empty_async_function_with_arguments():
    @transfunction
    def template(a, b):
        with sync_context:
            return a + b

    function = template.get_async_function()

    assert run(function(1, 2)) is None

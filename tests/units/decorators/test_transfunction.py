import traceback
from asyncio import run
from contextlib import contextmanager
from inspect import getsourcelines, iscoroutinefunction, isfunction, isgeneratorfunction

import full_match
import pytest

from transfunctions import (
    CallTransfunctionDirectlyError,
    DualUseOfDecoratorError,
    WrongDecoratorSyntaxError,
    WrongMarkerSyntaxError,
    async_context,
    await_it,
    generator_context,
    sync_context,
    transfunction,
    yield_from_it,
)
from transfunctions.transformer import FunctionTransformer

SOME_GLOBAL = 777

"""
Что нужно проверить:

В процессе:

1 фаза:

23. Если использовать 'await_it' вне асинк блока, поднимется исключение.
14. Вложенные функции запрещены, как обычные, так и асинк/генераторные. При попытке объявить - поднимется исключение.
16. При попытке использовать маркерные контекстные менеджеры со скобками поднимается информативное исключение.
18. При попытке сгенерировать генераторную функцию без "yield" или "yield from" - поднимается исключение.
19. При попытке сгенерировать обычную функцию, в которой есть "yield" или "yield from" - поднимется исключение.
20. При попытке сгенерировать асинк функцию, в которой есть "yield" или "yield from" - поднимется исключение.
25. Кэширование работает.
27. Работает совмещение 2 сторонних контекстных менеджеров (как со скобками, так и без).
28. Нельзя использовать контекстные маркеры вместе со сторонними контекстными менеджерами.
29. Сторонние контекстные менеджеры атрибутами работают.
30. Нельзя использовать контекстные маркеры с атрибутами.
32. Можно указывать для аргументов и возвращаемого значения функции произвольные тайп-хинты, т.е. они присутствуют в пространстве имен, в т.ч. если какой-то тайп-хинт заалиясить.
34. Если использовать 'yield_from_it' или 'yield_it' вне генераторного блока, поднимется исключение.
36. yield_it базово работает.
38. При попытке использовать yield_it с двумя аргументами или без аргументов или с именованным аргументом будет ошибка.
39. При попытке написать "return yield_it(...)" будет ошибка.
40. При попытке написать "return yield_from_it(...)" будет ошибка.
41. Контекстные маркеры можно использовать вместе, например: "with sync_context, async_context: ...".
43. Контекстные маркеры разного типа нельзя вкладывать друг в друга.
44. Можно использовать переменную с именем 'wrapper'.


2 фаза:

6. Нельзя ставить декораторы поверх @transfunction (2 фаза). Реализовывать через поиск через слабые ссылки функций, у которых в .__wrapped__ находится переданная ссылка, рекурсивно. См. https://stackoverflow.com/a/73769181/14522393
22. Декораторы ниже @transfunction - запрещены (2 фаза).
21. Декораторы ниже @transfunction работают (2 фаза).
22. При подмене имен переменных из списка все продолжает работать: 'transfunction', 'create_async_context', 'create_sync_context', 'create_generator_context', 'await_it'.

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
15. Сторонние контекстные менеджеры работают, как со скобками, так и без, как вне контекстных маркеров, так и внутри.
35. yield_from_it базово работает.
33. При попытке использовать await_it() с двумя аргументами или без аргументов или с именованным аргументом будет ошибка.
37. При попытке использовать yield_from_it с двумя аргументами или без аргументов или с именованным аргументом будет ошибка.
31. Дефолтные значения аргументов работают корректно при использовании литералов. При преобразовании одного шаблона в функции разных типов используется один и тот же экземпляр литерала.
42. Дефолтные значения аргументов работают корректно при использовании переменных, с уважением к иерархии пространств имен.
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
        global SOME_GLOBAL  # noqa: PLW0603
        SOME_GLOBAL += 1
        yield None

    global SOME_GLOBAL  # noqa: PLW0603
    SOME_GLOBAL_BEFORE = SOME_GLOBAL  # noqa: N806
    function = make.get_generator_function()
    list(function())

    assert SOME_GLOBAL == SOME_GLOBAL_BEFORE + 1

    SOME_GLOBAL = SOME_GLOBAL_BEFORE


def test_write_global_variable_from_generator_function_with_arguments():
    @transfunction
    def make(number):
        global SOME_GLOBAL  # noqa: PLW0603
        SOME_GLOBAL += number
        yield None

    global SOME_GLOBAL  # noqa: PLW0603
    SOME_GLOBAL_BEFORE = SOME_GLOBAL  # noqa: N806
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


def test_other_context_managers_with_empty_parentness_are_working_in_usual_function_without_arguments():
    @contextmanager
    def context_manager_with_parentnes():
        yield 123

    @transfunction
    def template():
        with context_manager_with_parentnes() as something:
            return something

    function = template.get_usual_function()

    assert function() == 123


def test_other_context_managers_with_empty_parentness_are_working_in_usual_function_with_arguments():
    @contextmanager
    def context_manager_with_parentnes():
        yield 123

    @transfunction
    def template(a, b):
        with context_manager_with_parentnes() as something:
            return something + a + b

    function = template.get_usual_function()

    assert function(1, 2) == 126


def test_other_context_managers_with_not_empty_parentness_are_working_in_usual_function_without_arguments():
    @contextmanager
    def context_manager_with_parentnes(c):
        yield 123 + c

    @transfunction
    def template():
        with context_manager_with_parentnes(4) as something:
            return something

    function = template.get_usual_function()

    assert function() == 127


def test_other_context_managers_with_not_empty_parentness_are_working_in_usual_function_with_arguments():
    @contextmanager
    def context_manager_with_parentnes(c):
        yield 123 + c

    @transfunction
    def template(a, b):
        with context_manager_with_parentnes(4) as something:
            return something + a + b

    function = template.get_usual_function()

    assert function(1, 2) == 130


def test_other_context_managers_with_empty_parentness_are_working_in_async_function_without_arguments():
    @contextmanager
    def context_manager_with_parentnes():
        yield 123

    @transfunction
    def template():
        with context_manager_with_parentnes() as something:
            return something

    function = template.get_async_function()

    assert run(function()) == 123


def test_other_context_managers_with_empty_parentness_are_working_in_async_function_with_arguments():
    @contextmanager
    def context_manager_with_parentnes():
        yield 123

    @transfunction
    def template(a, b):
        with context_manager_with_parentnes() as something:
            return something + a + b

    function = template.get_async_function()

    assert run(function(1, 2)) == 126


def test_other_context_managers_with_not_empty_parentness_are_working_in_async_function_without_arguments():
    @contextmanager
    def context_manager_with_parentnes(c):
        yield 123 + c

    @transfunction
    def template():
        with context_manager_with_parentnes(4) as something:
            return something

    function = template.get_async_function()

    assert run(function()) == 127


def test_other_context_managers_with_not_empty_parentness_are_working_in_async_function_with_arguments():
    @contextmanager
    def context_manager_with_parentnes(c):
        yield 123 + c

    @transfunction
    def template(a, b):
        with context_manager_with_parentnes(4) as something:
            return something + a + b

    function = template.get_async_function()

    assert run(function(1, 2)) == 130


def test_other_context_managers_with_empty_parentness_are_working_in_generator_function_without_arguments():
    @contextmanager
    def context_manager_with_parentnes():
        yield 123

    @transfunction
    def template():
        with context_manager_with_parentnes() as something:
            yield something

    function = template.get_generator_function()

    assert list(function()) == [123]


def test_other_context_managers_with_empty_parentness_are_working_in_generator_function_with_arguments():
    @contextmanager
    def context_manager_with_parentnes():
        yield 123

    @transfunction
    def template(a, b):
        with context_manager_with_parentnes() as something:
            yield something + a + b

    function = template.get_generator_function()

    assert list(function(1, 2)) == [126]


def test_other_context_managers_with_not_empty_parentness_are_working_in_generator_function_without_arguments():
    @contextmanager
    def context_manager_with_parentnes(c):
        yield 123 + c

    @transfunction
    def template():
        with context_manager_with_parentnes(4) as something:
            yield something

    function = template.get_generator_function()

    assert list(function()) == [127]


def test_other_context_managers_with_not_empty_parentness_are_working_in_generator_function_with_arguments():
    @contextmanager
    def context_manager_with_parentnes(c):
        yield 123 + c

    @transfunction
    def template(a, b):
        with context_manager_with_parentnes(4) as something:
            yield something + a + b

    function = template.get_generator_function()

    assert list(function(1, 2)) == [130]


def test_other_context_managers_into_context_marker_with_empty_parentness_are_working_in_usual_function_without_arguments():
    @contextmanager
    def context_manager_with_parentnes():
        yield 123

    @transfunction
    def template():
        with sync_context:  # noqa: SIM117
            with context_manager_with_parentnes() as something:
                return something

    function = template.get_usual_function()

    assert function() == 123


def test_other_context_managers_into_context_marker_with_empty_parentness_are_working_in_usual_function_with_arguments():
    @contextmanager
    def context_manager_with_parentnes():
        yield 123

    @transfunction
    def template(a, b):
        with sync_context:  # noqa: SIM117
            with context_manager_with_parentnes() as something:
                return something + a + b

    function = template.get_usual_function()

    assert function(1, 2) == 126


def test_other_context_managers_into_context_marker_with_not_empty_parentness_are_working_in_usual_function_without_arguments():
    @contextmanager
    def context_manager_with_parentnes(c):
        yield 123 + c

    @transfunction
    def template():
        with sync_context:  # noqa: SIM117
            with context_manager_with_parentnes(4) as something:
                return something

    function = template.get_usual_function()

    assert function() == 127


def test_other_context_managers_into_context_marker_with_not_empty_parentness_are_working_in_usual_function_with_arguments():
    @contextmanager
    def context_manager_with_parentnes(c):
        yield 123 + c

    @transfunction
    def template(a, b):
        with sync_context:  # noqa: SIM117
            with context_manager_with_parentnes(4) as something:
                return something + a + b

    function = template.get_usual_function()

    assert function(1, 2) == 130


def test_other_context_managers_into_context_marker_with_empty_parentness_are_working_in_async_function_without_arguments():
    @contextmanager
    def context_manager_with_parentnes():
        yield 123

    @transfunction
    def template():
        with async_context:  # noqa: SIM117
            with context_manager_with_parentnes() as something:
                return something

    function = template.get_async_function()

    assert run(function()) == 123


def test_other_context_managers_into_context_marker_with_empty_parentness_are_working_in_async_function_with_arguments():
    @contextmanager
    def context_manager_with_parentnes():
        yield 123

    @transfunction
    def template(a, b):
        with async_context:  # noqa: SIM117
            with context_manager_with_parentnes() as something:
                return something + a + b

    function = template.get_async_function()

    assert run(function(1, 2)) == 126


def test_other_context_managers_into_context_marker_with_not_empty_parentness_are_working_in_async_function_without_arguments():
    @contextmanager
    def context_manager_with_parentnes(c):
        yield 123 + c

    @transfunction
    def template():
        with async_context:  # noqa: SIM117
            with context_manager_with_parentnes(4) as something:
                return something

    function = template.get_async_function()

    assert run(function()) == 127


def test_other_context_managers_into_context_marker_with_not_empty_parentness_are_working_in_async_function_with_arguments():
    @contextmanager
    def context_manager_with_parentnes(c):
        yield 123 + c

    @transfunction
    def template(a, b):
        with async_context:  # noqa: SIM117
            with context_manager_with_parentnes(4) as something:
                return something + a + b

    function = template.get_async_function()

    assert run(function(1, 2)) == 130


def test_other_context_managers_into_context_marker_with_empty_parentness_are_working_in_generator_function_without_arguments():
    @contextmanager
    def context_manager_with_parentnes():
        yield 123

    @transfunction
    def template():
        with generator_context:  # noqa: SIM117
            with context_manager_with_parentnes() as something:
                yield something

    function = template.get_generator_function()

    assert list(function()) == [123]


def test_other_context_managers_into_context_marker_with_empty_parentness_are_working_in_generator_function_with_arguments():
    @contextmanager
    def context_manager_with_parentnes():
        yield 123

    @transfunction
    def template(a, b):
        with generator_context:  # noqa: SIM117
            with context_manager_with_parentnes() as something:
                yield something + a + b

    function = template.get_generator_function()

    assert list(function(1, 2)) == [126]


def test_other_context_managers_into_context_marker_with_not_empty_parentness_are_working_in_generator_function_without_arguments():
    @contextmanager
    def context_manager_with_parentnes(c):
        yield 123 + c

    @transfunction
    def template():
        with generator_context:  # noqa: SIM117
            with context_manager_with_parentnes(4) as something:
                yield something

    function = template.get_generator_function()

    assert list(function()) == [127]


def test_other_context_managers_into_context_marker_with_not_empty_parentness_are_working_in_generator_function_with_arguments():
    @contextmanager
    def context_manager_with_parentnes(c):
        yield 123 + c

    @transfunction
    def template(a, b):
        with generator_context:  # noqa: SIM117
            with context_manager_with_parentnes(4) as something:
                yield something + a + b

    function = template.get_generator_function()

    assert list(function(1, 2)) == [130]


def test_basic_yield_from_it():
    @transfunction
    def template():
        with generator_context:
            yield_from_it([1, 2, 3])

    generator_function = template.get_generator_function()

    assert list(generator_function()) == [1, 2, 3]


def test_yield_from_it_with_function_call():
    def some_other_function():
        return [1, 2, 3]

    @transfunction
    def template():
        with generator_context:
            yield_from_it(some_other_function())

    generator_function = template.get_generator_function()

    assert list(generator_function()) == [1, 2, 3]


def test_await_it_with_two_arguments():
    async def another_function():
        return None

    @transfunction
    def template():
        with async_context:
            return await_it(another_function(), another_function())

    with pytest.raises(WrongMarkerSyntaxError, match=full_match('The "await_it" marker can be used with only one positional argument.')):
        template.get_async_function()


def test_await_it_without_arguments():
    @transfunction
    def template():
        with async_context:
            return await_it()

    with pytest.raises(WrongMarkerSyntaxError, match=full_match('The "await_it" marker can be used with only one positional argument.')):
        template.get_async_function()


def test_await_it_with_one_usual_and_one_named_arguments():
    async def another_function():
        return None

    @transfunction
    def template():
        with async_context:
            return await_it(another_function(), kek=another_function())

    with pytest.raises(WrongMarkerSyntaxError, match=full_match('The "await_it" marker can be used with only one positional argument.')):
        template.get_async_function()


def test_yield_from_it_with_two_arguments():
    @transfunction
    def template():
        with generator_context:
            return yield_from_it([1, 2, 3], [1, 2, 3])

    with pytest.raises(WrongMarkerSyntaxError, match=full_match('The "yield_from_it" marker can be used with only one positional argument.')):
        template.get_generator_function()


def test_yield_from_it_without_arguments():
    @transfunction
    def template():
        with generator_context:
            return yield_from_it()

    with pytest.raises(WrongMarkerSyntaxError, match=full_match('The "yield_from_it" marker can be used with only one positional argument.')):
        template.get_generator_function()


def test_yield_from_it_with_one_usual_and_one_named_arguments():
    @transfunction
    def template():
        with generator_context:
            return yield_from_it([1, 2, 3], kek=[1, 2, 3])

    with pytest.raises(WrongMarkerSyntaxError, match=full_match('The "yield_from_it" marker can be used with only one positional argument.')):
        template.get_generator_function()


def test_string_literal_default_value_for_usual_function():
    @transfunction
    def template(string='kek'):
        return string

    function = template.get_usual_function()

    assert function() == 'kek'


def test_int_literal_default_value_for_usual_function():
    @transfunction
    def template(number=123):
        return number

    function = template.get_usual_function()

    assert function() == 123


def test_list_literal_default_value_for_usual_function():
    @transfunction
    def template(number, lst=[]):  # noqa: B006
        lst.append(number)
        return lst

    function = template.get_usual_function()

    assert function(1) == [1]
    assert function(2) == [1, 2]


def test_list_literal_default_value_it_the_same_for_all_types_of_functions():
    @transfunction
    def template(number, lst=[]):  # noqa: B006
        lst.append(number)
        with async_context:
            return lst
        with sync_context:
            return lst
        with generator_context:
            yield from lst

    function = template.get_usual_function()

    assert function(1) == [1]
    assert function(2) == [1, 2]

    async_function = template.get_async_function()

    assert run(async_function(3)) == [1, 2, 3]
    assert run(async_function(4)) == [1, 2, 3, 4]

    generator_function = template.get_generator_function()

    assert list(generator_function(5)) == [1, 2, 3, 4, 5]
    assert list(generator_function(6)) == [1, 2, 3, 4, 5, 6]


def test_string_literal_default_value_for_async_function():
    @transfunction
    def template(string='kek'):
        return string

    function = template.get_async_function()

    assert run(function()) == 'kek'


def test_int_literal_default_value_for_async_function():
    @transfunction
    def template(number=123):
        return number

    function = template.get_async_function()

    assert run(function()) == 123


def test_list_literal_default_value_for_async_function():
    @transfunction
    def template(number, lst=[]):  # noqa: B006
        lst.append(number)
        return lst

    function = template.get_async_function()

    assert run(function(1)) == [1]
    assert run(function(2)) == [1, 2]


def test_string_literal_default_value_for_generator_function():
    @transfunction
    def template(string='kek'):
        yield string

    function = template.get_generator_function()

    assert list(function()) == ['kek']


def test_int_literal_default_value_for_generator_function():
    @transfunction
    def template(number=123):
        yield number

    function = template.get_generator_function()

    assert list(function()) == [123]


def test_list_literal_default_value_for_generator_function():
    @transfunction
    def template(number, lst=[]):  # noqa: B006
        lst.append(number)
        yield from lst

    function = template.get_generator_function()

    assert list(function(1)) == [1]
    assert list(function(2)) == [1, 2]


def test_nonlocal_variable_default_value_for_usual_function():
    container = []
    variable = 123

    @transfunction
    def template(number=variable):
        container.append(number)

    function = template.get_usual_function()
    function()

    assert container == [variable]


def test_global_variable_default_value_for_usual_function():
    container = []

    @transfunction
    def template(number=SOME_GLOBAL):
        container.append(number)

    function = template.get_usual_function()
    function()

    assert container == [SOME_GLOBAL]


def test_resetted_global_variable_default_value_for_usual_function():
    container = []
    SOME_GLOBAL = 'kek'  # noqa: N806

    @transfunction
    def template(number=SOME_GLOBAL):
        container.append(number)

    function = template.get_usual_function()
    function()

    assert container == ['kek']


def test_nonlocal_variable_default_value_for_async_function():
    variable = 123

    @transfunction
    def template(number=variable):
        return number

    function = template.get_async_function()

    assert run(function()) == variable


def test_global_variable_default_value_for_async_function():
    @transfunction
    def template(number=SOME_GLOBAL):
        return number

    function = template.get_async_function()

    assert run(function()) == SOME_GLOBAL


def test_resetted_global_variable_default_value_for_async_function():
    SOME_GLOBAL = 'kek'  # noqa: N806

    @transfunction
    def template(number=SOME_GLOBAL):
        return number

    function = template.get_async_function()

    assert run(function()) == 'kek'


def test_nonlocal_variable_default_value_for_generator_function():
    variable = 123

    @transfunction
    def template(number=variable):
        yield number

    function = template.get_generator_function()

    assert list(function()) == [variable]


def test_global_variable_default_value_for_generator_function():
    @transfunction
    def template(number=SOME_GLOBAL):
        yield number

    function = template.get_generator_function()

    assert list(function()) == [SOME_GLOBAL]


def test_resetted_global_variable_default_value_for_generator_function():
    SOME_GLOBAL = 'kek'  # noqa: N806

    @transfunction
    def template(number=SOME_GLOBAL):
        yield number

    function = template.get_generator_function()

    assert list(function()) == ['kek']


def test_use_decorator_without_at():
    def template():
        pass

    template = transfunction(template)

    with pytest.raises(WrongDecoratorSyntaxError, match=full_match("The @transfunction decorator can only be used with the '@' symbol. Don't use it as a regular function. Also, don't rename it.")):
        template.get_usual_function()

    with pytest.raises(WrongDecoratorSyntaxError, match=full_match("The @transfunction decorator can only be used with the '@' symbol. Don't use it as a regular function. Also, don't rename it.")):
        template.get_async_function()

    with pytest.raises(WrongDecoratorSyntaxError, match=full_match("The @transfunction decorator can only be used with the '@' symbol. Don't use it as a regular function. Also, don't rename it.")):
        template.get_generator_function()

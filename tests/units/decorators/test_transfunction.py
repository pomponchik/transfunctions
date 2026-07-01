import traceback
from asyncio import run
from contextlib import contextmanager
from inspect import getsourcelines, iscoroutinefunction, isfunction, isgeneratorfunction

import pytest
from full_match import match

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
SOME_GLOBAL_OBJECT = object()

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
    """
    @transfunction turns a regular template function into a FunctionTransformer as soon as it is decorated.

    This checks the decorated object directly, before any derived sync, async, or generator function is requested.
    """
    @transfunction
    def function():
        pass

    assert isinstance(function, FunctionTransformer)


@pytest.mark.parametrize(
    ('args', 'kwargs'),
    [
        ((), {}),
        (('lol', 'kek'), {}),
        (('lol', 'kek'), {'lol': 'kek'}),
        ((), {'lol': 'kek'}),
    ],
)
def test_direct_call_or_transformer(args, kwargs):
    """
    Transfunction-decorated templates reject direct calls and require generating a usable function variant first.

    The check covers empty, positional, mixed, and keyword-only calls so the error is tied to direct transformer execution, not argument binding.
    """
    @transfunction
    def function_maker(*args, **kwargs):
        pass

    with pytest.raises(CallTransfunctionDirectlyError, match=match("You can't call a transfunction object directly, create a function, a generator function or a coroutine function from it.")):
        function_maker(*args, **kwargs)


def test_pass_coroutine_function_to_decorator():
    """
    @transfunction rejects an async template function at decoration time.

    The test defines an async function under the decorator and checks that the async-template ValueError is raised before any transformed function is requested.
    """
    with pytest.raises(ValueError, match=match("Only regular or generator functions can be used as a template for @transfunction. You can't use async functions.")):
        @transfunction
        async def function_maker():
            return 4


def test_pass_not_function_to_decorator():
    """Passing a non-function object to @transfunction raises the generic template-type ValueError immediately, before any function generation is attempted."""
    with pytest.raises(ValueError, match=match("Only regular or generator functions can be used as a template for @transfunction.")):
        transfunction(1)


def test_create_usual_function_without_any_markers():
    """
    Create a normal function from a transfunction template with no marker blocks.

    A template containing only ordinary body code should still produce a real Python function whose call result matches that body.
    """
    @transfunction
    def function_maker():
        return 4

    function = function_maker.get_usual_function()

    assert isfunction(function)
    assert function() == 4


def test_create_usual_function_with_parameters_without_any_markers():
    """
    A marker-free transfunction template with parameters and a default can generate a regular function that preserves argument handling.

    The generated function is checked as a real function and returns the template body result when called with positional arguments plus the keyword default.
    """
    @transfunction
    def function_maker(a, b, c=3):
        return a + b + c

    function = function_maker.get_usual_function()

    assert isfunction(function)
    assert function(1, 2, c=3) == 6


def test_null_indentation_usual_function():
    """
    A zero-indentation transfunction template can generate a regular function from its sync branch.

    The generated function should ignore the async and generator branches in the same template and return the sync result.
    """
    function = null_indentation_function.get_usual_function()

    assert function() == 1


def test_null_indentation_async_function():
    """
    A zero-indentation transfunction template can generate an async function that keeps only the async branch.

    The generated coroutine is run and its result confirms that the async branch was selected over the sync and generator alternatives.
    """
    function = null_indentation_function.get_async_function()

    assert run(function()) == 2


def test_null_indentation_generator_function():
    """
    Top-level transfunction templates can generate a generator function that keeps only the generator branch.

    This locks down the null-indented case by consuming the generated function and checking that it yields 1, 2, and 3 while the sync and async branches are excluded.
    """
    function = null_indentation_function.get_generator_function()

    assert [x for x in function()] == [1, 2, 3]


def test_create_async_function_without_any_markers():
    """
    Async functions can be created from plain transfunction templates without markers.

    The generated function is expected to be recognized as a coroutine function and to preserve the template's return value when awaited.
    """
    @transfunction
    def function_maker():
        return 4

    function = function_maker.get_async_function()

    assert iscoroutinefunction(function)
    assert run(function()) == 4


def test_create_async_function_with_parameters_without_any_markers():
    """
    An unmarked parameterized template can be generated as an async coroutine function.

    It preserves positional arguments, the defaulted keyword parameter, and the template's return calculation when invoked.
    """
    @transfunction
    def function_maker(a, b, c=3):
        return a + b + c

    function = function_maker.get_async_function()

    assert iscoroutinefunction(function)
    assert run(function(1, 2, c=3)) == 6


def test_try_to_pass_lambda_to_decorator():
    """
    Rejects using an inline lambda as the transfunction template.

    The test calls the decorator constructor directly because lambdas cannot use decorator syntax, and verifies the lambda-specific ValueError rather than the generic invalid-template error.
    """
    with pytest.raises(ValueError, match=match("Only regular or generator functions can be used as a template for @transfunction. Don't use lambdas here.")):
        transfunction(lambda x: x)


def test_create_generator_function_without_any_markers():
    """
    A marker-free zero-argument transfunction template that is already a generator can be materialized as a generator function.

    The generated function should be recognized as a generator function and yield the original sequence unchanged.
    """
    @transfunction
    def generator_maker():
        yield 1
        yield 2
        yield 3

    generator = generator_maker.get_generator_function()

    assert isgeneratorfunction(generator)
    assert [x for x in generator()] == [1, 2, 3]


def test_create_generator_function_with_parameters_without_any_markers():
    """
    A marker-free transfunction generator with parameters can be converted into a generator function.

    The generated function should still be recognized as a generator function and should yield values from both positional and keyword arguments.
    """
    @transfunction
    def generator_maker(a, b, c=3):
        yield a
        yield b
        yield c

    generator = generator_maker.get_generator_function()

    assert isgeneratorfunction(generator)
    assert [x for x in generator(1, 2, c=3)] == [1, 2, 3]


def test_traceback_is_working_in_simple_usual_function():
    """
    Generated usual functions preserve traceback locations for exceptions raised in the template body.

    This covers the plain synchronous case: a ValueError raised by the decorated template should propagate from the generated usual function, with the final traceback frame pointing back to the original raise line.
    """
    @transfunction
    def make():
        raise ValueError('message')

    function = make.get_usual_function()

    try:
        function()
        raise AssertionError
    except ValueError as e:
        certain_traceback = list(traceback.extract_tb(e.__traceback__))

    assert getsourcelines(make.function)[1] + 2 == certain_traceback[-1].lineno
    assert getsourcelines(make.function)[0][-1].strip() == certain_traceback[-1].line


def test_traceback_is_working_in_simple_async_function():
    """
    Generated async transfunctions preserve traceback location for exceptions raised in the original template body.

    The check runs the generated coroutine and verifies the final traceback frame still maps to the template raise line.
    """
    @transfunction
    def make():
        raise ValueError('message')

    function = make.get_async_function()

    try:
        run(function())
        raise AssertionError
    except ValueError as e:
        certain_traceback = list(traceback.extract_tb(e.__traceback__))

    assert getsourcelines(make.function)[1] + 2 == certain_traceback[-1].lineno
    assert getsourcelines(make.function)[0][-1].strip() == certain_traceback[-1].line


def test_traceback_is_working_in_simple_generator_function():
    """
    Generated generator functions preserve traceback location for exceptions raised in the template body.

    The template is generator-shaped only because of a trailing unreachable yield, so the check forces iteration and verifies the final traceback frame still points at the original raise line.
    """
    @transfunction
    def make():
        raise ValueError('message')
        yield 1

    function = make.get_generator_function()

    try:
        [x for x in function()]
        raise AssertionError
    except ValueError as e:
        certain_traceback = list(traceback.extract_tb(e.__traceback__))

    assert getsourcelines(make.function)[1] + 2 == certain_traceback[-1].lineno
    assert getsourcelines(make.function)[0][-2].strip() == certain_traceback[-1].line


def test_traceback_is_working_in_usual_function_with_marker():
    """
    Generated usual functions preserve traceback locations for errors raised inside sync_context markers.

    This checks that removing the marker wrapper still leaves the final traceback frame pointing at the original template raise line by both line number and source text.
    """
    @transfunction
    def make():
        with sync_context:
            raise ValueError('message')

    function = make.get_usual_function()

    try:
        function()
        raise AssertionError
    except ValueError as e:
        certain_traceback = list(traceback.extract_tb(e.__traceback__))

    assert getsourcelines(make.function)[1] + 3 == certain_traceback[-1].lineno
    assert getsourcelines(make.function)[0][-1].strip() == certain_traceback[-1].line


def test_traceback_is_working_in_simple_async_function_with_marker():
    """
    Generated async functions preserve tracebacks for exceptions raised inside async context marker blocks.

    The test checks that a propagated exception still reports the original template raise line as the final traceback frame.
    """
    @transfunction
    def make():
        with async_context:
            raise ValueError('message')

    function = make.get_async_function()

    try:
        run(function())
        raise AssertionError
    except ValueError as e:
        certain_traceback = list(traceback.extract_tb(e.__traceback__))

    assert getsourcelines(make.function)[1] + 3 == certain_traceback[-1].lineno
    assert getsourcelines(make.function)[0][-1].strip() == certain_traceback[-1].line


def test_traceback_is_working_in_simple_generator_function_with_marker():
    """
    Exceptions raised inside a generator marker keep the original template traceback location.

    The generated generator is forced to run by iteration, and the traceback is checked against the template line that raises the error.
    """
    @transfunction
    def make():
        with generator_context:
            raise ValueError('message')
            yield 1

    function = make.get_generator_function()

    try:
        [x for x in function()]
        raise AssertionError
    except ValueError as e:
        certain_traceback = list(traceback.extract_tb(e.__traceback__))

    assert getsourcelines(make.function)[1] + 3 == certain_traceback[-1].lineno
    assert getsourcelines(make.function)[0][-2].strip() == certain_traceback[-1].line


def test_try_to_use_transfunction_decorator_without_at_sign():
    """
    Using the transfunction decorator without @ syntax is rejected.

    This locks down the guard that prevents treating the decorator as an ordinary helper call when it must be applied through decorator syntax.
    """
    def function():
        with generator_context:
            raise ValueError('message')
            yield 1

    make = transfunction(function)

    with pytest.raises(WrongDecoratorSyntaxError, match=match("The @transfunction decorator can only be used with the '@' symbol. Don't use it as a regular function. Also, don't rename it.")):
        function = make.get_generator_function()


def test_double_use_of_decorator():
    """Using @transfunction twice on the same function is rejected at decoration time.

    The test defines a function with two stacked transfunction decorators and expects the duplicate-decorator error before any transformed function is requested.
    """
    with pytest.raises(DualUseOfDecoratorError, match=match("You cannot use the 'transfunction' decorator twice for the same function.")):
        @transfunction
        @transfunction
        def make():
            pass


def test_read_closures_with_usual_function():
    """
    Generated usual functions preserve read access to closed-over local variables.

    This covers the simple synchronous case where a transfunction template captures an object from its enclosing scope and the regular function produced from it returns that exact object.
    """
    nonlocal_variable = object()

    @transfunction
    def make():
        #nonlocal nonlocal_variable
        return nonlocal_variable

    function = make.get_usual_function()

    assert function() is nonlocal_variable


def test_read_closures_with_usual_function_with_arguments():
    """
    Converting a template to a usual function preserves read access to closure values while accepting runtime arguments.

    The generated function is checked across repeated calls with different positional arguments to confirm that closure reconstruction and parameter binding work together.
    """
    nonlocal_variable = 1

    @transfunction
    def make(some_number):
        #nonlocal nonlocal_variable
        return nonlocal_variable + some_number

    function = make.get_usual_function()

    assert function(1) == 2
    assert function(2) == 3


def test_read_closures_with_async_function():
    """
    Generated async functions preserve read-only access to closure variables from the template scope.

    The template captures a local value, is converted to an async function, and the resulting coroutine is run without arguments to verify it returns that captured value.
    """
    nonlocal_variable = 1

    @transfunction
    def make():
        #nonlocal nonlocal_variable
        return nonlocal_variable

    function = make.get_async_function()

    assert run(function()) == 1


def test_read_closures_with_async_function_with_arguments():
    """
    Generated async functions can read closed-over values while binding positional arguments.

    The test awaits the generated function with two different arguments to verify that both the captured value and the call argument are used.
    """
    nonlocal_variable = 1

    @transfunction
    def make(some_number):
        #nonlocal nonlocal_variable
        return nonlocal_variable + some_number

    function = make.get_async_function()

    assert run(function(1)) == 2
    assert run(function(2)) == 3


def test_read_closures_with_generator_function():
    """A generated generator function preserves read access to a closed-over local value."""
    nonlocal_variable = 1

    @transfunction
    def make():
        #nonlocal nonlocal_variable
        yield nonlocal_variable

    function = make.get_generator_function()

    assert list(function()) == [1]


def test_read_closures_with_generator_function_with_arguments():
    """
    A generated generator function preserves closure reads while accepting call arguments.

    The converted function is consumed with different argument values to confirm each yielded result combines the closed-over outer value with the value passed at runtime.
    """
    nonlocal_variable = 1

    @transfunction
    def make(some_number):
        #nonlocal nonlocal_variable
        yield nonlocal_variable + some_number

    function = make.get_generator_function()

    assert list(function(1)) == [2]
    assert list(function(2)) == [3]


def test_read_globals_with_usual_function():
    """
    Generated usual functions preserve access to globals read by the template.

    The check converts a parameterless transfunction with get_usual_function() and verifies that the resulting callable returns the exact module-level object it references.
    """
    @transfunction
    def make():
        return SOME_GLOBAL_OBJECT

    function = make.get_usual_function()

    assert function() is SOME_GLOBAL_OBJECT


def test_read_globals_with_usual_function_with_arguments():
    """
    Generated regular functions can read module globals while preserving positional arguments.

    The converted usual function should combine the module-level value with each supplied argument across repeated calls, showing that both global lookup and argument binding survive template conversion.
    """
    @transfunction
    def make(some_number):
        #nonlocal nonlocal_variable
        return SOME_GLOBAL + some_number

    function = make.get_usual_function()

    assert function(1) == SOME_GLOBAL + 1
    assert function(2) == SOME_GLOBAL + 2


def test_read_globals_with_async_function():
    """
    Generated async functions preserve access to globals read by the template.

    The template has no parameters or context markers, so the check isolates global name resolution after get_async_function() converts the body and the coroutine is run.
    """
    @transfunction
    def make():
        return SOME_GLOBAL

    function = make.get_async_function()

    assert run(function()) == SOME_GLOBAL


def test_read_globals_with_async_function_with_arguments():
    """
    Generated async functions can read template globals while using caller-supplied arguments.

    The check awaits the converted function with different argument values to lock down that global lookup is preserved and arguments are evaluated per call.
    """
    @transfunction
    def make(some_number):
        return SOME_GLOBAL + some_number

    function = make.get_async_function()

    assert run(function(1)) == SOME_GLOBAL + 1
    assert run(function(2)) == SOME_GLOBAL + 2


def test_read_globals_with_generator_function():
    """
    Generated generator functions preserve access to globals read from yielded expressions.

    The check iterates the converted generator and verifies it yields the module-level value from the template function's original namespace.
    """
    @transfunction
    def make():
        yield SOME_GLOBAL

    function = make.get_generator_function()

    assert list(function()) == [SOME_GLOBAL]


def test_read_globals_with_generator_function_with_arguments():
    """
    Generated generator functions preserve module global lookup while binding call arguments dynamically.

    The test consumes separate generator calls with different arguments to confirm each yielded value combines the same global with the current argument.
    """
    @transfunction
    def make(some_number):
        yield SOME_GLOBAL + some_number

    function = make.get_generator_function()

    assert list(function(1)) == [SOME_GLOBAL + 1]
    assert list(function(2)) == [SOME_GLOBAL + 2]


def test_write_nonlocal_variable_from_usual_function_without_arguments():
    """
    Generated no-argument regular functions preserve writes to nonlocal variables in the original closure.

    The check calls the converted function and verifies that the enclosing value is updated, proving the nonlocal binding targets the original closure cell.
    """
    nonlocal_variable = 1

    @transfunction
    def make():
        nonlocal nonlocal_variable
        nonlocal_variable += 1

    function = make.get_usual_function()
    function()

    assert nonlocal_variable == 2


def test_write_nonlocal_variable_from_usual_function_with_arguments():
    """A transformed ordinary function with arguments can update a nonlocal variable."""
    nonlocal_variable = 1

    @transfunction
    def make(number):
        nonlocal nonlocal_variable
        nonlocal_variable += number

    function = make.get_usual_function()
    function(3)

    assert nonlocal_variable == 4


def test_write_nonlocal_variable_from_async_function_without_arguments():
    """
    A no-argument transfunction can generate an async function that updates a nonlocal variable.

    The generated coroutine is executed and the enclosing variable is checked afterward, proving that assignment writes through to the original closure cell.
    """
    nonlocal_variable = 1

    @transfunction
    def make():
        nonlocal nonlocal_variable
        nonlocal_variable += 1

    function = make.get_async_function()
    run(function())

    assert nonlocal_variable == 2


def test_write_nonlocal_variable_from_async_function_with_arguments():
    """
    Generated async transfunctions preserve nonlocal writes from templates with arguments.

    Running the generated coroutine should update the original enclosing variable using the supplied argument, confirming that async conversion keeps the closure binding writable.
    """
    nonlocal_variable = 1

    @transfunction
    def make(number):
        nonlocal nonlocal_variable
        nonlocal_variable += number

    function = make.get_async_function()
    run(function(3))

    assert nonlocal_variable == 4


def test_write_nonlocal_variable_from_generator_function_without_arguments():
    """
    Generated no-argument generator functions preserve writable nonlocal closure variables.

    The test consumes the generator returned by get_generator_function() so the nonlocal update in the generator body executes and changes the enclosing value.
    """
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
    """
    Generated generator functions can mutate nonlocal closure variables using call arguments.

    The test exhausts a generated generator with an argument and checks that the enclosing variable changes by that value, proving the write reaches the original closure cell.
    """
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
    """
    A no-argument generated regular function can write to the template's module global.

    The check verifies that calling the generated function increments the original global value and restores the module state afterward.
    """
    @transfunction
    def make():
        global SOME_GLOBAL  # noqa: PLW0603
        SOME_GLOBAL += 1

    global SOME_GLOBAL  # noqa: PLW0603
    SOME_GLOBAL_BEFORE = SOME_GLOBAL  # noqa: N806
    function = make.get_usual_function()
    function()

    assert SOME_GLOBAL == SOME_GLOBAL_BEFORE + 1

    SOME_GLOBAL = SOME_GLOBAL_BEFORE


def test_write_global_variable_from_usual_function_with_arguments():
    """
    A usual function generated from a transfunction can write to a module global using its positional argument.

    The test checks that the generated callable mutates the original global value by the argument amount, then restores the global so the state change does not leak.
    """
    @transfunction
    def make(number):
        global SOME_GLOBAL  # noqa: PLW0603
        SOME_GLOBAL += number

    global SOME_GLOBAL  # noqa: PLW0603
    SOME_GLOBAL_BEFORE = SOME_GLOBAL  # noqa: N806
    function = make.get_usual_function()
    function(3)

    assert SOME_GLOBAL == SOME_GLOBAL_BEFORE + 3

    SOME_GLOBAL = SOME_GLOBAL_BEFORE


def test_write_global_variable_from_async_function_without_arguments():
    """
    A zero-argument async transfunction preserves writes to module globals.

    The generated coroutine should honor a global declaration and mutate the original module-level variable when run.
    """
    @transfunction
    def make():
        global SOME_GLOBAL  # noqa: PLW0603
        SOME_GLOBAL += 1

    global SOME_GLOBAL  # noqa: PLW0603
    SOME_GLOBAL_BEFORE = SOME_GLOBAL  # noqa: N806
    function = make.get_async_function()
    run(function())

    assert SOME_GLOBAL == SOME_GLOBAL_BEFORE + 1

    SOME_GLOBAL = SOME_GLOBAL_BEFORE


def test_write_global_variable_from_async_function_with_arguments():
    """
    Generated async functions preserve writable access to module-level globals while forwarding call arguments.

    The check runs a coroutine generated from a regular transfunction template, passes an increment value, and verifies that the global changes by that value.
    """
    @transfunction
    def make(number):
        global SOME_GLOBAL  # noqa: PLW0603
        SOME_GLOBAL += number

    global SOME_GLOBAL  # noqa: PLW0603
    SOME_GLOBAL_BEFORE = SOME_GLOBAL  # noqa: N806
    function = make.get_async_function()
    run(function(3))

    assert SOME_GLOBAL == SOME_GLOBAL_BEFORE + 3

    SOME_GLOBAL = SOME_GLOBAL_BEFORE


def test_write_global_variable_from_generator_function_without_arguments():
    """
    A no-argument generator function produced by a transfunction can write back to a module-level global variable.

    The check exhausts the generated generator and verifies the global value changes, while preserving the original global afterward.
    """
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
    """
    Generated generator functions can write to template module globals using call arguments.

    The generator is consumed to run the side effect, then the assertion checks that the original global was incremented by the argument value.
    """
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
    """
    Generated transfunction variants keep the module name of functions defined beside the template.

    The check compares module metadata for sync, async, and generator outputs against a local ordinary function without executing them.
    """
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
    """
    A transfunction-decorated instance method yields a usual function bound to that instance.

    The check calls the generated function without passing self and expects it to read instance state.
    """
    class SomeClass:
        some_value = 1
        @transfunction
        def template(self):
            return self.some_value + 1

    some_class_instance = SomeClass()

    assert isinstance(some_class_instance.template, FunctionTransformer)
    assert some_class_instance.template.get_usual_function()() == 2


def test_it_works_with_simple_usual_method_with_parameters():
    """
    A transfunction-decorated instance method exposes a usual generated function as a bound method with parameters intact.

    The generated function is called through an instance with one explicit argument; it should receive self automatically, use the default parameter value, and read the instance attribute when computing the result.
    """
    class SomeClass:
        some_value = 1
        @transfunction
        def template(self, a, b=5):
            return self.some_value + 1 + a + b

    some_class_instance = SomeClass()

    assert isinstance(some_class_instance.template, FunctionTransformer)
    assert some_class_instance.template.get_usual_function()(2) == 9


def test_it_works_with_simple_async_method():
    """A transfunction-decorated instance method can generate an async bound method that reads instance state."""
    class SomeClass:
        some_value = 1
        @transfunction
        def template(self):
            return self.some_value + 1

    some_class_instance = SomeClass()

    assert isinstance(some_class_instance.template, FunctionTransformer)
    assert run(some_class_instance.template.get_async_function()()) == 2


def test_it_works_with_simple_async_method_with_parameters():
    """
    Accessing a transfunction on an instance can produce an async bound method that receives self and preserves its parameters.

    The generated coroutine should use the instance state, accept the provided positional argument, apply the default argument value, and return the template expression result when awaited.
    """
    class SomeClass:
        some_value = 1
        @transfunction
        def template(self, a, b=5):
            return self.some_value + 1 + a + b

    some_class_instance = SomeClass()

    assert isinstance(some_class_instance.template, FunctionTransformer)
    assert run(some_class_instance.template.get_async_function()(2)) == 9


def test_it_works_with_simple_generator_method():
    """Decorating a simple generator method preserves its generator behavior and yielded values."""
    class SomeClass:
        some_value = 1
        @transfunction
        def template(self):
            yield self.some_value + 1

    some_class_instance = SomeClass()

    assert isinstance(some_class_instance.template, FunctionTransformer)
    assert list(some_class_instance.template.get_generator_function()()) == [2]


def test_it_works_with_simple_generator_method_with_parameters():
    """
    A transfunction-decorated generator method can generate a bound generator that applies self, explicit parameters, and default parameters correctly.

    The check calls the generated generator with one provided argument while relying on the method default for another, confirming that binding and default handling work together.
    """
    class SomeClass:
        some_value = 1
        @transfunction
        def template(self, a, b=5):
            yield self.some_value + 1 + a + b

    some_class_instance = SomeClass()

    assert isinstance(some_class_instance.template, FunctionTransformer)
    assert list(some_class_instance.template.get_generator_function()(2)) == [9]


def test_combine_with_other_decorator_before():
    """
    Rejects a transfunction template that already has another source-level decorator.

    The other decorator is applied before transfunction wrapping, and the syntax error is expected when the usual function is requested.
    """
    def other_decorator(function):
        return function

    @transfunction
    @other_decorator
    def template():
        pass

    with pytest.raises(WrongDecoratorSyntaxError, match=match('The @transfunction decorator cannot be used in conjunction with other decorators.')):
        template.get_usual_function()


def test_combine_with_other_decorator_after():
    """
    Reject a template that is wrapped by another decorator after @transfunction.

    The check is triggered when the usual function is requested, and the extra decorator is invalid even when it leaves the template unchanged.
    """
    def other_decorator(function):
        return function

    @other_decorator
    @transfunction
    def template():
        pass

    with pytest.raises(WrongDecoratorSyntaxError, match=match('The @transfunction decorator cannot be used in conjunction with other decorators.')):
        template.get_usual_function()


def test_create_empty_usual_function_without_arguments():
    """A zero-argument transfunction with only async-only content still creates a regular function that returns None."""
    @transfunction
    def template():
        with async_context:
            pass

    function = template.get_usual_function()

    assert function() is None


def test_create_empty_usual_function_with_arguments():
    """
    Generating a usual callable from an async-only template preserves its arguments and returns None.

    The discarded async_context body contains a return expression using both arguments, so the check ensures that unselected async code is removed rather than evaluated.
    """
    @transfunction
    def template(a, b):
        with async_context:
            return a + b

    function = template.get_usual_function()

    assert function(1, 2) is None


def test_create_empty_async_function_without_arguments():
    """
    Generating an async function from a zero-argument template with only sync-only content succeeds.

    The sync-only body is excluded from the async variant, leaving a valid empty coroutine that completes with None when awaited.
    """
    @transfunction
    def template():
        with sync_context:
            pass

    function = template.get_async_function()

    assert run(function()) is None


def test_create_empty_async_function_with_arguments():
    """
    Generating an async function from an argument-taking template with only sync-only content yields a callable coroutine that returns None.

    The generated async function must still accept the template arguments even though no async body remains.
    """
    @transfunction
    def template(a, b):
        with sync_context:
            return a + b

    function = template.get_async_function()

    assert run(function(1, 2)) is None


def test_other_context_managers_with_empty_parentness_are_working_in_usual_function_without_arguments():
    """
    A zero-argument transfunction template preserves and executes a top-level ordinary context manager call with empty parentheses in a generated usual function.

    The check confirms that the value yielded by the local context manager is bound by the with statement and returned unchanged.
    """
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
    """
    A generated usual function preserves a no-argument ordinary context manager while still binding template arguments.

    The result must combine the context manager's yielded value with the supplied arguments.
    """
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
    """
    Non-marker context managers with arguments are preserved in usual functions generated from no-argument templates.

    The generated function should execute the context manager normally, including both enter and exit paths, and return the value bound by its as-target.
    """
    events = []

    @contextmanager
    def context_manager_with_parentnes(c):
        events.append('enter')
        try:
            yield 123 + c
        finally:
            events.append('exit')

    @transfunction
    def template():
        with context_manager_with_parentnes(4) as something:
            return something

    function = template.get_usual_function()

    assert function() == 127
    assert events == ['enter', 'exit']


def test_other_context_managers_with_not_empty_parentness_are_working_in_usual_function_with_arguments():
    """
    Ensure @transfunction keeps an ordinary argument-bearing context manager intact in a generated usual function.

    The context manager should still receive its call argument, bind its yielded value through as, and let that value combine with the generated function's own positional arguments.
    """
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
    """
    Normal context managers called with empty parentheses keep working when a no-argument transfunction is converted to an async function.

    The coroutine should preserve the with-block binding, run both context manager paths, and return the value yielded by the ordinary context manager.
    """
    events = []

    @contextmanager
    def context_manager_with_parentnes():
        events.append('enter')
        try:
            yield 123
        finally:
            events.append('exit')

    @transfunction
    def template():
        with context_manager_with_parentnes() as something:
            return something

    function = template.get_async_function()

    assert run(function()) == 123
    assert events == ['enter', 'exit']


def test_other_context_managers_with_empty_parentness_are_working_in_async_function_with_arguments():
    """
    Async functions generated from argument-taking transfunctions preserve ordinary empty-argument context manager blocks.

    The generated coroutine should keep the context manager active, bind its yielded value, preserve positional arguments, and return the result computed from both sources.
    """
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
    """
    A generated async function from a zero-argument template preserves an ordinary context manager call with arguments.

    The awaited result should be the value yielded by that context manager.
    """
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
    """
    Generated async functions preserve ordinary context manager calls with their own arguments.

    This checks that a transfunction template containing a non-marker with block can become an async function and pass template arguments into the preserved context manager call when awaited.
    """
    context_manager_arguments = []

    @contextmanager
    def context_manager_with_parentnes(a, b):
        context_manager_arguments.append((a, b))
        yield 123 + a + b

    @transfunction
    def template(a, b):
        with context_manager_with_parentnes(a, b) as something:
            return something

    function = template.get_async_function()

    assert run(function(1, 2)) == 126
    assert context_manager_arguments == [(1, 2)]


def test_other_context_managers_with_empty_parentness_are_working_in_generator_function_without_arguments():
    """
    A no-argument transfunction preserves an ordinary no-argument context manager in generated generator output.

    The check ensures the context value is bound inside the with block and yielded by the generated generator.
    """
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
    """
    Preserves a zero-argument ordinary context manager and generated function arguments in a generator transfunction.

    The generated function should keep the context manager call and its `as` binding intact while yielding a value computed from the bound context value and the positional arguments.
    """
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
    """
    Generated generator functions preserve ordinary context manager calls with arguments in zero-argument transfunction templates.

    This locks down that non-marker with blocks remain usable common code and that the yielded value from the context manager is produced when the generated function is iterated.
    """
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
    """
    Generated generator functions preserve ordinary context manager calls with arguments in shared template code.

    The check also verifies that the generated generator forwards its own call arguments into the preserved with block and yields the value computed from both sources.
    """
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
    """
    A zero-argument transfunction preserves and executes a normal context manager nested inside a sync context marker when generating a usual function.

    The generated function should enter the nested context manager, bind its yielded value, and return it.
    """
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
    """
    A usual function generated from a transfunction preserves a zero-argument context manager nested inside a sync context marker.

    The check covers a template with positional arguments, where the nested context manager contributes its yielded value and the generated function combines it with the supplied arguments.
    """
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
    """
    Generates a usual function that preserves an argument-taking context manager nested inside a sync context marker.

    The template itself takes no arguments; the returned value proves the marker block was retained for the usual-function variant, the marker wrapper was removed, and the nested context manager still provided the value used by the return statement.
    """
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
    """
    A generated usual function preserves an argument-taking context manager nested inside sync_context while binding template arguments.

    The result must combine the nested manager's yielded value with the supplied arguments.
    """
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
    """
    A generated async function preserves a no-argument ordinary context manager nested inside async_context.

    The awaited result should come from the nested manager's yielded value, and the nested manager should run enter, body, and exit in order.
    """
    events = []

    @contextmanager
    def context_manager_with_parentnes():
        events.append('enter')
        try:
            yield 123
        finally:
            events.append('exit')

    @transfunction
    def template():
        with async_context:  # noqa: SIM117
            with context_manager_with_parentnes() as something:
                events.append('body')
                return something

    function = template.get_async_function()

    assert run(function()) == 123
    assert events == ['enter', 'body', 'exit']


def test_other_context_managers_into_context_marker_with_empty_parentness_are_working_in_async_function_with_arguments():
    """
    Ensure async function extraction preserves an ordinary context manager nested inside an async_context marker when the template has arguments.

    The generated coroutine should remove only the marker wrapper, keep the inner with binding, and return the context manager value combined with the supplied arguments.
    """
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
    """
    Generating an async function keeps a normal context manager nested inside the async marker.

    The marker wrapper is removed, but the inner context manager call with its positional argument still runs, so the coroutine returns the value yielded by that manager.
    """
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
    """
    Async transfunctions preserve nested regular context managers with arguments and as targets inside async-context marker blocks.

    The generated coroutine is called with template arguments and must combine them with the value yielded by the nested context manager, proving the conversion does not disturb that nested context.
    """
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
    """
    Generated generator functions keep ordinary nested context managers inside generator-only marker blocks.

    This covers the zero-argument case: the generator marker is removed, the inner context manager still runs, and its yielded value is emitted by the generated generator.
    """
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
    """
    Generator templates preserve nested ordinary context managers inside generator-only marker blocks.

    This checks that an empty-argument context manager call is entered, its yielded value is bound with an `as` target, and the generated generator can combine that value with call arguments.
    """
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
    """
    Generator transfunctions with no template arguments preserve regular context manager calls inside generator_context.

    The generated generator should execute the nested manager with its positional argument, bind the value it yields, and yield that value to the caller.
    """
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
    """
    Generator templates preserve nested context managers with arguments inside generator-only blocks.

    Checks that the generated generator enters the ordinary context manager, binds its yielded value, and combines it with the generator call arguments.
    """
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
    """
    Generated generator functions yield every value supplied through a basic yield_from_it marker.

    This locks down the simplest valid path: a no-argument transfunction template uses yield_from_it with a literal iterable, is converted with get_generator_function(), and produces the iterable values when consumed.
    """
    @transfunction
    def template():
        with generator_context:
            yield_from_it([1, 2, 3])

    generator_function = template.get_generator_function()

    assert list(generator_function()) == [1, 2, 3]


def test_yield_from_it_with_function_call():
    """
    Allow yield_from_it() in generator_context to delegate to the iterable returned by a helper call.

    The generated generator function is checked by iterating it and comparing the collected values from the helper.
    """
    def some_other_function():
        return [1, 2, 3]

    @transfunction
    def template():
        with generator_context:
            yield_from_it(some_other_function())

    generator_function = template.get_generator_function()

    assert list(generator_function()) == [1, 2, 3]


def test_await_it_with_two_arguments():
    """
    get_async_function() rejects await_it markers with two positional arguments inside async_context.

    The test checks that this is reported during async function generation as a marker syntax error, preserving the rule that await_it accepts exactly one awaited expression.
    """
    async def another_function():
        return None

    @transfunction
    def template():
        with async_context:
            return await_it(another_function(), another_function())

    with pytest.raises(WrongMarkerSyntaxError, match=match('The "await_it" marker can be used with only one positional argument.')):
        template.get_async_function()


def test_await_it_without_arguments():
    """
    await_it() without an argument inside async_context is rejected when generating the async function.

    The template can be decorated, but requesting the async version must fail because await_it needs exactly one positional value to await.
    """
    @transfunction
    def template():
        with async_context:
            return await_it()

    with pytest.raises(WrongMarkerSyntaxError, match=match('The "await_it" marker can be used with only one positional argument.')):
        template.get_async_function()


def test_await_it_with_one_usual_and_one_named_arguments():
    """
    await_it rejects a marker call that combines one positional coroutine expression with a keyword argument in async_context.

    The check is made when the generated async function is requested, so the test locks down lazy validation during transformation rather than template definition.
    """
    async def another_function():
        return None

    @transfunction
    def template():
        with async_context:
            return await_it(another_function(), kek=another_function())

    with pytest.raises(WrongMarkerSyntaxError, match=match('The "await_it" marker can be used with only one positional argument.')):
        template.get_async_function()


def test_yield_from_it_with_two_arguments():
    """
    yield_from_it with more than one positional argument is rejected when building a generator function.

    The invalid marker appears inside generator_context, so the check covers generator-function generation rather than template definition or iteration.
    """
    @transfunction
    def template():
        with generator_context:
            return yield_from_it([1, 2, 3], [1, 2, 3])

    with pytest.raises(WrongMarkerSyntaxError, match=match('The "yield_from_it" marker can be used with only one positional argument.')):
        template.get_generator_function()


def test_yield_from_it_without_arguments():
    """
    Reject yield_from_it markers that are called without an argument.

    The error is raised when the generator function is requested, confirming that marker arity is validated during template generation.
    """
    @transfunction
    def template():
        with generator_context:
            return yield_from_it()

    with pytest.raises(WrongMarkerSyntaxError, match=match('The "yield_from_it" marker can be used with only one positional argument.')):
        template.get_generator_function()


def test_yield_from_it_with_one_usual_and_one_named_arguments():
    """
    Reject yield_from_it calls that combine one positional iterable with a keyword argument.

    The template is validated when its generated function is requested, so the expected failure is a marker syntax error rather than normal generator execution.
    """
    @transfunction
    def template():
        with generator_context:
            return yield_from_it([1, 2, 3], kek=[1, 2, 3])

    with pytest.raises(WrongMarkerSyntaxError, match=match('The "yield_from_it" marker can be used with only one positional argument.')):
        template.get_generator_function()


def test_string_literal_default_value_for_usual_function():
    """
    Preserve a string literal default when a transfunction template is converted to a usual function.

    The generated usual function is called without arguments to confirm it returns the template's default value.
    """
    @transfunction
    def template(string='kek'):
        return string

    function = template.get_usual_function()

    assert function() == 'kek'


def test_int_literal_default_value_for_usual_function():
    """
    Decorating a regular function preserves an integer literal default argument.

    The test checks that omitting the argument uses the declared integer default instead of requiring an explicit value.
    """
    @transfunction
    def template(number=123):
        return number

    function = template.get_usual_function()

    assert function() == 123


def test_list_literal_default_value_for_usual_function():
    """
    A usual function generated from a transfunction preserves shared mutable list default semantics.

    Calling it repeatedly without providing the list argument should reuse the same default list, so mutations from earlier calls are visible later.
    """
    @transfunction
    def template(number, lst=[]):  # noqa: B006
        lst.append(number)
        return lst

    function = template.get_usual_function()

    assert function(1) == [1]
    assert function(2) == [1, 2]


def test_list_literal_default_value_it_the_same_for_all_types_of_functions():
    """
    Mutable list literal defaults are shared across all function variants generated from one transfunction.

    The test calls the usual, async, and generator functions without passing the list and checks that each call sees the cumulative appended values from earlier calls.
    """
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
    """
    @transfunction preserves a string literal default value when generating an async function.

    The generated coroutine is called without passing that argument, and its resolved result must come from the original default.
    """
    @transfunction
    def template(string='kek'):
        return string

    function = template.get_async_function()

    assert run(function()) == 'kek'


def test_int_literal_default_value_for_async_function():
    """
    Async transfunctions preserve integer literal default values.

    This covers an async function parameter whose default is an integer literal, ensuring the decorated callable keeps that default value intact.
    """
    @transfunction
    def template(number=123):
        return number

    function = template.get_async_function()

    assert run(function()) == 123


def test_list_literal_default_value_for_async_function():
    """
    Generated async functions preserve a mutable list literal default.

    The test checks that repeated awaited calls without an explicit list argument share the same default list and accumulate appended values.
    """
    @transfunction
    def template(number, lst=[]):  # noqa: B006
        lst.append(number)
        return lst

    function = template.get_async_function()

    assert run(function(1)) == [1]
    assert run(function(2)) == [1, 2]


def test_string_literal_default_value_for_generator_function():
    """
    Preserve a string literal default argument when building a generator function.

    The generated function is called without arguments and its yielded values are collected to confirm the default string is used.
    """
    @transfunction
    def template(string='kek'):
        yield string

    function = template.get_generator_function()

    assert list(function()) == ['kek']


def test_int_literal_default_value_for_generator_function():
    """
    Materialized generator transfunctions preserve integer literal default arguments.

    Calling the generated generator without arguments should yield the default integer value.
    """
    @transfunction
    def template(number=123):
        yield number

    function = template.get_generator_function()

    assert list(function()) == [123]


def test_list_literal_default_value_for_generator_function():
    """
    Preserve a list literal default across calls to a generated generator function.

    The generator should yield the accumulated list contents, showing that the same default list instance is reused after mutation.
    """
    @transfunction
    def template(number, lst=[]):  # noqa: B006
        lst.append(number)
        yield from lst

    function = template.get_generator_function()

    assert list(function(1)) == [1]
    assert list(function(2)) == [1, 2]


def test_nonlocal_variable_default_value_for_usual_function():
    """
    get_usual_function preserves a default argument value captured from an enclosing local variable.

    Calling the generated usual function without arguments should pass that exact preserved object into the body.
    """
    container = []
    variable = object()

    @transfunction
    def template(number=variable):
        container.append(number)

    function = template.get_usual_function()
    function()

    assert len(container) == 1
    assert container[0] is variable


def test_global_variable_default_value_for_usual_function():
    """
    A generated ordinary function preserves a default argument value bound from a module global.

    The test calls the generated function without an argument and checks the captured default through the function's side effect on a local container.
    """
    container = []

    @transfunction
    def template(number=SOME_GLOBAL):
        container.append(number)

    function = template.get_usual_function()
    function()

    assert container == [SOME_GLOBAL]


def test_resetted_global_variable_default_value_for_usual_function():
    """
    A generated usual function keeps the template's captured default value when it came from a local variable shadowing a global.

    The check calls the generated function without arguments and verifies that the side effect uses the local default value, not the module global.
    """
    container = []
    SOME_GLOBAL = 'kek'  # noqa: N806

    @transfunction
    def template(number=SOME_GLOBAL):
        container.append(number)

    function = template.get_usual_function()
    function()

    assert container == ['kek']


def test_nonlocal_variable_default_value_for_async_function():
    """
    Preserves an enclosing-scope parameter default when generating an async function.

    The generated coroutine is called without an explicit argument, so the returned value proves the nonlocal default was captured and used.
    """
    variable = 123

    @transfunction
    def template(number=variable):
        return number

    function = template.get_async_function()

    assert run(function()) == variable


def test_global_variable_default_value_for_async_function():
    """
    Async functions generated from a transfunction preserve module-level globals used as default parameter values.

    The generated coroutine is called without the parameter, so the check isolates default resolution through the template's global namespace rather than an explicit argument override.
    """
    @transfunction
    def template(number=SOME_GLOBAL):
        return number

    function = template.get_async_function()

    assert run(function()) == SOME_GLOBAL


def test_resetted_global_variable_default_value_for_async_function():
    """
    Generated async functions keep a default value evaluated from a local name that shadows a module global.

    Calling the coroutine without a keyword-only argument should use the local default, not the same-named global or a copied positional default.
    """
    SOME_GLOBAL = 'kek'  # noqa: N806

    @transfunction
    def template(*, number=SOME_GLOBAL):
        return number

    function = template.get_async_function()

    assert run(function()) == 'kek'


def test_nonlocal_variable_default_value_for_generator_function():
    """
    Generated generator functions preserve default argument values evaluated from the template's enclosing scope.

    The test defines a generator template whose parameter default comes from a local variable, builds the generator function, calls it without arguments, and verifies that iteration yields that captured default value.
    """
    variable = 123

    @transfunction
    def template(number=variable):
        yield number

    function = template.get_generator_function()

    assert list(function()) == [variable]


def test_global_variable_default_value_for_generator_function():
    """
    A generated generator preserves a module-level global used as a parameter default.

    The check converts a transfunction template with get_generator_function(), calls the generated generator without arguments, and verifies that iteration yields the default value from the global.
    """
    @transfunction
    def template(number=SOME_GLOBAL):
        yield number

    function = template.get_generator_function()

    assert list(function()) == [SOME_GLOBAL]


def test_resetted_global_variable_default_value_for_generator_function():
    """
    Generated generator functions keep evaluated default values from shadowed local names.

    This checks that a template default captured from a test-local variable is reused after generator conversion, so calling the generated function without arguments yields the local value rather than the same-named module global.
    """
    SOME_GLOBAL = 'kek'  # noqa: N806

    @transfunction
    def template(number=SOME_GLOBAL):
        yield number

    function = template.get_generator_function()

    assert list(function()) == ['kek']


def test_use_decorator_without_at():
    """
    Manually wrapping a template with transfunction() without @ syntax cannot generate any function variant.

    The test checks that the usual, async, and generator generation methods all reject the transformer with the decorator syntax error.
    """
    def template():
        pass

    template = transfunction(template)

    with pytest.raises(WrongDecoratorSyntaxError, match=match("The @transfunction decorator can only be used with the '@' symbol. Don't use it as a regular function. Also, don't rename it.")):
        template.get_usual_function()

    with pytest.raises(WrongDecoratorSyntaxError, match=match("The @transfunction decorator can only be used with the '@' symbol. Don't use it as a regular function. Also, don't rename it.")):
        template.get_async_function()

    with pytest.raises(WrongDecoratorSyntaxError, match=match("The @transfunction decorator can only be used with the '@' symbol. Don't use it as a regular function. Also, don't rename it.")):
        template.get_generator_function()

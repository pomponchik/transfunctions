![logo](https://raw.githubusercontent.com/pomponchik/transfunctions/develop/docs/assets/logo_2.svg)

[![Downloads](https://static.pepy.tech/badge/transfunctions/month)](https://pepy.tech/project/transfunctions)
[![Downloads](https://static.pepy.tech/badge/transfunctions)](https://pepy.tech/project/transfunctions)
[![Coverage Status](https://coveralls.io/repos/github/pomponchik/transfunctions/badge.svg?branch=main)](https://coveralls.io/github/pomponchik/transfunctions?branch=main)
[![Lines of code](https://sloc.xyz/github/pomponchik/transfunctions/?category=code)](https://github.com/boyter/scc/)
[![Hits-of-Code](https://hitsofcode.com/github/pomponchik/transfunctions?branch=main)](https://hitsofcode.com/github/pomponchik/transfunctions/view?branch=main)
[![Test-Package](https://github.com/pomponchik/transfunctions/actions/workflows/tests_and_coverage.yml/badge.svg)](https://github.com/pomponchik/transfunctions/actions/workflows/tests_and_coverage.yml)
[![Python versions](https://img.shields.io/pypi/pyversions/transfunctions.svg)](https://pypi.python.org/pypi/transfunctions)
[![PyPI version](https://badge.fury.io/py/transfunctions.svg)](https://badge.fury.io/py/transfunctions)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

This library is designed to solve one of the most important problems in python programming - dividing all written code into 2 camps: sync and async. We get rid of code duplication by using templates.


## Table of contents

- [**Quick start**](#quick-start)
- [**The problem**](#the-problem)
- [**Code generation**](#code-generation)
- [**Markers**](#markers)
- [**Superfunctions**](#superfunctions)


## Quick start

Install it:

```bash
pip install transfunctions
```

And use:

```python
from asyncio import run
from transfunctions import (
    transfunction,
    sync_context,
    async_context,
    generator_context,
)

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

function = template.get_usual_function()
function()
#> so, it's just usual function!

async_function = template.get_async_function()
run(async_function())
#> so, it's an async function!

generator_function = template.get_generator_function()
list(generator_function())
#> so, it's a generator function!
```

As you can see, in this case, 3 different functions were created based on the template, including both common parts and unique ones for a specific type of function.

You can also quickly try out this and other packages without having to install using [instld](https://github.com/pomponchik/instld).


## The problem

Since the `asyncio` module appeared in Python more than 10 years ago, many well-known libraries have received their asynchronous alternates. A lot of the code in the Python ecosystem has been [duplicated](https://en.wikipedia.org/wiki/Don%27t_repeat_yourself), and you probably know many such examples.

The reason for this problem is that the Python community has chosen a way to implement asynchrony expressed through syntax. There are new keywords in the language, such as `async` and `await`. Their use makes the code so-called "[multicolored](https://journal.stuffwithstuff.com/2015/02/01/what-color-is-your-function/)": all the functions in it can be red or blue, and depending on the color, the rules for calling them are different. You can only call blue functions from red ones, but not vice versa.

I must say that implementing asynchronous calls using a special syntax is not the only solution. There are languages like Go where runtime can independently determine "under the hood" where a function should be asynchronous and where not, and choose the correct way to call it. A programmer does not need to manually "colorize" their functions there. Personally, I think that choosing a different path is the mistake of the Python community, but that's not what we're discussing here.

The solution offered by this library is based on templating. You can take a certain function as a template and generate several others based on it: regular, asynchronous, or generator. This allows you to avoid duplicating code where it was previously impossible. And all this without major changes in Python syntax or in the internal structure of the interpreter. We're just "sweeping under the carpet" syntax differences. Combined with the idea of context-aware functions, this makes for an even more powerful tool: `superfunctions`. This allows you to create a single function object that can be handled as you like: as a regular function, as an asynchronous function, or as a generator. The function will behave the way you use it. Thus, this library solves the problem of code duplication caused by the syntactic approach to marking asynchronous execution sections.


## Code generation

This library is based on the idea of [generating code](https://en.wikipedia.org/wiki/Code_generation_(compiler)) at the [AST](https://en.wikipedia.org/wiki/Abstract_syntax_tree) level.

Several derivatives can be generated from a single template function. Let's take a simple template function as an example:

```python
@transfunction
def template():
    print('something')
```

Executing this code will actually return to us not a function, but a special object that can *produce* functions:

```python
print(template)
#> <transfunctions.transformer.FunctionTransformer object at 0x105368fa0>
```

To get a function from this object, you need to call the `get_usual_function` method from it:

```python
function = template.get_usual_function()
function()
#> something
```

Nothing unusual so far, right? We just defined the function and got it. But! You can also get an async function from this object:

```python
from asyncio import run

async_function = template.get_async_function()
run(async_function())
#> something
```

That's more interesting. In fact, we transferred all the contents from the original function to the generated async function. The content itself has not changed in any way, that is, we got a function that would look something like this:

```python
async def template():
    print('something')
```

But the true power of templating is revealed when we get the opportunity to generate *partially different* functions. Some parts of the template will be reused in all generated versions, while others will be used only in those that relate to a specific type of function. Let's look again at the template example from the ["quick start" section](#quick-start):

```python
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
```

The `get_usual_function` method will return a function that will contain a common part (the first `print`) and a part highlighted using the context manager as related to ordinary functions. It will look something like this:

```python
def template():
    print('so, ', end='')
    print("it's just usual function!")
```

The `get_async_function` method will return an async function that looks like this:

```python
def template():
    print('so, ', end='')
    print("it's an async function!")
```

Finally, method `get_generator_function` will return a generator function that looks like this:

```python
def template():
    print('so, ', end='')
    print("it's a generator function!")
    yield
```

All generated functions:

- Inherit the access to global variables and closures that the original template function had.
- Сan be either ordinary stand-alone functions or bound methods. In the latter case, they will be linked to the same object.

There is only one known limitation: you cannot use any third-party decorators on the template using the decorator syntax, because in some situations this can lead to ambiguous behavior. If you still really need to use a third-party decorator, just generate any of the functions from the template, and then apply your decorator to the result of the generation.


## Markers

Objects that we call "markers" are used to mark up specific blocks inside the template function. In the [section above](#code-generation), we have already seen how 3 context managers work: `sync_context`, `async_context`, and `generator_context`; all of them are markers. When generating a function with a type corresponding to each of these context managers, the contents of this context manager remain in the generated function, and the others with their contents are cut out.

There is another marker that is used to point to the place where you want to use the `await` keyword, it is called `await_it`. In the generated code, this will be converted into an `await` statement. From the template function, which looks like this:

```python
from asyncio import sleep

@transfunction
def template():
    with async_context:
        await_it(sleep(5))
```

... when calling the `get_async_function` method, you will get such an async function:

```python
async def template():
    await sleep(5)
```

All markers do not need to be imported in order for the generated code to be functional: they are destroyed during the [code generation](#code-generation). However, you can do this if your linter or syntax checker in your IDE requires it:

```python
from transfunctions import (
    sync_context,
    async_context,
    generator_context,
    await_it,
)
```

Make sure that the generated functions do not include keywords that are not related to this type of function. For example, you cannot generate a regular function using the `get_usual_function` method from such a template:

```python
from asyncio import sleep

@transfunction
def template():
    await_it(sleep(5))
```

Regular or generator functions cannot use the `await` keyword, so you will get an exception when you try to generate such a function. The same applies to the `yield` and `yield from` keywords. You cannot use them outside of code blocks that relate *only* to generator functions. Please note that not in all such cases, the `transfunctions` library will offer you an informative exception. Here you'd better rely on your own knowledge of `Python` syntax. However, even if such an exception is provided, it will only be raised when trying to generate a function of the type in which this syntax is inappropriate. At the template definition stage, you won't get an exception telling you that something went wrong, because the code generation here is lazy and the code is not analyzed for correctness in any way before you request it.


## Superfunctions

Superfunctions are the most powerful feature of the library. They allow you to completely "put under the hood" all the machinery for selecting the desired type of function based on the template function. The selection is completely automatic.

Let's take a look at the sample code:

```python
from transfunctions import (
    superfunction,
    sync_context,
    async_context,
    generator_context,
    await_it,
)

@superfunction   # Please note, there's a different decorator here.
def my_superfunction():
    print('so, ', end='')
    with sync_context:
        print("it's just usual function!")
    with async_context:
        print("it's an async function!")
    with generator_context:
        print("it's a generator function!")
        yield
```

With the `@superfunction` decorator, you no longer need to call special methods for code generation. You can use the resulting function right away, and it will behave differently depending on how you use it.

If you use it as a regular function, a regular function will be created "under the hood" based on the template and then called:

To call a superfunction like a regular function, you need to use a special tilde syntax:

```python
~my_superfunction()
#> so, it's just usual function!
```

Yes, the tilde syntax simply means putting the `~` symbol in front of the function name when calling it.

If you use `asyncio.run` or the `await` keyword when calling, the async version of the function will be automatically generated and called:

```python
from asyncio import run

run(my_superfunction())
#> so, it's an async function!
```

And finally, if you try to iterate through the result of calling this function, it turns out that it behaves like a generator function:

```python
list(my_superfunction())
#> so, it's a generator function!
```

How does it work? In fact, `my_superfunction` returns some kind of intermediate object that can be both a coroutine and a generator and an ordinary function. Depending on how it is handled, it lazily code-generates the desired version of the function from a given template and uses it.

By default, a superfunction is called as a regular function using tilde syntax, but there is another mode. To enable it, use the appropriate flag in the decorator:

```python
@superfunction(tilde_syntax=False)
```

In this case, the superfunction can be called in exactly the same way as a regular function:

```python
my_superfunction()
#> so, it's just usual function!
```

However, it is not completely free. The fact is that this mode uses a special trick with a reference counter, a special mechanism inside the interpreter that cleans up memory. When there is no reference to an object, the interpreter deletes it, and you can link your callback to this process. It is inside such a callback that the contents of your function are actually executed. This imposes some restrictions on you:

- You cannot use the return values from this function in any way. If you try to save the result of a function call to a variable, the reference counter to the returned object will not reset while this variable exists, and accordingly the function will not actually be called.
- Exceptions will not work normally inside this function. Rather, they can be picked up and intercepted in [`sys.unraisablehook`](https://docs.python.org/3/library/sys.html#sys.unraisablehook), but they will not go up the stack above this function. This is due to a feature of CPython: exceptions that occur inside callbacks for finalizing objects are completely escaped.

This mode is well suited for functions such as logging or sending statistics from your code: simple functions from which no exceptions or return values are expected. In all other cases, I recommend using the tilde syntax.

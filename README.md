# transfunctions

[![Downloads](https://static.pepy.tech/badge/transfunctions/month)](https://pepy.tech/project/transfunctions)
[![Downloads](https://static.pepy.tech/badge/transfunctions)](https://pepy.tech/project/transfunctions)
[![Coverage Status](https://coveralls.io/repos/github/pomponchik/transfunctions/badge.svg?branch=main)](https://coveralls.io/github/pomponchik/transfunctions?branch=develop)
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

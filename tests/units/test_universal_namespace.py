import builtins
from inspect import currentframe

import pytest

from transfunctions.universal_namespace import UniversalNamespaceAroundFunction

some_global = 321

def test_set_something_and_get():
    """A fresh universal namespace treats unknown names as missing and returns values assigned directly into it."""
    def function():
        pass

    frame = currentframe()

    namespace = UniversalNamespaceAroundFunction(function, frame)

    with pytest.raises(KeyError):
        namespace['key']

    namespace['key'] = 123

    assert namespace['key'] == 123


def test_get_nonlocal():
    """
    Resolve a requested name from the supplied frame's local variables.

    This locks down that lookup can use a caller-local value even when the wrapped function is empty and does not close over that name.
    """
    some_nonlocal = 123  # noqa: F841

    def function():
        pass

    frame = currentframe()

    namespace = UniversalNamespaceAroundFunction(function, frame)

    assert namespace['some_nonlocal'] == 123


def test_get_global():
    """
    Resolves missing names from the wrapped function's module globals.

    The check uses a module-level sentinel without local or builtin shadowing, so the lookup path being locked down is specifically the global fallback.
    """
    def function():
        pass

    frame = currentframe()

    namespace = UniversalNamespaceAroundFunction(function, frame)

    assert namespace['some_global'] == 321


def test_get_nonlocal_with_name_as_global():
    """
    Captured frame locals take precedence over globals with the same name.

    This locks down that UniversalNamespaceAroundFunction returns the nonlocal value when a requested identifier exists both in the captured frame and in the wrapped function's global namespace.
    """
    some_global = 123  # noqa: F841

    def function():
        pass

    frame = currentframe()

    namespace = UniversalNamespaceAroundFunction(function, frame)

    assert namespace['some_global'] == 123


def test_get_builtin():
    """
    Resolves a missing namespace name from Python builtins.

    The test uses a temporary unique builtin value so the assertion specifically verifies the final builtin fallback after namespace assignments, frame locals, and function globals do not provide the name.
    """
    builtins.some_name = 1234

    def function():
        pass

    frame = currentframe()

    namespace = UniversalNamespaceAroundFunction(function, frame)

    assert namespace['some_name'] == 1234

    del builtins.some_name


def test_get_nonlocal_with_name_as_builtin():
    """Frame-local names take precedence over builtins with the same name when resolving through the universal namespace."""
    builtins.some_name = 1234

    some_name = 123  # noqa: F841

    def function():
        pass

    frame = currentframe()

    namespace = UniversalNamespaceAroundFunction(function, frame)

    assert namespace['some_name'] == 123

    del builtins.some_name


def test_get_global_with_name_as_builtin():
    """
    Return the original function module global when the same name also exists in builtins.

    The check creates a temporary builtin with the same name as a module global and verifies that namespace lookup still resolves to the module value.
    """
    builtins.some_global = 1234

    def function():
        pass

    frame = currentframe()

    namespace = UniversalNamespaceAroundFunction(function, frame)

    assert namespace['some_global'] == 321

    del builtins.some_global


def test_set_value_with_same_name_as_nonlocal():
    """
    Assigned namespace values take precedence over same-named captured frame locals.

    This covers the case where an explicit write records a value for a name that is also visible through the captured frame; later lookup must return the written value.
    """
    some_nonlocal = 123  # noqa: F841

    def function():
        pass

    frame = currentframe()

    namespace = UniversalNamespaceAroundFunction(function, frame)

    namespace['some_nonlocal'] = 12345

    assert namespace['some_nonlocal'] == 12345


def test_set_value_with_same_name_as_global():
    """
    Assigned namespace values shadow globals with the same name.

    This checks that a value stored directly in the universal namespace is returned on lookup even when the wrapped function's module globals already contain that name.
    """
    def function():
        pass

    frame = currentframe()

    namespace = UniversalNamespaceAroundFunction(function, frame)

    namespace['some_global'] = 12345

    assert namespace['some_global'] == 12345


def test_set_value_with_same_name_as_builtin():
    """
    Explicit namespace assignments take precedence over same-named builtins.

    The check creates a temporary builtin, assigns a different value under that name in the namespace, and verifies lookup returns the assigned value.
    """
    builtins.some_builtin = 1234

    def function():
        pass

    frame = currentframe()

    namespace = UniversalNamespaceAroundFunction(function, frame)

    namespace['some_builtin'] = 12345

    assert namespace['some_builtin'] == 12345

    del builtins.some_builtin

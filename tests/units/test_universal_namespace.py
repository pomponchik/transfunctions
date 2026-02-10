import builtins
from inspect import currentframe

import pytest

from transfunctions.universal_namespace import UniversalNamespaceAroundFunction

some_global = 321

def test_set_something_and_get():
    def function():
        pass

    frame = currentframe()

    namespace = UniversalNamespaceAroundFunction(function, frame)

    with pytest.raises(KeyError):
        namespace['key']

    namespace['key'] = 123

    assert namespace['key'] == 123


def test_get_nonlocal():
    some_nonlocal = 123  # noqa: F841

    def function():
        pass

    frame = currentframe()

    namespace = UniversalNamespaceAroundFunction(function, frame)

    assert namespace['some_nonlocal'] == 123


def test_get_global():
    def function():
        pass

    frame = currentframe()

    namespace = UniversalNamespaceAroundFunction(function, frame)

    assert namespace['some_global'] == 321


def test_get_nonlocal_with_name_as_global():
    some_global = 123  # noqa: F841

    def function():
        pass

    frame = currentframe()

    namespace = UniversalNamespaceAroundFunction(function, frame)

    assert namespace['some_global'] == 123


def test_get_builtin():
    builtins.some_name = 1234

    def function():
        pass

    frame = currentframe()

    namespace = UniversalNamespaceAroundFunction(function, frame)

    assert namespace['some_name'] == 1234

    del builtins.some_name


def test_get_nonlocal_with_name_as_builtin():
    builtins.some_name = 1234

    some_name = 123  # noqa: F841

    def function():
        pass

    frame = currentframe()

    namespace = UniversalNamespaceAroundFunction(function, frame)

    assert namespace['some_name'] == 123

    del builtins.some_name


def test_get_global_with_name_as_builtin():
    builtins.some_global = 1234

    def function():
        pass

    frame = currentframe()

    namespace = UniversalNamespaceAroundFunction(function, frame)

    assert namespace['some_global'] == 321

    del builtins.some_global


def test_set_value_with_same_name_as_nonlocal():
    some_nonlocal = 123  # noqa: F841

    def function():
        pass

    frame = currentframe()

    namespace = UniversalNamespaceAroundFunction(function, frame)

    namespace['some_nonlocal'] = 12345

    assert namespace['some_nonlocal'] == 12345


def test_set_value_with_same_name_as_global():
    def function():
        pass

    frame = currentframe()

    namespace = UniversalNamespaceAroundFunction(function, frame)

    namespace['some_global'] = 12345

    assert namespace['some_global'] == 12345


def test_set_value_with_same_name_as_builtin():
    builtins.some_builtin = 1234

    def function():
        pass

    frame = currentframe()

    namespace = UniversalNamespaceAroundFunction(function, frame)

    namespace['some_builtin'] = 12345

    assert namespace['some_builtin'] == 12345

    del builtins.some_builtin

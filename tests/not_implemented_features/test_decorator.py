import pytest

from transfunctions import transfunction
from transfunctions.transformer import FunctionTransformer


@pytest.mark.skip(reason="There is no support for methods")
def test_it_works_with_simple_usual_method():
    class SomeClass:
        some_value = 1
        @transfunction
        def template(self):
            return self.some_value + 1

    some_class_instance = SomeClass()

    assert isinstance(some_class_instance.template, FunctionTransformer)
    assert some_class_instance.template.get_usual_function()() == 2

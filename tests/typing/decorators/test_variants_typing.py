import sys

if sys.version_info <= (3, 11):
    from typing_extensions import reveal_type
else:
    from typing import reveal_type

import pytest

from transfunctions import transfunction, variant_context


@pytest.mark.mypy_testing
def test_transfunction_variant_deduced_return_type_sync():
    @transfunction(variants=["trio"])
    def typed_transfunction(arg: float, *, kwarg: int = 0) -> int:
        with variant_context("trio"):
            return 1
        return 2

    reveal_type(typed_transfunction.get_variant_function("trio")(1.0))  # N: Revealed type is "builtins.int"



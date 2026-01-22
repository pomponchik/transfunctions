from transfunctions import transfunction, variant_context, patch_context


def test_custom_variants_basic_selection():
    @transfunction(variants=["requests", "httpx"])
    def template() -> str:
        with variant_context("requests"):
            return "requests"
        with variant_context("httpx"):
            return "httpx"
        return "common"

    assert template.get_variant_function("requests")() == "requests"
    assert template.get_variant_function("httpx")() == "httpx"


def test_custom_variants_fallback_to_common_code():
    @transfunction(variants=["trio"])
    def template() -> str:
        with variant_context("trio"):
            return "trio"
        return "common"

    assert template.get_variant_function("trio")() == "trio"


def test_patches_are_included_only_when_enabled():
    @transfunction(variants=["a", "b"])
    def template() -> list[str]:
        result: list[str] = []
        with patch_context("logging"):
            result.append("log")
        with variant_context("a"):
            result.append("a")
        with variant_context("b"):
            result.append("b")
        return result

    assert template.get_variant_function("a")() == ["a"]
    assert template.get_variant_function("a", patches=["logging"])() == ["log", "a"]
    assert template.get_variant_function("b", patches=["logging"])() == ["log", "b"]


def test_patch_can_be_limited_to_specific_variants():
    @transfunction(variants=["a", "b"])
    def template() -> list[str]:
        result: list[str] = []
        with patch_context("metrics", variants=["a"]):
            result.append("metrics")
        with variant_context("a"):
            result.append("a")
        with variant_context("b"):
            result.append("b")
        return result

    assert template.get_variant_function("a", patches=["metrics"])() == ["metrics", "a"]
    assert template.get_variant_function("b", patches=["metrics"])() == ["b"]



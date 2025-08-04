from typing import Dict, Any
from types import FrameType
import builtins


class Nothing:
    pass

class UniversalNamespaceAroundFunction(dict):
    def __init__(self, function, frame: FrameType) -> None:
        self.function = function
        self.frame = frame
        self.results: Dict[str, Any] = {}

    def __getitem__(self, key: str) -> Any:
        if key in self.results:
            return self.results[key]

        frame = self.frame

        while frame:
            locals = frame.f_locals
            if key in locals:
                return locals[key]
            frame = frame.f_back

        if key in self.function.__globals__:
            return self.function.__globals__[key]

        result_from_builtins = getattr(builtins, key, Nothing())
        if not isinstance(result_from_builtins, Nothing):
            return result_from_builtins

        raise KeyError(key)

    def __setitem__(self, key: str, value: Any) -> None:
        self.results[key] = value

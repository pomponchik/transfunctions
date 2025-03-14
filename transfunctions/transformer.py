from typing import Optional, Union, List, Any
from types import FunctionType
from collections.abc import Callable
from inspect import isfunction, getsource, getfile
from ast import parse, NodeTransformer, Expr, AST, AsyncFunctionDef
from functools import wraps, update_wrapper

from transfunctions.errors import CallTransfunctionDirectlyError


class FunctionTransformer:
    def __init__(self, function: Callable) -> None:
        if not isfunction(function):
            raise ValueError()

        self.function = function

    def __call__(self, *args: Any, **kwargs: Any) -> None:
        raise CallTransfunctionDirectlyError("You can't call a transfunction object directly, create a function, a generator function or a coroutine function from it.")

    def get_usual_function(self):
        return self.extract_context('sync_context')

    def get_async_function(self):
        original_function = self.function

        class ConvertSyncFunctionToAsync(NodeTransformer):
            def visit_FunctionDef(self, node: Expr) -> Optional[Union[AST, List[AST]]]:
                if node.name == original_function.__name__:
                    return AsyncFunctionDef(
                        name=original_function.__name__,
                        args=node.args,
                        body=node.body,
                        decorator_list=node.decorator_list,
                        lineno=node.lineno,
                        col_offset=node.col_offset,
                    )
                return node

        return self.extract_context('async_context', addictional_transformer=ConvertSyncFunctionToAsync())

    def get_generator_function(self):
        return self.extract_context('generator_context')

    def extract_context(self, context_name: str, addictional_transformer: Optional[NodeTransformer] = None):
        from ast import dump
        import astunparse
        source_code = getsource(self.function)
        tree = parse(source_code)

        class RewriteContexts(NodeTransformer):
            def visit_With(self, node: Expr) -> Optional[Union[AST, List[AST]]]:
                if len(node.items) == 1 and node.items[0].context_expr.func.id == context_name:
                    return node.body
                elif len(node.items) == 1 and node.items[0].context_expr.func.id != context_name and context_name in ('async_context', 'sync_context', 'generator_context'):
                    return None
                return node

        class DeleteDecorator(NodeTransformer):
            def visit_FunctionDef(self, node: Expr) -> Optional[Union[AST, List[AST]]]:
                node.decorator_list = [x for x in node.decorator_list if x.id != 'transfunction']
                return node

        RewriteContexts().visit(tree)
        DeleteDecorator().visit(tree)

        if addictional_transformer is not None:
            addictional_transformer.visit(tree)

        code = compile(tree, filename=getfile(self.function), mode='exec')
        namespace = {}
        exec(code, namespace)
        result = namespace[self.function.__name__]
        result = self.rewrite_globals_and_closure(result)
        result = wraps(self.function)(result)
        return result

    def rewrite_globals_and_closure(self, function):
        # https://stackoverflow.com/a/13503277/14522393
        new_function = FunctionType(
            function.__code__,
            self.function.__globals__,
            name=self.function.__name__,
            argdefs=self.function.__defaults__,
            closure=self.function.__closure__,
        )
        new_function = update_wrapper(new_function, function)
        new_function.__kwdefaults__ = function.__kwdefaults__
        return new_function

import ast
from ast import (
    AST,
    Assign,
    AsyncFunctionDef,
    Await,
    Call,
    Constant,
    FunctionDef,
    Module,
    Load,
    Name,
    NodeTransformer,
    Pass,
    Return,
    Store,
    With,
    arguments,
    increment_lineno,
    parse,
    YieldFrom,
)
from functools import update_wrapper, wraps
from inspect import getfile, getsource, iscoroutinefunction, isfunction
from sys import version_info
from types import FunctionType, MethodType, FrameType
from typing import Any, Dict, Generic, List, Optional, Union, Type, cast

from dill.source import getsource as dill_getsource  # type: ignore[import-untyped]

from transfunctions.errors import (
    AliasedDecoratorSyntaxError,
    CallTransfunctionDirectlyError,
    DualUseOfDecoratorError,
    WrongDecoratorSyntaxError,
    WrongMarkerSyntaxError,
)
from transfunctions.typing import Coroutine, Callable, Generator, FunctionParams, ReturnType, SomeClassInstance
from transfunctions.universal_namespace import UniversalNamespaceAroundFunction


class FunctionTransformer(Generic[FunctionParams, ReturnType]):
    def __init__(
        self, function: Callable[FunctionParams, ReturnType], decorator_lineno: int, decorator_name: str, frame: FrameType,
    ) -> None:
        if isinstance(function, type(self)):
            raise DualUseOfDecoratorError(f"You cannot use the '{decorator_name}' decorator twice for the same function.")
        if not isfunction(function):
            raise ValueError(f"Only regular or generator functions can be used as a template for @{decorator_name}.")
        if iscoroutinefunction(function):
            raise ValueError(f"Only regular or generator functions can be used as a template for @{decorator_name}. You can't use async functions.")
        if self.is_lambda(function):
            raise ValueError(f"Only regular or generator functions can be used as a template for @{decorator_name}. Don't use lambdas here.")

        self.function = function
        self.decorator_lineno = decorator_lineno
        self.decorator_name = decorator_name
        self.frame = frame
        self.base_object: Optional[SomeClassInstance] = None  # type: ignore[valid-type]
        self.cache: Dict[str, Callable[FunctionParams, ReturnType]] = {}

    def __call__(self, *args: Any, **kwargs: Any) -> None:
        raise CallTransfunctionDirectlyError("You can't call a transfunction object directly, create a function, a generator function or a coroutine function from it.")

    def __get__(
        self,
        base_object: SomeClassInstance,
        owner: Type[SomeClassInstance],
    ) -> 'FunctionTransformer[FunctionParams, ReturnType]':
        self.base_object = base_object
        return self

    @staticmethod
    def is_lambda(function: Callable[FunctionParams, ReturnType]) -> bool:
        # https://stackoverflow.com/a/3655857/14522393
        lambda_example = lambda: 0  # noqa: E731
        return isinstance(function, type(lambda_example)) and function.__name__ == lambda_example.__name__

    def get_usual_function(self, addictional_transformers: Optional[List[NodeTransformer]] = None) -> Callable[FunctionParams, ReturnType]:
        return cast(Callable[FunctionParams, ReturnType], self.extract_context('sync_context', addictional_transformers=addictional_transformers))

    def get_async_function(self) -> Callable[FunctionParams, Coroutine[Any, Any, ReturnType]]:
        original_function = self.function

        class ConvertSyncFunctionToAsync(NodeTransformer):
            def visit_FunctionDef(self, node: FunctionDef) -> Union[FunctionDef, AsyncFunctionDef]:
                if node.name == original_function.__name__:
                    return AsyncFunctionDef(  # type: ignore[no-any-return, call-overload]
                        name=original_function.__name__,
                        args=node.args,
                        body=node.body,
                        decorator_list=node.decorator_list,
                        lineno=node.lineno,
                        end_lineno=node.end_lineno,
                        col_offset=node.col_offset,
                        end_col_offset=node.end_col_offset,
                    )
                return node

        class ExtractAwaitExpressions(NodeTransformer):
            def visit_Call(self, node: Call) -> Union[Call, Await]:
                if isinstance(node.func, Name) and node.func.id == 'await_it':
                    if len(node.args) != 1 or node.keywords:
                        raise WrongMarkerSyntaxError('The "await_it" marker can be used with only one positional argument.')

                    return Await(
                        value=node.args[0],
                        lineno=node.lineno,
                        end_lineno=node.end_lineno,
                        col_offset=node.col_offset,
                        end_col_offset=node.end_col_offset,
                    )
                return node

        return cast(
            Callable[FunctionParams, Coroutine[Any, Any, ReturnType]],
            self.extract_context(
                'async_context',
                addictional_transformers=[
                    ConvertSyncFunctionToAsync(),
                    ExtractAwaitExpressions(),
                ],
            ),
        )

    def get_generator_function(self) -> Callable[FunctionParams, Generator[ReturnType, None, None]]:
        class ConvertYieldFroms(NodeTransformer):
            def visit_Call(self, node: Call) -> Optional[Union[AST, List[AST]]]:
                if isinstance(node.func, Name) and node.func.id == 'yield_from_it':
                    if len(node.args) != 1 or node.keywords:
                        raise WrongMarkerSyntaxError('The "yield_from_it" marker can be used with only one positional argument.')

                    return YieldFrom(
                        value=node.args[0],
                        lineno=node.lineno,
                        end_lineno=node.end_lineno,
                        col_offset=node.col_offset,
                        end_col_offset=node.end_col_offset,
                    )
                return node

        return cast(
            Callable[FunctionParams, Generator[ReturnType, None, None]],
            self.extract_context(
                'generator_context',
                addictional_transformers=[
                    ConvertYieldFroms(),
                ],
            ),
        )

    @staticmethod
    def clear_spaces_from_source_code(source_code: str) -> str:
        splitted_source_code = source_code.split('\n')

        indent = 0
        for letter in splitted_source_code[0]:
            if letter.isspace():
                indent += 1
            else:
                break

        new_splitted_source_code = [x[indent:] for x in splitted_source_code]

        return '\n'.join(new_splitted_source_code)


    def extract_context(self, context_name: str, addictional_transformers: Optional[List[NodeTransformer]] = None) -> Callable[FunctionParams, Union[Coroutine[Any, Any, ReturnType], Generator[ReturnType, None, None], ReturnType]]:
        if context_name in self.cache:
            return self.cache[context_name]
        try:
            source_code: str = getsource(self.function)
        except OSError:
            source_code = dill_getsource(self.function)

        converted_source_code = self.clear_spaces_from_source_code(source_code)
        tree = parse(converted_source_code)
        original_function = self.function
        transfunction_decorator = None
        decorator_name = self.decorator_name

        class RewriteContexts(NodeTransformer):
            def visit_With(self, node: With) -> Optional[Union[AST, List[AST]]]:
                if len(node.items) == 1:
                    if isinstance(node.items[0].context_expr, Name):
                        context_expr = node.items[0].context_expr
                    elif isinstance(node.items[0].context_expr, Call) and isinstance(node.items[0].context_expr.func, ast.Name):
                        context_expr = node.items[0].context_expr.func

                    if context_expr.id == context_name:
                        return cast(List[AST], node.body)
                    if context_expr.id != context_name and context_expr.id in ('async_context', 'sync_context', 'generator_context'):
                        return None
                return node

        class DeleteDecorator(NodeTransformer):
            def visit_FunctionDef(self, node: FunctionDef) -> Optional[Union[AST, List[AST]]]:
                if node.name == original_function.__name__:
                    nonlocal transfunction_decorator
                    transfunction_decorator = None

                    if not node.decorator_list:
                        raise WrongDecoratorSyntaxError(f"The @{decorator_name} decorator can only be used with the '@' symbol. Don't use it as a regular function. Also, don't rename it.")

                    for decorator in node.decorator_list:
                        if isinstance(decorator, Call):
                            decorator = decorator.func

                        if (
                            isinstance(decorator, Name)
                            and decorator.id != decorator_name
                        ):
                            raise WrongDecoratorSyntaxError(f'The @{decorator_name} decorator cannot be used in conjunction with other decorators.')
                        else:
                            if transfunction_decorator is not None:
                                raise DualUseOfDecoratorError(f"You cannot use the @{decorator_name} decorator twice for the same function.")
                            transfunction_decorator = decorator

                    node.decorator_list = []
                return node

        RewriteContexts().visit(tree)
        DeleteDecorator().visit(tree)

        function_def = cast(FunctionDef, tree.body[0])
        if not function_def.body:
            function_def.body.append(
                Pass(
                    col_offset=tree.body[0].col_offset,
                ),
            )

        if addictional_transformers is not None:
            for addictional_transformer in addictional_transformers:
                addictional_transformer.visit(tree)

        tree = self.wrap_ast_by_closures(tree)

        if version_info.minor > 10:
            increment_lineno(tree, n=(self.decorator_lineno - transfunction_decorator.lineno))
        else:
            increment_lineno(tree, n=(self.decorator_lineno - transfunction_decorator.lineno - 1))

        code = compile(tree, filename=getfile(self.function), mode='exec')
        namespace = UniversalNamespaceAroundFunction(self.function, self.frame)
        exec(code, namespace)
        function_factory = namespace['wrapper']
        result = function_factory()
        result = self.rewrite_globals_and_closure(result)
        result = wraps(self.function)(result)

        if self.base_object is not None:
            result = MethodType(
                result,
                self.base_object,
            )

        self.cache[context_name] = result

        return result  # type: ignore[no-any-return]

    def wrap_ast_by_closures(self, tree: Module) -> Module:
        old_functiondef = tree.body[0]

        tree.body[0] = FunctionDef(  # type: ignore[call-overload]
            name='wrapper',
            body=[Assign(targets=[Name(id=name, ctx=Store(), col_offset=0)], value=Constant(value=None, col_offset=0), col_offset=0) for name in self.function.__code__.co_freevars] + [
                old_functiondef,
                Return(value=Name(id=self.function.__name__, ctx=Load(), col_offset=0), col_offset=0),
            ],
            col_offset=0,
            args=arguments(
                posonlyargs=[],
                args=[],
                kwonlyargs=[],
                kw_defaults=[],
                defaults=[],
            ),
            decorator_list=[],
        )

        return tree


    def rewrite_globals_and_closure(self, function: FunctionType) -> FunctionType:
        # https://stackoverflow.com/a/13503277/14522393
        all_new_closure_names = set(self.function.__code__.co_freevars)

        if self.function.__closure__ is not None:
            old_function_closure_variables = {name: cell for name, cell in zip(self.function.__code__.co_freevars, self.function.__closure__)}
            filtered_closure = tuple([cell for name, cell in old_function_closure_variables.items() if name in all_new_closure_names])
            names = tuple([name for name, cell in old_function_closure_variables.items() if name in all_new_closure_names])
            new_code = function.__code__.replace(co_freevars=names)
        else:
            filtered_closure = None
            new_code = function.__code__

        new_function = FunctionType(
            new_code,
            self.function.__globals__,
            name=self.function.__name__,
            argdefs=self.function.__defaults__,
            closure=filtered_closure,
        )

        new_function = cast(FunctionType, update_wrapper(new_function, function))
        new_function.__kwdefaults__ = function.__kwdefaults__
        return new_function

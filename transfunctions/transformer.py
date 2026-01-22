import ast
from ast import (
    AST,
    Assign,
    AsyncFunctionDef,
    Await,
    Call,
    Constant,
    FunctionDef,
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
from typing import Any, Dict, Generic, List, Optional, Sequence, Set, Tuple, Union, cast, overload

from dill.source import getsource as dill_getsource  # type: ignore[import-untyped]

from transfunctions.errors import (
    AliasedDecoratorSyntaxError,
    CallTransfunctionDirectlyError,
    DualUseOfDecoratorError,
    WrongDecoratorSyntaxError,
    WrongMarkerSyntaxError,
)
from transfunctions.typing import Coroutine, Callable, Generator, FunctionParams, ReturnType
from transfunctions.universal_namespace import UniversalNamespaceAroundFunction


class FunctionTransformer(Generic[FunctionParams, ReturnType]):
    def __init__(
        self,
        function: Callable[FunctionParams, ReturnType],
        decorator_lineno: int,
        decorator_name: str,
        frame: FrameType,
        variants: Optional[Sequence[str]] = None,
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
        self.variants: Optional[Tuple[str, ...]] = tuple(variants) if variants is not None else None
        self.base_object = None
        self.cache: Dict[str, Callable] = {}

    def __call__(self, *args: Any, **kwargs: Any) -> None:
        raise CallTransfunctionDirectlyError("You can't call a transfunction object directly, create a function, a generator function or a coroutine function from it.")

    def __get__(self, base_object, type=None):
        self.base_object = base_object
        return self

    @staticmethod
    def is_lambda(function: Callable) -> bool:
        # https://stackoverflow.com/a/3655857/14522393
        lambda_example = lambda: 0  # noqa: E731
        return isinstance(function, type(lambda_example)) and function.__name__ == lambda_example.__name__

    def get_usual_function(self, addictional_transformers: Optional[List[NodeTransformer]] = None) -> Callable[FunctionParams, ReturnType]:
        return self.get_variant_function('sync', kind='sync', addictional_transformers=addictional_transformers)

    def get_async_function(self) -> Callable[FunctionParams, Coroutine[Any, Any, ReturnType]]:
        return self.get_variant_function('async', kind='async')

    def get_generator_function(self) -> Callable[FunctionParams, Generator[ReturnType, None, None]]:
        return self.get_variant_function('generator', kind='generator')

    def get_variants(self) -> Tuple[str, ...]:
        """
        Declared variants for this template (if provided in @transfunction(variants=[...])).
        """
        return self.variants if self.variants is not None else ()

    @overload
    def get_variant_function(
        self,
        variant: str,
        *,
        kind: str = ...,
        patches: Optional[Sequence[str]] = ...,
        addictional_transformers: Optional[List[NodeTransformer]] = ...,
    ) -> Callable[FunctionParams, ReturnType]: ...

    @overload
    def get_variant_function(
        self,
        variant: str,
        *,
        kind: str,
        patches: Optional[Sequence[str]] = ...,
        addictional_transformers: Optional[List[NodeTransformer]] = ...,
    ) -> Callable: ...

    def get_variant_function(
        self,
        variant: str,
        *,
        kind: str = 'sync',
        patches: Optional[Sequence[str]] = None,
        addictional_transformers: Optional[List[NodeTransformer]] = None,
    ) -> Callable:
        """
        Generate a function from the template by selecting a variant and optional patches.

        - variant blocks:
            with variant_context("trio"): ...
        - patch blocks (optional composition):
            with patch_context("logging"): ...
            with patch_context("metrics", variants=["async", "trio"]): ...

        Backward compatible:
            sync_context/async_context/generator_context are treated as variants: "sync"/"async"/"generator".

        kind defines the produced function type: "sync" | "async" | "generator".
        """
        if self.variants is not None and variant not in self.variants:
            raise ValueError(f'Unknown variant "{variant}". Declared variants are: {list(self.variants)}')

        enabled_patches: Set[str] = set(patches or ())
        cache_key = f'{kind}:{variant}:{";".join(sorted(enabled_patches))}'
        if cache_key in self.cache:
            return self.cache[cache_key]

        original_function = self.function

        class ConvertSyncFunctionToAsync(NodeTransformer):
            def visit_FunctionDef(self, node: FunctionDef) -> Optional[Union[AST, List[AST]]]:
                if node.name == original_function.__name__:
                    return AsyncFunctionDef(
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
            def visit_Call(self, node: Call) -> Optional[Union[AST, List[AST]]]:
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

        transforms: List[NodeTransformer] = []
        if kind == 'async':
            transforms.extend([ConvertSyncFunctionToAsync(), ExtractAwaitExpressions()])
        elif kind == 'generator':
            transforms.extend([ConvertYieldFroms()])
        elif kind != 'sync':
            raise ValueError('kind must be one of: "sync", "async", "generator".')

        if addictional_transformers is not None:
            transforms.extend(addictional_transformers)

        result = self._extract_by_variant_and_patches(variant=variant, enabled_patches=enabled_patches, addictional_transformers=transforms)
        self.cache[cache_key] = result
        return result

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


    def _extract_by_variant_and_patches(
        self,
        *,
        variant: str,
        enabled_patches: Set[str],
        addictional_transformers: Optional[List[NodeTransformer]] = None,
    ):
        try:
            source_code: str = getsource(self.function)
        except OSError:
            source_code = dill_getsource(self.function)

        converted_source_code = self.clear_spaces_from_source_code(source_code)
        tree = parse(converted_source_code)
        original_function = self.function
        transfunction_decorator = None
        decorator_name = self.decorator_name
        builtin_context_to_variant: Dict[str, str] = {
            'sync_context': 'sync',
            'async_context': 'async',
            'generator_context': 'generator',
        }

        def _extract_str_constant(node: AST, *, what: str) -> str:
            if isinstance(node, Constant) and isinstance(node.value, str):
                return node.value
            raise WrongMarkerSyntaxError(f'The "{what}" marker expects a string literal.')

        def _extract_str_sequence(node: AST, *, what: str) -> List[str]:
            if isinstance(node, (ast.List, ast.Tuple)):
                result: List[str] = []
                for elt in node.elts:
                    result.append(_extract_str_constant(elt, what=what))
                return result
            raise WrongMarkerSyntaxError(f'The "{what}" marker expects a list/tuple of string literals.')

        class RewriteContexts(NodeTransformer):
            def visit_With(self, node: With) -> Optional[Union[AST, List[AST]]]:
                self.generic_visit(node)
                if len(node.items) != 1:
                    return node

                item = node.items[0]
                context_expr = item.context_expr

                # Backward-compatible builtin markers: sync_context / async_context / generator_context
                if isinstance(context_expr, Name) and context_expr.id in builtin_context_to_variant:
                    marker_variant = builtin_context_to_variant[context_expr.id]
                    return cast(List[AST], node.body) if marker_variant == variant else None
                if isinstance(context_expr, Call) and isinstance(context_expr.func, ast.Name) and context_expr.func.id in builtin_context_to_variant:
                    # Historically treated as a marker too (even though it's not callable at runtime).
                    marker_variant = builtin_context_to_variant[context_expr.func.id]
                    return cast(List[AST], node.body) if marker_variant == variant else None

                # New variant marker: with variant_context("name"):
                if isinstance(context_expr, Call) and isinstance(context_expr.func, ast.Name) and context_expr.func.id == 'variant_context':
                    if len(context_expr.args) != 1 or context_expr.keywords:
                        raise WrongMarkerSyntaxError('The "variant_context" marker can be used with only one positional string argument.')
                    marker_variant = _extract_str_constant(context_expr.args[0], what='variant_context')
                    return cast(List[AST], node.body) if marker_variant == variant else None

                # New patch marker: with patch_context("name", variants=[...])
                if isinstance(context_expr, Call) and isinstance(context_expr.func, ast.Name) and context_expr.func.id == 'patch_context':
                    if len(context_expr.args) != 1:
                        raise WrongMarkerSyntaxError('The "patch_context" marker requires exactly one positional string argument (patch name).')

                    patch_name = _extract_str_constant(context_expr.args[0], what='patch_context')
                    allowed_variants: Optional[List[str]] = None

                    for kw in context_expr.keywords:
                        if kw.arg != 'variants':
                            raise WrongMarkerSyntaxError('The "patch_context" marker supports only the "variants" keyword argument.')
                        if kw.value is None or (isinstance(kw.value, Constant) and kw.value.value is None):
                            allowed_variants = None
                        else:
                            allowed_variants = _extract_str_sequence(kw.value, what='patch_context.variants')

                    if patch_name not in enabled_patches:
                        return None
                    if allowed_variants is not None and variant not in allowed_variants:
                        return None
                    return cast(List[AST], node.body)

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
                                raise DualUseOfDecoratorError(f"You cannot use the '{decorator_name}' decorator twice for the same function.")
                            transfunction_decorator = decorator

                    node.decorator_list = []
                return node

        RewriteContexts().visit(tree)
        DeleteDecorator().visit(tree)

        if transfunction_decorator is None:
            raise AliasedDecoratorSyntaxError(
                "The transfunction decorator must have been renamed."
            )

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

        return result

    def wrap_ast_by_closures(self, tree):
        old_functiondef = tree.body[0]

        tree.body[0] = FunctionDef(
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


    def rewrite_globals_and_closure(self, function):
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

        new_function = update_wrapper(new_function, function)
        new_function.__kwdefaults__ = function.__kwdefaults__
        return new_function

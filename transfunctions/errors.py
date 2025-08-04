class CallTransfunctionDirectlyError(NotImplementedError):
    pass


class DualUseOfDecoratorError(SyntaxError):
    pass


class WrongDecoratorSyntaxError(SyntaxError):
    pass


class WrongMarkerSyntaxError(SyntaxError):
    pass


class WrongTransfunctionSyntaxError(SyntaxError):
    pass


# TODO: we can later make this non-error, by identifying the name of decorator at call site
class AliasedDecoratorSyntaxError(SyntaxError):
    pass

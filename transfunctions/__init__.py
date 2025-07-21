from transfunctions.decorators.transfunction import transfunction as transfunction
from transfunctions.decorators.superfunction import superfunction as superfunction

from transfunctions.markers import (
    async_context as async_context,
    sync_context as sync_context,
    generator_context as generator_context,
    await_it as await_it,
)

from transfunctions.errors import (
    CallTransfunctionDirectlyError as CallTransfunctionDirectlyError,
    DualUseOfDecoratorError as DualUseOfDecoratorError,
    WrongDecoratorSyntaxError as WrongDecoratorSyntaxError,
    WrongTransfunctionSyntaxError as WrongTransfunctionSyntaxError,
)

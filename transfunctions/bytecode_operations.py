from types import FunctionType, CodeType
from typing import Callable, Optional

import dis
from threading import Lock


class ByteCodeOperation:
    def __init__(self, operation_bytes: bytes, have_argument: bool) -> None:
        self.code = operation_bytes[0]
        self.name = dis.opname[self.code]
        self.bytes = operation_bytes
        self.have_argument = have_argument
        self.size = len(self.bytes)
        self.argument = operation_bytes[1:] if have_argument else None

    def __repr__(self) -> str:
        return f'{type(self).__name__}(operation_bytes={repr(self.bytes)}, have_argument={repr(self.have_argument)})'

    def __str__(self) -> str:
        about_arguments = 'no arguments' if not self.have_argument else 'arguments'
        return f'<Operation "{self.name}" with {about_arguments}, lenth {self.size}>'


class ByteCodeOperator:
    def __init__(self, bytecode: bytes) -> None:
        self.lock = Lock()
        self.bytecode = bytecode
        self.operations = []
        index = 0

        # https://habr.com/ru/articles/140356/
        while index < len(bytecode):
            operation_code = bytecode[index]

            have_argument = operation_code >= dis.HAVE_ARGUMENT
            if have_argument:
                offset = 3
            else:
                offset = 1

            operation = ByteCodeOperation(bytecode[index:index+offset], have_argument)
            self.operations.append(operation)

            index += offset

    def __repr__(self) -> str:
        return f'{type(self).__name__}({repr(self.bytecode)})'

    def __str__(self) -> str:
        operations_representations = []

        cache_operation_number = 0
        for operation in self.operations:
            if operation.name == 'CACHE':
                cache_operation_number += 1
                if cache_operation_number == 1:
                    operations_representations.append('...')
            else:
                if operation.have_argument:
                    operations_representations.append(f'{operation.name} (with arguments)')
                else:
                    operations_representations.append(operation.name)

        full_operations_representation = ', '.join(operations_representations)

        return f'<Bytecode operation object with operations: {full_operations_representation}>'

    def replace_operation(self, recognize_operation: Callable[[ByteCodeOperation], bool], replace_operation: Callable[[ByteCodeOperation], Optional[ByteCodeOperation]]) -> None:
        new_operations = []

        for operation in self.operations:
            if recognize_operation(operation):
                new_operation = replace_operation(operation)
                if new_operation is not None:
                    new_operations.append(new_operation)
            else:
                new_operations.append(operation)

        with self.lock:
            self.operations = new_operations

    def get_bytes(self) -> bytes:
        return b''.join([x.bytes for x in self.operations])

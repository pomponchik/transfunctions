from contextlib import contextmanager


@contextmanager
def create_async_context():
    yield

@contextmanager
def create_sync_context():
    yield

@contextmanager
def create_generator_context():
    yield


async_context = create_async_context()
sync_context = create_sync_context()
generator_context = create_generator_context()

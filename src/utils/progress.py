"""Avance desde workers, sin referencias a widgets de Tk."""
from contextlib import contextmanager
from contextvars import ContextVar

_reporter = ContextVar('job_progress', default=None)


def report_progress(done=0, total=None, message='Procesando…'):
    callback = _reporter.get()
    if callback:
        callback(done, total, message)


@contextmanager
def progress_reporter(callback):
    token = _reporter.set(callback)
    try:
        yield
    finally:
        _reporter.reset(token)


@contextmanager
def progress_range(start, end, total, label=''):
    parent = _reporter.get()
    highest = 0
    def mapped(done, count, message):
        nonlocal highest
        fraction = max(0, min(1, done / count)) if count else highest
        highest = max(highest, fraction)
        if parent:
            parent(start + (end - start) * highest, total, f'{label} · {message}' if label else message)
    with progress_reporter(mapped):
        yield

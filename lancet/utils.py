import functools
import sys
import curses
import click


def cached_property(*args, **kwargs):
    return property(functools.lru_cache()(*args, **kwargs))


class PrintTaskStatus:
    _active_tasks = []

    def __init__(self, msg, *args, **kwargs):
        self.setup()
        self._done = False
        self.msg = msg.format(*args, **kwargs)

    @classmethod
    def setup(cls):
        if getattr(cls, '_setup', False):
            return
        curses.setupterm()
        cls.BOL = curses.tigetstr('cr')
        cls.CLEAR_EOL = curses.tigetstr('el')
        cls._setup = True

    @classmethod
    def clear_line(cls):
        sys.stdout.buffer.write(cls.BOL + cls.CLEAR_EOL)

    def __enter__(self):
        PrintTaskStatus._active_tasks.append(self)
        msg = ' {}  {}...'.format(
            click.style('*', fg='yellow', blink=True), self.msg)
        click.echo(msg, nl=False)
        return self

    def __exit__(self, type, value, tb):
        PrintTaskStatus._active_tasks.pop()
        if not self._done:
            self.clear_line()

    def ok(self, msg, *args, **kwargs):
        self.clear_line()
        msg = msg.format(*args, **kwargs)
        click.echo(' {}  {}'.format(click.style('✓', fg='green'), msg))
        self._done = True

    def fail(self, msg, *args, **kwargs):
        self.clear_line()
        abort = kwargs.pop('abort', False)
        msg = msg.format(*args, **kwargs)
        if abort:
            msg += ', aborting'
        click.echo(' {}  {}'.format(click.style('✗', fg='red'), msg))
        self._done = True
        if abort:
            sys.exit(1)

    @classmethod
    def suspend(cls):
        return SuspendTask(cls._active_tasks)


class SuspendTask:
    def __init__(self, stack):
        self.stack = stack

    def __enter__(self):
        if self.stack:
            task = self.stack[-1]
            if not task._done:
                task.clear_line()

    def __exit__(self, type, value, tb):
        if self.stack:
            task = self.stack.pop()
            if not task._done:
                task.__enter__()

taskstatus = PrintTaskStatus

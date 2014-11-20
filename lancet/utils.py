import functools
import sys
import curses
import click


def cached_property(*args, **kwargs):
    return property(functools.lru_cache()(*args, **kwargs))


class PrintTaskStatus:
    def __init__(self, msg):
        self.setup()
        self._done = False
        self.msg = msg

    @classmethod
    def setup(cls):
        if getattr(cls, '_setup', False):
            return
        curses.setupterm()
        cls.BOL = curses.tigetstr('cr')
        cls.CLEAR_EOL = curses.tigetstr('el')
        cls._setup = True

    def clear_line(self):
        sys.stdout.buffer.write(self.BOL + self.CLEAR_EOL)

    def __enter__(self):
        msg = ' {}  {}...'.format(
            click.style('*', fg='yellow', blink=True), self.msg)
        click.echo(msg, nl=False)
        return self

    def __exit__(self, type, value, tb):
        if not self._done:
            self.clear_line()

    def ok(self, msg):
        self.clear_line()
        click.echo(' {}  {}'.format(click.style('✓', fg='green'), msg))
        self._done = True

    def fail(self, msg, abort=False):
        self.clear_line()
        if abort:
            msg += ', aborting'
        click.echo(' {}  {}'.format(click.style('✗', fg='red'), msg))
        self._done = True
        if abort:
            sys.exit(1)

taskstatus = PrintTaskStatus

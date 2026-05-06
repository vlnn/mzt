from typing import TextIO

from mzt.repl import Repl, ReplExit, run_line


def run_interactive(
    repl: Repl,
    *,
    stdin: TextIO,
    stdout: TextIO,
    prompt: str = "mzt> ",
) -> None:
    while True:
        stdout.write(prompt)
        stdout.flush()
        line = stdin.readline()
        if not line:
            return
        try:
            output = run_line(repl, line)
        except ReplExit:
            return
        if output:
            if not output.endswith("\n"):
                output += "\n"
            stdout.write(output)
            stdout.flush()

"""The `voxx` command. Never imports an inference library: synthesis runs in the worker (ADR 0002)."""

import argparse
import sys
import traceback

from voxx.output import BUG_HINT, INTERNAL, OK, USAGE, VoxxError, print_error, print_result

ARGS_HINT = "Run `voxx schema` to see every command's arguments."


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise VoxxError("invalid_arguments", message, ARGS_HINT, {}, USAGE)


def _parser():
    # No --help: stdout carries only JSON, and `voxx schema` describes every command.
    parser = _Parser(prog="voxx", add_help=False)
    commands = parser.add_subparsers(dest="command", required=True, parser_class=_Parser)
    narrate = commands.add_parser("narrate", add_help=False)
    narrate.add_argument("narration")
    narrate.add_argument("--out", required=True)
    schema = commands.add_parser("schema", add_help=False)
    schema.add_argument("name", nargs="?")
    return parser


def main(argv=None):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    try:
        args = _parser().parse_args(argv)
        if args.command == "narrate":
            from voxx.narrate import narrate
            data = narrate(args.narration, args.out)
        else:
            from voxx.schema import schema
            data = schema(args.name)
        print_result(data)
    except VoxxError as e:
        print_error(e)
        return e.exit_code
    except Exception as e:
        print_error(VoxxError("internal_error", f"{type(e).__name__}: {e}", BUG_HINT, {"traceback": traceback.format_exc()}, INTERNAL))
        return INTERNAL
    return OK

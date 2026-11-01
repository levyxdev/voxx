"""The `voxx` command. Never imports an inference library: synthesis runs in the worker (ADR 0002)."""

import argparse
import io
import sys
import traceback
from typing import cast

from voxx.models import CAPABILITIES, list_models
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
    narrate.add_argument("--model")
    narrate.add_argument("--line", dest="lines", action="append", default=[])
    narrate.add_argument("--voices-dir")
    models = commands.add_parser("models", add_help=False)
    models.add_argument("--capability", choices=CAPABILITIES)
    installed = models.add_mutually_exclusive_group()
    installed.add_argument("--installed", dest="installed", action="store_const", const=True)
    installed.add_argument("--not-installed", dest="installed", action="store_const", const=False)
    commands.add_parser("voices", add_help=False).add_argument("--voices-dir")
    voice = commands.add_parser("voice", add_help=False).add_subparsers(dest="voice_command", required=True,
                                                                         parser_class=_Parser)
    add = voice.add_parser("add", add_help=False)
    add.add_argument("name")
    add.add_argument("--ref", required=True)
    add.add_argument("--ref-text")
    add.add_argument("--model")
    add.add_argument("--voices-dir")
    add.add_argument("--overwrite", action="store_true")
    install = commands.add_parser("install", add_help=False)
    install.add_argument("model")
    commands.add_parser("doctor", add_help=False)
    schema = commands.add_parser("schema", add_help=False)
    # Words, so `voxx schema voice add` names a command of two.
    schema.add_argument("name", nargs="*")
    return parser


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        cast(io.TextIOWrapper, stream).reconfigure(encoding="utf-8")
    try:
        args = _parser().parse_args(argv)
        if args.command == "narrate":
            from voxx.narrate import narrate
            data = narrate(args.narration, args.out, args.model, args.lines, args.voices_dir)
        elif args.command == "install":
            from voxx.install import install
            data = install(args.model)
        elif args.command == "doctor":
            from voxx.doctor import doctor
            data = doctor()
        elif args.command == "models":
            data = list_models(args.capability, args.installed)
        elif args.command == "voices":
            from voxx.voices import list_voices
            data = list_voices(args.voices_dir)
        elif args.command == "voice":
            from voxx.voices import add_voice
            data = add_voice(args.name, args.ref, args.ref_text, args.model, args.voices_dir, args.overwrite)
        else:
            from voxx.schema import schema
            data = schema(" ".join(args.name) or None)
        print_result(data)
    except VoxxError as e:
        print_error(e)
        return e.exit_code
    except KeyboardInterrupt:
        print_error(VoxxError("interrupted", "voxx was interrupted.", "Run the command again.", {}, INTERNAL))
        return INTERNAL
    except Exception as e:
        print_error(VoxxError("internal_error", f"{type(e).__name__}: {e}", BUG_HINT, {"traceback": traceback.format_exc()}, INTERNAL))
        return INTERNAL
    return OK

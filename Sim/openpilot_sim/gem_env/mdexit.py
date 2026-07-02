"""Clean shutdown for MetaDrive scripts on macOS.

MetaDrive/Panda3D segfaults in its atexit C++ destructor on Apple Silicon: a Bullet
physics CallbackObject destructor calls PyGILState_Ensure while the interpreter is
already tearing down, hitting a null threadstate -> SIGSEGV. It's cosmetic (fires
AFTER the sim has done its work) but produces a crash dialog and a nonzero exit.

Call clean_exit() at the end of any script that opened a MetaDrive env: flush output,
then skip Python finalizers so the buggy destructor never runs.
"""
import os
import sys


def clean_exit(env=None, code: int = 0):
    if env is not None:
        try:
            env.close()
        except Exception:
            pass
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(code)

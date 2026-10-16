import copy
import json
import os

from config import DEFAULT_SAVE, SAVE_FILE

PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), SAVE_FILE)


def merge(base, data):
    out = copy.deepcopy(base)
    for k, v in data.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = merge(out[k], v) if out[k] else dict(v)
        elif k in out:
            out[k] = v
    return out


def load():
    try:
        with open(PATH, "r", encoding="utf-8") as f:
            return merge(DEFAULT_SAVE, json.load(f))
    except (OSError, ValueError):
        return copy.deepcopy(DEFAULT_SAVE)


def store(data):
    try:
        with open(PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except OSError:
        pass

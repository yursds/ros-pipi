"""Utility to load Helix robot connection config."""

import os
import yaml
from pathlib import Path

DEFAULT_HOST = '192.168.238.104'
DEFAULT_PORT = 9090
CONFIG_FILENAME = 'helix_config.yaml'


def _find_config() -> Path | None:
    """Search for the config file in known locations.

    Order of precedence:
      1. HELIX_CONFIG env var
      2. src/config/helix_config.yaml (from CWD — works in container)
      3. ../config/helix_config.yaml (relative to this file's package)
    """
    env_path = os.environ.get('HELIX_CONFIG')
    if env_path:
        p = Path(env_path)
        if p.exists():
            return p

    candidates = [
        Path.cwd() / 'src' / 'config' / CONFIG_FILENAME,
        Path(__file__).resolve().parent.parent.parent.parent / 'config' / CONFIG_FILENAME,
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


def load_config() -> dict:
    """Load helix connection config, returning dict with 'host' and 'port' keys.

    Falls back to defaults if no config file is found.
    """
    cfg_path = _find_config()
    if cfg_path is None:
        return {'host': DEFAULT_HOST, 'port': DEFAULT_PORT}

    with open(cfg_path) as f:
        data = yaml.safe_load(f) or {}

    return {
        'host': data.get('host', DEFAULT_HOST),
        'port': data.get('port', DEFAULT_PORT),
    }

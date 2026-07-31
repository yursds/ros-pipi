"""Utility to load Helix robot connection config."""

import os
import yaml
from pathlib import Path

CONFIG_FILENAME = 'helix_config.yaml'

_CONFIG_HINT = (
    '    host: <robot-ip>\n'
    '    port: <rosbridge-port>\n'
    'e.g.:\n'
    '    host: 192.168.238.104\n'
    '    port: 9090')


class ConfigError(Exception):
    """Raised when the robot config file is missing or incomplete."""


def _find_config() -> Path | None:
    """Search for the config file in known locations.

    Order of precedence:
      1. HELIX_CONFIG env var
      2. src/config/helix_config.yaml (from CWD - works in container)
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
    """Load helix connection config as {'host': str, 'port': int}.

    Raises ConfigError when no config file is found or when host/port are
    missing or empty: the robot address is intentionally NOT defaulted, so
    every user must set it explicitly at first setup.
    """
    cfg_path = _find_config()
    if cfg_path is None:
        raise ConfigError(
            f'{CONFIG_FILENAME} not found. Create it with:\n'
            f'{_CONFIG_HINT}\n'
            'Search paths: HELIX_CONFIG env var, src/config/helix_config.yaml '
            '(relative to CWD), or ../config/ relative to the package.')

    with open(cfg_path) as f:
        data = yaml.safe_load(f) or {}

    missing = [k for k in ('host', 'port') if not data.get(k)]
    if missing:
        raise ConfigError(
            f'{cfg_path} is missing required key(s): {", ".join(missing)}.\n'
            f'Add them:\n{_CONFIG_HINT}')

    return {'host': str(data['host']), 'port': int(data['port'])}

"""Shared helpers for the MCP property tests."""

import json

from tests._support import SCRIPTS
from harness_validator import envfile, mcp, secrets

CONFIG = secrets.load_validator_config(SCRIPTS / "validator-config.json")
PATH = ".kiro/settings/mcp.json"


def entry(**overrides):
    base = {"command": "uvx", "args": ["some-mcp-server@1.0.0"], "disabled": False}
    base.update(overrides)
    return base


def check(servers, env_text=None):
    env = envfile.parse_env_example(env_text) if env_text is not None else None
    return mcp.check_mcp(PATH, json.dumps({"mcpServers": servers}), env, CONFIG)


def by_rule(findings, rule):
    return [f for f in findings if f.rule == rule]

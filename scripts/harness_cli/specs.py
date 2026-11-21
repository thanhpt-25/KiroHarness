"""``harness new-spec``: a skeleton spec that passes the Spec_Linter (agent-harness-platform R13.5)."""

from __future__ import annotations

import json
import os
import re
import uuid

NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")

REQUIREMENTS = """# Requirements Document

## Introduction

Describe the feature in two or three sentences: who needs it and why.

## Glossary

- **{title}**: The feature described by this spec. Add one entry per domain term.

## Requirements

### Requirement 1: {title}

**User Story:** As a user, I want the feature, so that I get its benefit.

#### Acceptance Criteria

1. THE {title} SHALL do the first thing the user needs.
"""

DESIGN = """# Design Document: {title}

## Overview

Summarize the approach in one paragraph.

## Architecture

Describe the main parts and how they connect.

## Components and Interfaces

List each component with its inputs and outputs.

## Data Models

Describe the data the feature stores or passes around.

## Error Handling

List each failure and what the feature does about it.

## Testing Strategy

Say which tests cover which criteria. Tag each test with `# Validates: {name}/R<n>.<m>`.
"""

TASKS = """# Implementation Plan

- [ ] 1. Implement the first criterion
  - Write the test first, then the code
  - _Requirements: 1.1_
"""


def create(root, name: str) -> tuple:
    """Create the spec. Return ``(exit code, message)``."""
    if not NAME_RE.match(name):
        return 2, f"invalid spec name {name!r}: use lowercase letters, digits and hyphens"
    directory = os.path.join(root, ".kiro", "specs", name)
    if os.path.exists(directory):
        return 1, f"{directory} already exists; nothing was written"
    title = name.replace("-", " ").title().replace(" ", "_")
    os.makedirs(directory)
    for filename, template in (("requirements.md", REQUIREMENTS), ("design.md", DESIGN), ("tasks.md", TASKS)):
        with open(os.path.join(directory, filename), "w", encoding="utf-8", newline="") as handle:
            handle.write(template.format(title=title, name=name))
    config = {"specId": str(uuid.uuid4()), "workflowType": "requirements-first", "specType": "feature"}
    with open(os.path.join(directory, ".config.kiro"), "w", encoding="utf-8", newline="") as handle:
        handle.write(json.dumps(config) + "\n")
    return 0, f"created {directory}"

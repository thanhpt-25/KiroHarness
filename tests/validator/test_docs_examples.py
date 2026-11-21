"""Examples in docs/CUSTOMIZING.md validate with zero errors (Requirement 13.11).

Each fenced block whose info string has ``example=<kind> path=<path>`` is
copied into a temporary Template copy. ``merge=mcpServers`` adds the entries
to the MCP_Config; ``merge=append`` appends to the file. Every ``merge=append``
block is applied to each copy, because the MCP example needs its
``.env.example`` lines.
"""
# Validates: kiro-agent-harness-template/R13.11

import json
import re
import unittest

from tests._support import ROOT, TemplateCopy, detail, errors, validate

FENCE_RE = re.compile(r"^```(\S*)([^\n]*)\n(.*?)^```\s*$", re.M | re.S)


def doc_examples(text=None):
    text = text if text is not None else (ROOT / "docs/CUSTOMIZING.md").read_text(encoding="utf-8")
    examples = []
    for match in FENCE_RE.finditer(text):
        attrs = dict(re.findall(r"(\w+)=(\S+)", match.group(2)))
        if "example" in attrs:
            examples.append((attrs, match.group(3)))
    return examples


def apply(root, attrs, body):
    target = root / attrs["path"]
    target.parent.mkdir(parents=True, exist_ok=True)
    merge = attrs.get("merge")
    if merge == "mcpServers":
        data = json.loads(target.read_text(encoding="utf-8")) if target.exists() else {"mcpServers": {}}
        data["mcpServers"].update(json.loads(body))
        target.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    elif merge == "append":
        existing = target.read_text(encoding="utf-8") if target.exists() else ""
        target.write_text(existing.rstrip("\n") + "\n\n" + body, encoding="utf-8")
    else:
        target.write_text(body, encoding="utf-8")


class DocsExamples(unittest.TestCase):
    def test_docs_have_examples_of_each_kind(self):
        kinds = {attrs["example"] for attrs, _ in doc_examples()}
        self.assertTrue({"steering", "hook", "mcp-server", "env"} <= kinds, kinds)

    def test_each_example_validates_with_zero_errors(self):
        examples = doc_examples()
        appends = [(a, b) for a, b in examples if a.get("merge") == "append"]
        for attrs, body in examples:
            if attrs.get("merge") == "append":
                continue
            with self.subTest(example=attrs["path"]), TemplateCopy() as root:
                for append_attrs, append_body in appends:
                    apply(root, append_attrs, append_body)
                apply(root, attrs, body)
                found = errors(validate(root)[0])
                self.assertEqual(found, [], detail(attrs, "0 errors", found))


if __name__ == "__main__":
    unittest.main()

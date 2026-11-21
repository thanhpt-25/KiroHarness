# Tutorial: install the Harness and see a guard block a command

This takes about ten minutes and needs Python 3.10 or newer and `sh`. You will install the Harness into a repository, check it, and watch a guard refuse a destructive command.

1. Check your machine: `scripts/harness doctor` in a checkout of the Harness. It should list `sh` and Python as found and end without an error.
2. Install into your own repository, enabling the Agents you use:

   ```sh
   scripts/harness init ../my-project --agents kiro,claude-code
   ```

   The command copies the Harness, writes `harness/manifest.json` with only your Agents, generates the Agent files, and runs the Config_Validator. It stops without changes if files already exist, unless you pass `--force`.
3. In `../my-project`, run `scripts/validate.sh`. It must print `0 errors` for the validator.
4. Try a guard by hand. The guard reads one hook payload on standard input:

   ```sh
   echo '{"hook_event_name":"PreToolUse","tool_name":"Bash","tool_input":{"command":"git push --force"}}' \
     | harness/bin/guard claude-code pre_tool; echo "exit=$?"
   ```

   Exit 2 and a message on standard error mean the call was blocked.
5. Fill in the placeholders listed in `README.md` under `## Placeholders`, then run `scripts/harness sync` and `scripts/validate.sh` again.

Next: [Install and upgrade](../how-to/install-and-upgrade.md), [Enable another Agent](../how-to/enable-an-agent.md), and [why the guards are a safety net, not a sandbox](../explanation/limits-and-threat-model.md).

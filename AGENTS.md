# AWS Cloud Cost Agent Instructions

These instructions apply to everything under this folder.

## Purpose

This project is a standalone Python OpenAI Agents SDK agent for AWS cloud cost analysis. It calls AWS APIs, identifies cost drivers, spawns specialist sub-agents for top services/SKUs, proposes reduction ideas, and stages future remediation plans.

The current implementation is read-only against AWS. It can call AWS Cost Explorer and STS APIs, but it must not mutate AWS resources.

## Safety Rules

1. Do not add mutating AWS API calls unless the owner explicitly asks for a specific change path.
2. Any future mutating tool must require all of the following:
   - The CLI is run with an explicit apply mode.
   - `AWS_COST_AGENT_ENABLE_MUTATIONS=true` is set.
   - The input contains exact account, region, service, resource IDs, rollback steps, and validation steps.
   - The tool records what it is about to do before it sends the AWS API request.
3. Never commit AWS credentials, OpenAI keys, `.env*` files, credential exports, profiles, or generated reports containing account-sensitive data.
4. Prefer read-only AWS IAM permissions for analysis runs. Add narrow service-specific write permissions only when implementing an approved mutating tool.
5. Treat dollar amounts and forecasts as decision support, not guaranteed savings. Include assumptions and validation checks in recommendations.
6. Keep `tools/tools.md` aligned with implemented tools. If the agent needs an unavailable AWS API, it must propose it in `tools/proposed_tools.md`.
7. Generated Markdown assessments belong under `assessment/`.
8. Candidate change actions belong under `optmization_script/considered_actions.py`. Keep this folder spelling because it is part of the requested interface.

## Code Conventions

1. Use Python only in this project.
2. Use the OpenAI Agents SDK `Agent`, `Runner`, web search, sub-agent tools, and function tools for agent orchestration.
3. Keep dependencies lean and justified in `README.md`.
4. Keep AWS wrappers small and service-specific. Avoid generic AWS command execution helpers for mutating calls.
5. Use type hints for public functions and clear docstrings for tools.

## Verification

Before committing or sharing changes:

```bash
python -m compileall aws_cloud_cost_agent
```

If dependencies and credentials are available, run a read-only smoke test:

```bash
python -m aws_cloud_cost_agent --start YYYY-MM-DD --end YYYY-MM-DD
```

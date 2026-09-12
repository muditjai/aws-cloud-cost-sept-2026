# AWS Cloud Cost Agent Instructions

These instructions apply to everything under this folder.

## Purpose

This project is a standalone Python OpenAI Agents SDK workflow for AWS cloud cost analysis. It runs focused steps for connection validation, overall billing, service/SKU analysis, and recommendations.

The current implementation is read-only against AWS. It can call AWS Cost Explorer and STS APIs, but it must not mutate AWS resources.

## Safety Rules

1. Do not add mutating AWS API calls unless the owner explicitly asks for a specific change path.
2. Never commit AWS credentials, OpenAI keys, `.env*` files, credential exports, profiles, or generated reports containing account-sensitive data.
3. Use read-only AWS IAM permissions for analysis runs.
4. Treat estimates as decision support, not guaranteed savings. Include assumptions and validation checks.
5. Keep `aws_cloud_cost_agent/tools/tools.md` aligned with implemented tools.
6. Record unavailable tool capabilities in `aws_cloud_cost_agent/tools/proposed_tools.md`.
7. Generated Markdown belongs under `output_artifact/`.

## Code Conventions

1. Use Python only in this project.
2. Keep CLI options limited to account information, dates, and workflow steps.
3. Keep each step prompt beside the corresponding Python tool module.
4. Use one independently rendered prompt per service/SKU analysis and recommendation.
5. Keep dependencies lean and justified in `README.md`.
6. Keep AWS wrappers small and service-specific.
7. Use type hints for public functions and clear docstrings for tools.

## Verification

Before committing or sharing changes:

```bash
python -m compileall aws_cloud_cost_agent
```

If dependencies and credentials are available, run a read-only smoke test:

```bash
python -m aws_cloud_cost_agent --start YYYY-MM-DD --end YYYY-MM-DD
```

# Implemented tools

## Authentication

- `get_account_identity`: calls AWS STS to confirm the active account and IAM principal.
- `auth/connection_check_prompt.md` documents the local report contract; this stage does not contact OpenAI.

## Bill reading

- `get_bill_data`: reads monthly unblended Cost Explorer data grouped by requested dimensions.
- Prompt: `bill_read/overall_bill_prompt.md`.

## Service/SKU cost analysis

- `get_top_service_skus`: finds the five highest-cost service and usage-type pairs.
- `get_service_sku_breakdown`: breaks one service down by usage type, operation, and region.
- Prompt: `cost_analysis/service_sku_analysis_prompt.md`; it is rendered and run separately for every selected service/SKU.

## Cost recommendations

- `get_ec2_rightsizing_recommendations`: reads EC2 rightsizing recommendations.
- `get_savings_plan_recommendations`: reads one-year Compute Savings Plan recommendations.
- Prompt: `cost_recommendation/service_sku_recommendation_prompt.md`; it is rendered and run separately for every selected service/SKU.

## Tool management

- `read_tools_registry`: reads this file.
- `propose_missing_tool`: appends unavailable capabilities to `proposed_tools.md`.

# Implemented tools

## Authentication

- `get_account_identity`: calls AWS STS to confirm the active account and IAM principal.
- `auth/connection_check_prompt.md` documents the local report contract; this stage does not contact OpenAI.

## Bill reading

- `get_bill_data`: reads monthly unblended Cost Explorer data grouped by requested dimensions.
- `bill_read/overall_bill_prompt.md` documents the deterministic local report contract; this stage does not contact OpenAI.

## Service/SKU cost analysis

- `get_top_service_skus`: finds the five highest-cost service and usage-type pairs.
- `get_service_sku_breakdown`: breaks one service down by usage type, operation, and region.
- Prompt: `cost_analysis/service_sku_analysis_prompt.md`; it is rendered and run separately for every selected service/SKU.

### Elastic Load Balancing

- `get_elb_component_costs`: returns exact ELB costs by usage type, operation, and region.
- `get_elb_resource_costs`: attempts opt-in daily resource-level ELB costs for AWS's available 14-day window.
- `get_elb_inventory`: lists Classic, Application, Network, and Gateway load balancers plus listeners, target groups, and targets in regions with ELB spend.
- `get_elb_utilization`: reads per-load-balancer CloudWatch traffic and LCU billing metrics for explicitly estimated dollar attribution.
- `get_elb_cost_attribution`: deterministically estimates transfer and LCU dollars per load balancer while leaving unsupported fixed-cost allocation explicit.
- Prompt: `cost_analysis/elb_analysis_prompt.md`.

### Amazon RDS

- `get_rds_component_costs`: returns exact RDS costs by usage type, operation, and region.
- `get_rds_resource_costs`: attempts opt-in resource-level RDS costs.
- `get_rds_inventory`: lists database instances, clusters, sizing, storage, and serverless settings.
- `get_rds_utilization`: reads CPU, connection, memory, and Aurora Serverless capacity metrics.
- `get_rds_cost_attribution`: estimates instance-class, GP3 storage, and Aurora Serverless v2 dollars by current DB instance.
- Prompt: `cost_analysis/rds_analysis_prompt.md`.

### Amazon CloudFront

- `get_cloudfront_component_costs`: returns exact CloudFront costs by usage type, operation, and region.
- `get_cloudfront_resource_costs`: attempts opt-in resource-level CloudFront costs.
- `get_cloudfront_inventory`: lists distributions, origins, cache settings, compression, and price class.
- `get_cloudfront_utilization`: reads requests, transfer, cache-hit, and error metrics by distribution.
- `get_cloudfront_cost_attribution`: estimates request and transfer dollars by distribution using metric shares.
- Prompt: `cost_analysis/cloudfront_analysis_prompt.md`.

## Cost recommendations

- `get_ec2_rightsizing_recommendations`: reads EC2 rightsizing recommendations.
- `get_savings_plan_recommendations`: reads one-year Compute Savings Plan recommendations.
- Prompt: `cost_recommendation/service_sku_recommendation_prompt.md`; it is rendered and run separately for every selected service/SKU.

## Tool management

- `read_tools_registry`: reads this file.
- `propose_missing_tool`: appends unavailable capabilities to `proposed_tools.md`.

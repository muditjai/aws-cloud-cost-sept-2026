# Proposed tools

The agent appends missing AWS API capabilities here when the implemented tools cannot complete an analysis.

## get_rds_serverless_v2_recommendations

- Reason: RDS inventory, capacity metrics, and estimated cost attribution are implemented, but the agent does not have a deterministic tool for modeling Aurora Serverless v2 minimum/maximum ACU changes or provisioned alternatives.
- AWS APIs: RDS DescribeDBClusters, RDS DescribeDBInstances, CloudWatch GetMetricData, Pricing GetProducts

## get_cloudfront_cost_optimization_recommendations

- Reason: The implemented recommendation tools cover EC2 rightsizing and Compute Savings Plans but do not provide CloudFront-native recommendations for request-cost optimization, cache-policy/TTL changes, price-class selection, or CloudFront security/WAF request reduction.
- AWS APIs: AWS Cost Explorer GetCostAndUsage, AWS CloudFront ListDistributions, AWS CloudFront GetDistributionConfig, AWS CloudFront ListCachePolicies, AWS CloudFront ListOriginRequestPolicies, AWS CloudFront ListResponseHeadersPolicies, AWS CloudFront ListCloudFrontOriginAccessIdentities, AWS CloudFront ListKeyGroups, AWS CloudFront ListPublicKeys, AWS CloudFront ListContinuousDeploymentPolicies, AWS CloudWatch GetMetricData, AWS WAFv2 ListWebACLs, AWS WAFv2 GetWebACL, AWS CloudFront ListInvalidations

## get_public_ipv4_resource_inventory_and_usage

- Reason: The available service breakdown identifies public IPv4 charges by operation and region but cannot map individual addresses to resources, allocation state, lifecycle duration, or owner tags.
- AWS APIs: EC2 DescribeAddresses, EC2 DescribeNetworkInterfaces, EC2 DescribeInstances, EC2 DescribeNatGateways, EC2 DescribeVpcEndpoints, EC2 DescribeSubnets, EC2 DescribeRouteTables, Resource Groups Tagging API GetResources

## get_cloudwatch_metric_inventory

- Reason: Identify specific namespaces, S3 request-metric filters, and Elastic Beanstalk environments generating CW:MetricMonitorUsage charges.
- AWS APIs: CloudWatch ListMetrics, CloudWatch GetMetricData, S3 ListBucketMetricsConfigurations, Elastic Beanstalk DescribeEnvironmentHealth

## get_s3_inventory_and_utilization

- Reason: Attribute S3 data-transfer spend to buckets and inspect region, public access, CloudFront origins, request metrics, and Storage Lens configuration.
- AWS APIs: S3 ListBuckets, S3 GetBucketLocation, S3 GetBucketPolicy, S3 GetBucketTagging, S3 ListBucketMetricsConfigurations, S3 ListStorageLensConfigurations, CloudWatch GetMetricData

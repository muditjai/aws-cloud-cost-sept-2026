import { z } from "zod";

export const defaultAwsRegion = "us-east-1";

const connectionIdSchema = z.string().cuid();
const awsAuthMethodSchema = z.enum(["aws-role", "aws-keys"]);
const connectionStatusSchema = z.enum(["pending", "verified", "failed"]);
const ingestionStatusSchema = z.enum(["queued", "running", "completed", "failed"]);
const awsRegionSchema = z.enum([
  "us-east-1",
  "us-east-2",
  "us-west-2",
  "eu-west-1",
  "eu-west-2",
  "eu-central-1",
  "ap-southeast-1",
  "ap-southeast-2",
  "ap-northeast-1",
  "ap-south-1",
]);
const awsRegionsSchema = z
  .array(awsRegionSchema)
  .min(1, "Select at least one region.")
  .max(10, "Select at most 10 regions.")
  .transform((regions) => [...new Set(regions)])
  .default([defaultAwsRegion]);

const CreateAwsConnectionRequestSchema = z
  .object({
    authMethod: awsAuthMethodSchema,
    regions: awsRegionsSchema,
  })
  .strict();

const VerifyAwsConnectionRequestSchema = z.discriminatedUnion("authMethod", [
  z
    .object({
      authMethod: z.literal("aws-role"),
      roleArn: z
        .string()
        .trim()
        .regex(/^arn:aws:iam::\d{12}:role\/.+$/, "Enter a valid IAM role ARN."),
      regions: awsRegionsSchema,
    })
    .strict(),
  z
    .object({
      authMethod: z.literal("aws-keys"),
      accessKeyId: z.string().trim(),
      secretAccessKey: z.string().trim(),
      regions: awsRegionsSchema,
    })
    .strict(),
]);

const CreateIngestionRequestSchema = z
  .object({
    kind: z.literal("bill-and-resources").default("bill-and-resources"),
    regions: awsRegionsSchema.optional(),
  })
  .strict();

const AwsConnectionResponseSchema = z.object({
  id: connectionIdSchema,
  provider: z.literal("aws"),
  authMethod: awsAuthMethodSchema,
  status: connectionStatusSchema,
  regions: z.array(awsRegionSchema),
  externalId: z.string().nullable(),
  roleArn: z.string().nullable(),
  accountId: z.string().nullable(),
  principalArn: z.string().nullable(),
  verificationError: z.string().nullable(),
  credentialsPersisted: z.boolean(),
});

const CreateIngestionResponseSchema = z.object({
  id: connectionIdSchema,
  connectionId: connectionIdSchema,
  kind: z.literal("bill-and-resources"),
  status: ingestionStatusSchema,
  regions: z.array(awsRegionSchema),
  error: z.string().nullable(),
  startedAt: z.string().datetime().nullable(),
  completedAt: z.string().datetime().nullable(),
});

export const CreateAwsConnectionRequest = CreateAwsConnectionRequestSchema;
export type CreateAwsConnectionRequest = z.infer<
  typeof CreateAwsConnectionRequestSchema
>;

export const VerifyAwsConnectionRequest = VerifyAwsConnectionRequestSchema;
export type VerifyAwsConnectionRequest = z.infer<
  typeof VerifyAwsConnectionRequestSchema
>;

export const CreateIngestionRequest = CreateIngestionRequestSchema;
export type CreateIngestionRequest = z.infer<typeof CreateIngestionRequestSchema>;

export const AwsConnectionResponse = AwsConnectionResponseSchema;
export type AwsConnectionResponse = z.infer<typeof AwsConnectionResponseSchema>;

export const CreateIngestionResponse = CreateIngestionResponseSchema;
export type CreateIngestionResponse = z.infer<
  typeof CreateIngestionResponseSchema
>;

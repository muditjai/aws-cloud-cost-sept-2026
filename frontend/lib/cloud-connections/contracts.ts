import { z } from "zod";

export const defaultAwsRegion = "us-east-1";

const connectionIdSchema = z.string().cuid();
const awsAuthMethodSchema = z.enum(["aws-role", "aws-keys"]);
const connectionStatusSchema = z.enum(["pending", "verified", "failed"]);
const ingestionStatusSchema = z.enum(["queued", "running", "completed", "failed"]);

export const awsRegionSchema = z
  .string()
  .trim()
  .regex(/^[a-z]{2}(?:-gov)?-[a-z]+-\d$/, "Enter a valid AWS region.");

export const awsRegionsSchema = z
  .array(awsRegionSchema)
  .min(1, "Select at least one region.")
  .max(40, "Select at most 40 regions.")
  .transform((regions) => [...new Set(regions)])
  .default([defaultAwsRegion]);

export const createAwsConnectionSchema = z
  .object({
    authMethod: awsAuthMethodSchema,
    regions: awsRegionsSchema,
  })
  .strict();

export const verifyAwsConnectionSchema = z.discriminatedUnion("authMethod", [
  z
    .object({
      authMethod: z.literal("aws-role"),
      roleArn: z
        .string()
        .trim()
        .regex(
          /^arn:aws(?:-[a-z-]+)?:iam::\d{12}:role\/.+$/,
          "Enter a valid IAM role ARN.",
        ),
      regions: awsRegionsSchema,
    })
    .strict(),
  z
    .object({
      authMethod: z.literal("aws-keys"),
      accessKeyId: z.string().trim().min(16).max(128),
      secretAccessKey: z.string().trim().min(16).max(128),
      sessionToken: z.string().trim().min(16).max(4096).optional(),
      regions: awsRegionsSchema,
    })
    .strict(),
]);

export const createIngestionRunSchema = z
  .object({
    kind: z.literal("bill-and-resources").default("bill-and-resources"),
    regions: awsRegionsSchema.optional(),
  })
  .strict();

export const awsConnectionResponseSchema = z.object({
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
  createdAt: z.string().datetime(),
  updatedAt: z.string().datetime(),
});

export const ingestionRunResponseSchema = z.object({
  id: connectionIdSchema,
  connectionId: connectionIdSchema,
  kind: z.literal("bill-and-resources"),
  status: ingestionStatusSchema,
  regions: z.array(awsRegionSchema),
  error: z.string().nullable(),
  startedAt: z.string().datetime().nullable(),
  completedAt: z.string().datetime().nullable(),
  createdAt: z.string().datetime(),
  updatedAt: z.string().datetime(),
});

export type AwsConnection = z.infer<typeof awsConnectionResponseSchema>;
export type CreateAwsConnectionInput = z.infer<typeof createAwsConnectionSchema>;
export type CreateIngestionRunInput = z.infer<typeof createIngestionRunSchema>;
export type VerifyAwsConnectionInput = z.infer<typeof verifyAwsConnectionSchema>;

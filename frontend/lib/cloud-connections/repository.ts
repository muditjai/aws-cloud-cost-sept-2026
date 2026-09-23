import type { CloudConnection, IngestionRun } from "@/generated/prisma/client";
import {
  awsConnectionResponseSchema,
  awsRegionsSchema,
  type CreateAwsConnectionInput,
  type CreateIngestionRunInput,
  ingestionRunResponseSchema,
} from "@/lib/cloud-connections/contracts";
import { database } from "@/lib/cloud-connections/database";

function serializeRegions(regions: string[]) {
  return JSON.stringify(regions);
}

function parseRegions(regionsJson: string) {
  try {
    return awsRegionsSchema.parse(JSON.parse(regionsJson));
  } catch {
    return ["us-east-1"];
  }
}

function toConnectionResponse(connection: CloudConnection) {
  return awsConnectionResponseSchema.parse({
    id: connection.id,
    provider: connection.provider,
    authMethod: connection.authMethod,
    status: connection.status,
    regions: parseRegions(connection.regionsJson),
    externalId: connection.externalId,
    roleArn: connection.roleArn,
    accountId: connection.accountId,
    principalArn: connection.principalArn,
    verificationError: connection.verificationError,
    credentialsPersisted: connection.credentialReference !== null,
    createdAt: connection.createdAt.toISOString(),
    updatedAt: connection.updatedAt.toISOString(),
  });
}

function toIngestionRunResponse(ingestionRun: IngestionRun) {
  return ingestionRunResponseSchema.parse({
    id: ingestionRun.id,
    connectionId: ingestionRun.connectionId,
    kind: ingestionRun.kind,
    status: ingestionRun.status,
    regions: parseRegions(ingestionRun.regionsJson),
    error: ingestionRun.error,
    startedAt: ingestionRun.startedAt?.toISOString() ?? null,
    completedAt: ingestionRun.completedAt?.toISOString() ?? null,
    createdAt: ingestionRun.createdAt.toISOString(),
    updatedAt: ingestionRun.updatedAt.toISOString(),
  });
}

export async function createAwsConnection({
  authMethod,
  regions,
}: CreateAwsConnectionInput) {
  const connection = await database.cloudConnection.create({
    data: {
      provider: "aws",
      authMethod,
      regionsJson: serializeRegions(regions),
      externalId:
        authMethod === "aws-role" ? `migracle-${crypto.randomUUID()}` : null,
    },
  });

  return toConnectionResponse(connection);
}

export async function getConnection(connectionId: string) {
  const connection = await database.cloudConnection.findUnique({
    where: { id: connectionId },
  });

  return connection ? toConnectionResponse(connection) : null;
}

export async function markConnectionVerified({
  connectionId,
  roleArn,
  accountId,
  principalArn,
  regions,
}: {
  connectionId: string;
  roleArn: string | null;
  accountId: string;
  principalArn: string;
  regions: string[];
}) {
  const connection = await database.cloudConnection.update({
    where: { id: connectionId },
    data: {
      status: "verified",
      roleArn,
      accountId,
      principalArn,
      regionsJson: serializeRegions(regions),
      verificationError: null,
    },
  });

  return toConnectionResponse(connection);
}

export async function markConnectionFailed({
  connectionId,
  verificationError,
}: {
  connectionId: string;
  verificationError: string;
}) {
  const connection = await database.cloudConnection.update({
    where: { id: connectionId },
    data: {
      status: "failed",
      verificationError,
    },
  });

  return toConnectionResponse(connection);
}

export async function createIngestionRun({
  connectionId,
  kind,
  regions,
}: CreateIngestionRunInput & { connectionId: string }) {
  const ingestionRun = await database.ingestionRun.create({
    data: {
      connectionId,
      kind,
      regionsJson: serializeRegions(regions ?? ["us-east-1"]),
    },
  });

  return toIngestionRunResponse(ingestionRun);
}

export async function getIngestionRun(ingestionId: string) {
  const ingestionRun = await database.ingestionRun.findUnique({
    where: { id: ingestionId },
  });

  return ingestionRun ? toIngestionRunResponse(ingestionRun) : null;
}

import { expect, test } from "@playwright/test";
import { markConnectionVerified } from "../lib/cloud-connections/repository";

test("AWS connection setup persists a role draft", async ({ request }) => {
  const setupResponse = await request.post("/api/connections/aws", {
    data: {
      authMethod: "aws-role",
      regions: ["us-east-1"],
    },
  });

  await expect(setupResponse).toBeOK();

  const connection = await setupResponse.json();

  expect(connection).toMatchObject({
    provider: "aws",
    authMethod: "aws-role",
    status: "pending",
    regions: ["us-east-1"],
  });
  expect(connection.externalId).toMatch(/^migracle-/);

  const getResponse = await request.get(`/api/connections/${connection.id}`);

  await expect(getResponse).toBeOK();
  expect(await getResponse.json()).toEqual(connection);
});

test("AWS connection setup rejects an invalid request", async ({ request }) => {
  const response = await request.post("/api/connections/aws", {
    data: {
      authMethod: "role",
    },
  });

  expect(response.status()).toBe(400);
  expect(await response.json()).toMatchObject({
    error: {
      code: "invalid_request",
      message: "Request body is invalid.",
      issues: expect.any(Array),
    },
  });
});

test("ingestion runs persist after a connection is verified", async ({ request }) => {
  const setupResponse = await request.post("/api/connections/aws", {
    data: {
      authMethod: "aws-role",
      regions: ["us-east-1"],
    },
  });
  const connection = await setupResponse.json();

  await markConnectionVerified({
    connectionId: connection.id,
    roleArn: "arn:aws:iam::123456789012:role/MigracleReadOnly",
    accountId: "123456789012",
    principalArn: "arn:aws:iam::123456789012:role/MigracleReadOnly",
    regions: ["us-east-1"],
  });

  const startResponse = await request.post(
    `/api/connections/${connection.id}/ingestions`,
    {
      data: {
        kind: "bill-and-resources",
      },
    },
  );

  expect(startResponse.status()).toBe(202);

  const ingestionRun = await startResponse.json();

  expect(ingestionRun).toMatchObject({
    connectionId: connection.id,
    kind: "bill-and-resources",
    status: "queued",
    regions: ["us-east-1"],
  });

  const getResponse = await request.get(`/api/ingestions/${ingestionRun.id}`);

  expect(await getResponse.json()).toEqual(ingestionRun);
});

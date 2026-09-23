import { expect, test } from "@playwright/test";

test("connect shows its stage and cloud providers", async ({ page }) => {
  await page.goto("/connect");

  await expect(
    page.getByRole("heading", { name: "Connect", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Connect", exact: true }),
  ).toHaveAttribute("aria-current", "page");
  const awsTrigger = page.getByRole("button", { name: "AWS", exact: true });

  await expect(awsTrigger).toBeVisible();
  await expect(awsTrigger).toHaveAttribute("data-state", "closed");
  await expect(
    page.getByRole("button", { name: "GCP", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Azure", exact: true }),
  ).toBeVisible();

  await awsTrigger.click();

  await expect(page.locator('button[data-state="open"]')).toHaveText("AWS");
  await page.getByRole("button", { name: "Close" }).click();
});

test("AWS role connection asks for role details", async ({ page }) => {
  await page.goto("/connect");
  await page.getByRole("button", { name: "AWS", exact: true }).click();

  await expect(
    page.getByRole("heading", { name: "Connect AWS" }),
  ).toBeVisible();
  await expect(
    page.getByText("Connect an AWS account with read-only access."),
  ).toBeVisible();
  await expect(page.getByRole("tab", { name: "IAM role" })).toHaveAttribute(
    "data-state",
    "active",
  );
  await expect(page.getByRole("tab", { name: "IAM role" })).toHaveAttribute(
    "aria-controls",
    /aws-role/,
  );
  await expect(page.getByLabel("IAM role ARN")).toBeVisible();
  await expect(page.getByLabel("External ID")).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Copy external ID" }),
  ).toBeVisible();
  await expect(page.getByLabel("Regions (optional)")).toBeVisible();
});

test("AWS access key connection asks for key details", async ({ page }) => {
  await page.goto("/connect");
  await page.getByRole("button", { name: "AWS", exact: true }).click();
  await page.getByRole("tab", { name: "Access keys" }).click();

  await expect(page.getByRole("tab", { name: "Access keys" })).toHaveAttribute(
    "data-state",
    "active",
  );
  await expect(page.getByRole("tab", { name: "Access keys" })).toHaveAttribute(
    "aria-controls",
    /aws-keys/,
  );
  await expect(page.getByLabel("Access key ID")).toBeVisible();
  await expect(page.getByLabel("Secret access key")).toHaveAttribute(
    "type",
    "password",
  );
  await expect(page.getByLabel("Regions (optional)")).toBeVisible();
});

test("GCP connection asks for project and service account details", async ({
  page,
}) => {
  await page.goto("/connect");
  await page.getByRole("button", { name: "GCP", exact: true }).click();

  await expect(
    page.getByRole("heading", { name: "Connect GCP" }),
  ).toBeVisible();
  await expect(page.getByLabel("Project ID")).toBeVisible();
  await expect(page.getByLabel("Service account email")).toBeVisible();
  await expect(page.getByLabel("Service account key")).toBeVisible();
});

test("Azure connection asks for tenant, subscription, and app details", async ({
  page,
}) => {
  await page.goto("/connect");
  await page.getByRole("button", { name: "Azure", exact: true }).click();

  await expect(
    page.getByRole("heading", { name: "Connect Azure" }),
  ).toBeVisible();
  await expect(page.getByLabel("Tenant ID")).toBeVisible();
  await expect(page.getByLabel("Subscription ID")).toBeVisible();
  await expect(page.getByLabel("Application (client) ID")).toBeVisible();
  await expect(page.getByLabel("Client secret")).toBeVisible();
});

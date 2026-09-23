import { expect, test } from "@playwright/test";

test("connect shows its stage and cloud providers", async ({ page }) => {
  await page.goto("/connect");

  await expect(page.getByRole("heading", { name: "Connect", exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: "Connect", exact: true })).toHaveAttribute("aria-current", "page");
  const awsTrigger = page.getByRole("button", { name: "AWS", exact: true });

  await expect(awsTrigger).toBeVisible();
  await expect(awsTrigger).toHaveAttribute("data-state", "closed");
  await expect(page.getByRole("button", { name: "GCP", exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Azure", exact: true })).toBeVisible();

  await awsTrigger.click();

  await expect(page.locator('button[data-state="open"]')).toHaveText("AWS");
  await page.getByRole("button", { name: "Close" }).click();
});

test("AWS connection asks for account and role details", async ({ page }) => {
  await page.goto("/connect");
  await page.getByRole("button", { name: "AWS", exact: true }).click();

  await expect(page.getByRole("heading", { name: "Connect AWS" })).toBeVisible();
  await expect(page.getByLabel("AWS account ID")).toBeVisible();
  await expect(page.getByLabel("IAM role ARN")).toBeVisible();
  await expect(page.getByLabel("External ID")).toBeVisible();
});

test("GCP connection asks for project and service account details", async ({ page }) => {
  await page.goto("/connect");
  await page.getByRole("button", { name: "GCP", exact: true }).click();

  await expect(page.getByRole("heading", { name: "Connect GCP" })).toBeVisible();
  await expect(page.getByLabel("Project ID")).toBeVisible();
  await expect(page.getByLabel("Service account email")).toBeVisible();
  await expect(page.getByLabel("Service account key")).toBeVisible();
});

test("Azure connection asks for tenant, subscription, and app details", async ({ page }) => {
  await page.goto("/connect");
  await page.getByRole("button", { name: "Azure", exact: true }).click();

  await expect(page.getByRole("heading", { name: "Connect Azure" })).toBeVisible();
  await expect(page.getByLabel("Tenant ID")).toBeVisible();
  await expect(page.getByLabel("Subscription ID")).toBeVisible();
  await expect(page.getByLabel("Application (client) ID")).toBeVisible();
  await expect(page.getByLabel("Client secret")).toBeVisible();
});

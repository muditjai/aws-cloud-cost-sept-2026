import { expect, test } from "@playwright/test";

test("connect shows its stage and start action", async ({ page }) => {
  await page.goto("/connect");

  await expect(page.getByRole("heading", { name: "Connect" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Start" })).toBeEnabled();
});

test("ingest shows its stage and start action", async ({ page }) => {
  await page.goto("/ingest");

  await expect(page.getByRole("heading", { name: "Ingest" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Start" })).toBeEnabled();
});

test("audit shows its stage and start action", async ({ page }) => {
  await page.goto("/audit");

  await expect(page.getByRole("heading", { name: "Audit" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Start" })).toBeEnabled();
});

test("recommend shows its stage and start action", async ({ page }) => {
  await page.goto("/recommend");

  await expect(page.getByRole("heading", { name: "Recommend" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Start" })).toBeEnabled();
});

test("create changes shows its stage and start action", async ({ page }) => {
  await page.goto("/create-changes");

  await expect(page.getByRole("heading", { name: "Create Changes" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Start" })).toBeEnabled();
});

test("test shows its stage and start action", async ({ page }) => {
  await page.goto("/test");

  await expect(page.getByRole("heading", { name: "Test" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Start" })).toBeEnabled();
});

test("deploy shows its stage and start action", async ({ page }) => {
  await page.goto("/deploy");

  await expect(page.getByRole("heading", { name: "Deploy" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Start" })).toBeEnabled();
});

test("live validate shows its stage and start action", async ({ page }) => {
  await page.goto("/live-validate");

  await expect(page.getByRole("heading", { name: "Live Validate" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Start" })).toBeEnabled();
});

test("prove savings shows its stage and start action", async ({ page }) => {
  await page.goto("/prove-savings");

  await expect(page.getByRole("heading", { name: "Prove Savings" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Start" })).toBeEnabled();
});

import { expect, test } from "@playwright/test";

test("ingest shows its stage and start action", async ({ page }) => {
  await page.goto("/ingest");

  await expect(page.getByRole("heading", { name: "Ingest", exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: "Ingest", exact: true })).toHaveAttribute("aria-current", "page");
});

test("audit shows its stage and start action", async ({ page }) => {
  await page.goto("/audit");

  await expect(page.getByRole("heading", { name: "Audit", exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: "Audit", exact: true })).toHaveAttribute("aria-current", "page");
});

test("recommend shows its stage and start action", async ({ page }) => {
  await page.goto("/recommend");

  await expect(page.getByRole("heading", { name: "Recommend", exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: "Recommend", exact: true })).toHaveAttribute("aria-current", "page");
});

test("create changes shows its stage and start action", async ({ page }) => {
  await page.goto("/create-changes");

  await expect(page.getByRole("heading", { name: "Create Changes", exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: "Create Changes", exact: true })).toHaveAttribute("aria-current", "page");
});

test("test shows its stage and start action", async ({ page }) => {
  await page.goto("/test");

  await expect(page.getByRole("heading", { name: "Test", exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: "Test", exact: true })).toHaveAttribute("aria-current", "page");
});

test("deploy shows its stage and start action", async ({ page }) => {
  await page.goto("/deploy");

  await expect(page.getByRole("heading", { name: "Deploy", exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: "Deploy", exact: true })).toHaveAttribute("aria-current", "page");
});

test("live validate shows its stage and start action", async ({ page }) => {
  await page.goto("/live-validate");

  await expect(page.getByRole("heading", { name: "Live Validate", exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: "Live Validate", exact: true })).toHaveAttribute("aria-current", "page");
});

test("prove savings shows its stage and start action", async ({ page }) => {
  await page.goto("/prove-savings");

  await expect(page.getByRole("heading", { name: "Prove Savings", exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: "Prove Savings", exact: true })).toHaveAttribute("aria-current", "page");
});

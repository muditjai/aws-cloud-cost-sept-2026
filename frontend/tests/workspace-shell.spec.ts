import { expect, test } from "@playwright/test";

test("artifacts can be hidden and reopened", async ({ page }) => {
  await page.goto("/connect");

  const artifactsToggle = page.getByRole("button", { name: "Artifacts", exact: true });

  await expect(artifactsToggle).toHaveAttribute("aria-expanded", "true");
  await expect(page.getByRole("heading", { name: "Artifacts" })).toBeVisible();

  await artifactsToggle.click();

  await expect(artifactsToggle).toHaveAttribute("aria-expanded", "false");
  await expect(page.getByRole("heading", { name: "Artifacts" })).not.toBeVisible();

  await artifactsToggle.click();

  await expect(artifactsToggle).toHaveAttribute("aria-expanded", "true");
  await expect(page.getByRole("heading", { name: "Artifacts" })).toBeVisible();
});

test("artifact content changes with the active stage", async ({ page }) => {
  await page.goto("/audit");

  await expect(page.getByText("Audit artifacts", { exact: true })).toBeVisible();
  await expect(page.getByText("Spend baselines and technical findings will appear here.")).toBeVisible();
});

import { expect, test } from "@playwright/test";

test("artifacts open and close in a drawer", async ({ page }) => {
  await page.goto("/connect");

  const artifactsToggle = page.getByRole("button", {
    name: "Artifacts",
    exact: true,
  });

  await expect(page.getByRole("dialog")).not.toBeVisible();

  await artifactsToggle.click();

  const artifactsDrawer = page.getByRole("dialog");
  await expect(artifactsDrawer).toBeVisible();
  await expect(
    artifactsDrawer.getByRole("heading", { name: "Artifacts" }),
  ).toBeVisible();
  await expect(
    artifactsDrawer.getByText("Connect artifacts", { exact: true }),
  ).toBeVisible();

  await artifactsDrawer
    .getByRole("button", { name: "Close artifacts" })
    .click();

  await expect(artifactsDrawer).not.toBeVisible();
});

test("artifact content changes with the active stage", async ({ page }) => {
  await page.goto("/audit");

  await page.getByRole("button", { name: "Artifacts", exact: true }).click();

  const artifactsDrawer = page.getByRole("dialog");
  await expect(
    artifactsDrawer.getByText("Audit artifacts", { exact: true }),
  ).toBeVisible();
  await expect(
    artifactsDrawer.getByText(
      "Spend baselines and technical findings will appear here.",
    ),
  ).toBeVisible();
});

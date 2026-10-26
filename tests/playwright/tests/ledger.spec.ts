import { expect, test } from "@playwright/test";

test("@lite @feature REQ-7 a share disposal is saved, listed, and discounted", async ({ page }) => {
  const email = `ledger-${Date.now()}@example.test`;
  await page.goto("/register");
  await page.getByLabel("Name").fill("Ada Investor");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill("correct-horse-1");
  await page.getByRole("button", { name: "Create account" }).click();
  await page.getByRole("link", { name: "Investment records" }).click();
  await expect(page.getByRole("heading", { name: "Income year ending 2027" })).toBeVisible();

  await page.getByLabel("Kind").selectOption("share");
  await page.getByLabel("Description").fill("CBA parcel");
  await page.getByLabel("Acquired").fill("2025-06-01");
  await page.getByLabel("Sold").fill("2026-08-01");
  await page.getByLabel("Cost base").fill("10000");
  await page.getByLabel("Sale proceeds").fill("14000");
  const save = page.waitForResponse(
    (response) => response.url().includes("/ledger/records") && response.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Save record" }).click();
  expect((await save).ok()).toBeTruthy();

  await expect(page.getByText("Recorded a share disposal of CBA parcel")).toBeVisible();
  await expect(page.getByText("Estimated taxable capital gain $2,000.00.")).toBeVisible();
});

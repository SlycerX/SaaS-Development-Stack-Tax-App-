import { expect, test } from "@playwright/test";

test("@lite @feature REQ-4 a new account reaches the dashboard", async ({ page }) => {
  const email = `tax-${Date.now()}@example.test`;
  await page.goto("/register");
  await page.getByLabel("Name").fill("Ada Investor");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill("correct-horse-1");
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Dashboard");
  await expect(page.getByText("Ada Investor")).toBeVisible();
});

test("@lite @feature REQ-5 account details can be saved and seen after signing in again", async ({ page }) => {
  const email = `tax-${Date.now()}@example.test`;
  await page.goto("/register");
  await page.getByLabel("Name").fill("Ada Investor");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill("correct-horse-1");
  await page.getByRole("button", { name: "Create account" }).click();
  await page.getByRole("link", { name: "Account details" }).click();
  await page.getByLabel("Name").fill("Ada Updated");
  await page.getByRole("button", { name: "Save" }).click();
  await expect(page.getByText("Saved")).toBeVisible();
  await page.getByRole("button", { name: "Sign out" }).click();
  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill("correct-horse-1");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByText("Ada Updated")).toBeVisible();
});

import { expect, test } from "@playwright/test";

const apiUrl = process.env.API_URL ?? "http://127.0.0.1:8000";
const productName = process.env.PRODUCT_NAME ?? "example";

test("@lite @feature REQ-1 home page shows the product name", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(productName);
});

test("@lite @feature REQ-2 health endpoint returns ok", async ({ request }) => {
  const response = await request.get(`${apiUrl}/health`);
  expect(response.ok()).toBeTruthy();
  expect(await response.json()).toEqual({ status: "ok" });
});

test("@lite @feature REQ-3 items endpoint returns the example item", async ({ request }) => {
  const response = await request.get(`${apiUrl}/items`);
  expect(response.ok()).toBeTruthy();
  const body = await response.json();
  const names = body.items.map((item: { name: string }) => item.name);
  expect(names).toContain("example");
});

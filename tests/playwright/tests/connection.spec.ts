import { expect, test } from "@playwright/test";

const webUrl = process.env.WEB_URL ?? "http://127.0.0.1:3000";

test("@lite @feature REQ-6 the web app accepts a connection", async ({ request }) => {
  let response;
  try {
    response = await request.get(webUrl);
  } catch (error) {
    const detail = error instanceof Error ? error.message : String(error);
    throw new Error(
      [
        `ERR_CONNECTION_REFUSED at ${webUrl}.`,
        "Nothing is listening on that port.",
        "The usual cause is Docker Desktop stopped, so the web container is not running.",
        "Check 1: start Docker Desktop and wait until it is running.",
        'Check 2: docker compose -f "D:\\SaaS Development\\compose.yaml" ps',
        "Check 3: if web is missing or Exited, run docker compose up -d from that folder.",
        detail,
      ].join("\n"),
    );
  }
  expect(response.ok()).toBeTruthy();
});

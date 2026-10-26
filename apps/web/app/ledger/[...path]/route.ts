import { NextRequest, NextResponse } from "next/server";

async function proxy(request: NextRequest, path: string[]) {
  const base = process.env.API_PROXY_URL ?? "http://127.0.0.1:8000";
  const target = `${base}/ledger/${path.join("/")}${request.nextUrl.search}`;
  const headers = new Headers();
  const cookie = request.headers.get("cookie");
  if (cookie) headers.set("cookie", cookie);
  const contentType = request.headers.get("content-type");
  if (contentType) headers.set("content-type", contentType);

  const response = await fetch(target, {
    method: request.method,
    headers,
    body: request.method === "GET" || request.method === "HEAD" ? undefined : await request.text(),
  });
  const next = new NextResponse(await response.text(), { status: response.status });
  const type = response.headers.get("content-type");
  if (type) next.headers.set("content-type", type);
  return next;
}

export async function GET(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params;
  return proxy(request, path);
}

export async function POST(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params;
  return proxy(request, path);
}

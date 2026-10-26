import Link from "next/link";

export default function Home() {
  const name = process.env.NEXT_PUBLIC_PRODUCT_NAME ?? "example";
  return (
    <main>
      <h1>{name}</h1>
      <p>Australian tax workspace for property, shares, and bitcoin.</p>
      <nav>
        <Link href="/register">Create account</Link>
        <Link href="/login">Sign in</Link>
      </nav>
    </main>
  );
}
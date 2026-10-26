"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

export default function RegisterPage() {
  const router = useRouter();
  const [error, setError] = useState("");

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    const form = new FormData(event.currentTarget);
    const response = await fetch("/auth/register", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        display_name: form.get("display_name"),
        email: form.get("email"),
        password: form.get("password"),
      }),
    });
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      setError(body.detail ?? "Could not create the account");
      return;
    }
    router.push("/dashboard");
  }

  return (
    <main>
      <h1>Create account</h1>
      <p className="muted">Password stays hashed. A tax file number is never stored.</p>
      <form onSubmit={onSubmit}>
        <label>
          Name
          <input name="display_name" required />
        </label>
        <label>
          Email
          <input name="email" type="email" required />
        </label>
        <label>
          Password
          <input name="password" type="password" minLength={12} required />
        </label>
        {error ? <p className="error">{error}</p> : null}
        <button type="submit">Create account</button>
      </form>
      <p>
        <Link href="/login">Already have an account</Link>
      </p>
    </main>
  );
}
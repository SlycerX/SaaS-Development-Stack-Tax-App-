"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

type Account = {
  email: string;
  display_name: string;
  australian_resident: boolean;
  income_year_ending: number;
  entity_type: string;
};

export default function AccountPage() {
  const router = useRouter();
  const [account, setAccount] = useState<Account | null>(null);
  const [saved, setSaved] = useState("");

  useEffect(() => {
    fetch("/auth/me").then(async (response) => {
      if (response.status === 401) {
        router.replace("/login");
        return;
      }
      setAccount(await response.json());
    });
  }, [router]);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!account) return;
    const form = new FormData(event.currentTarget);
    const response = await fetch("/auth/me", {
      method: "PATCH",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        display_name: form.get("display_name"),
        australian_resident: form.get("australian_resident") === "yes",
        income_year_ending: Number(form.get("income_year_ending")),
      }),
    });
    if (!response.ok) {
      setSaved("Could not save");
      return;
    }
    setAccount(await response.json());
    setSaved("Saved");
  }

  async function signOut() {
    await fetch("/auth/logout", { method: "POST" });
    router.push("/");
  }

  if (!account) return <main><p>Loading account</p></main>;

  return (
    <main>
      <h1>Account details</h1>
      <p className="muted">{account.email}</p>
      <form onSubmit={onSubmit}>
        <label>
          Name
          <input name="display_name" defaultValue={account.display_name} required />
        </label>
        <label>
          Australian resident for tax purposes
          <select name="australian_resident" defaultValue={account.australian_resident ? "yes" : "no"}>
            <option value="yes">Yes</option>
            <option value="no">No</option>
          </select>
        </label>
        <label>
          Income year ending 30 June
          <input name="income_year_ending" type="number" defaultValue={account.income_year_ending} required />
        </label>
        <label>
          Entity
          <input value={account.entity_type} readOnly />
        </label>
        {saved ? <p>{saved}</p> : null}
        <button type="submit">Save</button>
      </form>
      <p>
        <button type="button" onClick={signOut}>Sign out</button>
      </p>
      <p>
        <Link href="/dashboard">Back to dashboard</Link>
      </p>
    </main>
  );
}
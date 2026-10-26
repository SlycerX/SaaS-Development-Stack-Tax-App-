"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

type Account = {
  display_name: string;
  income_year_ending: number;
  entity_type: string;
};

const areas = [
  ["Property", "Purchase price, stamp duty, and sale proceeds."],
  ["Shares", "Parcels, brokerage, and contract-note amounts."],
  ["Bitcoin", "Exchange buys, sells, and swaps in Australian dollars."],
  ["History", "Each saved figure is written into the account history."],
];

export default function DashboardPage() {
  const router = useRouter();
  const [account, setAccount] = useState<Account | null>(null);

  useEffect(() => {
    fetch("/auth/me").then(async (response) => {
      if (response.status === 401) {
        router.replace("/login");
        return;
      }
      setAccount(await response.json());
    });
  }, [router]);

  if (!account) return <main><p>Loading account</p></main>;

  const start = account.income_year_ending - 1;
  return (
    <main>
      <h1>Dashboard</h1>
      <p>
        {account.display_name}, income year {start}–{account.income_year_ending} ({account.entity_type}).
      </p>
      <nav>
        <Link href="/account">Account details</Link>
        {" · "}
        <Link href="/records">Investment records</Link>
      </nav>
      <div className="cards">
        {areas.map(([title, text]) => (
          <section className="card" key={title}>
            <h2>{title}</h2>
            <p className="muted">{text}</p>
          </section>
        ))}
      </div>
      <p className="muted">The estimate uses the records you enter. It applies the 50% individual discount after capital losses.</p>
    </main>
  );
}
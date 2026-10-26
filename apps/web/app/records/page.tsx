"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

type Estimate = {
  income_year_ending: number;
  taxable_gain_cents: number;
  remaining_loss_cents: number;
  recommendations: string[];
  note: string;
};

type HistoryEvent = { id: number; detail: string };

function dollars(cents: number) {
  const sign = cents < 0 ? "-" : "";
  const amount = Math.abs(cents);
  return `${sign}$${Math.floor(amount / 100).toLocaleString("en-AU")}.${String(amount % 100).padStart(2, "0")}`;
}

export default function RecordsPage() {
  const router = useRouter();
  const [estimate, setEstimate] = useState<Estimate | null>(null);
  const [history, setHistory] = useState<HistoryEvent[]>([]);
  const [error, setError] = useState("");

  async function refresh() {
    const [estimateResponse, historyResponse] = await Promise.all([
      fetch("/ledger/estimate"),
      fetch("/ledger/history"),
    ]);
    if (estimateResponse.status === 401 || historyResponse.status === 401) {
      router.replace("/login");
      return;
    }
    setEstimate(await estimateResponse.json());
    const historyBody = await historyResponse.json();
    setHistory(historyBody.events);
  }

  useEffect(() => {
    refresh();
  }, [router]);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const response = await fetch("/ledger/records", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        kind: form.get("kind"),
        description: form.get("description"),
        acquired_on: form.get("acquired_on"),
        disposed_on: form.get("disposed_on") || null,
        cost_base: form.get("cost_base"),
        incidental: form.get("incidental") || "0",
        proceeds: form.get("proceeds") || null,
        quantity: form.get("quantity") || null,
        main_residence: form.get("main_residence") === "on",
      }),
    });
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      setError(body.detail ?? "The record was not saved");
      return;
    }
    formElement.reset();
    await refresh();
  }

  return (
    <main>
      <h1>Records</h1>
      <p>
        <Link href="/dashboard">Dashboard</Link>
      </p>
      {estimate ? (
        <section>
          <h2>Income year ending {estimate.income_year_ending}</h2>
          <p>Estimated taxable capital gain {dollars(estimate.taxable_gain_cents)}.</p>
          <p>Capital losses still available {dollars(estimate.remaining_loss_cents)}.</p>
          <p className="muted">{estimate.note}</p>
          <ul>
            {estimate.recommendations.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </section>
      ) : (
        <p>Loading records</p>
      )}
      <form onSubmit={onSubmit}>
        <label>
          Kind
          <select name="kind" aria-label="Kind">
            <option value="property">Property</option>
            <option value="share">Shares</option>
            <option value="bitcoin">Bitcoin</option>
          </select>
        </label>
        <label>
          Description
          <input name="description" aria-label="Description" required />
        </label>
        <label>
          Quantity
          <input name="quantity" aria-label="Quantity" />
        </label>
        <label>
          Acquired
          <input name="acquired_on" aria-label="Acquired" type="date" required />
        </label>
        <label>
          Sold
          <input name="disposed_on" aria-label="Sold" type="date" />
        </label>
        <label>
          Cost base
          <input name="cost_base" aria-label="Cost base" required />
        </label>
        <label>
          Brokerage, stamp duty, and legal costs
          <input name="incidental" aria-label="Incidental costs" defaultValue="0" />
        </label>
        <label>
          Sale proceeds
          <input name="proceeds" aria-label="Sale proceeds" />
        </label>
        <label>
          <input name="main_residence" type="checkbox" /> This property was my main residence
        </label>
        <button type="submit">Save record</button>
        {error ? <p>{error}</p> : null}
      </form>
      <h2>History</h2>
      <ul>
        {history.map((event) => (
          <li key={event.id}>{event.detail}</li>
        ))}
      </ul>
    </main>
  );
}

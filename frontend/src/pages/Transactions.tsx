import { useEffect, useState } from "react";
import { api } from "../services/api";
import { Card, SectionHeader, Badge } from "../components/ui";
import { inr0 } from "../lib";
import type { Transaction } from "../types";

export default function Transactions() {
  const [txns, setTxns] = useState<Transaction[]>([]);
  const [summary, setSummary] = useState<any>(null);

  useEffect(() => {
    Promise.all([api.transactions(), api.monthlySummary()]).then(([t, s]) => {
      setTxns(t);
      setSummary(s);
    });
  }, []);

  return (
    <div className="space-y-6">
      <SectionHeader title="Transactions" sub="Mock bank transactions (August 2026)" />

      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Mini label="Total Credit" value={inr0(summary.total_credit)} tone="text-green" />
          <Mini label="Total Debit" value={inr0(summary.total_debit)} tone="text-red" />
          <Mini label="Net Change" value={inr0(summary.net_change)} tone={summary.net_change >= 0 ? "text-green" : "text-red"} />
          <Mini label="Transactions" value={`${summary.transaction_count}`} tone="text-text" />
        </div>
      )}

      <Card className="!p-0 overflow-hidden">
        <div className="max-h-[70vh] overflow-y-auto">
          <table className="w-full text-xs">
            <thead className="sticky top-0 bg-card2">
              <tr className="text-muted text-left">
                <th className="p-3">Date</th>
                <th className="p-3">Account</th>
                <th className="p-3">Description</th>
                <th className="p-3">Category</th>
                <th className="p-3 text-right">Amount</th>
                <th className="p-3 text-center">Type</th>
              </tr>
            </thead>
            <tbody>
              {txns.map((t) => (
                <tr key={t.txn_id} className="border-t border-border hover:bg-card/50">
                  <td className="p-3 text-muted">{t.date}</td>
                  <td className="p-3">{t.account_id}</td>
                  <td className="p-3 max-w-[260px] truncate">{t.description}</td>
                  <td className="p-3"><Badge tone="gray">{t.category}</Badge></td>
                  <td className={`p-3 text-right font-semibold ${t.type === "CREDIT" ? "text-green" : "text-red"}`}>
                    {t.type === "CREDIT" ? "+" : "-"}{inr0(t.amount)}
                  </td>
                  <td className="p-3 text-center">{t.type}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}

function Mini({ label, value, tone }: { label: string; value: string; tone: string }) {
  return (
    <div className="bg-card border border-border rounded-2xl p-4">
      <div className="text-[11px] uppercase tracking-widest text-muted">{label}</div>
      <div className={`mt-2 text-xl font-bold ${tone}`}>{value}</div>
    </div>
  );
}

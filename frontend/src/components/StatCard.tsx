import type { ReactNode } from "react";

interface StatCardProps {
  label: string;
  value: ReactNode;
  tone?: "blue" | "green" | "amber" | "red";
}

export function StatCard({ label, value, tone = "blue" }: StatCardProps) {
  return (
    <article className={`stat-card stat-${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </article>
  );
}

export function LoadingState({ label = "A carregar dados..." }: { label?: string }) {
  return <div className="loading-state">{label}</div>;
}

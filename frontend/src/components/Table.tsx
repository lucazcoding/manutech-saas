import type { ReactNode } from "react";

interface TableProps {
  columns: string[];
  children: ReactNode;
  empty?: boolean;
  emptyLabel?: string;
}

export function Table({ columns, children, empty = false, emptyLabel = "Sem registros." }: TableProps) {
  return (
    <div className="table-container">
      <table>
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column}>{column}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {empty ? (
            <tr>
              <td colSpan={columns.length} className="muted">
                {emptyLabel}
              </td>
            </tr>
          ) : (
            children
          )}
        </tbody>
      </table>
    </div>
  );
}

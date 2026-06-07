import { ChevronLeft, ChevronRight } from "lucide-react";

interface PaginationProps {
  page: number;
  pages: number;
  total: number;
  pageSize: number;
  onPageChange: (page: number) => void;
}

export function Pagination({ page, pages, total, pageSize, onPageChange }: PaginationProps) {
  if (total <= pageSize) return null;

  const start = (page - 1) * pageSize + 1;
  const end = Math.min(page * pageSize, total);
  const canPrev = page > 1;
  const canNext = page < pages;

  return (
    <div className="pagination">
      <small className="muted">
        Exibindo {start}–{end} de {total}
      </small>
      <div className="pagination-controls">
        <button
          className="icon-button"
          type="button"
          onClick={() => onPageChange(page - 1)}
          disabled={!canPrev}
          aria-label="Página anterior"
          title="Página anterior"
        >
          <ChevronLeft size={16} />
        </button>
        <span className="pagination-page">
          Página {page} de {pages}
        </span>
        <button
          className="icon-button"
          type="button"
          onClick={() => onPageChange(page + 1)}
          disabled={!canNext}
          aria-label="Próxima página"
          title="Próxima página"
        >
          <ChevronRight size={16} />
        </button>
      </div>
    </div>
  );
}

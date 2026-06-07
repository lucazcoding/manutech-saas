import { useEffect, useMemo, useState } from "react";

const DEFAULT_PAGE_SIZE = 7;

export function usePagination<T>(items: T[], pageSize: number = DEFAULT_PAGE_SIZE) {
  const [page, setPage] = useState(1);
  const pages = Math.max(1, Math.ceil(items.length / pageSize));

  useEffect(() => {
    if (page > pages) setPage(1);
  }, [page, pages]);

  const visible = useMemo(() => {
    const start = (page - 1) * pageSize;
    return items.slice(start, start + pageSize);
  }, [items, page, pageSize]);

  return { page, setPage, pages, pageSize, total: items.length, visible };
}

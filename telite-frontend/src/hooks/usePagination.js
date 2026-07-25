import { useState, useCallback, useMemo } from 'react';

/**
 * Custom hook for pagination logic
 * @param {object} options - Pagination options
 * @returns {object} - Pagination state and handlers
 */
export function usePagination(options = {}) {
  const {
    initialPage = 1,
    initialPageSize = 25,
    totalItems = 0,
    pageSizeOptions = [25, 50, 100]
  } = options;

  const [currentPage, setCurrentPage] = useState(initialPage);
  const [pageSize, setPageSize] = useState(initialPageSize);

  const totalPages = useMemo(() => {
    return Math.ceil(totalItems / pageSize) || 1;
  }, [totalItems, pageSize]);

  const startIndex = useMemo(() => {
    return (currentPage - 1) * pageSize;
  }, [currentPage, pageSize]);

  const endIndex = useMemo(() => {
    return Math.min(startIndex + pageSize, totalItems);
  }, [startIndex, pageSize, totalItems]);

  const goToPage = useCallback((page) => {
    const newPage = Math.max(1, Math.min(page, totalPages));
    setCurrentPage(newPage);
  }, [totalPages]);

  const nextPage = useCallback(() => {
    goToPage(currentPage + 1);
  }, [currentPage, goToPage]);

  const prevPage = useCallback(() => {
    goToPage(currentPage - 1);
  }, [currentPage, goToPage]);

  const firstPage = useCallback(() => {
    goToPage(1);
  }, [goToPage]);

  const lastPage = useCallback(() => {
    goToPage(totalPages);
  }, [goToPage, totalPages]);

  const changePageSize = useCallback((newSize) => {
    setPageSize(newSize);
    setCurrentPage(1); // Reset to first page when changing page size
  }, []);

  const canGoToNextPage = currentPage < totalPages;
  const canGoToPrevPage = currentPage > 1;

  return {
    currentPage,
    pageSize,
    totalPages,
    startIndex,
    endIndex,
    pageSizeOptions,
    canGoToNextPage,
    canGoToPrevPage,
    goToPage,
    nextPage,
    prevPage,
    firstPage,
    lastPage,
    changePageSize,
    setCurrentPage,
    setPageSize
  };
}

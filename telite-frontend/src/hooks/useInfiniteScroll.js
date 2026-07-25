import { useState, useEffect, useCallback, useRef } from 'react';

/**
 * Custom hook for infinite scrolling
 * @param {function} callback - Function to call when more data should be loaded
 * @param {object} options - Configuration options
 * @returns {object} - { isFetching, reset }
 */
export function useInfiniteScroll(callback, options = {}) {
  const { 
    threshold = 100, 
    rootMargin = '100px',
    hasMore = true 
  } = options;

  const [isFetching, setIsFetching] = useState(false);
  const observerRef = useRef(null);
  const callbackRef = useRef(callback);

  // Update callback ref when callback changes
  useEffect(() => {
    callbackRef.current = callback;
  }, [callback]);

  const handleObserver = useCallback((entries) => {
    const [target] = entries;
    
    if (target.isIntersecting && hasMore && !isFetching) {
      setIsFetching(true);
      callbackRef.current().finally(() => {
        setIsFetching(false);
      });
    }
  }, [hasMore, isFetching]);

  useEffect(() => {
    const element = observerRef.current;
    if (!element) return;

    const option = {
      root: null,
      rootMargin,
      threshold
    };

    const observer = new IntersectionObserver(handleObserver, option);
    observer.observe(element);

    return () => {
      observer.unobserve(element);
    };
  }, [handleObserver, rootMargin, threshold]);

  const reset = useCallback(() => {
    setIsFetching(false);
  }, []);

  return { 
    isFetching, 
    observerRef, 
    reset 
  };
}

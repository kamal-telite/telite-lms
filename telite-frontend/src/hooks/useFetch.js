import { useState, useEffect, useCallback } from 'react';
import { api, getErrorMessage } from '../services/client';

/**
 * Custom hook for data fetching with loading, error, and retry states
 * @param {string} url - The API endpoint to fetch
 * @param {object} options - Fetch options
 * @returns {object} - { data, loading, error, refetch }
 */
export function useFetch(url, options = {}) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await api.get(url, options);
      setData(response.data);
    } catch (err) {
      setError(getErrorMessage(err, 'Failed to fetch data'));
    } finally {
      setLoading(false);
    }
  }, [url, options]);

  useEffect(() => {
    if (url) {
      fetchData();
    }
  }, [url, fetchData]);

  return { data, loading, error, refetch: fetchData };
}

/**
 * Custom hook for POST requests
 * @param {string} url - The API endpoint
 * @returns {object} - { data, loading, error, execute }
 */
export function usePost(url) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const execute = useCallback(async (payload, options = {}) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await api.post(url, payload, options);
      setData(response.data);
      return response.data;
    } catch (err) {
      setError(getErrorMessage(err, 'Request failed'));
      throw err;
    } finally {
      setLoading(false);
    }
  }, [url]);

  return { data, loading, error, execute };
}

/**
 * Custom hook for PUT requests
 * @param {string} url - The API endpoint
 * @returns {object} - { data, loading, error, execute }
 */
export function usePut(url) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const execute = useCallback(async (payload, options = {}) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await api.put(url, payload, options);
      setData(response.data);
      return response.data;
    } catch (err) {
      setError(getErrorMessage(err, 'Request failed'));
      throw err;
    } finally {
      setLoading(false);
    }
  }, [url]);

  return { data, loading, error, execute };
}

/**
 * Custom hook for DELETE requests
 * @param {string} url - The API endpoint
 * @returns {object} - { data, loading, error, execute }
 */
export function useDelete(url) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const execute = useCallback(async (options = {}) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await api.delete(url, options);
      setData(response.data);
      return response.data;
    } catch (err) {
      setError(getErrorMessage(err, 'Request failed'));
      throw err;
    } finally {
      setLoading(false);
    }
  }, [url]);

  return { data, loading, error, execute };
}

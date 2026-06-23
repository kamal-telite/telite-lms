import { useState, useCallback, useEffect } from 'react';
import {
  fetchNotifications as apiFetchNotifications,
  fetchUnreadNotificationCount,
  markNotificationRead,
  markAllNotificationsRead
} from '../services/client';

export function useNotifications() {
  const [notifications, setNotifications] = useState({
    items: [],
    total: 0,
    page: 1,
    page_size: 20
  });
  const [unreadCount, setUnreadCount] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [isCountLoading, setIsCountLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchCount = useCallback(async () => {
    try {
      setIsCountLoading(true);
      const res = await fetchUnreadNotificationCount();
      setUnreadCount(res.count);
    } catch (err) {
      console.error("Failed to fetch unread count", err);
    } finally {
      setIsCountLoading(false);
    }
  }, []);

  const fetchList = useCallback(async (page = 1) => {
    try {
      setIsLoading(true);
      setError(null);
      // Pass pagination params if the backend supports it eventually
      const res = await apiFetchNotifications({ page, limit: 20 });
      // Guard against backend returning just an array vs a paginated object
      if (Array.isArray(res)) {
        setNotifications({
          items: res,
          total: res.length,
          page: 1,
          page_size: res.length
        });
      } else if (res.items) {
        setNotifications({
          items: res.items,
          total: res.total || res.items.length,
          page: res.page || 1,
          page_size: res.page_size || 20
        });
      }
    } catch (err) {
      console.error("Failed to fetch notifications", err);
      setError("Failed to load notifications.");
    } finally {
      setIsLoading(false);
    }
  }, []);

  const refresh = useCallback(async () => {
    await Promise.all([fetchCount(), fetchList(1)]);
  }, [fetchCount, fetchList]);

  const markRead = useCallback(async (id) => {
    try {
      await markNotificationRead(id);
      
      // Update local state optimistically
      setNotifications(prev => ({
        ...prev,
        items: prev.items.map(n => 
          n.id === id ? { ...n, is_read: true } : n
        )
      }));
      setUnreadCount(prev => Math.max(0, prev - 1));
      
    } catch (err) {
      console.error(`Failed to mark notification ${id} as read`, err);
      // Revert optimism by fetching true state
      fetchCount();
      fetchList();
    }
  }, [fetchCount, fetchList]);

  const markAllRead = useCallback(async () => {
    try {
      await markAllNotificationsRead();
      
      // Update local state optimistically
      setNotifications(prev => ({
        ...prev,
        items: prev.items.map(n => ({ ...n, is_read: true }))
      }));
      setUnreadCount(0);
      
    } catch (err) {
      console.error("Failed to mark all notifications as read", err);
      // Revert optimism by fetching true state
      fetchCount();
      fetchList();
    }
  }, [fetchCount, fetchList]);

  return {
    notifications,
    unreadCount,
    isLoading,
    isCountLoading,
    error,
    fetchCount,
    fetchList,
    refresh,
    markRead,
    markAllRead
  };
}

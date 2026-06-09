/**
 * Offline Sync Manager for SCORM/xAPI tracking.
 * Uses IndexedDB to store sync queues when offline.
 */

const DB_NAME = 'telite_offline_sync';
const DB_VERSION = 1;
const STORE_NAME = 'sync_queue';

class OfflineSyncManager {
  constructor() {
    this.db = null;
    this.isOnline = navigator.onLine;
    this.syncInProgress = false;

    // Listen for network changes
    window.addEventListener('online', this.handleOnline.bind(this));
    window.addEventListener('offline', this.handleOffline.bind(this));
    
    this.initDB();
  }

  initDB() {
    const request = indexedDB.open(DB_NAME, DB_VERSION);

    request.onerror = (event) => {
      console.error('OfflineSyncManager: Error opening IndexedDB', event.target.error);
    };

    request.onupgradeneeded = (event) => {
      const db = event.target.result;
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        // Create store with an auto-incrementing key
        db.createObjectStore(STORE_NAME, { keyPath: 'id', autoIncrement: true });
      }
    };

    request.onsuccess = (event) => {
      this.db = event.target.result;
      console.log('OfflineSyncManager: IndexedDB initialized.');
      // Attempt sync if we booted up online
      if (this.isOnline) {
        this.syncQueue();
      }
    };
  }

  handleOnline() {
    this.isOnline = true;
    console.log('OfflineSyncManager: Back online. Starting sync...');
    this.syncQueue();
  }

  handleOffline() {
    this.isOnline = false;
    console.log('OfflineSyncManager: Gone offline. Tracking will be queued locally.');
  }

  async queueTrackingEvent(cmid, protocol, events, status, score, timeSpent) {
    const payload = {
      cmid,
      protocol,
      events,
      status,
      score,
      time_spent_seconds: timeSpent,
      timestamp: Date.now(),
      retry_count: 0
    };

    if (this.isOnline) {
      try {
        await this.sendToServer(payload);
        return true;
      } catch (error) {
        console.warn('OfflineSyncManager: Server sync failed. Queuing locally.', error);
        return this.saveToLocalDB(payload);
      }
    } else {
      return this.saveToLocalDB(payload);
    }
  }

  saveToLocalDB(payload) {
    return new Promise((resolve, reject) => {
      if (!this.db) {
        reject(new Error('IndexedDB not initialized'));
        return;
      }
      const transaction = this.db.transaction([STORE_NAME], 'readwrite');
      const store = transaction.objectStore(STORE_NAME);
      const request = store.add(payload);

      request.onsuccess = () => resolve(true);
      request.onerror = (err) => reject(err);
    });
  }

  async syncQueue() {
    if (this.syncInProgress || !this.isOnline || !this.db) return;
    this.syncInProgress = true;

    try {
      const transaction = this.db.transaction([STORE_NAME], 'readonly');
      const store = transaction.objectStore(STORE_NAME);
      const request = store.getAll();

      request.onsuccess = async () => {
        const items = request.result;
        if (items.length === 0) {
          this.syncInProgress = false;
          return;
        }

        console.log(`OfflineSyncManager: Syncing ${items.length} items to server...`);

        // Send items one by one (or could be batched)
        for (const item of items) {
          try {
            await this.sendToServer(item);
            await this.removeFromLocalDB(item.id);
          } catch (error) {
            console.error(`OfflineSyncManager: Failed to sync item ${item.id}`, error);
            item.retry_count = (item.retry_count || 0) + 1;
            
            // Basic conflict resolution/retry policy
            if (item.retry_count < 5) {
              await this.updateLocalDB(item);
            } else {
              console.warn(`OfflineSyncManager: Item ${item.id} exceeded retry count. Dropping.`);
              await this.removeFromLocalDB(item.id);
            }
          }
        }
        this.syncInProgress = false;
      };
    } catch (error) {
      console.error('OfflineSyncManager: Sync error', error);
      this.syncInProgress = false;
    }
  }

  async sendToServer(payload) {
    const token = localStorage.getItem('token');
    if (!token) throw new Error('No auth token available');

    const res = await fetch('/api/player/tracking', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify(payload)
    });

    if (!res.ok) {
      throw new Error(`Server returned ${res.status}`);
    }
    return await res.json();
  }

  removeFromLocalDB(id) {
    return new Promise((resolve) => {
      const transaction = this.db.transaction([STORE_NAME], 'readwrite');
      const store = transaction.objectStore(STORE_NAME);
      store.delete(id).onsuccess = () => resolve(true);
    });
  }

  updateLocalDB(item) {
    return new Promise((resolve) => {
      const transaction = this.db.transaction([STORE_NAME], 'readwrite');
      const store = transaction.objectStore(STORE_NAME);
      store.put(item).onsuccess = () => resolve(true);
    });
  }
}

// Singleton instance
export const offlineSyncManager = new OfflineSyncManager();

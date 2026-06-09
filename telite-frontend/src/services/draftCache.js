/**
 * DraftCache.js
 * IndexedDB wrapper for saving local draft changes of the course builder.
 */

const DB_NAME = "telite_builder_cache";
const DB_VERSION = 1;
const STORE_NAME = "course_drafts";

let dbPromise = null;

function getDB() {
  if (dbPromise) return dbPromise;

  dbPromise = new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);

    request.onerror = () => reject(request.error);

    request.onsuccess = () => resolve(request.result);

    request.onupgradeneeded = (event) => {
      const db = event.target.result;
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME, { keyPath: "courseId" });
      }
    };
  });

  return dbPromise;
}

export async function saveDraftToCache(courseId, payload) {
  const db = await getDB();
  return new Promise((resolve, reject) => {
    const transaction = db.transaction(STORE_NAME, "readwrite");
    const store = transaction.objectStore(STORE_NAME);
    
    const draftData = {
      courseId,
      payload,
      updatedAt: new Date().toISOString()
    };

    const request = store.put(draftData);

    request.onsuccess = () => resolve(draftData);
    request.onerror = () => reject(request.error);
  });
}

export async function getDraftFromCache(courseId) {
  const db = await getDB();
  return new Promise((resolve, reject) => {
    const transaction = db.transaction(STORE_NAME, "readonly");
    const store = transaction.objectStore(STORE_NAME);
    
    const request = store.get(courseId);

    request.onsuccess = () => resolve(request.result || null);
    request.onerror = () => reject(request.error);
  });
}

export async function clearDraftFromCache(courseId) {
  const db = await getDB();
  return new Promise((resolve, reject) => {
    const transaction = db.transaction(STORE_NAME, "readwrite");
    const store = transaction.objectStore(STORE_NAME);
    
    const request = store.delete(courseId);

    request.onsuccess = () => resolve(true);
    request.onerror = () => reject(request.error);
  });
}

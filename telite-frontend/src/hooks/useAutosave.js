import { useEffect, useRef, useState, useCallback } from "react";
import { api } from "../services/client";
import { saveDraftToCache, clearDraftFromCache, getDraftFromCache } from "../services/draftCache";
import { useToast } from "../components/common/ui";

export function useAutosave({ courseId, data, onConflict, onBlocksSaved, onRecoverDraft }) {
  const { showToast } = useToast();
  const [saveState, setSaveState] = useState("idle"); // idle, saving, error, offline
  const [lastSaved, setLastSaved] = useState(null);
  const [pendingDraft, setPendingDraft] = useState(null);
  
  const timerRef = useRef(null);
  const previousDataRef = useRef(null);
  const isFirstMount = useRef(true);

  // Attempt to recover draft on mount
  useEffect(() => {
    async function recoverDraft() {
      const draft = await getDraftFromCache(courseId);
      if (draft && draft.payload) {
        setPendingDraft(draft);
        showToast("Unsaved changes recovered from local cache.", "warning");
      }
    }
    recoverDraft();
  }, [courseId, showToast]);

  const restoreDraft = useCallback(() => {
    if (!pendingDraft?.payload) return;
    onRecoverDraft?.(pendingDraft.payload);
    setPendingDraft(null);
    showToast("Recovered draft applied. Autosave will sync it shortly.", "success");
  }, [onRecoverDraft, pendingDraft, showToast]);

  const discardDraft = useCallback(async () => {
    await clearDraftFromCache(courseId);
    setPendingDraft(null);
    showToast("Recovered draft discarded.", "info");
  }, [courseId, showToast]);

  const clearConflict = useCallback(() => {
    setSaveState("idle");
  }, []);

  const performSave = useCallback(async (payload, hasRetriedLock = false) => {
    setSaveState("saving");
    try {
      // Filter: only send blocks that have a real id OR are new (no id) and not deleted.
      // Deleted blocks with no id never need to be sent — they were never persisted.
      const blocksToSend = payload
        .filter(b => !(b.is_deleted && !b.id))   // skip deleted new blocks
        .map(b => ({
          ...b,
          media_asset_id: b.media_asset_id || b.settings?.asset_id || null,
          // Strip _tempId — backend doesn't know about it
          id: b.id || null,
        }));

      // Optimistic cache write first
      await saveDraftToCache(courseId, payload);

      // Attempt backend sync
      const response = await api.put(`/authoring/courses/${courseId}/blocks`, {
        blocks: blocksToSend
      });

      // Back-fill real IDs onto newly created blocks so subsequent saves update, not duplicate
      const saved = response.data?.blocks || [];
      if (saved.length > 0 && onBlocksSaved) {
        onBlocksSaved(saved);
      }

      // Clear cache on success
      await clearDraftFromCache(courseId);
      setPendingDraft(null);
      setLastSaved(new Date());
      setSaveState("idle");
    } catch (err) {
      if (err.response && err.response.status === 409) {
        // Optimistic Concurrency Conflict
        setSaveState("conflict");
        if (onConflict) onConflict(err.response.data, payload);
      } else if (err.response && err.response.status === 403) {
        // Lock expired — surface clearly rather than silently caching
        if (!hasRetriedLock) {
          try {
            await api.post(`/authoring/courses/${courseId}/lock`);
            await performSave(payload, true);
            return;
          } catch {
          }
        }
        setSaveState("error");
        showToast("Editor lock expired. Please refresh the page to continue editing.", "error");
      } else {
        // Network/Server Error - Keep in local draft
        setSaveState("offline");
        showToast("Offline. Changes saved locally.", "warning");
      }
    }
  }, [courseId, onConflict, onBlocksSaved, showToast]);

  useEffect(() => {
    if (isFirstMount.current) {
      isFirstMount.current = false;
      previousDataRef.current = data;
      return;
    }

    // Basic deep equality check for changes (simplified for this context)
    const hasChanged = JSON.stringify(data) !== JSON.stringify(previousDataRef.current);
    if (!hasChanged) return;

    previousDataRef.current = data;

    if (timerRef.current) {
      clearTimeout(timerRef.current);
    }

    // 2000ms debounce
    timerRef.current = setTimeout(() => {
      performSave(data);
    }, 2000);

    return () => clearTimeout(timerRef.current);
  }, [data, performSave]);

  return {
    saveState,
    lastSaved,
    pendingDraft,
    restoreDraft,
    discardDraft,
    clearConflict,
    forceSave: () => performSave(data),
  };
}

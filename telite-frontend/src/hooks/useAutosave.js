import { useEffect, useRef, useState, useCallback } from "react";
import { api } from "../services/client";
import { saveDraftToCache, clearDraftFromCache, getDraftFromCache } from "../services/draftCache";
import { useToast } from "../components/common/ui";

function errorDetail(error) {
  const detail = error?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map((item) => item?.msg || item).join(" ");
  return error?.response?.data?.message || error?.message || "";
}

function isCapabilityError(error) {
  const detail = errorDetail(error).toLowerCase();
  return detail.includes("capability") || detail.includes("permission denied") || detail.includes("required capability");
}

export function useAutosave({ courseId, data, onConflict, onBlocksSaved, onRecoverDraft }) {
  const { showToast } = useToast();
  const [saveState, setSaveState] = useState("idle");
  const [lastSaved, setLastSaved] = useState(null);
  const [pendingDraft, setPendingDraft] = useState(null);

  const timerRef = useRef(null);
  const previousDataRef = useRef(null);
  const isFirstMount = useRef(true);

  useEffect(() => {
    async function recoverDraft() {
      const draft = await getDraftFromCache(courseId);
      if (draft?.payload) {
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
      const blocksToSend = payload
        .filter((block) => !(block.is_deleted && !block.id))
        .map((block) => ({
          id: block.id || null,
          module_id: block.module_id,
          block_type: block.block_type,
          content: block.content || "",
          media_asset_id: block.media_asset_id || block.settings?.asset_id || null,
          settings: block.settings || {},
          sort_order: Number.isFinite(block.sort_order) ? block.sort_order : 0,
          is_deleted: Boolean(block.is_deleted),
        }));

      await saveDraftToCache(courseId, payload);

      const response = await api.put(`/authoring/courses/${courseId}/blocks`, {
        blocks: blocksToSend,
      });

      const saved = response.data?.blocks || [];
      if (saved.length > 0 && onBlocksSaved) {
        onBlocksSaved(saved);
      }

      await clearDraftFromCache(courseId);
      setPendingDraft(null);
      setLastSaved(new Date());
      setSaveState("idle");
    } catch (error) {
      if (error.response?.status === 409) {
        setSaveState("conflict");
        onConflict?.(error.response.data, payload);
        return;
      }

      if (error.response?.status === 403) {
        if (isCapabilityError(error)) {
          setSaveState("error");
          showToast(`Permission denied: ${errorDetail(error)}`, "error");
          return;
        }

        if (!hasRetriedLock) {
          try {
            await api.post(`/authoring/courses/${courseId}/lock`);
            await performSave(payload, true);
            return;
          } catch (lockError) {
            console.debug("Unable to renew editor lock before autosave retry.", lockError);
          }
        }

        setSaveState("error");
        showToast("Editor lock expired. Please refresh the page to continue editing.", "error");
        return;
      }

      const detail = errorDetail(error);
      if (error.response?.status === 400 || error.response?.status === 422) {
        setSaveState("error");
        showToast(detail || "Could not save quiz content. Check your questions and try again.", "error");
        return;
      }

      setSaveState("offline");
      showToast(
        detail
          ? `Autosave failed: ${detail}`
          : "Autosave failed. Your changes are stored locally and will retry when possible.",
        "warning"
      );
    }
  }, [courseId, onConflict, onBlocksSaved, showToast]);

  useEffect(() => {
    if (isFirstMount.current) {
      isFirstMount.current = false;
      previousDataRef.current = data;
      return undefined;
    }

    const hasChanged = JSON.stringify(data) !== JSON.stringify(previousDataRef.current);
    if (!hasChanged) return undefined;

    previousDataRef.current = data;

    if (timerRef.current) {
      clearTimeout(timerRef.current);
    }

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

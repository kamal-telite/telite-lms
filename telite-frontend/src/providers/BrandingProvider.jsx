import React, { createContext, useContext, useEffect, useState } from "react";
import { fetchBranding } from "../services/client";
import { getTenantSlugFromUrl } from "../utils/tenant";
import { ThemeEngine } from "../utils/ThemeEngine";

const BrandingContext = createContext({
  branding: null,
  loading: false,
  tenantSlug: null,
});

export function BrandingProvider({ session, children }) {
  const [branding, setBranding] = useState(null);
  const [loading, setLoading] = useState(false);
  const tenantSlug = getTenantSlugFromUrl(session?.user);

  useEffect(() => {
    if (!tenantSlug) {
      setBranding(null);
      ThemeEngine.resetBrandingStyles();
      return undefined;
    }

    let cancelled = false;

    async function loadBranding() {
      setLoading(true);
      try {
        const data = await fetchBranding(tenantSlug);
        if (cancelled) return;
        setBranding(data);
        ThemeEngine.applyBrandingStyles(data);
      } catch (err) {
        console.warn(`[Branding] Failed to load branding for tenant "${tenantSlug}":`, err);
        if (cancelled) return;
        setBranding(null);
        ThemeEngine.resetBrandingStyles();
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    loadBranding();

    return () => {
      cancelled = true;
    };
  }, [tenantSlug]);

  // Live preview postMessage listener
  useEffect(() => {
    function handleMessage(event) {
      // Validate that this is our preview message
      if (event.data && event.data.type === 'UPDATE_BRANDING_PREVIEW') {
        const previewBranding = event.data.branding;
        setBranding(prev => ({ ...prev, ...previewBranding }));
        ThemeEngine.applyBrandingStyles(previewBranding);
      }
    }
    window.addEventListener('message', handleMessage);
    return () => window.removeEventListener('message', handleMessage);
  }, []);

  return (
    <BrandingContext.Provider value={{ branding, loading, tenantSlug }}>
      {children}
    </BrandingContext.Provider>
  );
}

export function useBranding() {
  return useContext(BrandingContext);
}

import React, { useMemo, Suspense } from 'react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { MockContextProviders } from './MockContextProviders';

// Use React.lazy to break circular dependencies (SuperAdminPage -> BrandingSettingsTab -> RuntimePreviewShell -> SuperAdminPage)
const LearnerPage = React.lazy(() => import('../../../pages/learner/LearnerPage'));
const CategoryAdminPage = React.lazy(() => import('../../../pages/company/CategoryAdminPage'));
const SuperAdminPage = React.lazy(() => import('../../../pages/super-admin/SuperAdminPage'));
const Login = React.lazy(() => import('../../../pages/auth/Login'));

// Import branding provider to inject the draft theme
import { BrandingProvider } from '../../../providers/BrandingProvider';

export function RuntimePreviewShell({ role, draftBranding }) {
  // Inject the draft branding configuration exactly as the global provider would
  const brandingConfig = useMemo(() => ({
    status: 'success',
    branding: {
      primary_color: draftBranding.primary_color || '#2563EB',
      secondary_color: draftBranding.secondary_color || '#111827',
      font: draftBranding.font_family || 'Inter',
      theme: draftBranding.theme_mode || 'light',
      logo: draftBranding.logo || draftBranding.logo_url,
      favicon: draftBranding.favicon || draftBranding.favicon_url,
      banner: draftBranding.banner || draftBranding.login_banner_url,
      terminology: draftBranding.terminology || {},
    }
  }), [draftBranding]);

  return (
    <div style={{ width: '100%', height: '100%', overflow: 'auto', background: 'var(--background)' }}>
      {/* 
        The BrandingProvider intercepts and applies the CSS variables.
        MemoryRouter isolates navigation so clicking links doesn't change the main browser URL.
      */}
      <BrandingProvider preloadedConfig={brandingConfig}>
        <MockContextProviders role={role}>
          <MemoryRouter initialEntries={['/']}>
            <Suspense fallback={<div style={{ padding: 40, textAlign: 'center' }}>Loading preview...</div>}>
              <Routes>
                {role === 'learner' && <Route path="/*" element={<LearnerPage previewMode />} />}
                {role === 'category_admin' && <Route path="/*" element={<CategoryAdminPage previewMode />} />}
                {role === 'super_admin' && <Route path="/*" element={<SuperAdminPage previewMode />} />}
                {role === 'public' && <Route path="/*" element={<Login previewMode />} />}
              </Routes>
            </Suspense>
          </MemoryRouter>
        </MockContextProviders>
      </BrandingProvider>
    </div>
  );
}

import { createContext, useContext, useState, useEffect } from 'react';

const ScrollContext = createContext(null);

export function ScrollProvider({ children }) {
  const [platform, setPlatform] = useState('unknown');
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(false);
  
  useEffect(() => {
    if (typeof window !== 'undefined') {
      // Basic platform detection
      const isMac = navigator.userAgent.toUpperCase().indexOf('MAC') >= 0;
      setPlatform(isMac ? 'macos' : 'windows');

      // Check for reduced motion accessibility preference
      const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
      setPrefersReducedMotion(mediaQuery.matches);

      const handleChange = (e) => setPrefersReducedMotion(e.matches);
      
      if (mediaQuery.addEventListener) {
        mediaQuery.addEventListener('change', handleChange);
      } else {
        mediaQuery.addListener(handleChange);
      }

      return () => {
        if (mediaQuery.removeEventListener) {
          mediaQuery.removeEventListener('change', handleChange);
        } else {
          mediaQuery.removeListener(handleChange);
        }
      };
    }
  }, []);

  return (
    <ScrollContext.Provider value={{ platform, prefersReducedMotion }}>
      {/* Root wrapper is styled via CSS to prevent nested body overflow issues */}
      <div 
        className="telite-scroll-root"
        data-platform={platform}
        data-reduced-motion={prefersReducedMotion}
      >
        {children}
      </div>
    </ScrollContext.Provider>
  );
}

export function useScrollContext() {
  const context = useContext(ScrollContext);
  if (!context) {
    throw new Error('useScrollContext must be used within a ScrollProvider');
  }
  return context;
}

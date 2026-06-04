import { adjustColorBrightness } from "./color";

export class ThemeEngine {
  static applyBrandingStyles(branding) {
    const root = document.documentElement;

    // 1. Primary branding colors
    if (branding.primary_color) {
      const primary = branding.primary_color.trim();
      root.style.setProperty("--primary", primary);
      root.style.setProperty("--primary-dark", adjustColorBrightness(primary, -15));
      root.style.setProperty("--primary-light", adjustColorBrightness(primary, 15));
    }

    // 2. Secondary branding colors
    if (branding.secondary_color) {
      const secondary = branding.secondary_color.trim();
      root.style.setProperty("--secondary-color", secondary);
    }

    // 3. Custom Typography / Google Font injection
    if (branding.font_family || branding.font) {
      const fontName = (branding.font_family || branding.font).trim();
      
      // Inject Google Font link dynamically if not already present
      const fontId = `branding-font-${fontName.replace(/\\s+/g, "-").toLowerCase()}`;
      if (!document.getElementById(fontId)) {
        const link = document.createElement("link");
        link.id = fontId;
        link.rel = "stylesheet";
        link.href = `https://fonts.googleapis.com/css2?family=${encodeURIComponent(fontName)}:wght@300;400;500;600;700&display=swap`;
        document.head.appendChild(link);
      }
      
      root.style.setProperty("--font-body", `'${fontName}', 'Inter', sans-serif`);
      root.style.setProperty("--font-display", `'${fontName}', 'Inter', sans-serif`);
    }

    // 4. Custom Favicon injection
    if (branding.favicon) {
      let link = document.querySelector("link[rel~='icon']");
      if (!link) {
        link = document.createElement("link");
        link.rel = "icon";
        document.head.appendChild(link);
      }
      link.href = branding.favicon.trim();
    }

    // 5. Custom dynamic document Title
    if (branding.seo_title || branding.organization) {
      document.title = branding.seo_title || `${branding.organization} | Telite LMS`;
    }
  }

  static resetBrandingStyles() {
    const root = document.documentElement;
    
    // Remove all customized inline token styles
    root.style.removeProperty("--primary");
    root.style.removeProperty("--primary-dark");
    root.style.removeProperty("--primary-light");
    root.style.removeProperty("--secondary-color");
    root.style.removeProperty("--font-body");
    root.style.removeProperty("--font-display");

    // Reset standard favicon
    let link = document.querySelector("link[rel~='icon']");
    if (link) {
      link.href = "/favicon.ico";
    }

    // Reset standard document title
    document.title = "Telite Systems LMS";
  }
}

/**
 * Utility to dynamically load external scripts
 */
export const loadScript = (id, src) => {
  return new Promise((resolve, reject) => {
    if (document.getElementById(id)) {
      resolve(window);
      return;
    }

    const script = document.createElement("script");
    script.src = src;
    script.id = id;
    script.async = true;
    script.onload = () => resolve(window);
    script.onerror = () => reject(new Error(`Failed to load script: ${src}`));
    document.body.appendChild(script);
  });
};

export const canUseWebGL = () => {
  try {
    const canvas = document.createElement("canvas");
    const gl =
      canvas.getContext("webgl", { powerPreference: "low-power" }) ||
      canvas.getContext("experimental-webgl", { powerPreference: "low-power" });
    return !!gl;
  } catch {
    return false;
  }
};

/**
 * Specifically for Vanta and its dependency Three.js
 */
export const loadVantaDependencies = async () => {
  try {
    // 1. Ensure Three.js is loaded first (Vanta dependency)
    if (!window.THREE) {
      await loadScript("three-js", "https://cdnjs.cloudflare.com/ajax/libs/three.js/r134/three.min.js");
    }

    // 2. Load Vanta NET and WAVES in parallel
    await Promise.all([
      loadScript("vanta-net", "https://cdn.jsdelivr.net/npm/vanta@latest/dist/vanta.net.min.js"),
      loadScript("vanta-waves", "https://cdn.jsdelivr.net/npm/vanta@latest/dist/vanta.waves.min.js")
    ]);

    return window.VANTA;
  } catch (error) {
    console.error("Vanta load error:", error);
    return null;
  }
};

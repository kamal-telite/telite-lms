/**
 * Manipulates the brightness of a hex color by a specified percentage.
 *
 * @param {string} hex - The hex color code (e.g., "#4648d4" or "4648d4").
 * @param {number} percent - The percentage to adjust (negative to darken, positive to lighten).
 * @returns {string} The adjusted hex color (e.g., "#3b3db4").
 */
export function adjustColorBrightness(hex, percent) {
  let cleanHex = hex.replace("#", "");

  // Expand shorthand hex (e.g. "03F" -> "0033FF")
  if (cleanHex.length === 3) {
    cleanHex = cleanHex
      .split("")
      .map((char) => char + char)
      .join("");
  }

  if (cleanHex.length !== 6) {
    return hex; // Return original if invalid
  }

  let R = parseInt(cleanHex.substring(0, 2), 16);
  let G = parseInt(cleanHex.substring(2, 4), 16);
  let B = parseInt(cleanHex.substring(4, 6), 16);

  R = parseInt((R * (100 + percent)) / 100);
  G = parseInt((G * (100 + percent)) / 100);
  B = parseInt((B * (100 + percent)) / 100);

  // Clamp color channels between 0 and 255
  R = Math.max(0, Math.min(255, R));
  G = Math.max(0, Math.min(255, G));
  B = Math.max(0, Math.min(255, B));

  const rHex = R.toString(16).padStart(2, "0");
  const gHex = G.toString(16).padStart(2, "0");
  const bHex = B.toString(16).padStart(2, "0");

  return `#${rHex}${gHex}${bHex}`;
}

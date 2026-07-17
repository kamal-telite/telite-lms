/**
 * Utility functions for handling embed URLs
 */

/**
 * Converts a YouTube watch URL to embed format
 * @param {string} url - The YouTube URL to convert
 * @returns {string|null} - The embed URL or null if not a YouTube URL
 */
export function convertYouTubeToEmbed(url) {
  if (!url || typeof url !== 'string') return null;

  // Match YouTube watch URLs
  const watchMatch = url.match(/(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/watch\?v=|youtu\.be\/)([a-zA-Z0-9_-]+)/);
  if (watchMatch) {
    return `https://www.youtube.com/embed/${watchMatch[1]}`;
  }

  // Match YouTube short URLs
  const shortMatch = url.match(/(?:https?:\/\/)?(?:www\.)?youtu\.be\/([a-zA-Z0-9_-]+)/);
  if (shortMatch) {
    return `https://www.youtube.com/embed/${shortMatch[1]}`;
  }

  // Already an embed URL, return as-is
  if (url.includes('youtube.com/embed/')) {
    return url;
  }

  return null;
}

/**
 * Validates if a URL is suitable for embedding
 * @param {string} url - The URL to validate
 * @returns {object} - Validation result with isValid and error message
 */
export function validateEmbedUrl(url) {
  if (!url || typeof url !== 'string' || !url.trim()) {
    return { isValid: false, error: 'URL is required' };
  }

  const trimmedUrl = url.trim();

  // Check if it's a valid URL format
  try {
    new URL(trimmedUrl);
  } catch (e) {
    return { isValid: false, error: 'Invalid URL format' };
  }

  // Check for HTTPS (recommended but not required)
  if (!trimmedUrl.startsWith('https://') && !trimmedUrl.startsWith('http://')) {
    return { isValid: false, error: 'URL must start with http:// or https://' };
  }

  // Check for common embeddable domains
  const embeddableDomains = [
    'youtube.com',
    'youtu.be',
    'vimeo.com',
    'dailymotion.com',
    'wistia.com',
    'soundcloud.com',
    'spotify.com',
    'google.com',
    'docs.google.com',
    'slides.google.com',
    'forms.google.com',
  ];

  const urlObj = new URL(trimmedUrl);
  const domain = urlObj.hostname.replace('www.', '');

  const isEmbeddable = embeddableDomains.some(d => domain === d || domain.endsWith(`.${d}`));

  if (!isEmbeddable) {
    return { 
      isValid: false, 
      error: 'Unsupported URL. Please use YouTube, Vimeo, or other supported embed services.' 
    };
  }

  return { isValid: true, error: null };
}

/**
 * Converts a URL to its embed format if needed
 * @param {string} url - The URL to convert
 * @returns {string} - The embed-ready URL
 */
export function getEmbedUrl(url) {
  if (!url) return url;

  // Try YouTube conversion first
  const youtubeEmbed = convertYouTubeToEmbed(url);
  if (youtubeEmbed) return youtubeEmbed;

  // Return original URL for other services
  return url;
}

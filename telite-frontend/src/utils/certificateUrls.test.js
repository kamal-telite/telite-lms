import test from 'node:test';
import assert from 'node:assert/strict';

import { buildApiUrl, buildCertificateDownloadUrl } from './certificateUrls.js';

test('buildApiUrl resolves certificate routes against a configured backend base URL', () => {
  const url = buildApiUrl('/api/certificates/course-123/download', 'https://api.example.com');
  assert.equal(url, 'https://api.example.com/api/certificates/course-123/download');
});

test('buildCertificateDownloadUrl preserves inline flag and query string', () => {
  const url = buildCertificateDownloadUrl('course-123', { inline: true, baseUrl: 'https://api.example.com' });
  assert.equal(url, 'https://api.example.com/api/certificates/course-123/download?inline=true');
});

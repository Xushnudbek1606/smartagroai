import { afterEach, describe, expect, it, vi } from 'vitest';

// The module reads VITE_API_URL at import time, so each case re-imports it with
// the environment it wants to simulate.
async function loadApi(viteApiUrl?: string) {
  vi.resetModules();
  vi.unstubAllEnvs();
  if (viteApiUrl) vi.stubEnv('VITE_API_URL', viteApiUrl);
  return await import('../src/services/api');
}

describe('assetUrl (uploaded photos and avatars)', () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.resetModules();
  });

  it('keeps backend-relative paths in development, where Vite proxies /static', async () => {
    const { API_ORIGIN, assetUrl } = await loadApi();
    expect(API_ORIGIN).toBe('');
    expect(assetUrl('/static/plant_images/a.jpg')).toBe('/static/plant_images/a.jpg');
  });

  it('resolves backend-relative paths against the API host in production', async () => {
    const { API_ORIGIN, assetUrl } = await loadApi('https://api.example.com/api/v1');
    expect(API_ORIGIN).toBe('https://api.example.com');
    expect(assetUrl('/static/plant_images/a.jpg')).toBe(
      'https://api.example.com/static/plant_images/a.jpg',
    );
    expect(assetUrl('/static/avatars/b.png')).toBe('https://api.example.com/static/avatars/b.png');
  });

  it('passes through absolute URLs and empty values', async () => {
    const { assetUrl } = await loadApi('https://api.example.com/api/v1');
    expect(assetUrl('https://cdn.example.com/a.png')).toBe('https://cdn.example.com/a.png');
    expect(assetUrl('data:image/png;base64,AAA')).toBe('data:image/png;base64,AAA');
    expect(assetUrl(null)).toBe('');
    expect(assetUrl(undefined)).toBe('');
  });

  it('keeps relative paths relative when the API is configured with a relative base', async () => {
    const { API_ORIGIN, assetUrl } = await loadApi('/api/v1');
    expect(API_ORIGIN).toBe('');
    expect(assetUrl('/static/plant_images/a.jpg')).toBe('/static/plant_images/a.jpg');
  });
});

import { afterEach, describe, expect, it } from 'vitest';
import { buildUrl } from './api';

const env = import.meta.env as { VITE_API_BASE_URL?: string };
const originalBase = env.VITE_API_BASE_URL;

afterEach(() => {
  if (originalBase === undefined) {
    delete env.VITE_API_BASE_URL;
  } else {
    env.VITE_API_BASE_URL = originalBase;
  }
});

describe('buildUrl', () => {
  it('normalises whitespace around base and path while avoiding duplicate slashes', () => {
    env.VITE_API_BASE_URL = ' https://api.example.com/v1/ ';

    expect(buildUrl('  /invoices  ')).toBe('https://api.example.com/v1/invoices');
  });

  it('falls back to a relative path when the base URL is whitespace', () => {
    env.VITE_API_BASE_URL = '   ';

    expect(buildUrl(' invoices ')).toBe('/invoices');
  });

  it('uses relative paths when no base URL is set', () => {
    delete env.VITE_API_BASE_URL;

    expect(buildUrl('workspace/items')).toBe('/workspace/items');
    expect(buildUrl('   /workspace/items  ')).toBe('/workspace/items');
  });
});

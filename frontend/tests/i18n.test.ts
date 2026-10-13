import { describe, expect, it } from 'vitest';
import uzLatn from '../src/locales/uz-Latn/translation.json';
import uzCyrl from '../src/locales/uz-Cyrl/translation.json';
import en from '../src/locales/en/translation.json';
import ru from '../src/locales/ru/translation.json';

type Json = { [key: string]: string | Json };

function flatten(obj: Json, prefix = ''): Record<string, string> {
  const out: Record<string, string> = {};
  for (const [key, value] of Object.entries(obj)) {
    const path = prefix ? `${prefix}.${key}` : key;
    if (typeof value === 'string') out[path] = value;
    else Object.assign(out, flatten(value as Json, path));
  }
  return out;
}

const locales = {
  'uz-Latn': flatten(uzLatn as Json),
  'uz-Cyrl': flatten(uzCyrl as Json),
  en: flatten(en as Json),
  ru: flatten(ru as Json),
};

describe('translation coverage', () => {
  const reference = Object.keys(locales['uz-Latn']).sort();

  it('uz-Latn (reference locale) is non-empty', () => {
    expect(reference.length).toBeGreaterThan(100);
  });

  for (const [name, dict] of Object.entries(locales)) {
    if (name === 'uz-Latn') continue;

    it(`${name} has every uz-Latn key`, () => {
      const keys = Object.keys(dict).sort();
      const missing = reference.filter((k) => !(k in dict));
      expect(missing, `missing keys in ${name}: ${missing.join(', ')}`).toEqual([]);
      // no extra keys either (keeps locales in sync)
      const extra = keys.filter((k) => !reference.includes(k));
      expect(extra, `extra keys in ${name}: ${extra.join(', ')}`).toEqual([]);
    });

    it(`${name} has no empty translations`, () => {
      const empty = Object.entries(dict)
        .filter(([, v]) => !v || !v.trim())
        .map(([k]) => k);
      expect(empty, `empty values in ${name}: ${empty.join(', ')}`).toEqual([]);
    });

    it(`${name} keeps interpolation placeholders`, () => {
      for (const key of reference) {
        const ref = locales['uz-Latn'][key] || '';
        const target = dict[key] || '';
        const refVars = [...ref.matchAll(/\{\{(\w+)\}\}/g)].map((m) => m[1]).sort();
        const targetVars = [...target.matchAll(/\{\{(\w+)\}\}/g)].map((m) => m[1]).sort();
        expect(targetVars, `placeholder mismatch for ${key} in ${name}`).toEqual(refVars);
      }
    });
  }

  it('uz-Cyrl contains no Latin-script text (except allowed brand names)', () => {
    // brand names, technical acronyms and file formats that stay in Latin script
    const allowedWords = new Set([
      'SmartAgroAI', 'Telegram', 'Redis', 'API', 'AI', 'JPG', 'JPEG', 'PNG', 'WEBP',
      'HTTP', 'HTTPS', 'WebSocket', 'OpenWeatherMap', 'SmartAgroAIBot', 'deg', 'Pro',
    ]);
    const offenders: string[] = [];
    for (const [key, value] of Object.entries(locales['uz-Cyrl'])) {
      for (const token of value.split(/\s+/)) {
        if (token.includes('{{')) continue; // interpolation placeholders
        if (token.startsWith('/')) continue; // bot commands like /start
        const bare = token.replace(/^[^\w@]+|[^\w@.]+$/g, '');
        if (!bare) continue;
        if (/^[A-Z][A-Z0-9_]+$/.test(bare)) continue; // env vars like AI_API_KEY
        const runs = bare.match(/[A-Za-z]{2,}/g) || [];
        for (const run of runs) {
          if (!allowedWords.has(run)) {
            offenders.push(`${key}: "${token}"`);
            break;
          }
        }
      }
    }
    expect(offenders, `Latin text found in uz-Cyrl:\n${offenders.join('\n')}`).toEqual([]);
  });
});

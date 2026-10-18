import { describe, expect, it } from 'vitest';
import { createInstance } from 'i18next';
import en from './en/common.json';
import ru from './ru/common.json';

function flatten(value: Record<string, unknown>, prefix = ''): Record<string, string> {
  return Object.fromEntries(Object.entries(value).flatMap(([key, child]) => {
    const path = prefix ? `${prefix}.${key}` : key;
    return typeof child === 'string' ? [[path, child]] : Object.entries(flatten(child as Record<string, unknown>, path));
  }));
}

describe('Russian interface resources', () => {
  const english = flatten(en);
  const russian = flatten(ru);

  it('covers the complete core patient journey', () => {
    const core = ['common', 'nav', 'dashboard', 'patients', 'examinations', 'examination_detail', 'biomarkers', 'documents_explorer', 'auth', 'account', 'patient_form'];
    for (const key of Object.keys(english).filter(key => core.includes(key.split('.')[0]))) {
      expect(russian[key], key).toBeTruthy();
    }
  });

  it('keeps interpolation variables and valid source keys', () => {
    for (const [key, value] of Object.entries(russian)) {
      expect(english[key], key).toBeDefined();
      expect(value.trim(), key).not.toBe('');
      expect(value.match(/{{[^}]+}}/g)?.sort() ?? [], key)
        .toEqual(english[key].match(/{{[^}]+}}/g)?.sort() ?? []);
    }
  });

  it('switches languages and falls back to English in untranslated sections', async () => {
    const i18n = createInstance();
    await i18n.init({ lng: 'ru', fallbackLng: 'en', resources: { en: { translation: en }, ru: { translation: ru } } });
    expect(i18n.t('common.biomarkers')).toBe('Показатели');
    expect(i18n.t('settings.display_stored')).toBe('Сохранённая точность, без округления');
    expect(i18n.t('patients.no_results', { term: 'sample' })).toContain('sample');
    expect(i18n.t('settings.ai.caps_text')).toBe(en.settings.ai.caps_text);
    await i18n.changeLanguage('en');
    expect(i18n.t('common.biomarkers')).toBe('Biomarkers');
  });
});

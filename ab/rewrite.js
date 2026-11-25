// Preload (all frames) for the A/B comparison: wraps every Intl service's resolvedOptions() so the
// `locale` it reports goes through a variant's mapping. A and A2 install the same wrapper with the
// identity mapping, so pages that check for tampering see the same wrapper in A and B. The variant is
// read when called: B sets window.__abVariant (applied), A sets window.__abCount (counted only), both
// non-enumerable. window.__abRewrites counts reads the variant changed (B) or would change (A).
(() => {
  if (typeof Intl !== 'object' || window.__abInstalled) return;
  Object.defineProperty(window, '__abInstalled', { value: true });
  const Locale = Intl.Locale, maximize = Intl.Locale.prototype.maximize;
  const baseName = Object.getOwnPropertyDescriptor(Intl.Locale.prototype, 'baseName').get;
  const max = tag => Reflect.apply(baseName, Reflect.apply(maximize, new Locale(tag), []), []);
  const TAG = /^([a-z]{2,3})(?:-([A-Z][a-z]{3}))?(?:-([A-Z]{2}|\d{3}))?((?:-[0-9A-Za-z]{1,8})*)$/;
  const VARIANTS = {
    // Henri's stress test: language only; Chinese keeps the script (zh-TW/zh-HK -> zh-Hant, zh-CN -> zh).
    B1(tag) {
      const m = TAG.exec(tag);
      if (!m) return tag;
      const [, lang, script, region, rest] = m;
      if (lang === 'zh') {
        const hant = script ? script === 'Hant' : ['TW', 'HK', 'MO'].includes(region);
        return (hant ? 'zh-Hant' : 'zh') + rest;
      }
      return lang + (script ? '-' + script : '') + rest;
    },
    // Likely-subtags dedup (my approximation of the ICU4X model): the first of lang, lang-Script
    // that maximizes to the same tag (en-US -> en, zh-TW -> zh-Hant, ar-EG -> ar; en-GB, zh-HK kept).
    B2(tag) {
      const m = TAG.exec(tag);
      if (!m) return tag;
      const [, lang, script, region, rest] = m;
      const base = lang + (script ? '-' + script : '') + (region ? '-' + region : '');
      try {
        const full = max(base);
        const s = full.split('-')[1];
        for (const cand of [lang, lang + '-' + s]) {
          if (max(cand) === full) return cand + rest;
        }
      } catch (e) {}
      return tag;
    },
  };
  let rewrites = 0;
  Object.defineProperty(window, '__abRewrites', { get: () => rewrites });
  const nativeToString = Function.prototype.toString;
  const fakes = new WeakMap();
  Function.prototype.toString = new Proxy(nativeToString, {
    apply(t, self, a) { return Reflect.apply(t, fakes.get(self) || self, a); }
  });
  fakes.set(Function.prototype.toString, nativeToString);
  for (const svc of ['Collator', 'DateTimeFormat', 'NumberFormat', 'PluralRules', 'RelativeTimeFormat',
                     'ListFormat', 'Segmenter', 'DisplayNames', 'DurationFormat']) {
    const C = Intl[svc];
    if (typeof C !== 'function') continue;
    const orig = C.prototype.resolvedOptions;
    const w = { resolvedOptions() {
      const r = Reflect.apply(orig, this, arguments);
      const v = window.__abVariant, f = VARIANTS[v || window.__abCount];
      if (f && r && typeof r.locale === 'string') {
        const mapped = f(r.locale);
        if (mapped !== r.locale) {
          rewrites++;
          if (v) r.locale = mapped;
        }
      }
      return r;
    } }.resolvedOptions;
    fakes.set(w, orig);
    Object.defineProperty(C.prototype, 'resolvedOptions', { value: w, writable: true, configurable: true, enumerable: false });
  }
})();

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
  // CLDR-derived tables (cldr_table.py), substituted by the runners.
  const CLDR = /*CLDR_TABLE*/null;
  const split = tag => { const m = TAG.exec(tag); return m && { lang: m[1], script: m[2], region: m[3], rest: m[4] }; };
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
    // Henri's rule: non-Collator objects constructed without a locales argument drop the region when
    // the CLDR main/ file for the region has no data beyond its parent (en-US -> en, zh-TW -> zh-Hant).
    B3(tag, svc, noArg) {
      const m = split(tag);
      if (svc === 'Collator' || !noArg || !m) return tag;
      const to = CLDR.mainDrop[tag.slice(0, tag.length - m.rest.length)];
      return to ? to + m.rest : tag;
    },
    // Collator, any construction: drop the region where CLDR collation/ has nothing for it
    // (en-US, en-GB, ar-SA, zh-CN), and report zh-TW/zh-HK as zh-Hant (C1) or zh-u-co-stroke (C2).
    C1(tag, svc) { return svc === 'Collator' ? collator(tag, 'zh-Hant') : tag; },
    C2(tag, svc) { return svc === 'Collator' ? collator(tag, 'zh-u-co-stroke') : tag; },
    // Segmenter reports und (SU) or its language only, so it differs from DateTimeFormat (SL).
    SU(tag, svc) { return svc === 'Segmenter' ? 'und' : tag; },
    SL(tag, svc) { const m = split(tag); return svc === 'Segmenter' && m ? m.lang : tag; },
  };
  const collator = (tag, hant) => {
    const m = split(tag);
    if (!m) return tag;
    const base = tag.slice(0, tag.length - m.rest.length);
    if (CLDR.collatorHant.includes(base)) return hant + (hant.includes('-u-') ? m.rest.replace(/^-u/, '') : m.rest);
    const to = CLDR.collatorDrop[base];
    return to ? to + m.rest : tag;
  };
  const noArgs = new WeakSet();  // instances constructed without a locales argument
  let rewrites = 0;
  Object.defineProperty(window, '__abRewrites', { get: () => rewrites });
  const originalOf = new Map();  // rewritten tag -> original, for ab/passback.js
  Object.defineProperty(window, '__abOriginalOf', { value: originalOf });
  const nativeToString = Function.prototype.toString;
  const fakes = new WeakMap();
  Function.prototype.toString = new Proxy(nativeToString, {
    apply(t, self, a) { return Reflect.apply(t, fakes.get(self) || self, a); }
  });
  fakes.set(Function.prototype.toString, nativeToString);
  Object.defineProperty(window, '__abFakes', { value: fakes });
  for (const svc of ['Collator', 'DateTimeFormat', 'NumberFormat', 'PluralRules', 'RelativeTimeFormat',
                     'ListFormat', 'Segmenter', 'DisplayNames', 'DurationFormat']) {
    const C = Intl[svc];
    if (typeof C !== 'function') continue;
    const P = new Proxy(C, {
      construct(t, a, nt) { const o = Reflect.construct(t, a, nt === P ? t : nt); if (a[0] === undefined) noArgs.add(o); return o; },
      apply(t, self, a) { const o = Reflect.apply(t, self, a); if (a[0] === undefined && o && typeof o === 'object') noArgs.add(o); return o; },
    });
    fakes.set(P, C);
    Object.defineProperty(Intl, svc, { value: P, writable: true, configurable: true, enumerable: false });
    try { Object.defineProperty(C.prototype, 'constructor', { value: P, writable: true, configurable: true }); } catch (e) {}
    const orig = C.prototype.resolvedOptions;
    const w = { resolvedOptions() {
      const r = Reflect.apply(orig, this, arguments);
      const v = window.__abVariant, f = VARIANTS[v || window.__abCount];
      if (f && r && typeof r.locale === 'string') {
        const mapped = f(r.locale, svc, noArgs.has(this));
        if (mapped !== r.locale) {
          rewrites++;
          if (v) {
            if (!originalOf.has(mapped)) originalOf.set(mapped, r.locale);
            r.locale = mapped;
          }
        }
      }
      return r;
    } }.resolvedOptions;
    fakes.set(w, orig);
    Object.defineProperty(C.prototype, 'resolvedOptions', { value: w, writable: true, configurable: true, enumerable: false });
  }
})();

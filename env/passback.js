// For pairs (actual, reported): does formatting with the reported tag match formatting with the
// actual one? That's what a library storing resolvedOptions().locale as its default would see.
window.__passback = function () {
  const PAIRS = [['en-US', 'en'], ['en-GB', 'en'], ['pt-BR', 'pt'], ['pt-PT', 'pt'], ['ar-EG', 'ar'], ['ar-SA', 'ar'],
                 ['zh-CN', 'zh'], ['zh-TW', 'zh-Hant'], ['zh-HK', 'zh-Hant'], ['is-IS', 'is'], ['de-AT', 'de'],
                 ['sv-SE', 'sv'], ['es-MX', 'es'], ['fr-CA', 'fr'], ['zh-Hans-CN', 'zh-Hans'], ['zh-Hant-TW', 'zh-Hant'],
                 ['zh-Hant-HK', 'zh-Hant']];
  const d = new Date(Date.UTC(2026, 8, 3, 15, 4, 5));
  const probe = l => {
    const o = { timeZone: 'UTC' };
    const r = {
      date: new Intl.DateTimeFormat(l, o).format(d),
      full: new Intl.DateTimeFormat(l, { ...o, dateStyle: 'full', timeStyle: 'short' }).format(d),
      month: new Intl.DateTimeFormat(l, { ...o, month: 'short' }).format(d),
      num: new Intl.NumberFormat(l).format(1234567.891),
      cur: new Intl.NumberFormat(l, { style: 'currency', currency: 'EUR' }).format(1234.5),
      rel: new Intl.RelativeTimeFormat(l).format(-1, 'day'),
      ro: (({ calendar, numberingSystem, hourCycle }) => ({ calendar, numberingSystem, hourCycle }))(
        new Intl.DateTimeFormat(l, { hour: 'numeric' }).resolvedOptions()),
    };
    try { const w = new Intl.Locale(l); r.week = JSON.stringify(w.getWeekInfo ? w.getWeekInfo() : w.weekInfo); } catch (e) { r.week = 'n/a'; }
    return r;
  };
  return PAIRS.map(([a, b]) => {
    const pa = probe(a), pb = probe(b);
    const diff = Object.keys(pa).filter(k => JSON.stringify(pa[k]) !== JSON.stringify(pb[k]));
    return { actual: a, reported: b, same: diff.length === 0, diff: diff.map(k => `${k}: ${JSON.stringify(pa[k])} vs ${JSON.stringify(pb[k])}`) };
  });
};

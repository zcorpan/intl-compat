// Reports what a page can observe about the locale environment. Used by env_test.py.
window.__report = async function () {
  const S = ['Collator', 'DateTimeFormat', 'NumberFormat', 'PluralRules', 'RelativeTimeFormat',
             'ListFormat', 'Segmenter', 'DisplayNames', 'DurationFormat'];
  const def = {};
  for (const k of S) {
    try { def[k] = new Intl[k](undefined, k === 'DisplayNames' ? { type: 'region' } : {}).resolvedOptions().locale; }
    catch (e) { def[k] = 'ERR ' + e.name; }
  }
  const d = new Date(Date.UTC(2026, 0, 31, 15, 4));
  const worker = await new Promise(res => {
    const w = new Worker(URL.createObjectURL(new Blob(
      ['postMessage([navigator.language, new Intl.DateTimeFormat().resolvedOptions().locale])'])));
    w.onmessage = e => res(e.data); setTimeout(() => res('timeout'), 3000);
  });
  return {
    accept_language: document.documentElement.dataset.acceptLanguage,
    language: navigator.language, languages: navigator.languages, default: def,
    date: d.toLocaleDateString(), time: d.toLocaleTimeString(), number: (1234567.891).toLocaleString(),
    hourCycle: new Intl.DateTimeFormat(undefined, { hour: 'numeric' }).resolvedOptions().hourCycle,
    worker,
  };
};

// Preload after ab/rewrite.js (all frames): when a page passes a rewritten tag back to Intl (a
// constructor, toLocale*() or localeCompare), formats each call's input with the original tag too and
// records whether the output differs: window.__abPassback = {calls, differ, samples}. Installed in A
// and B alike; only B has rewritten tags, so A records nothing.
(() => {
  if (typeof Intl !== 'object' || window.__abPassbackInstalled || !window.__abOriginalOf) return;
  Object.defineProperty(window, '__abPassbackInstalled', { value: true });
  const originalOf = window.__abOriginalOf;  // rewritten tag -> original tag, filled by rewrite.js
  const stats = { calls: 0, differ: 0, samples: [] };
  Object.defineProperty(window, '__abPassback', { get: () => JSON.parse(JSON.stringify(stats)) });
  const fakes = window.__abFakes;
  const NativeCtor = {};
  const swap = loc => {
    if (typeof loc === 'string') return originalOf.get(loc);
    if (Array.isArray(loc) && typeof loc[0] === 'string' && originalOf.has(loc[0])) return [originalOf.get(loc[0]), ...loc.slice(1)];
    return undefined;
  };
  const show = v => { try { return typeof v === 'string' ? v : JSON.stringify(v); } catch (e) { return String(v); } };
  const record = (what, got, want) => {
    stats.calls++;
    const g = show(got), w = show(want);
    if (g !== w) {
      stats.differ++;
      if (stats.samples.length < 20) stats.samples.push({ what, got: g.slice(0, 120), original: w.slice(0, 120) });
    }
  };
  const twin = new WeakMap();  // instance built from a rewritten tag -> same options, original tag
  const SVCS = ['DateTimeFormat', 'NumberFormat', 'RelativeTimeFormat', 'ListFormat', 'PluralRules', 'Collator',
                'DisplayNames', 'DurationFormat'];
  for (const svc of SVCS) {
    const C = Intl[svc];
    if (typeof C !== 'function') continue;
    NativeCtor[svc] = C;
    const make = (a, nt) => {
      const o = Reflect.construct(C, a, nt);
      const orig = swap(a[0]);
      if (orig !== undefined) {
        try { twin.set(o, Reflect.construct(C, [orig, ...a.slice(1)])); } catch (e) {}
      }
      return o;
    };
    const P = new Proxy(C, {
      construct(t, a, nt) { return make(a, nt === P ? C : nt); },
      apply(t, self, a) { return svc === 'DateTimeFormat' || svc === 'NumberFormat' || svc === 'Collator' ? make(a, C) : Reflect.apply(t, self, a); },
    });
    fakes.set(P, C);
    Object.defineProperty(Intl, svc, { value: P, writable: true, configurable: true, enumerable: false });
    try { Object.defineProperty(C.prototype, 'constructor', { value: P, writable: true, configurable: true }); } catch (e) {}
    const proto = C.prototype;
    for (const name of ['format', 'formatToParts', 'formatRange', 'formatRangeToParts', 'select', 'selectRange', 'compare', 'of']) {
      const d = Object.getOwnPropertyDescriptor(proto, name);
      if (!d) continue;
      if (d.get) {  // format and compare are getters returning bound functions
        const g = d.get;
        const bound = new WeakMap();
        const w = { get [name]() {
          const f = Reflect.apply(g, this, []);
          const t = twin.get(this);
          if (!t) return f;
          if (!bound.has(this)) {
            const tf = Reflect.apply(g, t, []);
            const wf = function (...a) { const r = Reflect.apply(f, undefined, a); try { record(svc + '.' + name, r, Reflect.apply(tf, undefined, a)); } catch (e) {} return r; };
            fakes.set(wf, f);
            Object.defineProperty(wf, 'name', { value: '' });
            bound.set(this, wf);
          }
          return bound.get(this);
        } };
        const fn = Object.getOwnPropertyDescriptor(w, name).get;
        fakes.set(fn, g);
        Object.defineProperty(proto, name, { ...d, get: fn });
      } else if (typeof d.value === 'function') {
        const m = d.value;
        const w = { [name](...a) {
          const r = Reflect.apply(m, this, a);
          const t = twin.get(this);
          if (t) { try { record(svc + '.' + name, r, Reflect.apply(m, t, a)); } catch (e) {} }
          return r;
        } };
        fakes.set(w[name], m);
        Object.defineProperty(proto, name, { ...d, value: w[name] });
      }
    }
  }
  const wrapLocaleMethod = (proto, name, label) => {
    const m = proto[name];
    if (typeof m !== 'function') return;
    const w = { [name](...a) {
      const r = Reflect.apply(m, this, a);
      const i = name === 'localeCompare' ? 1 : 0;
      const orig = swap(a[i]);
      if (orig !== undefined) {
        const b = a.slice(); b[i] = orig;
        try { record(label, r, Reflect.apply(m, this, b)); } catch (e) {}
      }
      return r;
    } };
    fakes.set(w[name], m);
    Object.defineProperty(proto, name, { value: w[name], writable: true, configurable: true, enumerable: false });
  };
  for (const n of ['toLocaleString', 'toLocaleDateString', 'toLocaleTimeString']) wrapLocaleMethod(Date.prototype, n, 'Date.' + n);
  wrapLocaleMethod(Number.prototype, 'toLocaleString', 'Number.toLocaleString');
  wrapLocaleMethod(String.prototype, 'localeCompare', 'String.localeCompare');
  wrapLocaleMethod(String.prototype, 'toLocaleUpperCase', 'String.toLocaleUpperCase');
  wrapLocaleMethod(String.prototype, 'toLocaleLowerCase', 'String.toLocaleLowerCase');
  if (typeof BigInt === 'function') wrapLocaleMethod(BigInt.prototype, 'toLocaleString', 'BigInt.toLocaleString');
  if (Intl.Locale) {  // getWeekInfo() etc. on a Locale built from a rewritten tag
    const L = Intl.Locale;
    const P = new Proxy(L, {
      construct(t, a, nt) {
        const o = Reflect.construct(L, a, nt === P ? L : nt);
        const orig = swap(a[0]);
        if (orig !== undefined) { try { twin.set(o, new L(orig, a[1])); } catch (e) {} }
        return o;
      },
    });
    fakes.set(P, L);
    Object.defineProperty(Intl, 'Locale', { value: P, writable: true, configurable: true, enumerable: false });
    try { Object.defineProperty(L.prototype, 'constructor', { value: P, writable: true, configurable: true }); } catch (e) {}
    for (const name of Object.getOwnPropertyNames(L.prototype)) {
      if (!/^get[A-Z]|^(region|maximize|minimize|firstDayOfWeek|hourCycle)$/.test(name)) continue;
      const d = Object.getOwnPropertyDescriptor(L.prototype, name);
      const f = d.get || d.value;
      if (typeof f !== 'function') continue;
      const call = function (...a) {
        const r = Reflect.apply(f, this, a);
        const t = twin.get(this);
        if (t) { try { record('Locale.' + name, d.get ? r : show(r), d.get ? Reflect.apply(f, t, []) : show(Reflect.apply(f, t, a))); } catch (e) {} }
        return r;
      };
      const w = d.get ? Object.getOwnPropertyDescriptor({ get [name]() { return Reflect.apply(call, this, []); } }, name).get
                      : { [name](...a) { return Reflect.apply(call, this, a); } }[name];
      fakes.set(w, f);
      Object.defineProperty(L.prototype, name, d.get ? { ...d, get: w } : { ...d, value: w });
    }
  }
})();

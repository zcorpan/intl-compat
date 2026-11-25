// Preload (all frames): logs reads of `locale` on Intl resolvedOptions() results, with the service,
// the constructor's locales argument, the value and a stack. Also counts resolvedOptions() calls
// and logs supportedLocalesOf() and toLocale*/localeCompare default-locale-dependent calls are not
// traced (they don't expose the resolved locale). Reports through the __intlTrace binding if present
// (survives navigation) and keeps a copy in window.__intlTraceLog.
(() => {
  if (typeof Intl !== 'object' || window.__intlTraceInstalled) return;
  Object.defineProperty(window, '__intlTraceInstalled', { value: true });
  const SERVICES = ['Collator', 'DateTimeFormat', 'NumberFormat', 'PluralRules', 'RelativeTimeFormat',
                    'ListFormat', 'Segmenter', 'DisplayNames', 'DurationFormat', 'Locale'];
  const log = [];
  Object.defineProperty(window, '__intlTraceLog', { value: log });
  const seen = new Map();
  const send = ev => {
    const key = ev.kind + '|' + ev.svc + '|' + ev.args + '|' + ev.stack;
    const n = seen.get(key) || 0;
    seen.set(key, n + 1);
    if (n || log.length >= 300) return;
    log.push(ev);
    try { window.__intlTrace && window.__intlTrace(ev); } catch (e) {}
  };
  const calls = {};
  Object.defineProperty(window, '__intlTraceCalls', { value: calls });
  const argsOf = new WeakMap();
  const descr = v => {
    if (v === undefined) return 'none';
    try { return JSON.stringify(v).slice(0, 200); } catch (e) { return String(v).slice(0, 200); }
  };
  const stack = () => {
    const s = (new Error().stack || '').split('\n').slice(3, 15).join('\n');
    return s.slice(0, 2000);
  };
  const nativeToString = Function.prototype.toString;
  const fakes = new WeakMap();
  Function.prototype.toString = new Proxy(nativeToString, {
    apply(t, self, a) { return Reflect.apply(t, fakes.get(self) || self, a); }
  });
  fakes.set(Function.prototype.toString, nativeToString);
  for (const svc of SERVICES) {
    const C = Intl[svc];
    if (typeof C !== 'function') continue;
    const P = new Proxy(C, {
      construct(t, a, nt) {
        const o = Reflect.construct(t, a, nt);
        argsOf.set(o, a.length ? descr(a[0]) : 'none');
        return o;
      },
      apply(t, self, a) {
        const o = Reflect.apply(t, self, a);
        if (o && typeof o === 'object') argsOf.set(o, a.length ? descr(a[0]) : 'none');
        return o;
      },
    });
    Object.defineProperty(Intl, svc, { value: P, writable: true, configurable: true, enumerable: false });
    try { Object.defineProperty(C.prototype, 'constructor', { value: P, writable: true, configurable: true }); } catch (e) {}
    const slo = C.supportedLocalesOf;
    if (typeof slo === 'function') {
      const w = { supportedLocalesOf(...a) {
        const r = Reflect.apply(slo, this, a);
        send({ kind: 'supportedLocalesOf', svc, args: descr(a[0]), value: descr(r), stack: stack(), href: location.href });
        return r;
      } }.supportedLocalesOf;
      fakes.set(w, slo);
      Object.defineProperty(C, 'supportedLocalesOf', { value: w, writable: true, configurable: true });
    }
    if (svc === 'Locale') continue;
    const ro = C.prototype.resolvedOptions;
    if (typeof ro !== 'function') continue;
    const w = { resolvedOptions() {
      const r = Reflect.apply(ro, this, arguments);
      calls[svc] = (calls[svc] || 0) + 1;
      if (r && typeof r === 'object' && 'locale' in r) {
        const value = r.locale, args = argsOf.has(this) ? argsOf.get(this) : 'unknown';
        Object.defineProperty(r, 'locale', {
          get() { send({ kind: 'locale', svc, args, value, stack: stack(), href: location.href }); return value; },
          set(v) { Object.defineProperty(r, 'locale', { value: v, writable: true, enumerable: true, configurable: true }); },
          enumerable: true, configurable: true,
        });
      }
      return r;
    } }.resolvedOptions;
    fakes.set(w, ro);
    Object.defineProperty(C.prototype, 'resolvedOptions', { value: w, writable: true, configurable: true });
  }
})();

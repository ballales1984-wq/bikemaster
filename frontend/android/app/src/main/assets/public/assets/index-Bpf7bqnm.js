(function () {
  const t = document.createElement("link").relList;
  if (t && t.supports && t.supports("modulepreload")) return;
  for (const i of document.querySelectorAll('link[rel="modulepreload"]')) s(i);
  new MutationObserver((i) => {
    for (const o of i)
      if (o.type === "childList")
        for (const r of o.addedNodes)
          r.tagName === "LINK" && r.rel === "modulepreload" && s(r);
  }).observe(document, { childList: !0, subtree: !0 });
  function n(i) {
    const o = {};
    return (
      i.integrity && (o.integrity = i.integrity),
      i.referrerPolicy && (o.referrerPolicy = i.referrerPolicy),
      i.crossOrigin === "use-credentials"
        ? (o.credentials = "include")
        : i.crossOrigin === "anonymous"
          ? (o.credentials = "omit")
          : (o.credentials = "same-origin"),
      o
    );
  }
  function s(i) {
    if (i.ep) return;
    i.ep = !0;
    const o = n(i);
    fetch(i.href, o);
  }
})();
/**
 * @vue/shared v3.5.35
 * (c) 2018-present Yuxi (Evan) You and Vue contributors
 * @license MIT
 **/ function es(e) {
  const t = Object.create(null);
  for (const n of e.split(",")) t[n] = 1;
  return (n) => n in t;
}
const Y = {},
  bt = [],
  Ke = () => {},
  ni = () => !1,
  mn = (e) =>
    e.charCodeAt(0) === 111 &&
    e.charCodeAt(1) === 110 &&
    (e.charCodeAt(2) > 122 || e.charCodeAt(2) < 97),
  _n = (e) => e.startsWith("onUpdate:"),
  pe = Object.assign,
  ts = (e, t) => {
    const n = e.indexOf(t);
    n > -1 && e.splice(n, 1);
  },
  co = Object.prototype.hasOwnProperty,
  W = (e, t) => co.call(e, t),
  F = Array.isArray,
  yt = (e) => Jt(e) === "[object Map]",
  bn = (e) => Jt(e) === "[object Set]",
  xs = (e) => Jt(e) === "[object Date]",
  N = (e) => typeof e == "function",
  ne = (e) => typeof e == "string",
  Be = (e) => typeof e == "symbol",
  q = (e) => e !== null && typeof e == "object",
  si = (e) => (q(e) || N(e)) && N(e.then) && N(e.catch),
  ii = Object.prototype.toString,
  Jt = (e) => ii.call(e),
  uo = (e) => Jt(e).slice(8, -1),
  oi = (e) => Jt(e) === "[object Object]",
  ns = (e) =>
    ne(e) && e !== "NaN" && e[0] !== "-" && "" + parseInt(e, 10) === e,
  kt = es(
    ",key,ref,ref_for,ref_key,onVnodeBeforeMount,onVnodeMounted,onVnodeBeforeUpdate,onVnodeUpdated,onVnodeBeforeUnmount,onVnodeUnmounted",
  ),
  yn = (e) => {
    const t = Object.create(null);
    return (n) => t[n] || (t[n] = e(n));
  },
  fo = /-\w/g,
  Oe = yn((e) => e.replace(fo, (t) => t.slice(1).toUpperCase())),
  po = /\B([A-Z])/g,
  ht = yn((e) => e.replace(po, "-$1").toLowerCase()),
  ri = yn((e) => e.charAt(0).toUpperCase() + e.slice(1)),
  Mn = yn((e) => (e ? `on${ri(e)}` : "")),
  He = (e, t) => !Object.is(e, t),
  sn = (e, ...t) => {
    for (let n = 0; n < e.length; n++) e[n](...t);
  },
  li = (e, t, n, s = !1) => {
    Object.defineProperty(e, t, {
      configurable: !0,
      enumerable: !1,
      writable: s,
      value: n,
    });
  },
  xn = (e) => {
    const t = parseFloat(e);
    return isNaN(t) ? e : t;
  };
let Ss;
const Sn = () =>
  Ss ||
  (Ss =
    typeof globalThis < "u"
      ? globalThis
      : typeof self < "u"
        ? self
        : typeof window < "u"
          ? window
          : typeof global < "u"
            ? global
            : {});
function ss(e) {
  if (F(e)) {
    const t = {};
    for (let n = 0; n < e.length; n++) {
      const s = e[n],
        i = ne(s) ? mo(s) : ss(s);
      if (i) for (const o in i) t[o] = i[o];
    }
    return t;
  } else if (ne(e) || q(e)) return e;
}
const ho = /;(?![^(]*\))/g,
  go = /:([^]+)/,
  vo = /\/\*[^]*?\*\//g;
function mo(e) {
  const t = {};
  return (
    e
      .replace(vo, "")
      .split(ho)
      .forEach((n) => {
        if (n) {
          const s = n.split(go);
          s.length > 1 && (t[s[0].trim()] = s[1].trim());
        }
      }),
    t
  );
}
function me(e) {
  let t = "";
  if (ne(e)) t = e;
  else if (F(e))
    for (let n = 0; n < e.length; n++) {
      const s = me(e[n]);
      s && (t += s + " ");
    }
  else if (q(e)) for (const n in e) e[n] && (t += n + " ");
  return t.trim();
}
const _o =
    "itemscope,allowfullscreen,formnovalidate,ismap,nomodule,novalidate,readonly",
  bo = es(_o);
function ai(e) {
  return !!e || e === "";
}
function yo(e, t) {
  if (e.length !== t.length) return !1;
  let n = !0;
  for (let s = 0; n && s < e.length; s++) n = Yt(e[s], t[s]);
  return n;
}
function Yt(e, t) {
  if (e === t) return !0;
  let n = xs(e),
    s = xs(t);
  if (n || s) return n && s ? e.getTime() === t.getTime() : !1;
  if (((n = Be(e)), (s = Be(t)), n || s)) return e === t;
  if (((n = F(e)), (s = F(t)), n || s)) return n && s ? yo(e, t) : !1;
  if (((n = q(e)), (s = q(t)), n || s)) {
    if (!n || !s) return !1;
    const i = Object.keys(e).length,
      o = Object.keys(t).length;
    if (i !== o) return !1;
    for (const r in e) {
      const l = e.hasOwnProperty(r),
        a = t.hasOwnProperty(r);
      if ((l && !a) || (!l && a) || !Yt(e[r], t[r])) return !1;
    }
  }
  return String(e) === String(t);
}
function xo(e, t) {
  return e.findIndex((n) => Yt(n, t));
}
const ci = (e) => !!(e && e.__v_isRef === !0),
  L = (e) =>
    ne(e)
      ? e
      : e == null
        ? ""
        : F(e) || (q(e) && (e.toString === ii || !N(e.toString)))
          ? ci(e)
            ? L(e.value)
            : JSON.stringify(e, ui, 2)
          : String(e),
  ui = (e, t) =>
    ci(t)
      ? ui(e, t.value)
      : yt(t)
        ? {
            [`Map(${t.size})`]: [...t.entries()].reduce(
              (n, [s, i], o) => ((n[In(s, o) + " =>"] = i), n),
              {},
            ),
          }
        : bn(t)
          ? { [`Set(${t.size})`]: [...t.values()].map((n) => In(n)) }
          : Be(t)
            ? In(t)
            : q(t) && !F(t) && !oi(t)
              ? String(t)
              : t,
  In = (e, t = "") => {
    var n;
    return Be(e) ? `Symbol(${(n = e.description) != null ? n : t})` : e;
  };
/**
 * @vue/reactivity v3.5.35
 * (c) 2018-present Yuxi (Evan) You and Vue contributors
 * @license MIT
 **/ let ce;
class So {
  constructor(t = !1) {
    ((this.detached = t),
      (this._active = !0),
      (this._on = 0),
      (this.effects = []),
      (this.cleanups = []),
      (this._isPaused = !1),
      (this._warnOnRun = !0),
      (this.__v_skip = !0),
      !t &&
        ce &&
        (ce.active
          ? ((this.parent = ce),
            (this.index = (ce.scopes || (ce.scopes = [])).push(this) - 1))
          : ((this._active = !1), (this._warnOnRun = !1))));
  }
  get active() {
    return this._active;
  }
  pause() {
    if (this._active) {
      this._isPaused = !0;
      let t, n;
      if (this.scopes)
        for (t = 0, n = this.scopes.length; t < n; t++) this.scopes[t].pause();
      for (t = 0, n = this.effects.length; t < n; t++) this.effects[t].pause();
    }
  }
  resume() {
    if (this._active && this._isPaused) {
      this._isPaused = !1;
      let t, n;
      if (this.scopes)
        for (t = 0, n = this.scopes.length; t < n; t++) this.scopes[t].resume();
      for (t = 0, n = this.effects.length; t < n; t++) this.effects[t].resume();
    }
  }
  run(t) {
    if (this._active) {
      const n = ce;
      try {
        return ((ce = this), t());
      } finally {
        ce = n;
      }
    }
  }
  on() {
    ++this._on === 1 && ((this.prevScope = ce), (ce = this));
  }
  off() {
    if (this._on > 0 && --this._on === 0) {
      if (ce === this) ce = this.prevScope;
      else {
        let t = ce;
        for (; t;) {
          if (t.prevScope === this) {
            t.prevScope = this.prevScope;
            break;
          }
          t = t.prevScope;
        }
      }
      this.prevScope = void 0;
    }
  }
  stop(t) {
    if (this._active) {
      this._active = !1;
      let n, s;
      for (n = 0, s = this.effects.length; n < s; n++) this.effects[n].stop();
      for (this.effects.length = 0, n = 0, s = this.cleanups.length; n < s; n++)
        this.cleanups[n]();
      if (((this.cleanups.length = 0), this.scopes)) {
        for (n = 0, s = this.scopes.length; n < s; n++) this.scopes[n].stop(!0);
        this.scopes.length = 0;
      }
      if (!this.detached && this.parent && !t) {
        const i = this.parent.scopes.pop();
        i &&
          i !== this &&
          ((this.parent.scopes[this.index] = i), (i.index = this.index));
      }
      this.parent = void 0;
    }
  }
}
function wo() {
  return ce;
}
let Z;
const Dn = new WeakSet();
class fi {
  constructor(t) {
    ((this.fn = t),
      (this.deps = void 0),
      (this.depsTail = void 0),
      (this.flags = 5),
      (this.next = void 0),
      (this.cleanup = void 0),
      (this.scheduler = void 0),
      ce && (ce.active ? ce.effects.push(this) : (this.flags &= -2)));
  }
  pause() {
    this.flags |= 64;
  }
  resume() {
    this.flags & 64 &&
      ((this.flags &= -65), Dn.has(this) && (Dn.delete(this), this.trigger()));
  }
  notify() {
    (this.flags & 2 && !(this.flags & 32)) || this.flags & 8 || pi(this);
  }
  run() {
    if (!(this.flags & 1)) return this.fn();
    ((this.flags |= 2), ws(this), hi(this));
    const t = Z,
      n = Pe;
    ((Z = this), (Pe = !0));
    try {
      return this.fn();
    } finally {
      (gi(this), (Z = t), (Pe = n), (this.flags &= -3));
    }
  }
  stop() {
    if (this.flags & 1) {
      for (let t = this.deps; t; t = t.nextDep) rs(t);
      ((this.deps = this.depsTail = void 0),
        ws(this),
        this.onStop && this.onStop(),
        (this.flags &= -2));
    }
  }
  trigger() {
    this.flags & 64
      ? Dn.add(this)
      : this.scheduler
        ? this.scheduler()
        : this.runIfDirty();
  }
  runIfDirty() {
    Un(this) && this.run();
  }
  get dirty() {
    return Un(this);
  }
}
let di = 0,
  Nt,
  Lt;
function pi(e, t = !1) {
  if (((e.flags |= 8), t)) {
    ((e.next = Lt), (Lt = e));
    return;
  }
  ((e.next = Nt), (Nt = e));
}
function is() {
  di++;
}
function os() {
  if (--di > 0) return;
  if (Lt) {
    let t = Lt;
    for (Lt = void 0; t;) {
      const n = t.next;
      ((t.next = void 0), (t.flags &= -9), (t = n));
    }
  }
  let e;
  for (; Nt;) {
    let t = Nt;
    for (Nt = void 0; t;) {
      const n = t.next;
      if (((t.next = void 0), (t.flags &= -9), t.flags & 1))
        try {
          t.trigger();
        } catch (s) {
          e || (e = s);
        }
      t = n;
    }
  }
  if (e) throw e;
}
function hi(e) {
  for (let t = e.deps; t; t = t.nextDep)
    ((t.version = -1),
      (t.prevActiveLink = t.dep.activeLink),
      (t.dep.activeLink = t));
}
function gi(e) {
  let t,
    n = e.depsTail,
    s = n;
  for (; s;) {
    const i = s.prevDep;
    (s.version === -1 ? (s === n && (n = i), rs(s), $o(s)) : (t = s),
      (s.dep.activeLink = s.prevActiveLink),
      (s.prevActiveLink = void 0),
      (s = i));
  }
  ((e.deps = t), (e.depsTail = n));
}
function Un(e) {
  for (let t = e.deps; t; t = t.nextDep)
    if (
      t.dep.version !== t.version ||
      (t.dep.computed && (vi(t.dep.computed) || t.dep.version !== t.version))
    )
      return !0;
  return !!e._dirty;
}
function vi(e) {
  if (
    (e.flags & 4 && !(e.flags & 16)) ||
    ((e.flags &= -17), e.globalVersion === Kt) ||
    ((e.globalVersion = Kt),
    !e.isSSR && e.flags & 128 && ((!e.deps && !e._dirty) || !Un(e)))
  )
    return;
  e.flags |= 2;
  const t = e.dep,
    n = Z,
    s = Pe;
  ((Z = e), (Pe = !0));
  try {
    hi(e);
    const i = e.fn(e._value);
    (t.version === 0 || He(i, e._value)) &&
      ((e.flags |= 128), (e._value = i), t.version++);
  } catch (i) {
    throw (t.version++, i);
  } finally {
    ((Z = n), (Pe = s), gi(e), (e.flags &= -3));
  }
}
function rs(e, t = !1) {
  const { dep: n, prevSub: s, nextSub: i } = e;
  if (
    (s && ((s.nextSub = i), (e.prevSub = void 0)),
    i && ((i.prevSub = s), (e.nextSub = void 0)),
    n.subs === e && ((n.subs = s), !s && n.computed))
  ) {
    n.computed.flags &= -5;
    for (let o = n.computed.deps; o; o = o.nextDep) rs(o, !0);
  }
  !t && !--n.sc && n.map && n.map.delete(n.key);
}
function $o(e) {
  const { prevDep: t, nextDep: n } = e;
  (t && ((t.nextDep = n), (e.prevDep = void 0)),
    n && ((n.prevDep = t), (e.nextDep = void 0)));
}
let Pe = !0;
const mi = [];
function Xe() {
  (mi.push(Pe), (Pe = !1));
}
function Ze() {
  const e = mi.pop();
  Pe = e === void 0 ? !0 : e;
}
function ws(e) {
  const { cleanup: t } = e;
  if (((e.cleanup = void 0), t)) {
    const n = Z;
    Z = void 0;
    try {
      t();
    } finally {
      Z = n;
    }
  }
}
let Kt = 0;
class Co {
  constructor(t, n) {
    ((this.sub = t),
      (this.dep = n),
      (this.version = n.version),
      (this.nextDep =
        this.prevDep =
        this.nextSub =
        this.prevSub =
        this.prevActiveLink =
          void 0));
  }
}
class ls {
  constructor(t) {
    ((this.computed = t),
      (this.version = 0),
      (this.activeLink = void 0),
      (this.subs = void 0),
      (this.map = void 0),
      (this.key = void 0),
      (this.sc = 0),
      (this.__v_skip = !0));
  }
  track(t) {
    if (!Z || !Pe || Z === this.computed) return;
    let n = this.activeLink;
    if (n === void 0 || n.sub !== Z)
      ((n = this.activeLink = new Co(Z, this)),
        Z.deps
          ? ((n.prevDep = Z.depsTail),
            (Z.depsTail.nextDep = n),
            (Z.depsTail = n))
          : (Z.deps = Z.depsTail = n),
        _i(n));
    else if (n.version === -1 && ((n.version = this.version), n.nextDep)) {
      const s = n.nextDep;
      ((s.prevDep = n.prevDep),
        n.prevDep && (n.prevDep.nextDep = s),
        (n.prevDep = Z.depsTail),
        (n.nextDep = void 0),
        (Z.depsTail.nextDep = n),
        (Z.depsTail = n),
        Z.deps === n && (Z.deps = s));
    }
    return n;
  }
  trigger(t) {
    (this.version++, Kt++, this.notify(t));
  }
  notify(t) {
    is();
    try {
      for (let n = this.subs; n; n = n.prevSub)
        n.sub.notify() && n.sub.dep.notify();
    } finally {
      os();
    }
  }
}
function _i(e) {
  if ((e.dep.sc++, e.sub.flags & 4)) {
    const t = e.dep.computed;
    if (t && !e.dep.subs) {
      t.flags |= 20;
      for (let s = t.deps; s; s = s.nextDep) _i(s);
    }
    const n = e.dep.subs;
    (n !== e && ((e.prevSub = n), n && (n.nextSub = e)), (e.dep.subs = e));
  }
}
const Hn = new WeakMap(),
  dt = Symbol(""),
  Kn = Symbol(""),
  Bt = Symbol("");
function fe(e, t, n) {
  if (Pe && Z) {
    let s = Hn.get(e);
    s || Hn.set(e, (s = new Map()));
    let i = s.get(n);
    (i || (s.set(n, (i = new ls())), (i.map = s), (i.key = n)), i.track());
  }
}
function Je(e, t, n, s, i, o) {
  const r = Hn.get(e);
  if (!r) {
    Kt++;
    return;
  }
  const l = (a) => {
    a && a.trigger();
  };
  if ((is(), t === "clear")) r.forEach(l);
  else {
    const a = F(e),
      f = a && ns(n);
    if (a && n === "length") {
      const p = Number(s);
      r.forEach((g, E) => {
        (E === "length" || E === Bt || (!Be(E) && E >= p)) && l(g);
      });
    } else
      switch (
        ((n !== void 0 || r.has(void 0)) && l(r.get(n)), f && l(r.get(Bt)), t)
      ) {
        case "add":
          a ? f && l(r.get("length")) : (l(r.get(dt)), yt(e) && l(r.get(Kn)));
          break;
        case "delete":
          a || (l(r.get(dt)), yt(e) && l(r.get(Kn)));
          break;
        case "set":
          yt(e) && l(r.get(dt));
          break;
      }
  }
  os();
}
function mt(e) {
  const t = B(e);
  return t === e ? t : (fe(t, "iterate", Bt), Ee(e) ? t : t.map(Me));
}
function wn(e) {
  return (fe((e = B(e)), "iterate", Bt), e);
}
function Ve(e, t) {
  return Qe(e) ? Ct(pt(e) ? Me(t) : t) : Me(t);
}
const Eo = {
  __proto__: null,
  [Symbol.iterator]() {
    return Rn(this, Symbol.iterator, (e) => Ve(this, e));
  },
  concat(...e) {
    return mt(this).concat(...e.map((t) => (F(t) ? mt(t) : t)));
  },
  entries() {
    return Rn(this, "entries", (e) => ((e[1] = Ve(this, e[1])), e));
  },
  every(e, t) {
    return Ge(this, "every", e, t, void 0, arguments);
  },
  filter(e, t) {
    return Ge(
      this,
      "filter",
      e,
      t,
      (n) => n.map((s) => Ve(this, s)),
      arguments,
    );
  },
  find(e, t) {
    return Ge(this, "find", e, t, (n) => Ve(this, n), arguments);
  },
  findIndex(e, t) {
    return Ge(this, "findIndex", e, t, void 0, arguments);
  },
  findLast(e, t) {
    return Ge(this, "findLast", e, t, (n) => Ve(this, n), arguments);
  },
  findLastIndex(e, t) {
    return Ge(this, "findLastIndex", e, t, void 0, arguments);
  },
  forEach(e, t) {
    return Ge(this, "forEach", e, t, void 0, arguments);
  },
  includes(...e) {
    return Fn(this, "includes", e);
  },
  indexOf(...e) {
    return Fn(this, "indexOf", e);
  },
  join(e) {
    return mt(this).join(e);
  },
  lastIndexOf(...e) {
    return Fn(this, "lastIndexOf", e);
  },
  map(e, t) {
    return Ge(this, "map", e, t, void 0, arguments);
  },
  pop() {
    return It(this, "pop");
  },
  push(...e) {
    return It(this, "push", e);
  },
  reduce(e, ...t) {
    return $s(this, "reduce", e, t);
  },
  reduceRight(e, ...t) {
    return $s(this, "reduceRight", e, t);
  },
  shift() {
    return It(this, "shift");
  },
  some(e, t) {
    return Ge(this, "some", e, t, void 0, arguments);
  },
  splice(...e) {
    return It(this, "splice", e);
  },
  toReversed() {
    return mt(this).toReversed();
  },
  toSorted(e) {
    return mt(this).toSorted(e);
  },
  toSpliced(...e) {
    return mt(this).toSpliced(...e);
  },
  unshift(...e) {
    return It(this, "unshift", e);
  },
  values() {
    return Rn(this, "values", (e) => Ve(this, e));
  },
};
function Rn(e, t, n) {
  const s = wn(e),
    i = s[t]();
  return (
    s !== e &&
      !Ee(e) &&
      ((i._next = i.next),
      (i.next = () => {
        const o = i._next();
        return (o.done || (o.value = n(o.value)), o);
      })),
    i
  );
}
const To = Array.prototype;
function Ge(e, t, n, s, i, o) {
  const r = wn(e),
    l = r !== e && !Ee(e),
    a = r[t];
  if (a !== To[t]) {
    const g = a.apply(e, o);
    return l ? Me(g) : g;
  }
  let f = n;
  r !== e &&
    (l
      ? (f = function (g, E) {
          return n.call(this, Ve(e, g), E, e);
        })
      : n.length > 2 &&
        (f = function (g, E) {
          return n.call(this, g, E, e);
        }));
  const p = a.call(r, f, s);
  return l && i ? i(p) : p;
}
function $s(e, t, n, s) {
  const i = wn(e),
    o = i !== e && !Ee(e);
  let r = n,
    l = !1;
  i !== e &&
    (o
      ? ((l = s.length === 0),
        (r = function (f, p, g) {
          return (
            l && ((l = !1), (f = Ve(e, f))),
            n.call(this, f, Ve(e, p), g, e)
          );
        }))
      : n.length > 3 &&
        (r = function (f, p, g) {
          return n.call(this, f, p, g, e);
        }));
  const a = i[t](r, ...s);
  return l ? Ve(e, a) : a;
}
function Fn(e, t, n) {
  const s = B(e);
  fe(s, "iterate", Bt);
  const i = s[t](...n);
  return (i === -1 || i === !1) && fs(n[0])
    ? ((n[0] = B(n[0])), s[t](...n))
    : i;
}
function It(e, t, n = []) {
  (Xe(), is());
  const s = B(e)[t].apply(e, n);
  return (os(), Ze(), s);
}
const Ao = es("__proto__,__v_isRef,__isVue"),
  bi = new Set(
    Object.getOwnPropertyNames(Symbol)
      .filter((e) => e !== "arguments" && e !== "caller")
      .map((e) => Symbol[e])
      .filter(Be),
  );
function Oo(e) {
  Be(e) || (e = String(e));
  const t = B(this);
  return (fe(t, "has", e), t.hasOwnProperty(e));
}
class yi {
  constructor(t = !1, n = !1) {
    ((this._isReadonly = t), (this._isShallow = n));
  }
  get(t, n, s) {
    if (n === "__v_skip") return t.__v_skip;
    const i = this._isReadonly,
      o = this._isShallow;
    if (n === "__v_isReactive") return !i;
    if (n === "__v_isReadonly") return i;
    if (n === "__v_isShallow") return o;
    if (n === "__v_raw")
      return s === (i ? (o ? jo : $i) : o ? wi : Si).get(t) ||
        Object.getPrototypeOf(t) === Object.getPrototypeOf(s)
        ? t
        : void 0;
    const r = F(t);
    if (!i) {
      let a;
      if (r && (a = Eo[n])) return a;
      if (n === "hasOwnProperty") return Oo;
    }
    const l = Reflect.get(t, n, de(t) ? t : s);
    if ((Be(n) ? bi.has(n) : Ao(n)) || (i || fe(t, "get", n), o)) return l;
    if (de(l)) {
      const a = r && ns(n) ? l : l.value;
      return i && q(a) ? Wn(a) : a;
    }
    return q(l) ? (i ? Wn(l) : cs(l)) : l;
  }
}
class xi extends yi {
  constructor(t = !1) {
    super(!1, t);
  }
  set(t, n, s, i) {
    let o = t[n];
    const r = F(t) && ns(n);
    if (!this._isShallow) {
      const f = Qe(o);
      if ((!Ee(s) && !Qe(s) && ((o = B(o)), (s = B(s))), !r && de(o) && !de(s)))
        return (f || (o.value = s), !0);
    }
    const l = r ? Number(n) < t.length : W(t, n),
      a = Reflect.set(t, n, s, de(t) ? t : i);
    return (
      t === B(i) && (l ? He(s, o) && Je(t, "set", n, s) : Je(t, "add", n, s)),
      a
    );
  }
  deleteProperty(t, n) {
    const s = W(t, n);
    t[n];
    const i = Reflect.deleteProperty(t, n);
    return (i && s && Je(t, "delete", n, void 0), i);
  }
  has(t, n) {
    const s = Reflect.has(t, n);
    return ((!Be(n) || !bi.has(n)) && fe(t, "has", n), s);
  }
  ownKeys(t) {
    return (fe(t, "iterate", F(t) ? "length" : dt), Reflect.ownKeys(t));
  }
}
class Po extends yi {
  constructor(t = !1) {
    super(!0, t);
  }
  set(t, n) {
    return !0;
  }
  deleteProperty(t, n) {
    return !0;
  }
}
const Mo = new xi(),
  Io = new Po(),
  Do = new xi(!0);
const Bn = (e) => e,
  en = (e) => Reflect.getPrototypeOf(e);
function Ro(e, t, n) {
  return function (...s) {
    const i = this.__v_raw,
      o = B(i),
      r = yt(o),
      l = e === "entries" || (e === Symbol.iterator && r),
      a = e === "keys" && r,
      f = i[e](...s),
      p = n ? Bn : t ? Ct : Me;
    return (
      !t && fe(o, "iterate", a ? Kn : dt),
      pe(Object.create(f), {
        next() {
          const { value: g, done: E } = f.next();
          return E
            ? { value: g, done: E }
            : { value: l ? [p(g[0]), p(g[1])] : p(g), done: E };
        },
      })
    );
  };
}
function tn(e) {
  return function (...t) {
    return e === "delete" ? !1 : e === "clear" ? void 0 : this;
  };
}
function Fo(e, t) {
  const n = {
    get(i) {
      const o = this.__v_raw,
        r = B(o),
        l = B(i);
      e || (He(i, l) && fe(r, "get", i), fe(r, "get", l));
      const { has: a } = en(r),
        f = t ? Bn : e ? Ct : Me;
      if (a.call(r, i)) return f(o.get(i));
      if (a.call(r, l)) return f(o.get(l));
      o !== r && o.get(i);
    },
    get size() {
      const i = this.__v_raw;
      return (!e && fe(B(i), "iterate", dt), i.size);
    },
    has(i) {
      const o = this.__v_raw,
        r = B(o),
        l = B(i);
      return (
        e || (He(i, l) && fe(r, "has", i), fe(r, "has", l)),
        i === l ? o.has(i) : o.has(i) || o.has(l)
      );
    },
    forEach(i, o) {
      const r = this,
        l = r.__v_raw,
        a = B(l),
        f = t ? Bn : e ? Ct : Me;
      return (
        !e && fe(a, "iterate", dt),
        l.forEach((p, g) => i.call(o, f(p), f(g), r))
      );
    },
  };
  return (
    pe(
      n,
      e
        ? {
            add: tn("add"),
            set: tn("set"),
            delete: tn("delete"),
            clear: tn("clear"),
          }
        : {
            add(i) {
              const o = B(this),
                r = en(o),
                l = B(i),
                a = !t && !Ee(i) && !Qe(i) ? l : i;
              return (
                r.has.call(o, a) ||
                  (He(i, a) && r.has.call(o, i)) ||
                  (He(l, a) && r.has.call(o, l)) ||
                  (o.add(a), Je(o, "add", a, a)),
                this
              );
            },
            set(i, o) {
              !t && !Ee(o) && !Qe(o) && (o = B(o));
              const r = B(this),
                { has: l, get: a } = en(r);
              let f = l.call(r, i);
              f || ((i = B(i)), (f = l.call(r, i)));
              const p = a.call(r, i);
              return (
                r.set(i, o),
                f ? He(o, p) && Je(r, "set", i, o) : Je(r, "add", i, o),
                this
              );
            },
            delete(i) {
              const o = B(this),
                { has: r, get: l } = en(o);
              let a = r.call(o, i);
              (a || ((i = B(i)), (a = r.call(o, i))), l && l.call(o, i));
              const f = o.delete(i);
              return (a && Je(o, "delete", i, void 0), f);
            },
            clear() {
              const i = B(this),
                o = i.size !== 0,
                r = i.clear();
              return (o && Je(i, "clear", void 0, void 0), r);
            },
          },
    ),
    ["keys", "values", "entries", Symbol.iterator].forEach((i) => {
      n[i] = Ro(i, e, t);
    }),
    n
  );
}
function as(e, t) {
  const n = Fo(e, t);
  return (s, i, o) =>
    i === "__v_isReactive"
      ? !e
      : i === "__v_isReadonly"
        ? e
        : i === "__v_raw"
          ? s
          : Reflect.get(W(n, i) && i in s ? n : s, i, o);
}
const ko = { get: as(!1, !1) },
  No = { get: as(!1, !0) },
  Lo = { get: as(!0, !1) };
const Si = new WeakMap(),
  wi = new WeakMap(),
  $i = new WeakMap(),
  jo = new WeakMap();
function Vo(e) {
  switch (e) {
    case "Object":
    case "Array":
      return 1;
    case "Map":
    case "Set":
    case "WeakMap":
    case "WeakSet":
      return 2;
    default:
      return 0;
  }
}
function cs(e) {
  return Qe(e) ? e : us(e, !1, Mo, ko, Si);
}
function Uo(e) {
  return us(e, !1, Do, No, wi);
}
function Wn(e) {
  return us(e, !0, Io, Lo, $i);
}
function us(e, t, n, s, i) {
  if (
    !q(e) ||
    (e.__v_raw && !(t && e.__v_isReactive)) ||
    e.__v_skip ||
    !Object.isExtensible(e)
  )
    return e;
  const o = i.get(e);
  if (o) return o;
  const r = Vo(uo(e));
  if (r === 0) return e;
  const l = new Proxy(e, r === 2 ? s : n);
  return (i.set(e, l), l);
}
function pt(e) {
  return Qe(e) ? pt(e.__v_raw) : !!(e && e.__v_isReactive);
}
function Qe(e) {
  return !!(e && e.__v_isReadonly);
}
function Ee(e) {
  return !!(e && e.__v_isShallow);
}
function fs(e) {
  return e ? !!e.__v_raw : !1;
}
function B(e) {
  const t = e && e.__v_raw;
  return t ? B(t) : e;
}
function Ho(e) {
  return (
    !W(e, "__v_skip") && Object.isExtensible(e) && li(e, "__v_skip", !0),
    e
  );
}
const Me = (e) => (q(e) ? cs(e) : e),
  Ct = (e) => (q(e) ? Wn(e) : e);
function de(e) {
  return e ? e.__v_isRef === !0 : !1;
}
function Q(e) {
  return Ko(e, !1);
}
function Ko(e, t) {
  return de(e) ? e : new Bo(e, t);
}
class Bo {
  constructor(t, n) {
    ((this.dep = new ls()),
      (this.__v_isRef = !0),
      (this.__v_isShallow = !1),
      (this._rawValue = n ? t : B(t)),
      (this._value = n ? t : Me(t)),
      (this.__v_isShallow = n));
  }
  get value() {
    return (this.dep.track(), this._value);
  }
  set value(t) {
    const n = this._rawValue,
      s = this.__v_isShallow || Ee(t) || Qe(t);
    ((t = s ? t : B(t)),
      He(t, n) &&
        ((this._rawValue = t),
        (this._value = s ? t : Me(t)),
        this.dep.trigger()));
  }
}
function Wo(e) {
  return de(e) ? e.value : e;
}
const Go = {
  get: (e, t, n) => (t === "__v_raw" ? e : Wo(Reflect.get(e, t, n))),
  set: (e, t, n, s) => {
    const i = e[t];
    return de(i) && !de(n) ? ((i.value = n), !0) : Reflect.set(e, t, n, s);
  },
};
function Ci(e) {
  return pt(e) ? e : new Proxy(e, Go);
}
class qo {
  constructor(t, n, s) {
    ((this.fn = t),
      (this.setter = n),
      (this._value = void 0),
      (this.dep = new ls(this)),
      (this.__v_isRef = !0),
      (this.deps = void 0),
      (this.depsTail = void 0),
      (this.flags = 16),
      (this.globalVersion = Kt - 1),
      (this.next = void 0),
      (this.effect = this),
      (this.__v_isReadonly = !n),
      (this.isSSR = s));
  }
  notify() {
    if (((this.flags |= 16), !(this.flags & 8) && Z !== this))
      return (pi(this, !0), !0);
  }
  get value() {
    const t = this.dep.track();
    return (vi(this), t && (t.version = this.dep.version), this._value);
  }
  set value(t) {
    this.setter && this.setter(t);
  }
}
function zo(e, t, n = !1) {
  let s, i;
  return (N(e) ? (s = e) : ((s = e.get), (i = e.set)), new qo(s, i, n));
}
const nn = {},
  cn = new WeakMap();
let ut;
function Jo(e, t = !1, n = ut) {
  if (n) {
    let s = cn.get(n);
    (s || cn.set(n, (s = [])), s.push(e));
  }
}
function Yo(e, t, n = Y) {
  const {
      immediate: s,
      deep: i,
      once: o,
      scheduler: r,
      augmentJob: l,
      call: a,
    } = n,
    f = (D) => (i ? D : Ee(D) || i === !1 || i === 0 ? Ye(D, 1) : Ye(D));
  let p,
    g,
    E,
    T,
    K = !1,
    k = !1;
  if (
    (de(e)
      ? ((g = () => e.value), (K = Ee(e)))
      : pt(e)
        ? ((g = () => f(e)), (K = !0))
        : F(e)
          ? ((k = !0),
            (K = e.some((D) => pt(D) || Ee(D))),
            (g = () =>
              e.map((D) => {
                if (de(D)) return D.value;
                if (pt(D)) return f(D);
                if (N(D)) return a ? a(D, 2) : D();
              })))
          : N(e)
            ? t
              ? (g = a ? () => a(e, 2) : e)
              : (g = () => {
                  if (E) {
                    Xe();
                    try {
                      E();
                    } finally {
                      Ze();
                    }
                  }
                  const D = ut;
                  ut = p;
                  try {
                    return a ? a(e, 3, [T]) : e(T);
                  } finally {
                    ut = D;
                  }
                })
            : (g = Ke),
    t && i)
  ) {
    const D = g,
      se = i === !0 ? 1 / 0 : i;
    g = () => Ye(D(), se);
  }
  const te = wo(),
    X = () => {
      (p.stop(), te && te.active && ts(te.effects, p));
    };
  if (o && t) {
    const D = t;
    t = (...se) => {
      (D(...se), X());
    };
  }
  let U = k ? new Array(e.length).fill(nn) : nn;
  const z = (D) => {
    if (!(!(p.flags & 1) || (!p.dirty && !D)))
      if (t) {
        const se = p.run();
        if (i || K || (k ? se.some((De, $e) => He(De, U[$e])) : He(se, U))) {
          E && E();
          const De = ut;
          ut = p;
          try {
            const $e = [se, U === nn ? void 0 : k && U[0] === nn ? [] : U, T];
            ((U = se), a ? a(t, 3, $e) : t(...$e));
          } finally {
            ut = De;
          }
        }
      } else p.run();
  };
  return (
    l && l(z),
    (p = new fi(g)),
    (p.scheduler = r ? () => r(z, !1) : z),
    (T = (D) => Jo(D, !1, p)),
    (E = p.onStop =
      () => {
        const D = cn.get(p);
        if (D) {
          if (a) a(D, 4);
          else for (const se of D) se();
          cn.delete(p);
        }
      }),
    t ? (s ? z(!0) : (U = p.run())) : r ? r(z.bind(null, !0), !0) : p.run(),
    (X.pause = p.pause.bind(p)),
    (X.resume = p.resume.bind(p)),
    (X.stop = X),
    X
  );
}
function Ye(e, t = 1 / 0, n) {
  if (
    t <= 0 ||
    !q(e) ||
    e.__v_skip ||
    ((n = n || new Map()), (n.get(e) || 0) >= t)
  )
    return e;
  if ((n.set(e, t), t--, de(e))) Ye(e.value, t, n);
  else if (F(e)) for (let s = 0; s < e.length; s++) Ye(e[s], t, n);
  else if (bn(e) || yt(e))
    e.forEach((s) => {
      Ye(s, t, n);
    });
  else if (oi(e)) {
    for (const s in e) Ye(e[s], t, n);
    for (const s of Object.getOwnPropertySymbols(e))
      Object.prototype.propertyIsEnumerable.call(e, s) && Ye(e[s], t, n);
  }
  return e;
}
/**
 * @vue/runtime-core v3.5.35
 * (c) 2018-present Yuxi (Evan) You and Vue contributors
 * @license MIT
 **/ function Xt(e, t, n, s) {
  try {
    return s ? e(...s) : e();
  } catch (i) {
    $n(i, t, n);
  }
}
function Ie(e, t, n, s) {
  if (N(e)) {
    const i = Xt(e, t, n, s);
    return (
      i &&
        si(i) &&
        i.catch((o) => {
          $n(o, t, n);
        }),
      i
    );
  }
  if (F(e)) {
    const i = [];
    for (let o = 0; o < e.length; o++) i.push(Ie(e[o], t, n, s));
    return i;
  }
}
function $n(e, t, n, s = !0) {
  const i = t ? t.vnode : null,
    { errorHandler: o, throwUnhandledErrorInProduction: r } =
      (t && t.appContext.config) || Y;
  if (t) {
    let l = t.parent;
    const a = t.proxy,
      f = `https://vuejs.org/error-reference/#runtime-${n}`;
    for (; l;) {
      const p = l.ec;
      if (p) {
        for (let g = 0; g < p.length; g++) if (p[g](e, a, f) === !1) return;
      }
      l = l.parent;
    }
    if (o) {
      (Xe(), Xt(o, null, 10, [e, a, f]), Ze());
      return;
    }
  }
  Xo(e, n, i, s, r);
}
function Xo(e, t, n, s = !0, i = !1) {
  if (i) throw e;
  console.error(e);
}
const _e = [];
let je = -1;
const xt = [];
let nt = null,
  _t = 0;
const Ei = Promise.resolve();
let un = null;
function Ti(e) {
  const t = un || Ei;
  return e ? t.then(this ? e.bind(this) : e) : t;
}
function Zo(e) {
  let t = je + 1,
    n = _e.length;
  for (; t < n;) {
    const s = (t + n) >>> 1,
      i = _e[s],
      o = Wt(i);
    o < e || (o === e && i.flags & 2) ? (t = s + 1) : (n = s);
  }
  return t;
}
function ds(e) {
  if (!(e.flags & 1)) {
    const t = Wt(e),
      n = _e[_e.length - 1];
    (!n || (!(e.flags & 2) && t >= Wt(n)) ? _e.push(e) : _e.splice(Zo(t), 0, e),
      (e.flags |= 1),
      Ai());
  }
}
function Ai() {
  un || (un = Ei.then(Pi));
}
function Qo(e) {
  (F(e)
    ? xt.push(...e)
    : nt && e.id === -1
      ? nt.splice(_t + 1, 0, e)
      : e.flags & 1 || (xt.push(e), (e.flags |= 1)),
    Ai());
}
function Cs(e, t, n = je + 1) {
  for (; n < _e.length; n++) {
    const s = _e[n];
    if (s && s.flags & 2) {
      if (e && s.id !== e.uid) continue;
      (_e.splice(n, 1),
        n--,
        s.flags & 4 && (s.flags &= -2),
        s(),
        s.flags & 4 || (s.flags &= -2));
    }
  }
}
function Oi(e) {
  if (xt.length) {
    const t = [...new Set(xt)].sort((n, s) => Wt(n) - Wt(s));
    if (((xt.length = 0), nt)) {
      nt.push(...t);
      return;
    }
    for (nt = t, _t = 0; _t < nt.length; _t++) {
      const n = nt[_t];
      (n.flags & 4 && (n.flags &= -2), n.flags & 8 || n(), (n.flags &= -2));
    }
    ((nt = null), (_t = 0));
  }
}
const Wt = (e) => (e.id == null ? (e.flags & 2 ? -1 : 1 / 0) : e.id);
function Pi(e) {
  try {
    for (je = 0; je < _e.length; je++) {
      const t = _e[je];
      t &&
        !(t.flags & 8) &&
        (t.flags & 4 && (t.flags &= -2),
        Xt(t, t.i, t.i ? 15 : 14),
        t.flags & 4 || (t.flags &= -2));
    }
  } finally {
    for (; je < _e.length; je++) {
      const t = _e[je];
      t && (t.flags &= -2);
    }
    ((je = -1),
      (_e.length = 0),
      Oi(),
      (un = null),
      (_e.length || xt.length) && Pi());
  }
}
let Ce = null,
  Mi = null;
function fn(e) {
  const t = Ce;
  return ((Ce = e), (Mi = (e && e.type.__scopeId) || null), t);
}
function er(e, t = Ce, n) {
  if (!t || e._n) return e;
  const s = (...i) => {
    s._d && ks(-1);
    const o = fn(t);
    let r;
    try {
      r = e(...i);
    } finally {
      (fn(o), s._d && ks(1));
    }
    return r;
  };
  return ((s._n = !0), (s._c = !0), (s._d = !0), s);
}
function le(e, t) {
  if (Ce === null) return e;
  const n = On(Ce),
    s = e.dirs || (e.dirs = []);
  for (let i = 0; i < t.length; i++) {
    let [o, r, l, a = Y] = t[i];
    o &&
      (N(o) && (o = { mounted: o, updated: o }),
      o.deep && Ye(r),
      s.push({
        dir: o,
        instance: n,
        value: r,
        oldValue: void 0,
        arg: l,
        modifiers: a,
      }));
  }
  return e;
}
function at(e, t, n, s) {
  const i = e.dirs,
    o = t && t.dirs;
  for (let r = 0; r < i.length; r++) {
    const l = i[r];
    o && (l.oldValue = o[r].value);
    let a = l.dir[s];
    a && (Xe(), Ie(a, n, 8, [e.el, l, e, t]), Ze());
  }
}
function tr(e, t) {
  if (be) {
    let n = be.provides;
    const s = be.parent && be.parent.provides;
    (s === n && (n = be.provides = Object.create(s)), (n[e] = t));
  }
}
function on(e, t, n = !1) {
  const s = Qr();
  if (s || St) {
    let i = St
      ? St._context.provides
      : s
        ? s.parent == null || s.ce
          ? s.vnode.appContext && s.vnode.appContext.provides
          : s.parent.provides
        : void 0;
    if (i && e in i) return i[e];
    if (arguments.length > 1) return n && N(t) ? t.call(s && s.proxy) : t;
  }
}
const nr = Symbol.for("v-scx"),
  sr = () => on(nr);
function rn(e, t, n) {
  return Ii(e, t, n);
}
function Ii(e, t, n = Y) {
  const { immediate: s, deep: i, flush: o, once: r } = n,
    l = pe({}, n),
    a = (t && s) || (!t && o !== "post");
  let f;
  if (qt) {
    if (o === "sync") {
      const T = sr();
      f = T.__watcherHandles || (T.__watcherHandles = []);
    } else if (!a) {
      const T = () => {};
      return ((T.stop = Ke), (T.resume = Ke), (T.pause = Ke), T);
    }
  }
  const p = be;
  l.call = (T, K, k) => Ie(T, p, K, k);
  let g = !1;
  (o === "post"
    ? (l.scheduler = (T) => {
        xe(T, p && p.suspense);
      })
    : o !== "sync" &&
      ((g = !0),
      (l.scheduler = (T, K) => {
        K ? T() : ds(T);
      })),
    (l.augmentJob = (T) => {
      (t && (T.flags |= 4),
        g && ((T.flags |= 2), p && ((T.id = p.uid), (T.i = p))));
    }));
  const E = Yo(e, t, l);
  return (qt && (f ? f.push(E) : a && E()), E);
}
function ir(e, t, n) {
  const s = this.proxy,
    i = ne(e) ? (e.includes(".") ? Di(s, e) : () => s[e]) : e.bind(s, s);
  let o;
  N(t) ? (o = t) : ((o = t.handler), (n = t));
  const r = Zt(this),
    l = Ii(i, o.bind(s), n);
  return (r(), l);
}
function Di(e, t) {
  const n = t.split(".");
  return () => {
    let s = e;
    for (let i = 0; i < n.length && s; i++) s = s[n[i]];
    return s;
  };
}
const or = Symbol("_vte"),
  rr = (e) => e.__isTeleport,
  kn = Symbol("_leaveCb");
function ps(e, t) {
  e.shapeFlag & 6 && e.component
    ? ((e.transition = t), ps(e.component.subTree, t))
    : e.shapeFlag & 128
      ? ((e.ssContent.transition = t.clone(e.ssContent)),
        (e.ssFallback.transition = t.clone(e.ssFallback)))
      : (e.transition = t);
}
function Ri(e) {
  e.ids = [e.ids[0] + e.ids[2]++ + "-", 0, 0];
}
function Es(e, t) {
  let n;
  return !!((n = Object.getOwnPropertyDescriptor(e, t)) && !n.configurable);
}
const dn = new WeakMap();
function jt(e, t, n, s, i = !1) {
  if (F(e)) {
    e.forEach((k, te) => jt(k, t && (F(t) ? t[te] : t), n, s, i));
    return;
  }
  if (Vt(s) && !i) {
    s.shapeFlag & 512 &&
      s.type.__asyncResolved &&
      s.component.subTree.component &&
      jt(e, t, n, s.component.subTree);
    return;
  }
  const o = s.shapeFlag & 4 ? On(s.component) : s.el,
    r = i ? null : o,
    { i: l, r: a } = e,
    f = t && t.r,
    p = l.refs === Y ? (l.refs = {}) : l.refs,
    g = l.setupState,
    E = B(g),
    T = g === Y ? ni : (k) => (Es(p, k) ? !1 : W(E, k)),
    K = (k, te) => !(te && Es(p, te));
  if (f != null && f !== a) {
    if ((Ts(t), ne(f))) ((p[f] = null), T(f) && (g[f] = null));
    else if (de(f)) {
      const k = t;
      (K(f, k.k) && (f.value = null), k.k && (p[k.k] = null));
    }
  }
  if (N(a)) Xt(a, l, 12, [r, p]);
  else {
    const k = ne(a),
      te = de(a);
    if (k || te) {
      const X = () => {
        if (e.f) {
          const U = k ? (T(a) ? g[a] : p[a]) : K() || !e.k ? a.value : p[e.k];
          if (i) F(U) && ts(U, o);
          else if (F(U)) U.includes(o) || U.push(o);
          else if (k) ((p[a] = [o]), T(a) && (g[a] = p[a]));
          else {
            const z = [o];
            (K(a, e.k) && (a.value = z), e.k && (p[e.k] = z));
          }
        } else
          k
            ? ((p[a] = r), T(a) && (g[a] = r))
            : te && (K(a, e.k) && (a.value = r), e.k && (p[e.k] = r));
      };
      if (r) {
        const U = () => {
          (X(), dn.delete(e));
        };
        ((U.id = -1), dn.set(e, U), xe(U, n));
      } else (Ts(e), X());
    }
  }
}
function Ts(e) {
  const t = dn.get(e);
  t && ((t.flags |= 8), dn.delete(e));
}
Sn().requestIdleCallback;
Sn().cancelIdleCallback;
const Vt = (e) => !!e.type.__asyncLoader,
  Fi = (e) => e.type.__isKeepAlive;
function lr(e, t) {
  ki(e, "a", t);
}
function ar(e, t) {
  ki(e, "da", t);
}
function ki(e, t, n = be) {
  const s =
    e.__wdc ||
    (e.__wdc = () => {
      let i = n;
      for (; i;) {
        if (i.isDeactivated) return;
        i = i.parent;
      }
      return e();
    });
  if ((Cn(t, s, n), n)) {
    let i = n.parent;
    for (; i && i.parent;)
      (Fi(i.parent.vnode) && cr(s, t, n, i), (i = i.parent));
  }
}
function cr(e, t, n, s) {
  const i = Cn(t, e, s, !0);
  Ni(() => {
    ts(s[t], i);
  }, n);
}
function Cn(e, t, n = be, s = !1) {
  if (n) {
    const i = n[e] || (n[e] = []),
      o =
        t.__weh ||
        (t.__weh = (...r) => {
          Xe();
          const l = Zt(n),
            a = Ie(t, n, e, r);
          return (l(), Ze(), a);
        });
    return (s ? i.unshift(o) : i.push(o), o);
  }
}
const et =
    (e) =>
    (t, n = be) => {
      (!qt || e === "sp") && Cn(e, (...s) => t(...s), n);
    },
  ur = et("bm"),
  En = et("m"),
  fr = et("bu"),
  dr = et("u"),
  pr = et("bum"),
  Ni = et("um"),
  hr = et("sp"),
  gr = et("rtg"),
  vr = et("rtc");
function mr(e, t = be) {
  Cn("ec", e, t);
}
const _r = Symbol.for("v-ndc");
function st(e, t, n, s) {
  let i;
  const o = n,
    r = F(e);
  if (r || ne(e)) {
    const l = r && pt(e);
    let a = !1,
      f = !1;
    (l && ((a = !Ee(e)), (f = Qe(e)), (e = wn(e))), (i = new Array(e.length)));
    for (let p = 0, g = e.length; p < g; p++)
      i[p] = t(a ? (f ? Ct(Me(e[p])) : Me(e[p])) : e[p], p, void 0, o);
  } else if (typeof e == "number") {
    i = new Array(e);
    for (let l = 0; l < e; l++) i[l] = t(l + 1, l, void 0, o);
  } else if (q(e))
    if (e[Symbol.iterator]) i = Array.from(e, (l, a) => t(l, a, void 0, o));
    else {
      const l = Object.keys(e);
      i = new Array(l.length);
      for (let a = 0, f = l.length; a < f; a++) {
        const p = l[a];
        i[a] = t(e[p], p, a, o);
      }
    }
  else i = [];
  return i;
}
const Gn = (e) => (e ? (oo(e) ? On(e) : Gn(e.parent)) : null),
  Ut = pe(Object.create(null), {
    $: (e) => e,
    $el: (e) => e.vnode.el,
    $data: (e) => e.data,
    $props: (e) => e.props,
    $attrs: (e) => e.attrs,
    $slots: (e) => e.slots,
    $refs: (e) => e.refs,
    $parent: (e) => Gn(e.parent),
    $root: (e) => Gn(e.root),
    $host: (e) => e.ce,
    $emit: (e) => e.emit,
    $options: (e) => ji(e),
    $forceUpdate: (e) =>
      e.f ||
      (e.f = () => {
        ds(e.update);
      }),
    $nextTick: (e) => e.n || (e.n = Ti.bind(e.proxy)),
    $watch: (e) => ir.bind(e),
  }),
  Nn = (e, t) => e !== Y && !e.__isScriptSetup && W(e, t),
  br = {
    get({ _: e }, t) {
      if (t === "__v_skip") return !0;
      const {
        ctx: n,
        setupState: s,
        data: i,
        props: o,
        accessCache: r,
        type: l,
        appContext: a,
      } = e;
      if (t[0] !== "$") {
        const E = r[t];
        if (E !== void 0)
          switch (E) {
            case 1:
              return s[t];
            case 2:
              return i[t];
            case 4:
              return n[t];
            case 3:
              return o[t];
          }
        else {
          if (Nn(s, t)) return ((r[t] = 1), s[t]);
          if (i !== Y && W(i, t)) return ((r[t] = 2), i[t]);
          if (W(o, t)) return ((r[t] = 3), o[t]);
          if (n !== Y && W(n, t)) return ((r[t] = 4), n[t]);
          qn && (r[t] = 0);
        }
      }
      const f = Ut[t];
      let p, g;
      if (f) return (t === "$attrs" && fe(e.attrs, "get", ""), f(e));
      if ((p = l.__cssModules) && (p = p[t])) return p;
      if (n !== Y && W(n, t)) return ((r[t] = 4), n[t]);
      if (((g = a.config.globalProperties), W(g, t))) return g[t];
    },
    set({ _: e }, t, n) {
      const { data: s, setupState: i, ctx: o } = e;
      return Nn(i, t)
        ? ((i[t] = n), !0)
        : s !== Y && W(s, t)
          ? ((s[t] = n), !0)
          : W(e.props, t) || (t[0] === "$" && t.slice(1) in e)
            ? !1
            : ((o[t] = n), !0);
    },
    has(
      {
        _: {
          data: e,
          setupState: t,
          accessCache: n,
          ctx: s,
          appContext: i,
          props: o,
          type: r,
        },
      },
      l,
    ) {
      let a;
      return !!(
        n[l] ||
        (e !== Y && l[0] !== "$" && W(e, l)) ||
        Nn(t, l) ||
        W(o, l) ||
        W(s, l) ||
        W(Ut, l) ||
        W(i.config.globalProperties, l) ||
        ((a = r.__cssModules) && a[l])
      );
    },
    defineProperty(e, t, n) {
      return (
        n.get != null
          ? (e._.accessCache[t] = 0)
          : W(n, "value") && this.set(e, t, n.value, null),
        Reflect.defineProperty(e, t, n)
      );
    },
  };
function As(e) {
  return F(e) ? e.reduce((t, n) => ((t[n] = null), t), {}) : e;
}
let qn = !0;
function yr(e) {
  const t = ji(e),
    n = e.proxy,
    s = e.ctx;
  ((qn = !1), t.beforeCreate && Os(t.beforeCreate, e, "bc"));
  const {
    data: i,
    computed: o,
    methods: r,
    watch: l,
    provide: a,
    inject: f,
    created: p,
    beforeMount: g,
    mounted: E,
    beforeUpdate: T,
    updated: K,
    activated: k,
    deactivated: te,
    beforeDestroy: X,
    beforeUnmount: U,
    destroyed: z,
    unmounted: D,
    render: se,
    renderTracked: De,
    renderTriggered: $e,
    errorCaptured: Re,
    serverPrefetch: ye,
    expose: Te,
    inheritAttrs: rt,
    components: gt,
    directives: vt,
    filters: A,
  } = t;
  if ((f && xr(f, s, null), r))
    for (const V in r) {
      const j = r[V];
      N(j) && (s[V] = j.bind(n));
    }
  if (i) {
    const V = i.call(n, n);
    q(V) && (e.data = cs(V));
  }
  if (((qn = !0), o))
    for (const V in o) {
      const j = o[V],
        he = N(j) ? j.bind(n, n) : N(j.get) ? j.get.bind(n, n) : Ke,
        tt = !N(j) && N(j.set) ? j.set.bind(n) : Ke,
        We = it({ get: he, set: tt });
      Object.defineProperty(s, V, {
        enumerable: !0,
        configurable: !0,
        get: () => We.value,
        set: (ee) => (We.value = ee),
      });
    }
  if (l) for (const V in l) Li(l[V], s, n, V);
  if (a) {
    const V = N(a) ? a.call(n) : a;
    Reflect.ownKeys(V).forEach((j) => {
      tr(j, V[j]);
    });
  }
  p && Os(p, e, "c");
  function S(V, j) {
    F(j) ? j.forEach((he) => V(he.bind(n))) : j && V(j.bind(n));
  }
  if (
    (S(ur, g),
    S(En, E),
    S(fr, T),
    S(dr, K),
    S(lr, k),
    S(ar, te),
    S(mr, Re),
    S(vr, De),
    S(gr, $e),
    S(pr, U),
    S(Ni, D),
    S(hr, ye),
    F(Te))
  )
    if (Te.length) {
      const V = e.exposed || (e.exposed = {});
      Te.forEach((j) => {
        Object.defineProperty(V, j, {
          get: () => n[j],
          set: (he) => (n[j] = he),
          enumerable: !0,
        });
      });
    } else e.exposed || (e.exposed = {});
  (se && e.render === Ke && (e.render = se),
    rt != null && (e.inheritAttrs = rt),
    gt && (e.components = gt),
    vt && (e.directives = vt),
    ye && Ri(e));
}
function xr(e, t, n = Ke) {
  F(e) && (e = zn(e));
  for (const s in e) {
    const i = e[s];
    let o;
    (q(i)
      ? "default" in i
        ? (o = on(i.from || s, i.default, !0))
        : (o = on(i.from || s))
      : (o = on(i)),
      de(o)
        ? Object.defineProperty(t, s, {
            enumerable: !0,
            configurable: !0,
            get: () => o.value,
            set: (r) => (o.value = r),
          })
        : (t[s] = o));
  }
}
function Os(e, t, n) {
  Ie(F(e) ? e.map((s) => s.bind(t.proxy)) : e.bind(t.proxy), t, n);
}
function Li(e, t, n, s) {
  let i = s.includes(".") ? Di(n, s) : () => n[s];
  if (ne(e)) {
    const o = t[e];
    N(o) && rn(i, o);
  } else if (N(e)) rn(i, e.bind(n));
  else if (q(e))
    if (F(e)) e.forEach((o) => Li(o, t, n, s));
    else {
      const o = N(e.handler) ? e.handler.bind(n) : t[e.handler];
      N(o) && rn(i, o, e);
    }
}
function ji(e) {
  const t = e.type,
    { mixins: n, extends: s } = t,
    {
      mixins: i,
      optionsCache: o,
      config: { optionMergeStrategies: r },
    } = e.appContext,
    l = o.get(t);
  let a;
  return (
    l
      ? (a = l)
      : !i.length && !n && !s
        ? (a = t)
        : ((a = {}),
          i.length && i.forEach((f) => pn(a, f, r, !0)),
          pn(a, t, r)),
    q(t) && o.set(t, a),
    a
  );
}
function pn(e, t, n, s = !1) {
  const { mixins: i, extends: o } = t;
  (o && pn(e, o, n, !0), i && i.forEach((r) => pn(e, r, n, !0)));
  for (const r in t)
    if (!(s && r === "expose")) {
      const l = Sr[r] || (n && n[r]);
      e[r] = l ? l(e[r], t[r]) : t[r];
    }
  return e;
}
const Sr = {
  data: Ps,
  props: Ms,
  emits: Ms,
  methods: Rt,
  computed: Rt,
  beforeCreate: ge,
  created: ge,
  beforeMount: ge,
  mounted: ge,
  beforeUpdate: ge,
  updated: ge,
  beforeDestroy: ge,
  beforeUnmount: ge,
  destroyed: ge,
  unmounted: ge,
  activated: ge,
  deactivated: ge,
  errorCaptured: ge,
  serverPrefetch: ge,
  components: Rt,
  directives: Rt,
  watch: $r,
  provide: Ps,
  inject: wr,
};
function Ps(e, t) {
  return t
    ? e
      ? function () {
          return pe(
            N(e) ? e.call(this, this) : e,
            N(t) ? t.call(this, this) : t,
          );
        }
      : t
    : e;
}
function wr(e, t) {
  return Rt(zn(e), zn(t));
}
function zn(e) {
  if (F(e)) {
    const t = {};
    for (let n = 0; n < e.length; n++) t[e[n]] = e[n];
    return t;
  }
  return e;
}
function ge(e, t) {
  return e ? [...new Set([].concat(e, t))] : t;
}
function Rt(e, t) {
  return e ? pe(Object.create(null), e, t) : t;
}
function Ms(e, t) {
  return e
    ? F(e) && F(t)
      ? [...new Set([...e, ...t])]
      : pe(Object.create(null), As(e), As(t ?? {}))
    : t;
}
function $r(e, t) {
  if (!e) return t;
  if (!t) return e;
  const n = pe(Object.create(null), e);
  for (const s in t) n[s] = ge(e[s], t[s]);
  return n;
}
function Vi() {
  return {
    app: null,
    config: {
      isNativeTag: ni,
      performance: !1,
      globalProperties: {},
      optionMergeStrategies: {},
      errorHandler: void 0,
      warnHandler: void 0,
      compilerOptions: {},
    },
    mixins: [],
    components: {},
    directives: {},
    provides: Object.create(null),
    optionsCache: new WeakMap(),
    propsCache: new WeakMap(),
    emitsCache: new WeakMap(),
  };
}
let Cr = 0;
function Er(e, t) {
  return function (s, i = null) {
    (N(s) || (s = pe({}, s)), i != null && !q(i) && (i = null));
    const o = Vi(),
      r = new WeakSet(),
      l = [];
    let a = !1;
    const f = (o.app = {
      _uid: Cr++,
      _component: s,
      _props: i,
      _container: null,
      _context: o,
      _instance: null,
      version: ol,
      get config() {
        return o.config;
      },
      set config(p) {},
      use(p, ...g) {
        return (
          r.has(p) ||
            (p && N(p.install)
              ? (r.add(p), p.install(f, ...g))
              : N(p) && (r.add(p), p(f, ...g))),
          f
        );
      },
      mixin(p) {
        return (o.mixins.includes(p) || o.mixins.push(p), f);
      },
      component(p, g) {
        return g ? ((o.components[p] = g), f) : o.components[p];
      },
      directive(p, g) {
        return g ? ((o.directives[p] = g), f) : o.directives[p];
      },
      mount(p, g, E) {
        if (!a) {
          const T = f._ceVNode || oe(s, i);
          return (
            (T.appContext = o),
            E === !0 ? (E = "svg") : E === !1 && (E = void 0),
            e(T, p, E),
            (a = !0),
            (f._container = p),
            (p.__vue_app__ = f),
            On(T.component)
          );
        }
      },
      onUnmount(p) {
        l.push(p);
      },
      unmount() {
        a &&
          (Ie(l, f._instance, 16),
          e(null, f._container),
          delete f._container.__vue_app__);
      },
      provide(p, g) {
        return ((o.provides[p] = g), f);
      },
      runWithContext(p) {
        const g = St;
        St = f;
        try {
          return p();
        } finally {
          St = g;
        }
      },
    });
    return f;
  };
}
let St = null;
const Tr = (e, t) =>
  t === "modelValue" || t === "model-value"
    ? e.modelModifiers
    : e[`${t}Modifiers`] || e[`${Oe(t)}Modifiers`] || e[`${ht(t)}Modifiers`];
function Ar(e, t, ...n) {
  if (e.isUnmounted) return;
  const s = e.vnode.props || Y;
  let i = n;
  const o = t.startsWith("update:"),
    r = o && Tr(s, t.slice(7));
  r &&
    (r.trim && (i = n.map((p) => (ne(p) ? p.trim() : p))),
    r.number && (i = n.map(xn)));
  let l,
    a = s[(l = Mn(t))] || s[(l = Mn(Oe(t)))];
  (!a && o && (a = s[(l = Mn(ht(t)))]), a && Ie(a, e, 6, i));
  const f = s[l + "Once"];
  if (f) {
    if (!e.emitted) e.emitted = {};
    else if (e.emitted[l]) return;
    ((e.emitted[l] = !0), Ie(f, e, 6, i));
  }
}
const Or = new WeakMap();
function Ui(e, t, n = !1) {
  const s = n ? Or : t.emitsCache,
    i = s.get(e);
  if (i !== void 0) return i;
  const o = e.emits;
  let r = {},
    l = !1;
  if (!N(e)) {
    const a = (f) => {
      const p = Ui(f, t, !0);
      p && ((l = !0), pe(r, p));
    };
    (!n && t.mixins.length && t.mixins.forEach(a),
      e.extends && a(e.extends),
      e.mixins && e.mixins.forEach(a));
  }
  return !o && !l
    ? (q(e) && s.set(e, null), null)
    : (F(o) ? o.forEach((a) => (r[a] = null)) : pe(r, o),
      q(e) && s.set(e, r),
      r);
}
function Tn(e, t) {
  return !e || !mn(t)
    ? !1
    : ((t = t.slice(2).replace(/Once$/, "")),
      W(e, t[0].toLowerCase() + t.slice(1)) || W(e, ht(t)) || W(e, t));
}
function Is(e) {
  const {
      type: t,
      vnode: n,
      proxy: s,
      withProxy: i,
      propsOptions: [o],
      slots: r,
      attrs: l,
      emit: a,
      render: f,
      renderCache: p,
      props: g,
      data: E,
      setupState: T,
      ctx: K,
      inheritAttrs: k,
    } = e,
    te = fn(e);
  let X, U;
  try {
    if (n.shapeFlag & 4) {
      const D = i || s,
        se = D;
      ((X = Ue(f.call(se, D, p, g, T, E, K))), (U = l));
    } else {
      const D = t;
      ((X = Ue(
        D.length > 1 ? D(g, { attrs: l, slots: r, emit: a }) : D(g, null),
      )),
        (U = t.props ? l : Pr(l)));
    }
  } catch (D) {
    ((Ht.length = 0), $n(D, e, 1), (X = oe(ot)));
  }
  let z = X;
  if (U && k !== !1) {
    const D = Object.keys(U),
      { shapeFlag: se } = z;
    D.length &&
      se & 7 &&
      (o && D.some(_n) && (U = Mr(U, o)), (z = Et(z, U, !1, !0)));
  }
  return (
    n.dirs &&
      ((z = Et(z, null, !1, !0)),
      (z.dirs = z.dirs ? z.dirs.concat(n.dirs) : n.dirs)),
    n.transition && ps(z, n.transition),
    (X = z),
    fn(te),
    X
  );
}
const Pr = (e) => {
    let t;
    for (const n in e)
      (n === "class" || n === "style" || mn(n)) && ((t || (t = {}))[n] = e[n]);
    return t;
  },
  Mr = (e, t) => {
    const n = {};
    for (const s in e) (!_n(s) || !(s.slice(9) in t)) && (n[s] = e[s]);
    return n;
  };
function Ir(e, t, n) {
  const { props: s, children: i, component: o } = e,
    { props: r, children: l, patchFlag: a } = t,
    f = o.emitsOptions;
  if (t.dirs || t.transition) return !0;
  if (n && a >= 0) {
    if (a & 1024) return !0;
    if (a & 16) return s ? Ds(s, r, f) : !!r;
    if (a & 8) {
      const p = t.dynamicProps;
      for (let g = 0; g < p.length; g++) {
        const E = p[g];
        if (Hi(r, s, E) && !Tn(f, E)) return !0;
      }
    }
  } else
    return (i || l) && (!l || !l.$stable)
      ? !0
      : s === r
        ? !1
        : s
          ? r
            ? Ds(s, r, f)
            : !0
          : !!r;
  return !1;
}
function Ds(e, t, n) {
  const s = Object.keys(t);
  if (s.length !== Object.keys(e).length) return !0;
  for (let i = 0; i < s.length; i++) {
    const o = s[i];
    if (Hi(t, e, o) && !Tn(n, o)) return !0;
  }
  return !1;
}
function Hi(e, t, n) {
  const s = e[n],
    i = t[n];
  return n === "style" && q(s) && q(i) ? !Yt(s, i) : s !== i;
}
function Dr({ vnode: e, parent: t, suspense: n }, s) {
  for (; t;) {
    const i = t.subTree;
    if (
      (i.suspense &&
        i.suspense.activeBranch === e &&
        ((i.suspense.vnode.el = i.el = s), (e = i)),
      i === e)
    )
      (((e = t.vnode).el = s), (t = t.parent));
    else break;
  }
  n && n.activeBranch === e && (n.vnode.el = s);
}
const Ki = {},
  Bi = () => Object.create(Ki),
  Wi = (e) => Object.getPrototypeOf(e) === Ki;
function Rr(e, t, n, s = !1) {
  const i = {},
    o = Bi();
  ((e.propsDefaults = Object.create(null)), Gi(e, t, i, o));
  for (const r in e.propsOptions[0]) r in i || (i[r] = void 0);
  (n ? (e.props = s ? i : Uo(i)) : e.type.props ? (e.props = i) : (e.props = o),
    (e.attrs = o));
}
function Fr(e, t, n, s) {
  const {
      props: i,
      attrs: o,
      vnode: { patchFlag: r },
    } = e,
    l = B(i),
    [a] = e.propsOptions;
  let f = !1;
  if ((s || r > 0) && !(r & 16)) {
    if (r & 8) {
      const p = e.vnode.dynamicProps;
      for (let g = 0; g < p.length; g++) {
        let E = p[g];
        if (Tn(e.emitsOptions, E)) continue;
        const T = t[E];
        if (a)
          if (W(o, E)) T !== o[E] && ((o[E] = T), (f = !0));
          else {
            const K = Oe(E);
            i[K] = Jn(a, l, K, T, e, !1);
          }
        else T !== o[E] && ((o[E] = T), (f = !0));
      }
    }
  } else {
    Gi(e, t, i, o) && (f = !0);
    let p;
    for (const g in l)
      (!t || (!W(t, g) && ((p = ht(g)) === g || !W(t, p)))) &&
        (a
          ? n &&
            (n[g] !== void 0 || n[p] !== void 0) &&
            (i[g] = Jn(a, l, g, void 0, e, !0))
          : delete i[g]);
    if (o !== l) for (const g in o) (!t || !W(t, g)) && (delete o[g], (f = !0));
  }
  f && Je(e.attrs, "set", "");
}
function Gi(e, t, n, s) {
  const [i, o] = e.propsOptions;
  let r = !1,
    l;
  if (t)
    for (let a in t) {
      if (kt(a)) continue;
      const f = t[a];
      let p;
      i && W(i, (p = Oe(a)))
        ? !o || !o.includes(p)
          ? (n[p] = f)
          : ((l || (l = {}))[p] = f)
        : Tn(e.emitsOptions, a) ||
          ((!(a in s) || f !== s[a]) && ((s[a] = f), (r = !0)));
    }
  if (o) {
    const a = B(n),
      f = l || Y;
    for (let p = 0; p < o.length; p++) {
      const g = o[p];
      n[g] = Jn(i, a, g, f[g], e, !W(f, g));
    }
  }
  return r;
}
function Jn(e, t, n, s, i, o) {
  const r = e[n];
  if (r != null) {
    const l = W(r, "default");
    if (l && s === void 0) {
      const a = r.default;
      if (r.type !== Function && !r.skipFactory && N(a)) {
        const { propsDefaults: f } = i;
        if (n in f) s = f[n];
        else {
          const p = Zt(i);
          ((s = f[n] = a.call(null, t)), p());
        }
      } else s = a;
      i.ce && i.ce._setProp(n, s);
    }
    r[0] &&
      (o && !l ? (s = !1) : r[1] && (s === "" || s === ht(n)) && (s = !0));
  }
  return s;
}
const kr = new WeakMap();
function qi(e, t, n = !1) {
  const s = n ? kr : t.propsCache,
    i = s.get(e);
  if (i) return i;
  const o = e.props,
    r = {},
    l = [];
  let a = !1;
  if (!N(e)) {
    const p = (g) => {
      a = !0;
      const [E, T] = qi(g, t, !0);
      (pe(r, E), T && l.push(...T));
    };
    (!n && t.mixins.length && t.mixins.forEach(p),
      e.extends && p(e.extends),
      e.mixins && e.mixins.forEach(p));
  }
  if (!o && !a) return (q(e) && s.set(e, bt), bt);
  if (F(o))
    for (let p = 0; p < o.length; p++) {
      const g = Oe(o[p]);
      Rs(g) && (r[g] = Y);
    }
  else if (o)
    for (const p in o) {
      const g = Oe(p);
      if (Rs(g)) {
        const E = o[p],
          T = (r[g] = F(E) || N(E) ? { type: E } : pe({}, E)),
          K = T.type;
        let k = !1,
          te = !0;
        if (F(K))
          for (let X = 0; X < K.length; ++X) {
            const U = K[X],
              z = N(U) && U.name;
            if (z === "Boolean") {
              k = !0;
              break;
            } else z === "String" && (te = !1);
          }
        else k = N(K) && K.name === "Boolean";
        ((T[0] = k), (T[1] = te), (k || W(T, "default")) && l.push(g));
      }
    }
  const f = [r, l];
  return (q(e) && s.set(e, f), f);
}
function Rs(e) {
  return e[0] !== "$" && !kt(e);
}
const hs = (e) => e === "_" || e === "_ctx" || e === "$stable",
  gs = (e) => (F(e) ? e.map(Ue) : [Ue(e)]),
  Nr = (e, t, n) => {
    if (t._n) return t;
    const s = er((...i) => gs(t(...i)), n);
    return ((s._c = !1), s);
  },
  zi = (e, t, n) => {
    const s = e._ctx;
    for (const i in e) {
      if (hs(i)) continue;
      const o = e[i];
      if (N(o)) t[i] = Nr(i, o, s);
      else if (o != null) {
        const r = gs(o);
        t[i] = () => r;
      }
    }
  },
  Ji = (e, t) => {
    const n = gs(t);
    e.slots.default = () => n;
  },
  Yi = (e, t, n) => {
    for (const s in t) (n || !hs(s)) && (e[s] = t[s]);
  },
  Lr = (e, t, n) => {
    const s = (e.slots = Bi());
    if (e.vnode.shapeFlag & 32) {
      const i = t._;
      i ? (Yi(s, t, n), n && li(s, "_", i, !0)) : zi(t, s);
    } else t && Ji(e, t);
  },
  jr = (e, t, n) => {
    const { vnode: s, slots: i } = e;
    let o = !0,
      r = Y;
    if (s.shapeFlag & 32) {
      const l = t._;
      (l
        ? n && l === 1
          ? (o = !1)
          : Yi(i, t, n)
        : ((o = !t.$stable), zi(t, i)),
        (r = t));
    } else t && (Ji(e, t), (r = { default: 1 }));
    if (o) for (const l in i) !hs(l) && r[l] == null && delete i[l];
  },
  xe = Br;
function Vr(e) {
  return Ur(e);
}
function Ur(e, t) {
  const n = Sn();
  n.__VUE__ = !0;
  const {
      insert: s,
      remove: i,
      patchProp: o,
      createElement: r,
      createText: l,
      createComment: a,
      setText: f,
      setElementText: p,
      parentNode: g,
      nextSibling: E,
      setScopeId: T = Ke,
      insertStaticContent: K,
    } = e,
    k = (
      c,
      u,
      h,
      b = null,
      m = null,
      v = null,
      w = void 0,
      x = null,
      y = !!u.dynamicChildren,
    ) => {
      if (c === u) return;
      (c && !Dt(c, u) && ((b = Qt(c)), ee(c, m, v, !0), (c = null)),
        u.patchFlag === -2 && ((y = !1), (u.dynamicChildren = null)));
      const { type: _, ref: P, shapeFlag: C } = u;
      switch (_) {
        case An:
          te(c, u, h, b);
          break;
        case ot:
          X(c, u, h, b);
          break;
        case ln:
          c == null && U(u, h, b, w);
          break;
        case ue:
          gt(c, u, h, b, m, v, w, x, y);
          break;
        default:
          C & 1
            ? se(c, u, h, b, m, v, w, x, y)
            : C & 6
              ? vt(c, u, h, b, m, v, w, x, y)
              : (C & 64 || C & 128) && _.process(c, u, h, b, m, v, w, x, y, Pt);
      }
      P != null && m
        ? jt(P, c && c.ref, v, u || c, !u)
        : P == null && c && c.ref != null && jt(c.ref, null, v, c, !0);
    },
    te = (c, u, h, b) => {
      if (c == null) s((u.el = l(u.children)), h, b);
      else {
        const m = (u.el = c.el);
        u.children !== c.children && f(m, u.children);
      }
    },
    X = (c, u, h, b) => {
      c == null ? s((u.el = a(u.children || "")), h, b) : (u.el = c.el);
    },
    U = (c, u, h, b) => {
      [c.el, c.anchor] = K(c.children, u, h, b, c.el, c.anchor);
    },
    z = ({ el: c, anchor: u }, h, b) => {
      let m;
      for (; c && c !== u;) ((m = E(c)), s(c, h, b), (c = m));
      s(u, h, b);
    },
    D = ({ el: c, anchor: u }) => {
      let h;
      for (; c && c !== u;) ((h = E(c)), i(c), (c = h));
      i(u);
    },
    se = (c, u, h, b, m, v, w, x, y) => {
      if (
        (u.type === "svg" ? (w = "svg") : u.type === "math" && (w = "mathml"),
        c == null)
      )
        De(u, h, b, m, v, w, x, y);
      else {
        const _ = c.el && c.el._isVueCE ? c.el : null;
        try {
          (_ && _._beginPatch(), ye(c, u, m, v, w, x, y));
        } finally {
          _ && _._endPatch();
        }
      }
    },
    De = (c, u, h, b, m, v, w, x) => {
      let y, _;
      const { props: P, shapeFlag: C, transition: O, dirs: R } = c;
      if (
        ((y = c.el = r(c.type, v, P && P.is, P)),
        C & 8
          ? p(y, c.children)
          : C & 16 && Re(c.children, y, null, b, m, Ln(c, v), w, x),
        R && at(c, null, b, "created"),
        $e(y, c, c.scopeId, w, b),
        P)
      ) {
        for (const J in P) J !== "value" && !kt(J) && o(y, J, null, P[J], v, b);
        ("value" in P && o(y, "value", null, P.value, v),
          (_ = P.onVnodeBeforeMount) && Le(_, b, c));
      }
      R && at(c, null, b, "beforeMount");
      const H = Hr(m, O);
      (H && O.beforeEnter(y),
        s(y, u, h),
        ((_ = P && P.onVnodeMounted) || H || R) &&
          xe(() => {
            try {
              (_ && Le(_, b, c),
                H && O.enter(y),
                R && at(c, null, b, "mounted"));
            } finally {
            }
          }, m));
    },
    $e = (c, u, h, b, m) => {
      if ((h && T(c, h), b)) for (let v = 0; v < b.length; v++) T(c, b[v]);
      if (m) {
        let v = m.subTree;
        if (
          u === v ||
          (eo(v.type) && (v.ssContent === u || v.ssFallback === u))
        ) {
          const w = m.vnode;
          $e(c, w, w.scopeId, w.slotScopeIds, m.parent);
        }
      }
    },
    Re = (c, u, h, b, m, v, w, x, y = 0) => {
      for (let _ = y; _ < c.length; _++) {
        const P = (c[_] = x ? ze(c[_]) : Ue(c[_]));
        k(null, P, u, h, b, m, v, w, x);
      }
    },
    ye = (c, u, h, b, m, v, w) => {
      const x = (u.el = c.el);
      let { patchFlag: y, dynamicChildren: _, dirs: P } = u;
      y |= c.patchFlag & 16;
      const C = c.props || Y,
        O = u.props || Y;
      let R;
      if (
        (h && ct(h, !1),
        (R = O.onVnodeBeforeUpdate) && Le(R, h, u, c),
        P && at(u, c, h, "beforeUpdate"),
        h && ct(h, !0),
        ((C.innerHTML && O.innerHTML == null) ||
          (C.textContent && O.textContent == null)) &&
          p(x, ""),
        _
          ? Te(c.dynamicChildren, _, x, h, b, Ln(u, m), v)
          : w || j(c, u, x, null, h, b, Ln(u, m), v, !1),
        y > 0)
      ) {
        if (y & 16) rt(x, C, O, h, m);
        else if (
          (y & 2 && C.class !== O.class && o(x, "class", null, O.class, m),
          y & 4 && o(x, "style", C.style, O.style, m),
          y & 8)
        ) {
          const H = u.dynamicProps;
          for (let J = 0; J < H.length; J++) {
            const G = H[J],
              ie = C[G],
              ae = O[G];
            (ae !== ie || G === "value") && o(x, G, ie, ae, m, h);
          }
        }
        y & 1 && c.children !== u.children && p(x, u.children);
      } else !w && _ == null && rt(x, C, O, h, m);
      ((R = O.onVnodeUpdated) || P) &&
        xe(() => {
          (R && Le(R, h, u, c), P && at(u, c, h, "updated"));
        }, b);
    },
    Te = (c, u, h, b, m, v, w) => {
      for (let x = 0; x < u.length; x++) {
        const y = c[x],
          _ = u[x],
          P =
            y.el && (y.type === ue || !Dt(y, _) || y.shapeFlag & 198)
              ? g(y.el)
              : h;
        k(y, _, P, null, b, m, v, w, !0);
      }
    },
    rt = (c, u, h, b, m) => {
      if (u !== h) {
        if (u !== Y)
          for (const v in u) !kt(v) && !(v in h) && o(c, v, u[v], null, m, b);
        for (const v in h) {
          if (kt(v)) continue;
          const w = h[v],
            x = u[v];
          w !== x && v !== "value" && o(c, v, x, w, m, b);
        }
        "value" in h && o(c, "value", u.value, h.value, m);
      }
    },
    gt = (c, u, h, b, m, v, w, x, y) => {
      const _ = (u.el = c ? c.el : l("")),
        P = (u.anchor = c ? c.anchor : l(""));
      let { patchFlag: C, dynamicChildren: O, slotScopeIds: R } = u;
      (R && (x = x ? x.concat(R) : R),
        c == null
          ? (s(_, h, b), s(P, h, b), Re(u.children || [], h, P, m, v, w, x, y))
          : C > 0 &&
              C & 64 &&
              O &&
              c.dynamicChildren &&
              c.dynamicChildren.length === O.length
            ? (Te(c.dynamicChildren, O, h, m, v, w, x),
              (u.key != null || (m && u === m.subTree)) && Xi(c, u, !0))
            : j(c, u, h, P, m, v, w, x, y));
    },
    vt = (c, u, h, b, m, v, w, x, y) => {
      ((u.slotScopeIds = x),
        c == null
          ? u.shapeFlag & 512
            ? m.ctx.activate(u, h, b, w, y)
            : A(u, h, b, m, v, w, y)
          : $(c, u, y));
    },
    A = (c, u, h, b, m, v, w) => {
      const x = (c.component = Zr(c, b, m));
      if ((Fi(c) && (x.ctx.renderer = Pt), el(x, !1, w), x.asyncDep)) {
        if ((m && m.registerDep(x, S, w), !c.el)) {
          const y = (x.subTree = oe(ot));
          (X(null, y, u, h), (c.placeholder = y.el));
        }
      } else S(x, c, u, h, m, v, w);
    },
    $ = (c, u, h) => {
      const b = (u.component = c.component);
      if (Ir(c, u, h))
        if (b.asyncDep && !b.asyncResolved) {
          V(b, u, h);
          return;
        } else ((b.next = u), b.update());
      else ((u.el = c.el), (b.vnode = u));
    },
    S = (c, u, h, b, m, v, w) => {
      const x = () => {
        if (c.isMounted) {
          let { next: C, bu: O, u: R, parent: H, vnode: J } = c;
          {
            const ke = Zi(c);
            if (ke) {
              (C && ((C.el = J.el), V(c, C, w)),
                ke.asyncDep.then(() => {
                  xe(() => {
                    c.isUnmounted || _();
                  }, m);
                }));
              return;
            }
          }
          let G = C,
            ie;
          (ct(c, !1),
            C ? ((C.el = J.el), V(c, C, w)) : (C = J),
            O && sn(O),
            (ie = C.props && C.props.onVnodeBeforeUpdate) && Le(ie, H, C, J),
            ct(c, !0));
          const ae = Is(c),
            Fe = c.subTree;
          ((c.subTree = ae),
            k(Fe, ae, g(Fe.el), Qt(Fe), c, m, v),
            (C.el = ae.el),
            G === null && Dr(c, ae.el),
            R && xe(R, m),
            (ie = C.props && C.props.onVnodeUpdated) &&
              xe(() => Le(ie, H, C, J), m));
        } else {
          let C;
          const { el: O, props: R } = u,
            { bm: H, m: J, parent: G, root: ie, type: ae } = c,
            Fe = Vt(u);
          (ct(c, !1),
            H && sn(H),
            !Fe && (C = R && R.onVnodeBeforeMount) && Le(C, G, u),
            ct(c, !0));
          {
            ie.ce &&
              ie.ce._hasShadowRoot() &&
              ie.ce._injectChildStyle(ae, c.parent ? c.parent.type : void 0);
            const ke = (c.subTree = Is(c));
            (k(null, ke, h, b, c, m, v), (u.el = ke.el));
          }
          if ((J && xe(J, m), !Fe && (C = R && R.onVnodeMounted))) {
            const ke = u;
            xe(() => Le(C, G, ke), m);
          }
          ((u.shapeFlag & 256 ||
            (G && Vt(G.vnode) && G.vnode.shapeFlag & 256)) &&
            c.a &&
            xe(c.a, m),
            (c.isMounted = !0),
            (u = h = b = null));
        }
      };
      c.scope.on();
      const y = (c.effect = new fi(x));
      c.scope.off();
      const _ = (c.update = y.run.bind(y)),
        P = (c.job = y.runIfDirty.bind(y));
      ((P.i = c), (P.id = c.uid), (y.scheduler = () => ds(P)), ct(c, !0), _());
    },
    V = (c, u, h) => {
      u.component = c;
      const b = c.vnode.props;
      ((c.vnode = u),
        (c.next = null),
        Fr(c, u.props, b, h),
        jr(c, u.children, h),
        Xe(),
        Cs(c),
        Ze());
    },
    j = (c, u, h, b, m, v, w, x, y = !1) => {
      const _ = c && c.children,
        P = c ? c.shapeFlag : 0,
        C = u.children,
        { patchFlag: O, shapeFlag: R } = u;
      if (O > 0) {
        if (O & 128) {
          tt(_, C, h, b, m, v, w, x, y);
          return;
        } else if (O & 256) {
          he(_, C, h, b, m, v, w, x, y);
          return;
        }
      }
      R & 8
        ? (P & 16 && Ot(_, m, v), C !== _ && p(h, C))
        : P & 16
          ? R & 16
            ? tt(_, C, h, b, m, v, w, x, y)
            : Ot(_, m, v, !0)
          : (P & 8 && p(h, ""), R & 16 && Re(C, h, b, m, v, w, x, y));
    },
    he = (c, u, h, b, m, v, w, x, y) => {
      ((c = c || bt), (u = u || bt));
      const _ = c.length,
        P = u.length,
        C = Math.min(_, P);
      let O;
      for (O = 0; O < C; O++) {
        const R = (u[O] = y ? ze(u[O]) : Ue(u[O]));
        k(c[O], R, h, null, m, v, w, x, y);
      }
      _ > P ? Ot(c, m, v, !0, !1, C) : Re(u, h, b, m, v, w, x, y, C);
    },
    tt = (c, u, h, b, m, v, w, x, y) => {
      let _ = 0;
      const P = u.length;
      let C = c.length - 1,
        O = P - 1;
      for (; _ <= C && _ <= O;) {
        const R = c[_],
          H = (u[_] = y ? ze(u[_]) : Ue(u[_]));
        if (Dt(R, H)) k(R, H, h, null, m, v, w, x, y);
        else break;
        _++;
      }
      for (; _ <= C && _ <= O;) {
        const R = c[C],
          H = (u[O] = y ? ze(u[O]) : Ue(u[O]));
        if (Dt(R, H)) k(R, H, h, null, m, v, w, x, y);
        else break;
        (C--, O--);
      }
      if (_ > C) {
        if (_ <= O) {
          const R = O + 1,
            H = R < P ? u[R].el : b;
          for (; _ <= O;)
            (k(null, (u[_] = y ? ze(u[_]) : Ue(u[_])), h, H, m, v, w, x, y),
              _++);
        }
      } else if (_ > O) for (; _ <= C;) (ee(c[_], m, v, !0), _++);
      else {
        const R = _,
          H = _,
          J = new Map();
        for (_ = H; _ <= O; _++) {
          const Se = (u[_] = y ? ze(u[_]) : Ue(u[_]));
          Se.key != null && J.set(Se.key, _);
        }
        let G,
          ie = 0;
        const ae = O - H + 1;
        let Fe = !1,
          ke = 0;
        const Mt = new Array(ae);
        for (_ = 0; _ < ae; _++) Mt[_] = 0;
        for (_ = R; _ <= C; _++) {
          const Se = c[_];
          if (ie >= ae) {
            ee(Se, m, v, !0);
            continue;
          }
          let Ne;
          if (Se.key != null) Ne = J.get(Se.key);
          else
            for (G = H; G <= O; G++)
              if (Mt[G - H] === 0 && Dt(Se, u[G])) {
                Ne = G;
                break;
              }
          Ne === void 0
            ? ee(Se, m, v, !0)
            : ((Mt[Ne - H] = _ + 1),
              Ne >= ke ? (ke = Ne) : (Fe = !0),
              k(Se, u[Ne], h, null, m, v, w, x, y),
              ie++);
        }
        const _s = Fe ? Kr(Mt) : bt;
        for (G = _s.length - 1, _ = ae - 1; _ >= 0; _--) {
          const Se = H + _,
            Ne = u[Se],
            bs = u[Se + 1],
            ys = Se + 1 < P ? bs.el || Qi(bs) : b;
          Mt[_] === 0
            ? k(null, Ne, h, ys, m, v, w, x, y)
            : Fe && (G < 0 || _ !== _s[G] ? We(Ne, h, ys, 2) : G--);
        }
      }
    },
    We = (c, u, h, b, m = null) => {
      const { el: v, type: w, transition: x, children: y, shapeFlag: _ } = c;
      if (_ & 6) {
        We(c.component.subTree, u, h, b);
        return;
      }
      if (_ & 128) {
        c.suspense.move(u, h, b);
        return;
      }
      if (_ & 64) {
        w.move(c, u, h, Pt);
        return;
      }
      if (w === ue) {
        s(v, u, h);
        for (let C = 0; C < y.length; C++) We(y[C], u, h, b);
        s(c.anchor, u, h);
        return;
      }
      if (w === ln) {
        z(c, u, h);
        return;
      }
      if (b !== 2 && _ & 1 && x)
        if (b === 0)
          x.persisted && !v[kn]
            ? s(v, u, h)
            : (x.beforeEnter(v), s(v, u, h), xe(() => x.enter(v), m));
        else {
          const { leave: C, delayLeave: O, afterLeave: R } = x,
            H = () => {
              c.ctx.isUnmounted ? i(v) : s(v, u, h);
            },
            J = () => {
              const G = v._isLeaving || !!v[kn];
              (v._isLeaving && v[kn](!0),
                x.persisted && !G
                  ? H()
                  : C(v, () => {
                      (H(), R && R());
                    }));
            };
          O ? O(v, H, J) : J();
        }
      else s(v, u, h);
    },
    ee = (c, u, h, b = !1, m = !1) => {
      const {
        type: v,
        props: w,
        ref: x,
        children: y,
        dynamicChildren: _,
        shapeFlag: P,
        patchFlag: C,
        dirs: O,
        cacheIndex: R,
        memo: H,
      } = c;
      if (
        (C === -2 && (m = !1),
        x != null && (Xe(), jt(x, null, h, c, !0), Ze()),
        R != null && (u.renderCache[R] = void 0),
        P & 256)
      ) {
        u.ctx.deactivate(c);
        return;
      }
      const J = P & 1 && O,
        G = !Vt(c);
      let ie;
      if ((G && (ie = w && w.onVnodeBeforeUnmount) && Le(ie, u, c), P & 6))
        At(c.component, h, b);
      else {
        if (P & 128) {
          c.suspense.unmount(h, b);
          return;
        }
        (J && at(c, null, u, "beforeUnmount"),
          P & 64
            ? c.type.remove(c, u, h, Pt, b)
            : _ && !_.hasOnce && (v !== ue || (C > 0 && C & 64))
              ? Ot(_, u, h, !1, !0)
              : ((v === ue && C & 384) || (!m && P & 16)) && Ot(y, u, h),
          b && Ae(c));
      }
      const ae = H != null && R == null;
      ((G && (ie = w && w.onVnodeUnmounted)) || J || ae) &&
        xe(() => {
          (ie && Le(ie, u, c),
            J && at(c, null, u, "unmounted"),
            ae && (c.el = null));
        }, h);
    },
    Ae = (c) => {
      const { type: u, el: h, anchor: b, transition: m } = c;
      if (u === ue) {
        lt(h, b);
        return;
      }
      if (u === ln) {
        D(c);
        return;
      }
      const v = () => {
        (i(h), m && !m.persisted && m.afterLeave && m.afterLeave());
      };
      if (c.shapeFlag & 1 && m && !m.persisted) {
        const { leave: w, delayLeave: x } = m,
          y = () => w(h, v);
        x ? x(c.el, v, y) : y();
      } else v();
    },
    lt = (c, u) => {
      let h;
      for (; c !== u;) ((h = E(c)), i(c), (c = h));
      i(u);
    },
    At = (c, u, h) => {
      const { bum: b, scope: m, job: v, subTree: w, um: x, m: y, a: _ } = c;
      (Fs(y),
        Fs(_),
        b && sn(b),
        m.stop(),
        v && ((v.flags |= 8), ee(w, c, u, h)),
        x && xe(x, u),
        xe(() => {
          c.isUnmounted = !0;
        }, u));
    },
    Ot = (c, u, h, b = !1, m = !1, v = 0) => {
      for (let w = v; w < c.length; w++) ee(c[w], u, h, b, m);
    },
    Qt = (c) => {
      if (c.shapeFlag & 6) return Qt(c.component.subTree);
      if (c.shapeFlag & 128) return c.suspense.next();
      const u = E(c.anchor || c.el),
        h = u && u[or];
      return h ? E(h) : u;
    };
  let Pn = !1;
  const ms = (c, u, h) => {
      let b;
      (c == null
        ? u._vnode && (ee(u._vnode, null, null, !0), (b = u._vnode.component))
        : k(u._vnode || null, c, u, null, null, null, h),
        (u._vnode = c),
        Pn || ((Pn = !0), Cs(b), Oi(), (Pn = !1)));
    },
    Pt = {
      p: k,
      um: ee,
      m: We,
      r: Ae,
      mt: A,
      mc: Re,
      pc: j,
      pbc: Te,
      n: Qt,
      o: e,
    };
  return { render: ms, hydrate: void 0, createApp: Er(ms) };
}
function Ln({ type: e, props: t }, n) {
  return (n === "svg" && e === "foreignObject") ||
    (n === "mathml" &&
      e === "annotation-xml" &&
      t &&
      t.encoding &&
      t.encoding.includes("html"))
    ? void 0
    : n;
}
function ct({ effect: e, job: t }, n) {
  n ? ((e.flags |= 32), (t.flags |= 4)) : ((e.flags &= -33), (t.flags &= -5));
}
function Hr(e, t) {
  return (!e || (e && !e.pendingBranch)) && t && !t.persisted;
}
function Xi(e, t, n = !1) {
  const s = e.children,
    i = t.children;
  if (F(s) && F(i))
    for (let o = 0; o < s.length; o++) {
      const r = s[o];
      let l = i[o];
      (l.shapeFlag & 1 &&
        !l.dynamicChildren &&
        ((l.patchFlag <= 0 || l.patchFlag === 32) &&
          ((l = i[o] = ze(i[o])), (l.el = r.el)),
        !n && l.patchFlag !== -2 && Xi(r, l)),
        l.type === An &&
          (l.patchFlag === -1 && (l = i[o] = ze(l)), (l.el = r.el)),
        l.type === ot && !l.el && (l.el = r.el));
    }
}
function Kr(e) {
  const t = e.slice(),
    n = [0];
  let s, i, o, r, l;
  const a = e.length;
  for (s = 0; s < a; s++) {
    const f = e[s];
    if (f !== 0) {
      if (((i = n[n.length - 1]), e[i] < f)) {
        ((t[s] = i), n.push(s));
        continue;
      }
      for (o = 0, r = n.length - 1; o < r;)
        ((l = (o + r) >> 1), e[n[l]] < f ? (o = l + 1) : (r = l));
      f < e[n[o]] && (o > 0 && (t[s] = n[o - 1]), (n[o] = s));
    }
  }
  for (o = n.length, r = n[o - 1]; o-- > 0;) ((n[o] = r), (r = t[r]));
  return n;
}
function Zi(e) {
  const t = e.subTree.component;
  if (t) return t.asyncDep && !t.asyncResolved ? t : Zi(t);
}
function Fs(e) {
  if (e) for (let t = 0; t < e.length; t++) e[t].flags |= 8;
}
function Qi(e) {
  if (e.placeholder) return e.placeholder;
  const t = e.component;
  return t ? Qi(t.subTree) : null;
}
const eo = (e) => e.__isSuspense;
function Br(e, t) {
  t && t.pendingBranch
    ? F(e)
      ? t.effects.push(...e)
      : t.effects.push(e)
    : Qo(e);
}
const ue = Symbol.for("v-fgt"),
  An = Symbol.for("v-txt"),
  ot = Symbol.for("v-cmt"),
  ln = Symbol.for("v-stc"),
  Ht = [];
let we = null;
function M(e = !1) {
  Ht.push((we = e ? null : []));
}
function Wr() {
  (Ht.pop(), (we = Ht[Ht.length - 1] || null));
}
let Gt = 1;
function ks(e, t = !1) {
  ((Gt += e), e < 0 && we && t && (we.hasOnce = !0));
}
function to(e) {
  return (
    (e.dynamicChildren = Gt > 0 ? we || bt : null),
    Wr(),
    Gt > 0 && we && we.push(e),
    e
  );
}
function I(e, t, n, s, i, o) {
  return to(d(e, t, n, s, i, o, !0));
}
function Gr(e, t, n, s, i) {
  return to(oe(e, t, n, s, i, !0));
}
function no(e) {
  return e ? e.__v_isVNode === !0 : !1;
}
function Dt(e, t) {
  return e.type === t.type && e.key === t.key;
}
const so = ({ key: e }) => e ?? null,
  an = ({ ref: e, ref_key: t, ref_for: n }) => (
    typeof e == "number" && (e = "" + e),
    e != null
      ? ne(e) || de(e) || N(e)
        ? { i: Ce, r: e, k: t, f: !!n }
        : e
      : null
  );
function d(
  e,
  t = null,
  n = null,
  s = 0,
  i = null,
  o = e === ue ? 0 : 1,
  r = !1,
  l = !1,
) {
  const a = {
    __v_isVNode: !0,
    __v_skip: !0,
    type: e,
    props: t,
    key: t && so(t),
    ref: t && an(t),
    scopeId: Mi,
    slotScopeIds: null,
    children: n,
    component: null,
    suspense: null,
    ssContent: null,
    ssFallback: null,
    dirs: null,
    transition: null,
    el: null,
    anchor: null,
    target: null,
    targetStart: null,
    targetAnchor: null,
    staticCount: 0,
    shapeFlag: o,
    patchFlag: s,
    dynamicProps: i,
    dynamicChildren: null,
    appContext: null,
    ctx: Ce,
  };
  return (
    l
      ? (vs(a, n), o & 128 && e.normalize(a))
      : n && (a.shapeFlag |= ne(n) ? 8 : 16),
    Gt > 0 &&
      !r &&
      we &&
      (a.patchFlag > 0 || o & 6) &&
      a.patchFlag !== 32 &&
      we.push(a),
    a
  );
}
const oe = qr;
function qr(e, t = null, n = null, s = 0, i = null, o = !1) {
  if (((!e || e === _r) && (e = ot), no(e))) {
    const l = Et(e, t, !0);
    return (
      n && vs(l, n),
      Gt > 0 &&
        !o &&
        we &&
        (l.shapeFlag & 6 ? (we[we.indexOf(e)] = l) : we.push(l)),
      (l.patchFlag = -2),
      l
    );
  }
  if ((il(e) && (e = e.__vccOpts), t)) {
    t = zr(t);
    let { class: l, style: a } = t;
    (l && !ne(l) && (t.class = me(l)),
      q(a) && (fs(a) && !F(a) && (a = pe({}, a)), (t.style = ss(a))));
  }
  const r = ne(e) ? 1 : eo(e) ? 128 : rr(e) ? 64 : q(e) ? 4 : N(e) ? 2 : 0;
  return d(e, t, n, s, i, r, o, !0);
}
function zr(e) {
  return e ? (fs(e) || Wi(e) ? pe({}, e) : e) : null;
}
function Et(e, t, n = !1, s = !1) {
  const { props: i, ref: o, patchFlag: r, children: l, transition: a } = e,
    f = t ? Jr(i || {}, t) : i,
    p = {
      __v_isVNode: !0,
      __v_skip: !0,
      type: e.type,
      props: f,
      key: f && so(f),
      ref:
        t && t.ref
          ? n && o
            ? F(o)
              ? o.concat(an(t))
              : [o, an(t)]
            : an(t)
          : o,
      scopeId: e.scopeId,
      slotScopeIds: e.slotScopeIds,
      children: l,
      target: e.target,
      targetStart: e.targetStart,
      targetAnchor: e.targetAnchor,
      staticCount: e.staticCount,
      shapeFlag: e.shapeFlag,
      patchFlag: t && e.type !== ue ? (r === -1 ? 16 : r | 16) : r,
      dynamicProps: e.dynamicProps,
      dynamicChildren: e.dynamicChildren,
      appContext: e.appContext,
      dirs: e.dirs,
      transition: a,
      component: e.component,
      suspense: e.suspense,
      ssContent: e.ssContent && Et(e.ssContent),
      ssFallback: e.ssFallback && Et(e.ssFallback),
      placeholder: e.placeholder,
      el: e.el,
      anchor: e.anchor,
      ctx: e.ctx,
      ce: e.ce,
    };
  return (a && s && ps(p, a.clone(p)), p);
}
function io(e = " ", t = 0) {
  return oe(An, null, e, t);
}
function Ns(e, t) {
  const n = oe(ln, null, e);
  return ((n.staticCount = t), n);
}
function re(e = "", t = !1) {
  return t ? (M(), Gr(ot, null, e)) : oe(ot, null, e);
}
function Ue(e) {
  return e == null || typeof e == "boolean"
    ? oe(ot)
    : F(e)
      ? oe(ue, null, e.slice())
      : no(e)
        ? ze(e)
        : oe(An, null, String(e));
}
function ze(e) {
  return (e.el === null && e.patchFlag !== -1) || e.memo ? e : Et(e);
}
function vs(e, t) {
  let n = 0;
  const { shapeFlag: s } = e;
  if (t == null) t = null;
  else if (F(t)) n = 16;
  else if (typeof t == "object")
    if (s & 65) {
      const i = t.default;
      i && (i._c && (i._d = !1), vs(e, i()), i._c && (i._d = !0));
      return;
    } else {
      n = 32;
      const i = t._;
      !i && !Wi(t)
        ? (t._ctx = Ce)
        : i === 3 &&
          Ce &&
          (Ce.slots._ === 1 ? (t._ = 1) : ((t._ = 2), (e.patchFlag |= 1024)));
    }
  else
    N(t)
      ? ((t = { default: t, _ctx: Ce }), (n = 32))
      : ((t = String(t)), s & 64 ? ((n = 16), (t = [io(t)])) : (n = 8));
  ((e.children = t), (e.shapeFlag |= n));
}
function Jr(...e) {
  const t = {};
  for (let n = 0; n < e.length; n++) {
    const s = e[n];
    for (const i in s)
      if (i === "class")
        t.class !== s.class && (t.class = me([t.class, s.class]));
      else if (i === "style") t.style = ss([t.style, s.style]);
      else if (mn(i)) {
        const o = t[i],
          r = s[i];
        r && o !== r && !(F(o) && o.includes(r))
          ? (t[i] = o ? [].concat(o, r) : r)
          : r == null && o == null && !_n(i) && (t[i] = r);
      } else i !== "" && (t[i] = s[i]);
  }
  return t;
}
function Le(e, t, n, s = null) {
  Ie(e, t, 7, [n, s]);
}
const Yr = Vi();
let Xr = 0;
function Zr(e, t, n) {
  const s = e.type,
    i = (t ? t.appContext : e.appContext) || Yr,
    o = {
      uid: Xr++,
      vnode: e,
      type: s,
      parent: t,
      appContext: i,
      root: null,
      next: null,
      subTree: null,
      effect: null,
      update: null,
      job: null,
      scope: new So(!0),
      render: null,
      proxy: null,
      exposed: null,
      exposeProxy: null,
      withProxy: null,
      provides: t ? t.provides : Object.create(i.provides),
      ids: t ? t.ids : ["", 0, 0],
      accessCache: null,
      renderCache: [],
      components: null,
      directives: null,
      propsOptions: qi(s, i),
      emitsOptions: Ui(s, i),
      emit: null,
      emitted: null,
      propsDefaults: Y,
      inheritAttrs: s.inheritAttrs,
      ctx: Y,
      data: Y,
      props: Y,
      attrs: Y,
      slots: Y,
      refs: Y,
      setupState: Y,
      setupContext: null,
      suspense: n,
      suspenseId: n ? n.pendingId : 0,
      asyncDep: null,
      asyncResolved: !1,
      isMounted: !1,
      isUnmounted: !1,
      isDeactivated: !1,
      bc: null,
      c: null,
      bm: null,
      m: null,
      bu: null,
      u: null,
      um: null,
      bum: null,
      da: null,
      a: null,
      rtg: null,
      rtc: null,
      ec: null,
      sp: null,
    };
  return (
    (o.ctx = { _: o }),
    (o.root = t ? t.root : o),
    (o.emit = Ar.bind(null, o)),
    e.ce && e.ce(o),
    o
  );
}
let be = null;
const Qr = () => be || Ce;
let hn, Yn;
{
  const e = Sn(),
    t = (n, s) => {
      let i;
      return (
        (i = e[n]) || (i = e[n] = []),
        i.push(s),
        (o) => {
          i.length > 1 ? i.forEach((r) => r(o)) : i[0](o);
        }
      );
    };
  ((hn = t("__VUE_INSTANCE_SETTERS__", (n) => (be = n))),
    (Yn = t("__VUE_SSR_SETTERS__", (n) => (qt = n))));
}
const Zt = (e) => {
    const t = be;
    return (
      hn(e),
      e.scope.on(),
      () => {
        (e.scope.off(), hn(t));
      }
    );
  },
  Ls = () => {
    (be && be.scope.off(), hn(null));
  };
function oo(e) {
  return e.vnode.shapeFlag & 4;
}
let qt = !1;
function el(e, t = !1, n = !1) {
  t && Yn(t);
  const { props: s, children: i } = e.vnode,
    o = oo(e);
  (Rr(e, s, o, t), Lr(e, i, n || t));
  const r = o ? tl(e, t) : void 0;
  return (t && Yn(!1), r);
}
function tl(e, t) {
  const n = e.type;
  ((e.accessCache = Object.create(null)), (e.proxy = new Proxy(e.ctx, br)));
  const { setup: s } = n;
  if (s) {
    Xe();
    const i = (e.setupContext = s.length > 1 ? sl(e) : null),
      o = Zt(e),
      r = Xt(s, e, 0, [e.props, i]),
      l = si(r);
    if ((Ze(), o(), (l || e.sp) && !Vt(e) && Ri(e), l)) {
      if ((r.then(Ls, Ls), t))
        return r
          .then((a) => {
            js(e, a);
          })
          .catch((a) => {
            $n(a, e, 0);
          });
      e.asyncDep = r;
    } else js(e, r);
  } else ro(e);
}
function js(e, t, n) {
  (N(t)
    ? e.type.__ssrInlineRender
      ? (e.ssrRender = t)
      : (e.render = t)
    : q(t) && (e.setupState = Ci(t)),
    ro(e));
}
function ro(e, t, n) {
  const s = e.type;
  e.render || (e.render = s.render || Ke);
  {
    const i = Zt(e);
    Xe();
    try {
      yr(e);
    } finally {
      (Ze(), i());
    }
  }
}
const nl = {
  get(e, t) {
    return (fe(e, "get", ""), e[t]);
  },
};
function sl(e) {
  const t = (n) => {
    e.exposed = n || {};
  };
  return {
    attrs: new Proxy(e.attrs, nl),
    slots: e.slots,
    emit: e.emit,
    expose: t,
  };
}
function On(e) {
  return e.exposed
    ? e.exposeProxy ||
        (e.exposeProxy = new Proxy(Ci(Ho(e.exposed)), {
          get(t, n) {
            if (n in t) return t[n];
            if (n in Ut) return Ut[n](e);
          },
          has(t, n) {
            return n in t || n in Ut;
          },
        }))
    : e.proxy;
}
function il(e) {
  return N(e) && "__vccOpts" in e;
}
const it = (e, t) => zo(e, t, qt),
  ol = "3.5.35";
/**
 * @vue/runtime-dom v3.5.35
 * (c) 2018-present Yuxi (Evan) You and Vue contributors
 * @license MIT
 **/ let Xn;
const Vs = typeof window < "u" && window.trustedTypes;
if (Vs)
  try {
    Xn = Vs.createPolicy("vue", { createHTML: (e) => e });
  } catch {}
const lo = Xn ? (e) => Xn.createHTML(e) : (e) => e,
  rl = "http://www.w3.org/2000/svg",
  ll = "http://www.w3.org/1998/Math/MathML",
  qe = typeof document < "u" ? document : null,
  Us = qe && qe.createElement("template"),
  al = {
    insert: (e, t, n) => {
      t.insertBefore(e, n || null);
    },
    remove: (e) => {
      const t = e.parentNode;
      t && t.removeChild(e);
    },
    createElement: (e, t, n, s) => {
      const i =
        t === "svg"
          ? qe.createElementNS(rl, e)
          : t === "mathml"
            ? qe.createElementNS(ll, e)
            : n
              ? qe.createElement(e, { is: n })
              : qe.createElement(e);
      return (
        e === "select" &&
          s &&
          s.multiple != null &&
          i.setAttribute("multiple", s.multiple),
        i
      );
    },
    createText: (e) => qe.createTextNode(e),
    createComment: (e) => qe.createComment(e),
    setText: (e, t) => {
      e.nodeValue = t;
    },
    setElementText: (e, t) => {
      e.textContent = t;
    },
    parentNode: (e) => e.parentNode,
    nextSibling: (e) => e.nextSibling,
    querySelector: (e) => qe.querySelector(e),
    setScopeId(e, t) {
      e.setAttribute(t, "");
    },
    insertStaticContent(e, t, n, s, i, o) {
      const r = n ? n.previousSibling : t.lastChild;
      if (i && (i === o || i.nextSibling))
        for (
          ;
          t.insertBefore(i.cloneNode(!0), n),
            !(i === o || !(i = i.nextSibling));
        );
      else {
        Us.innerHTML = lo(
          s === "svg"
            ? `<svg>${e}</svg>`
            : s === "mathml"
              ? `<math>${e}</math>`
              : e,
        );
        const l = Us.content;
        if (s === "svg" || s === "mathml") {
          const a = l.firstChild;
          for (; a.firstChild;) l.appendChild(a.firstChild);
          l.removeChild(a);
        }
        t.insertBefore(l, n);
      }
      return [
        r ? r.nextSibling : t.firstChild,
        n ? n.previousSibling : t.lastChild,
      ];
    },
  },
  cl = Symbol("_vtc");
function ul(e, t, n) {
  const s = e[cl];
  (s && (t = (t ? [t, ...s] : [...s]).join(" ")),
    t == null
      ? e.removeAttribute("class")
      : n
        ? e.setAttribute("class", t)
        : (e.className = t));
}
const Hs = Symbol("_vod"),
  fl = Symbol("_vsh"),
  dl = Symbol(""),
  pl = /(?:^|;)\s*display\s*:/;
function hl(e, t, n) {
  const s = e.style,
    i = ne(n);
  let o = !1;
  if (n && !i) {
    if (t)
      if (ne(t))
        for (const r of t.split(";")) {
          const l = r.slice(0, r.indexOf(":")).trim();
          n[l] == null && Ft(s, l, "");
        }
      else for (const r in t) n[r] == null && Ft(s, r, "");
    for (const r in n) {
      r === "display" && (o = !0);
      const l = n[r];
      l != null
        ? vl(e, r, !ne(t) && t ? t[r] : void 0, l) || Ft(s, r, l)
        : Ft(s, r, "");
    }
  } else if (i) {
    if (t !== n) {
      const r = s[dl];
      (r && (n += ";" + r), (s.cssText = n), (o = pl.test(n)));
    }
  } else t && e.removeAttribute("style");
  Hs in e && ((e[Hs] = o ? s.display : ""), e[fl] && (s.display = "none"));
}
const Ks = /\s*!important$/;
function Ft(e, t, n) {
  if (F(n)) n.forEach((s) => Ft(e, t, s));
  else if ((n == null && (n = ""), t.startsWith("--"))) e.setProperty(t, n);
  else {
    const s = gl(e, t);
    Ks.test(n)
      ? e.setProperty(ht(s), n.replace(Ks, ""), "important")
      : (e[s] = n);
  }
}
const Bs = ["Webkit", "Moz", "ms"],
  jn = {};
function gl(e, t) {
  const n = jn[t];
  if (n) return n;
  let s = Oe(t);
  if (s !== "filter" && s in e) return (jn[t] = s);
  s = ri(s);
  for (let i = 0; i < Bs.length; i++) {
    const o = Bs[i] + s;
    if (o in e) return (jn[t] = o);
  }
  return t;
}
function vl(e, t, n, s) {
  return (
    e.tagName === "TEXTAREA" &&
    (t === "width" || t === "height") &&
    ne(s) &&
    n === s
  );
}
const Ws = "http://www.w3.org/1999/xlink";
function Gs(e, t, n, s, i, o = bo(t)) {
  s && t.startsWith("xlink:")
    ? n == null
      ? e.removeAttributeNS(Ws, t.slice(6, t.length))
      : e.setAttributeNS(Ws, t, n)
    : n == null || (o && !ai(n))
      ? e.removeAttribute(t)
      : e.setAttribute(t, o ? "" : Be(n) ? String(n) : n);
}
function qs(e, t, n, s, i) {
  if (t === "innerHTML" || t === "textContent") {
    n != null && (e[t] = t === "innerHTML" ? lo(n) : n);
    return;
  }
  const o = e.tagName;
  if (t === "value" && o !== "PROGRESS" && !o.includes("-")) {
    const l = o === "OPTION" ? e.getAttribute("value") || "" : e.value,
      a = n == null ? (e.type === "checkbox" ? "on" : "") : String(n);
    ((l !== a || !("_value" in e)) && (e.value = a),
      n == null && e.removeAttribute(t),
      (e._value = n));
    return;
  }
  let r = !1;
  if (n === "" || n == null) {
    const l = typeof e[t];
    l === "boolean"
      ? (n = ai(n))
      : n == null && l === "string"
        ? ((n = ""), (r = !0))
        : l === "number" && ((n = 0), (r = !0));
  }
  try {
    e[t] = n;
  } catch {}
  r && e.removeAttribute(i || t);
}
function ft(e, t, n, s) {
  e.addEventListener(t, n, s);
}
function ml(e, t, n, s) {
  e.removeEventListener(t, n, s);
}
const zs = Symbol("_vei");
function _l(e, t, n, s, i = null) {
  const o = e[zs] || (e[zs] = {}),
    r = o[t];
  if (s && r) r.value = s;
  else {
    const [l, a] = bl(t);
    if (s) {
      const f = (o[t] = Sl(s, i));
      ft(e, l, f, a);
    } else r && (ml(e, l, r, a), (o[t] = void 0));
  }
}
const Js = /(?:Once|Passive|Capture)$/;
function bl(e) {
  let t;
  if (Js.test(e)) {
    t = {};
    let s;
    for (; (s = e.match(Js));)
      ((e = e.slice(0, e.length - s[0].length)), (t[s[0].toLowerCase()] = !0));
  }
  return [e[2] === ":" ? e.slice(3) : ht(e.slice(2)), t];
}
let Vn = 0;
const yl = Promise.resolve(),
  xl = () => Vn || (yl.then(() => (Vn = 0)), (Vn = Date.now()));
function Sl(e, t) {
  const n = (s) => {
    if (!s._vts) s._vts = Date.now();
    else if (s._vts <= n.attached) return;
    const i = n.value;
    if (F(i)) {
      const o = s.stopImmediatePropagation;
      s.stopImmediatePropagation = () => {
        (o.call(s), (s._stopped = !0));
      };
      const r = i.slice(),
        l = [s];
      for (let a = 0; a < r.length && !s._stopped; a++) {
        const f = r[a];
        f && Ie(f, t, 5, l);
      }
    } else Ie(i, t, 5, [s]);
  };
  return ((n.value = e), (n.attached = xl()), n);
}
const Ys = (e) =>
    e.charCodeAt(0) === 111 &&
    e.charCodeAt(1) === 110 &&
    e.charCodeAt(2) > 96 &&
    e.charCodeAt(2) < 123,
  wl = (e, t, n, s, i, o) => {
    const r = i === "svg";
    t === "class"
      ? ul(e, s, r)
      : t === "style"
        ? hl(e, n, s)
        : mn(t)
          ? _n(t) || _l(e, t, n, s, o)
          : (
                t[0] === "."
                  ? ((t = t.slice(1)), !0)
                  : t[0] === "^"
                    ? ((t = t.slice(1)), !1)
                    : $l(e, t, s, r)
              )
            ? (qs(e, t, s),
              !e.tagName.includes("-") &&
                (t === "value" || t === "checked" || t === "selected") &&
                Gs(e, t, s, r, o, t !== "value"))
            : e._isVueCE &&
                (Cl(e, t) ||
                  (e._def.__asyncLoader && (/[A-Z]/.test(t) || !ne(s))))
              ? qs(e, Oe(t), s, o, t)
              : (t === "true-value"
                  ? (e._trueValue = s)
                  : t === "false-value" && (e._falseValue = s),
                Gs(e, t, s, r));
  };
function $l(e, t, n, s) {
  if (s)
    return !!(
      t === "innerHTML" ||
      t === "textContent" ||
      (t in e && Ys(t) && N(n))
    );
  if (
    t === "spellcheck" ||
    t === "draggable" ||
    t === "translate" ||
    t === "autocorrect" ||
    (t === "sandbox" && e.tagName === "IFRAME") ||
    t === "form" ||
    (t === "list" && e.tagName === "INPUT") ||
    (t === "type" && e.tagName === "TEXTAREA")
  )
    return !1;
  if (t === "width" || t === "height") {
    const i = e.tagName;
    if (i === "IMG" || i === "VIDEO" || i === "CANVAS" || i === "SOURCE")
      return !1;
  }
  return Ys(t) && ne(n) ? !1 : t in e;
}
function Cl(e, t) {
  const n = e._def.props;
  if (!n) return !1;
  const s = Oe(t);
  return Array.isArray(n)
    ? n.some((i) => Oe(i) === s)
    : Object.keys(n).some((i) => Oe(i) === s);
}
const gn = (e) => {
  const t = e.props["onUpdate:modelValue"] || !1;
  return F(t) ? (n) => sn(t, n) : t;
};
function El(e) {
  e.target.composing = !0;
}
function Xs(e) {
  const t = e.target;
  t.composing && ((t.composing = !1), t.dispatchEvent(new Event("input")));
}
const wt = Symbol("_assign");
function Zs(e, t, n) {
  return (t && (e = e.trim()), n && (e = xn(e)), e);
}
const ve = {
    created(e, { modifiers: { lazy: t, trim: n, number: s } }, i) {
      e[wt] = gn(i);
      const o = s || (i.props && i.props.type === "number");
      (ft(e, t ? "change" : "input", (r) => {
        r.target.composing || e[wt](Zs(e.value, n, o));
      }),
        (n || o) &&
          ft(e, "change", () => {
            e.value = Zs(e.value, n, o);
          }),
        t ||
          (ft(e, "compositionstart", El),
          ft(e, "compositionend", Xs),
          ft(e, "change", Xs)));
    },
    mounted(e, { value: t }) {
      e.value = t ?? "";
    },
    beforeUpdate(
      e,
      { value: t, oldValue: n, modifiers: { lazy: s, trim: i, number: o } },
      r,
    ) {
      if (((e[wt] = gn(r)), e.composing)) return;
      const l =
          (o || e.type === "number") && !/^0\d/.test(e.value)
            ? xn(e.value)
            : e.value,
        a = t ?? "";
      if (l === a) return;
      const f = e.getRootNode();
      ((f instanceof Document || f instanceof ShadowRoot) &&
        f.activeElement === e &&
        e.type !== "range" &&
        ((s && t === n) || (i && e.value.trim() === a))) ||
        (e.value = a);
    },
  },
  Zn = {
    deep: !0,
    created(e, { value: t, modifiers: { number: n } }, s) {
      const i = bn(t);
      (ft(e, "change", () => {
        const o = Array.prototype.filter
          .call(e.options, (r) => r.selected)
          .map((r) => (n ? xn(vn(r)) : vn(r)));
        (e[wt](e.multiple ? (i ? new Set(o) : o) : o[0]),
          (e._assigning = !0),
          Ti(() => {
            e._assigning = !1;
          }));
      }),
        (e[wt] = gn(s)));
    },
    mounted(e, { value: t }) {
      Qs(e, t);
    },
    beforeUpdate(e, t, n) {
      e[wt] = gn(n);
    },
    updated(e, { value: t }) {
      e._assigning || Qs(e, t);
    },
  };
function Qs(e, t) {
  const n = e.multiple,
    s = F(t);
  if (!(n && !s && !bn(t))) {
    for (let i = 0, o = e.options.length; i < o; i++) {
      const r = e.options[i],
        l = vn(r);
      if (n)
        if (s) {
          const a = typeof l;
          a === "string" || a === "number"
            ? (r.selected = t.some((f) => String(f) === String(l)))
            : (r.selected = xo(t, l) > -1);
        } else r.selected = t.has(l);
      else if (Yt(vn(r), t)) {
        e.selectedIndex !== i && (e.selectedIndex = i);
        return;
      }
    }
    !n && e.selectedIndex !== -1 && (e.selectedIndex = -1);
  }
}
function vn(e) {
  return "_value" in e ? e._value : e.value;
}
const Tl = ["ctrl", "shift", "alt", "meta"],
  Al = {
    stop: (e) => e.stopPropagation(),
    prevent: (e) => e.preventDefault(),
    self: (e) => e.target !== e.currentTarget,
    ctrl: (e) => !e.ctrlKey,
    shift: (e) => !e.shiftKey,
    alt: (e) => !e.altKey,
    meta: (e) => !e.metaKey,
    left: (e) => "button" in e && e.button !== 0,
    middle: (e) => "button" in e && e.button !== 1,
    right: (e) => "button" in e && e.button !== 2,
    exact: (e, t) => Tl.some((n) => e[`${n}Key`] && !t.includes(n)),
  },
  Qn = (e, t) => {
    if (!e) return e;
    const n = e._withMods || (e._withMods = {}),
      s = t.join(".");
    return (
      n[s] ||
      (n[s] = (i, ...o) => {
        for (let r = 0; r < t.length; r++) {
          const l = Al[t[r]];
          if (l && l(i, t)) return;
        }
        return e(i, ...o);
      })
    );
  },
  Ol = pe({ patchProp: wl }, al);
let ei;
function Pl() {
  return ei || (ei = Vr(Ol));
}
const Ml = (...e) => {
  const t = Pl().createApp(...e),
    { mount: n } = t;
  return (
    (t.mount = (s) => {
      const i = Dl(s);
      if (!i) return;
      const o = t._component;
      (!N(o) && !o.render && !o.template && (o.template = i.innerHTML),
        i.nodeType === 1 && (i.textContent = ""));
      const r = n(i, !1, Il(i));
      return (
        i instanceof Element &&
          (i.removeAttribute("v-cloak"), i.setAttribute("data-v-app", "")),
        r
      );
    }),
    t
  );
};
function Il(e) {
  if (e instanceof SVGElement) return "svg";
  if (typeof MathMLElement == "function" && e instanceof MathMLElement)
    return "mathml";
}
function Dl(e) {
  return ne(e) ? document.querySelector(e) : e;
}
const Rl = "modulepreload",
  Fl = function (e) {
    return "/" + e;
  },
  ti = {},
  kl = function (t, n, s) {
    let i = Promise.resolve();
    if (n && n.length > 0) {
      document.getElementsByTagName("link");
      const r = document.querySelector("meta[property=csp-nonce]"),
        l =
          (r == null ? void 0 : r.nonce) ||
          (r == null ? void 0 : r.getAttribute("nonce"));
      i = Promise.allSettled(
        n.map((a) => {
          if (((a = Fl(a)), a in ti)) return;
          ti[a] = !0;
          const f = a.endsWith(".css"),
            p = f ? '[rel="stylesheet"]' : "";
          if (document.querySelector(`link[href="${a}"]${p}`)) return;
          const g = document.createElement("link");
          if (
            ((g.rel = f ? "stylesheet" : Rl),
            f || (g.as = "script"),
            (g.crossOrigin = ""),
            (g.href = a),
            l && g.setAttribute("nonce", l),
            document.head.appendChild(g),
            f)
          )
            return new Promise((E, T) => {
              (g.addEventListener("load", E),
                g.addEventListener("error", () =>
                  T(new Error(`Unable to preload CSS for ${a}`)),
                ));
            });
        }),
      );
    }
    function o(r) {
      const l = new Event("vite:preloadError", { cancelable: !0 });
      if (((l.payload = r), window.dispatchEvent(l), !l.defaultPrevented))
        throw r;
    }
    return i.then((r) => {
      for (const l of r || []) l.status === "rejected" && o(l.reason);
      return t().catch(o);
    });
  },
  Nl = { class: "tabs", "aria-label": "Navigazione principale" },
  Ll = {
    __name: "HeaderTabs",
    props: { active: { type: String, default: "rides" } },
    setup(e) {
      return (t, n) => (
        M(),
        I("nav", Nl, [
          d(
            "button",
            {
              class: me(["tab", { active: e.active === "rides" }]),
              onClick:
                n[0] || (n[0] = (s) => t.$emit("update:active", "rides")),
            },
            "🏍️ Rides",
            2,
          ),
          d(
            "button",
            {
              class: me(["tab", { active: e.active === "import" }]),
              onClick:
                n[1] || (n[1] = (s) => t.$emit("update:active", "import")),
            },
            "📥 Import",
            2,
          ),
          d(
            "button",
            {
              class: me(["tab", { active: e.active === "athlete" }]),
              onClick:
                n[2] || (n[2] = (s) => t.$emit("update:active", "athlete")),
            },
            "🏃 Atleta",
            2,
          ),
          d(
            "button",
            {
              class: me(["tab", { active: e.active === "coach" }]),
              onClick:
                n[3] || (n[3] = (s) => t.$emit("update:active", "coach")),
            },
            "🧠 AI Coach",
            2,
          ),
          d(
            "button",
            {
              class: me(["tab", { active: e.active === "knowledge" }]),
              onClick:
                n[4] || (n[4] = (s) => t.$emit("update:active", "knowledge")),
            },
            "📚 Knowledge",
            2,
          ),
          d(
            "button",
            {
              class: me(["tab", { active: e.active === "calendar" }]),
              onClick:
                n[5] || (n[5] = (s) => t.$emit("update:active", "calendar")),
            },
            "📅 Calendario",
            2,
          ),
          d(
            "button",
            {
              class: me(["tab", { active: e.active === "admin" }]),
              onClick:
                n[6] || (n[6] = (s) => t.$emit("update:active", "admin")),
            },
            "⚙️ Admin",
            2,
          ),
        ])
      );
    },
  },
  jl = { class: "stats", "aria-label": "Statistiche generali" },
  Vl = { class: "stat-card", role: "status" },
  Ul = { class: "stat-value" },
  Hl = { class: "stat-card", role: "status" },
  Kl = { class: "stat-value" },
  Bl = { class: "stat-card", role: "status" },
  Wl = { class: "stat-value" },
  Gl = { class: "stat-card", role: "status" },
  ql = { class: "stat-value" },
  zl = { class: "stat-card", role: "status" },
  Jl = { class: "stat-value" },
  Yl = {
    __name: "StatsSummary",
    props: { stats: { type: Object, default: null } },
    setup(e) {
      const t = e;
      function n(i, o = 1) {
        return i == null || isNaN(i) ? "0" : Number(i).toFixed(o);
      }
      const s = it(() => {
        var o;
        const i = (o = t.stats) == null ? void 0 : o.duration_minutes;
        return i == null || isNaN(i) ? "0" : (Number(i) / 60).toFixed(1);
      });
      return (i, o) => {
        var r, l, a, f;
        return (
          M(),
          I("div", jl, [
            d("div", Vl, [
              d(
                "div",
                Ul,
                L(n((r = e.stats) == null ? void 0 : r.rides, 0)),
                1,
              ),
              o[0] || (o[0] = d("div", { class: "stat-label" }, "Rides", -1)),
            ]),
            d("div", Hl, [
              d(
                "div",
                Kl,
                L(n((l = e.stats) == null ? void 0 : l.distance_km, 1)),
                1,
              ),
              o[1] ||
                (o[1] = d("div", { class: "stat-label" }, "Km Totali", -1)),
            ]),
            d("div", Bl, [
              d(
                "div",
                Wl,
                L(n((a = e.stats) == null ? void 0 : a.calories, 0)),
                1,
              ),
              o[2] || (o[2] = d("div", { class: "stat-label" }, "Calorie", -1)),
            ]),
            d("div", Gl, [
              d(
                "div",
                ql,
                L(n((f = e.stats) == null ? void 0 : f.avg_speed_kmh, 1)),
                1,
              ),
              o[3] ||
                (o[3] = d("div", { class: "stat-label" }, "Vel Media", -1)),
            ]),
            d("div", zl, [
              d("div", Jl, L(s.value), 1),
              o[4] ||
                (o[4] = d("div", { class: "stat-label" }, "Ore Totali", -1)),
            ]),
          ])
        );
      };
    },
  },
  zt = "";
async function $t(e, t = {}) {
  const n = new URLSearchParams(t).toString(),
    s = n ? `${zt}${e}?${n}` : `${zt}${e}`,
    i = await fetch(s);
  if (!i.ok) throw new Error(`GET ${e}: ${i.status}`);
  return i.json();
}
async function Tt(e, t) {
  const n = await fetch(`${zt}${e}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(t),
  });
  if (!n.ok) throw new Error(`POST ${e}: ${n.status}`);
  return n.json();
}
async function ao(e) {
  const t = await fetch(`${zt}${e}`, { method: "DELETE" });
  if (!t.ok) throw new Error(`DELETE ${e}: ${t.status}`);
  return t.json();
}
async function Xl(e, t) {
  const n = await fetch(`${zt}${e}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(t),
  });
  if (!n.ok) throw new Error(`PUT ${e}: ${n.status}`);
  return n.json();
}
const Zl = { class: "panel" },
  Ql = { key: 0, class: "loading-text" },
  ea = { key: 1, class: "rides-list" },
  ta = { class: "ride-date" },
  na = { class: "ride-stats" },
  sa = ["onClick"],
  ia = {
    __name: "RidesPanel",
    setup(e) {
      const t = Q(!0),
        n = Q([]);
      async function s() {
        t.value = !0;
        try {
          const o = await $t("/api/v1/rides");
          n.value = o.rides || [];
        } finally {
          t.value = !1;
        }
      }
      async function i(o) {
        confirm("Eliminare questa ride?") &&
          (await ao(`/api/v1/rides/${o}`),
          (n.value = n.value.filter((r) => r.id !== o)));
      }
      return (
        En(() => {
          s();
        }),
        (o, r) => (
          M(),
          I("section", null, [
            d("div", Zl, [
              r[0] || (r[0] = d("h2", null, "📋 Le tue Ride", -1)),
              t.value
                ? (M(), I("p", Ql, "Caricamento..."))
                : (M(),
                  I("div", ea, [
                    (M(!0),
                    I(
                      ue,
                      null,
                      st(
                        n.value,
                        (l) => (
                          M(),
                          I("div", { class: "ride-item", key: l.id }, [
                            d("div", null, [
                              d("div", ta, L(l.date), 1),
                              d(
                                "div",
                                na,
                                L(l.distance_km) +
                                  "km • " +
                                  L(l.duration_minutes) +
                                  "min • " +
                                  L(l.avg_speed_kmh) +
                                  " km/h",
                                1,
                              ),
                            ]),
                            d(
                              "button",
                              {
                                class: "btn btn-danger btn-sm",
                                onClick: (a) => i(l.id),
                              },
                              "Elimina",
                              8,
                              sa,
                            ),
                          ])
                        ),
                      ),
                      128,
                    )),
                  ])),
            ]),
          ])
        )
      );
    },
  },
  oa = { class: "panel" },
  ra = { class: "form-group" },
  la = { class: "upload-placeholder" },
  aa = { key: 0, id: "import-progress", class: "result-box" },
  ca = {
    __name: "ImportPanel",
    emits: ["summary-change"],
    setup(e, { emit: t }) {
      const n = Q(null),
        s = Q([]),
        i = Q(""),
        o = it(() =>
          s.value.length
            ? `${s.value.length} file selezionati`
            : "Trascina file qui o clicca per selezionare (GPX/FIT)",
        );
      function r() {
        var f;
        (f = n.value) == null || f.click();
      }
      function l(f) {
        s.value = Array.from(f.target.files || []);
      }
      function a(f) {
        s.value = Array.from(f.dataTransfer.files || []);
      }
      return (
        En(() => {}),
        (f, p) => (
          M(),
          I("section", null, [
            d("div", oa, [
              p[2] || (p[2] = d("h2", null, "📥 Importa Percorsi", -1)),
              d("div", ra, [
                p[1] ||
                  (p[1] = d(
                    "label",
                    { for: "import-file" },
                    "Carica file GPX o FIT",
                    -1,
                  )),
                d(
                  "div",
                  {
                    class: "upload-area",
                    onClick: r,
                    onDragover: p[0] || (p[0] = Qn(() => {}, ["prevent"])),
                    onDrop: Qn(a, ["prevent"]),
                  },
                  [
                    d(
                      "input",
                      {
                        ref_key: "fileInput",
                        ref: n,
                        type: "file",
                        accept: ".gpx,.fit",
                        multiple: "",
                        onChange: l,
                      },
                      null,
                      544,
                    ),
                    d("div", la, L(o.value), 1),
                  ],
                  32,
                ),
              ]),
              i.value ? (M(), I("div", aa, L(i.value), 1)) : re("", !0),
            ]),
          ])
        )
      );
    },
  },
  ua = { class: "panel" },
  fa = { id: "athlete-form", class: "form-grid", novalidate: "" },
  da = { class: "form-group" },
  pa = { class: "form-group" },
  ha = { class: "form-group" },
  ga = { class: "form-group" },
  va = { class: "form-group" },
  ma = { class: "form-group" },
  _a = { class: "form-group" },
  ba = { class: "form-group" },
  ya = { class: "form-group" },
  xa = { class: "form-group" },
  Sa = { key: 0, class: "result-box" },
  wa = {
    __name: "AthletePanel",
    emits: ["toast"],
    setup(e, { emit: t }) {
      const n = Q({
          name: "",
          age: 30,
          weight_kg: 70,
          height_cm: 175,
          fat_percentage: 15,
          years_active: 1,
          weekly_sessions: 3,
          monthly_hours: 0,
          annual_hours: 0,
          experience_level: "Beginner",
        }),
        s = Q(""),
        i = Q(null);
      async function o() {
        try {
          const l = await Tt("/api/v1/athletes", n.value);
          ((i.value = l.id),
            (s.value = "Profilo atleta salvato (ID: " + l.id + ")"));
        } catch (l) {
          s.value = "Errore: " + (l.message || l);
        }
      }
      async function r() {
        try {
          const l = i.value;
          if (!l) {
            s.value = "Salva prima il profilo atleta";
            return;
          }
          const a = await $t("/api/v1/scores/athlete/" + l);
          s.value = JSON.stringify(a, null, 2);
        } catch (l) {
          s.value = "Errore: " + (l.message || l);
        }
      }
      return (l, a) => (
        M(),
        I("div", ua, [
          a[21] || (a[21] = d("h2", null, "🏃 Profilo Atleta", -1)),
          d("form", fa, [
            d("div", da, [
              a[10] ||
                (a[10] = d("label", { for: "athlete-name" }, "Nome", -1)),
              le(
                d(
                  "input",
                  {
                    type: "text",
                    "onUpdate:modelValue":
                      a[0] || (a[0] = (f) => (n.value.name = f)),
                    required: "",
                  },
                  null,
                  512,
                ),
                [[ve, n.value.name]],
              ),
            ]),
            d("div", pa, [
              a[11] || (a[11] = d("label", { for: "athlete-age" }, "Età", -1)),
              le(
                d(
                  "input",
                  {
                    type: "number",
                    "onUpdate:modelValue":
                      a[1] || (a[1] = (f) => (n.value.age = f)),
                    min: "10",
                    max: "100",
                  },
                  null,
                  512,
                ),
                [[ve, n.value.age, void 0, { number: !0 }]],
              ),
            ]),
            d("div", ha, [
              a[12] ||
                (a[12] = d(
                  "label",
                  { for: "athlete-weight" },
                  "Peso (kg)",
                  -1,
                )),
              le(
                d(
                  "input",
                  {
                    type: "number",
                    "onUpdate:modelValue":
                      a[2] || (a[2] = (f) => (n.value.weight_kg = f)),
                    min: "20",
                    max: "300",
                    step: "0.1",
                  },
                  null,
                  512,
                ),
                [[ve, n.value.weight_kg, void 0, { number: !0 }]],
              ),
            ]),
            d("div", ga, [
              a[13] ||
                (a[13] = d(
                  "label",
                  { for: "athlete-height" },
                  "Altezza (cm)",
                  -1,
                )),
              le(
                d(
                  "input",
                  {
                    type: "number",
                    "onUpdate:modelValue":
                      a[3] || (a[3] = (f) => (n.value.height_cm = f)),
                    min: "100",
                    max: "250",
                  },
                  null,
                  512,
                ),
                [[ve, n.value.height_cm, void 0, { number: !0 }]],
              ),
            ]),
            d("div", va, [
              a[14] ||
                (a[14] = d(
                  "label",
                  { for: "athlete-fat" },
                  "Massa Grassa (%)",
                  -1,
                )),
              le(
                d(
                  "input",
                  {
                    type: "number",
                    "onUpdate:modelValue":
                      a[4] || (a[4] = (f) => (n.value.fat_percentage = f)),
                    min: "3",
                    max: "60",
                    step: "0.1",
                  },
                  null,
                  512,
                ),
                [[ve, n.value.fat_percentage, void 0, { number: !0 }]],
              ),
            ]),
            d("div", ma, [
              a[15] ||
                (a[15] = d(
                  "label",
                  { for: "athlete-years" },
                  "Anni attività",
                  -1,
                )),
              le(
                d(
                  "input",
                  {
                    type: "number",
                    "onUpdate:modelValue":
                      a[5] || (a[5] = (f) => (n.value.years_active = f)),
                    min: "0",
                    max: "80",
                  },
                  null,
                  512,
                ),
                [[ve, n.value.years_active, void 0, { number: !0 }]],
              ),
            ]),
            d("div", _a, [
              a[16] ||
                (a[16] = d(
                  "label",
                  { for: "athlete-weekly" },
                  "Sessioni/settimana",
                  -1,
                )),
              le(
                d(
                  "input",
                  {
                    type: "number",
                    "onUpdate:modelValue":
                      a[6] || (a[6] = (f) => (n.value.weekly_sessions = f)),
                    min: "0",
                    max: "14",
                  },
                  null,
                  512,
                ),
                [[ve, n.value.weekly_sessions, void 0, { number: !0 }]],
              ),
            ]),
            d("div", ba, [
              a[17] ||
                (a[17] = d(
                  "label",
                  { for: "athlete-monthly" },
                  "Ore/mese",
                  -1,
                )),
              le(
                d(
                  "input",
                  {
                    type: "number",
                    "onUpdate:modelValue":
                      a[7] || (a[7] = (f) => (n.value.monthly_hours = f)),
                    min: "0",
                    step: "0.5",
                  },
                  null,
                  512,
                ),
                [[ve, n.value.monthly_hours, void 0, { number: !0 }]],
              ),
            ]),
            d("div", ya, [
              a[18] ||
                (a[18] = d("label", { for: "athlete-annual" }, "Ore/anno", -1)),
              le(
                d(
                  "input",
                  {
                    type: "number",
                    "onUpdate:modelValue":
                      a[8] || (a[8] = (f) => (n.value.annual_hours = f)),
                    min: "0",
                    step: "0.5",
                  },
                  null,
                  512,
                ),
                [[ve, n.value.annual_hours, void 0, { number: !0 }]],
              ),
            ]),
            d("div", xa, [
              a[20] ||
                (a[20] = d("label", { for: "athlete-level" }, "Livello", -1)),
              le(
                d(
                  "select",
                  {
                    "onUpdate:modelValue":
                      a[9] || (a[9] = (f) => (n.value.experience_level = f)),
                  },
                  [
                    ...(a[19] ||
                      (a[19] = [
                        d("option", null, "Beginner", -1),
                        d("option", null, "Amateur", -1),
                        d("option", null, "Intermediate", -1),
                        d("option", null, "Advanced", -1),
                        d("option", null, "Elite", -1),
                      ])),
                  ],
                  512,
                ),
                [[Zn, n.value.experience_level]],
              ),
            ]),
          ]),
          d("div", { class: "form-actions" }, [
            d(
              "button",
              { class: "btn btn-primary", onClick: o },
              "Salva Atleta",
            ),
            d(
              "button",
              { class: "btn btn-secondary", onClick: r },
              "📊 Punteggi",
            ),
          ]),
          s.value ? (M(), I("div", Sa, L(s.value), 1)) : re("", !0),
        ])
      );
    },
  },
  $a = { class: "panel" },
  Ca = { class: "form-grid" },
  Ea = { class: "form-group" },
  Ta = { key: 0, class: "loading-text" },
  Aa = { key: 1, class: "stats", style: { "margin-top": "15px" } },
  Oa = { class: "stat-card" },
  Pa = { class: "stat-value" },
  Ma = { class: "stat-card" },
  Ia = { class: "stat-value" },
  Da = { class: "stat-card" },
  Ra = { class: "stat-value" },
  Fa = { class: "stat-card" },
  ka = { class: "stat-value" },
  Na = { key: 2, class: "panel", style: { "margin-top": "15px" } },
  La = { class: "result-box" },
  ja = { class: "result-box" },
  Va = { class: "result-box" },
  Ua = {
    __name: "CoachPanel",
    setup(e) {
      const t = Q(0),
        n = Q(!1),
        s = Q(null);
      async function i() {
        n.value = !0;
        try {
          s.value = await $t("/api/v1/coach/full", {
            athlete_id: t.value || 0,
          });
        } catch (o) {
          console.error("coach", o);
        } finally {
          n.value = !1;
        }
      }
      return (o, r) => {
        var l, a, f, p;
        return (
          M(),
          I("div", $a, [
            r[9] || (r[9] = d("h2", null, "🧠 AI Coach", -1)),
            d("div", Ca, [
              d("div", Ea, [
                r[1] ||
                  (r[1] = d(
                    "label",
                    { for: "coach-athlete-id" },
                    "ID Atleta (0 = ultimo)",
                    -1,
                  )),
                le(
                  d(
                    "input",
                    {
                      type: "number",
                      "onUpdate:modelValue":
                        r[0] || (r[0] = (g) => (t.value = g)),
                      min: "0",
                    },
                    null,
                    512,
                  ),
                  [[ve, t.value, void 0, { number: !0 }]],
                ),
              ]),
              d("div", { class: "form-group" }, [
                d(
                  "button",
                  { class: "btn btn-primary", onClick: i },
                  "📊 Carica Coach Completo",
                ),
              ]),
            ]),
            n.value ? (M(), I("div", Ta, "Analisi in corso...")) : re("", !0),
            s.value
              ? (M(),
                I("div", Aa, [
                  d("div", Oa, [
                    d(
                      "div",
                      Pa,
                      L(
                        ((l = s.value.scores) == null
                          ? void 0
                          : l.performance) ?? 0,
                      ),
                      1,
                    ),
                    r[2] ||
                      (r[2] = d(
                        "div",
                        { class: "stat-label" },
                        "Performance",
                        -1,
                      )),
                  ]),
                  d("div", Ma, [
                    d(
                      "div",
                      Ia,
                      L(
                        ((a = s.value.scores) == null ? void 0 : a.endurance) ??
                          0,
                      ),
                      1,
                    ),
                    r[3] ||
                      (r[3] = d(
                        "div",
                        { class: "stat-label" },
                        "Endurance",
                        -1,
                      )),
                  ]),
                  d("div", Da, [
                    d(
                      "div",
                      Ra,
                      L(
                        ((f = s.value.scores) == null ? void 0 : f.fatigue) ??
                          0,
                      ),
                      1,
                    ),
                    r[4] ||
                      (r[4] = d("div", { class: "stat-label" }, "Fatigue", -1)),
                  ]),
                  d("div", Fa, [
                    d(
                      "div",
                      ka,
                      L(
                        ((p = s.value.scores) == null ? void 0 : p.recovery) ??
                          0,
                      ),
                      1,
                    ),
                    r[5] ||
                      (r[5] = d(
                        "div",
                        { class: "stat-label" },
                        "Recovery",
                        -1,
                      )),
                  ]),
                ]))
              : re("", !0),
            s.value
              ? (M(),
                I("div", Na, [
                  r[6] ||
                    (r[6] = d("h3", null, "💡 Consigli di Allenamento", -1)),
                  d("div", La, L(s.value.training_advice), 1),
                  r[7] || (r[7] = d("h3", null, "📈 Analisi Storica", -1)),
                  d("div", ja, L(s.value.historical), 1),
                  r[8] || (r[8] = d("h3", null, "🧘 Consigli di Recupero", -1)),
                  d("div", Va, L(s.value.recovery_advice), 1),
                ]))
              : re("", !0),
          ])
        );
      };
    },
  },
  Ha = { class: "panel" },
  Ka = { class: "form-grid" },
  Ba = { class: "form-group" },
  Wa = { key: 0, class: "result-box" },
  Ga = {
    __name: "KnowledgePanel",
    setup(e) {
      const t = Q(""),
        n = Q("");
      async function s() {
        try {
          const o = await Tt("/api/v1/knowledge/query", { query: t.value });
          n.value = JSON.stringify(o, null, 2);
        } catch (o) {
          n.value = "Errore: " + (o.message || o);
        }
      }
      async function i() {
        try {
          const o = await apiGet("/api/v1/knowledge");
          n.value = JSON.stringify(o, null, 2);
        } catch (o) {
          n.value = "Errore: " + (o.message || o);
        }
      }
      return (o, r) => (
        M(),
        I("div", Ha, [
          r[2] || (r[2] = d("h2", null, "📚 Knowledge Base", -1)),
          d("div", Ka, [
            d("div", Ba, [
              r[1] ||
                (r[1] = d("label", { for: "kb-query" }, "Cerca argomento", -1)),
              le(
                d(
                  "input",
                  {
                    type: "text",
                    "onUpdate:modelValue":
                      r[0] || (r[0] = (l) => (t.value = l)),
                  },
                  null,
                  512,
                ),
                [[ve, t.value]],
              ),
            ]),
            d("button", { class: "btn btn-primary", onClick: s }, "Cerca"),
            d(
              "button",
              { class: "btn btn-secondary", onClick: i },
              "Lista Argomenti",
            ),
          ]),
          n.value ? (M(), I("div", Wa, L(n.value), 1)) : re("", !0),
        ])
      );
    },
  },
  qa = { class: "panel" },
  za = { class: "calendar-controls" },
  Ja = { class: "calendar-nav" },
  Ya = { class: "month-label" },
  Xa = { class: "athlete-select" },
  Za = ["value"],
  Qa = { class: "calendar-grid" },
  ec = ["onClick"],
  tc = { class: "day-num" },
  nc = { class: "day-events" },
  sc = { key: 0, class: "more-events" },
  ic = { key: 0, class: "day-detail" },
  oc = { class: "event-count" },
  rc = { class: "event-list" },
  lc = { class: "event-check" },
  ac = ["checked", "onChange"],
  cc = { class: "event-info" },
  uc = { class: "event-title" },
  fc = { class: "event-meta" },
  dc = { key: 0 },
  pc = { key: 0, class: "event-desc" },
  hc = { class: "event-actions" },
  gc = ["onClick"],
  vc = ["onClick"],
  mc = { class: "panel" },
  _c = { class: "objectives-box" },
  bc = ["onClick"],
  yc = { class: "obj-icon" },
  xc = { class: "obj-text" },
  Sc = { key: 0, class: "athlete-goals-display" },
  wc = { key: 0, class: "panel form-overlay" },
  $c = { class: "form-group" },
  Cc = { class: "form-group" },
  Ec = { class: "form-group" },
  Tc = { class: "form-group" },
  Ac = { class: "form-group full-width" },
  Oc = { class: "form-actions" },
  Pc = {
    __name: "CalendarPanel",
    setup(e) {
      const t = Q(1),
        n = Q([]),
        s = Q(new Date().getFullYear()),
        i = Q(new Date().getMonth()),
        o = Q([]),
        r = Q(!1),
        l = Q(null),
        a = Q({
          title: "",
          event_type: "training",
          date: "",
          duration_minutes: 0,
          description: "",
          completed: !1,
        }),
        f = Q(""),
        p = ["Lun", "Mar", "Mer", "Gio", "Ven", "Sab", "Dom"],
        g = it(
          () =>
            `${["Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno", "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"][i.value]} ${s.value}`,
        ),
        E = it(() => {
          let $ = new Date(s.value, i.value, 1).getDay() - 1;
          $ < 0 && ($ = 6);
          const S = new Date(s.value, i.value + 1, 0).getDate(),
            V = new Date(s.value, i.value, 0).getDate(),
            j = [],
            he = new Date(),
            tt = `${he.getFullYear()}-${(he.getMonth() + 1).toString().padStart(2, "0")}-${he.getDate().toString().padStart(2, "0")}`;
          for (let ee = 0; ee < $; ee++) {
            const Ae = V - $ + 1 + ee,
              lt = i.value === 0 ? 12 : i.value,
              At = i.value === 0 ? s.value - 1 : s.value;
            j.push({
              day: Ae,
              date: `${At}-${lt.toString().padStart(2, "0")}-${Ae.toString().padStart(2, "0")}`,
              currentMonth: !1,
              events: [],
            });
          }
          for (let ee = 1; ee <= S; ee++) {
            const Ae = `${s.value}-${(i.value + 1).toString().padStart(2, "0")}-${ee.toString().padStart(2, "0")}`,
              lt = o.value.filter((At) => At.date === Ae);
            j.push({
              day: ee,
              date: Ae,
              currentMonth: !0,
              events: lt,
              isToday: Ae === tt,
            });
          }
          const We = 42 - j.length;
          for (let ee = 1; ee <= We; ee++) {
            const Ae = i.value === 11 ? 1 : i.value + 2,
              lt = i.value === 11 ? s.value + 1 : s.value;
            j.push({
              day: ee,
              date: `${lt}-${Ae.toString().padStart(2, "0")}-${ee.toString().padStart(2, "0")}`,
              currentMonth: !1,
              events: [],
            });
          }
          return j;
        }),
        T = it(() => {
          const A = new Date(),
            $ = A.getFullYear(),
            S = A.getMonth(),
            V = A.getDate();
          return i.value === S && s.value === $
            ? A.toLocaleDateString("it-IT")
            : `${V}/${S + 1}/${$}`;
        }),
        K = it(() => {
          const A = new Date(),
            $ = A.getFullYear(),
            S = A.getMonth(),
            V = A.getDate();
          if (i.value === S && s.value === $) {
            const j = `${$}-${(S + 1).toString().padStart(2, "0")}-${V.toString().padStart(2, "0")}`;
            return o.value
              .filter((he) => he.date === j)
              .sort((he, tt) => he.id - tt.id);
          }
          return [];
        }),
        k = it(() => [
          {
            label: "Allenamento Intervalli",
            icon: "⚡",
            hint: "Sessione HIIT",
            event_type: "training",
            duration: 45,
            title: "Allenamento Intervalli",
          },
          {
            label: "Uscita Lunga",
            icon: "🏔️",
            hint: "Fondo lento",
            event_type: "training",
            duration: 120,
            title: "Uscita Lunga",
          },
          {
            label: "Recupero Attivo",
            icon: "🧘",
            hint: "Allungamento",
            event_type: "recovery",
            duration: 30,
            title: "Recupero Attivo",
          },
          {
            label: "Test FTP",
            icon: "🔬",
            hint: "Misura potenza",
            event_type: "test",
            duration: 60,
            title: "Test FTP",
          },
          {
            label: "Gara",
            icon: "🏁",
            hint: "Competizione",
            event_type: "race",
            duration: 180,
            title: "Gara",
          },
          {
            label: "Scadenza Obiettivo",
            icon: "🎯",
            hint: "Deadline",
            event_type: "goal_deadline",
            duration: 0,
            title: "Scadenza Obiettivo",
          },
        ]);
      function te(A) {
        if (!A.isToday) return !1;
        const $ = new Date();
        return (
          A.date ===
          `${$.getFullYear()}-${($.getMonth() + 1).toString().padStart(2, "0")}-${$.getDate().toString().padStart(2, "0")}`
        );
      }
      function X() {
        (i.value === 0 ? ((i.value = 11), s.value--) : i.value--, ye());
      }
      function U() {
        (i.value === 11 ? ((i.value = 0), s.value++) : i.value++, ye());
      }
      function z() {
        const A = new Date();
        ((s.value = A.getFullYear()), (i.value = A.getMonth()), ye());
      }
      function D(A) {
        return (
          {
            training: "Allenamento",
            race: "Gara",
            recovery: "Recupero",
            goal_deadline: "Obiettivo",
            test: "Test",
            other: "Altro",
          }[A] || A
        );
      }
      function se(A) {
        ((l.value = null),
          (a.value = {
            title: "",
            event_type: "training",
            date: A,
            duration_minutes: 0,
            description: "",
            completed: !1,
          }),
          (r.value = !0));
      }
      function De(A) {
        ((l.value = A), (a.value = { ...A }), (r.value = !0));
      }
      function $e(A) {
        const $ = new Date(),
          S = `${$.getFullYear()}-${($.getMonth() + 1).toString().padStart(2, "0")}-${$.getDate().toString().padStart(2, "0")}`;
        ((l.value = null),
          (a.value = {
            title: A.title,
            event_type: A.event_type,
            date: S,
            duration_minutes: A.duration,
            description: A.hint,
            completed: !1,
          }),
          (r.value = !0));
      }
      async function Re() {
        try {
          const A = await $t("/api/v1/athletes");
          ((n.value = A.athletes || []),
            n.value.length > 0 && t.value <= 0 && (t.value = n.value[0].id));
        } catch {
          n.value = [];
        }
      }
      async function ye() {
        if (t.value <= 0) {
          o.value = [];
          return;
        }
        try {
          const A = await $t("/api/v1/calendar/events", {
            athlete_id: t.value,
            year: s.value,
            month: i.value + 1,
          });
          o.value = A.events || [];
        } catch {
          o.value = [];
        }
      }
      async function Te() {
        if (t.value <= 0) {
          f.value = "";
          return;
        }
        try {
          const A = await $t("/api/v1/athletes/" + t.value);
          f.value = A.goals || "";
        } catch {
          f.value = "";
        }
      }
      async function rt() {
        try {
          const A = { ...a.value, athlete_id: t.value };
          (l.value
            ? await Xl(`/api/v1/calendar/events/${l.value.id}`, A)
            : await Tt("/api/v1/calendar/events", A),
            (r.value = !1),
            (l.value = null),
            ye(),
            Te());
        } catch (A) {
          alert("Errore: " + (A.message || A));
        }
      }
      async function gt(A) {
        if (confirm("Eliminare questo evento?"))
          try {
            (await ao(`/api/v1/calendar/events/${A}`), ye());
          } catch ($) {
            alert("Errore: " + ($.message || $));
          }
      }
      async function vt(A) {
        try {
          (await Tt(`/api/v1/calendar/events/${A.id}/complete`, {}), ye());
        } catch ($) {
          alert("Errore: " + ($.message || $));
        }
      }
      return (
        En(() => {
          (Re(), ye(), Te());
        }),
        rn(t, () => {
          (ye(), Te());
        }),
        (A, $) => (
          M(),
          I("section", null, [
            d("div", qa, [
              $[9] || ($[9] = d("h2", null, "📅 Calendario & Obiettivi", -1)),
              d("div", za, [
                d("div", Ja, [
                  d(
                    "button",
                    { class: "btn btn-secondary btn-sm", onClick: X },
                    "◀",
                  ),
                  d("span", Ya, L(g.value), 1),
                  d(
                    "button",
                    { class: "btn btn-secondary btn-sm", onClick: U },
                    "▶",
                  ),
                  d(
                    "button",
                    { class: "btn btn-secondary btn-sm", onClick: z },
                    "Oggi",
                  ),
                ]),
                d("div", Xa, [
                  $[8] || ($[8] = d("label", null, "Atleta:", -1)),
                  le(
                    d(
                      "select",
                      {
                        "onUpdate:modelValue":
                          $[0] || ($[0] = (S) => (t.value = S)),
                        onChange: ye,
                      },
                      [
                        $[7] ||
                          ($[7] = d("option", { value: 0 }, "Generale", -1)),
                        (M(!0),
                        I(
                          ue,
                          null,
                          st(
                            n.value,
                            (S) => (
                              M(),
                              I(
                                "option",
                                { key: S.id, value: S.id },
                                L(S.name),
                                9,
                                Za,
                              )
                            ),
                          ),
                          128,
                        )),
                      ],
                      544,
                    ),
                    [[Zn, t.value, void 0, { number: !0 }]],
                  ),
                ]),
              ]),
              $[10] ||
                ($[10] = Ns(
                  '<div class="calendar-legend"><span class="legend-item legend-training">Allenamento</span><span class="legend-item legend-race">Gara</span><span class="legend-item legend-recovery">Recupero</span><span class="legend-item legend-goal">Obiettivo</span><span class="legend-item legend-test">Test</span><span class="legend-item legend-other">Altro</span></div>',
                  1,
                )),
              d("div", Qa, [
                (M(),
                I(
                  ue,
                  null,
                  st(p, (S) =>
                    d("div", { class: "cal-header", key: S }, L(S), 1),
                  ),
                  64,
                )),
                (M(!0),
                I(
                  ue,
                  null,
                  st(
                    E.value,
                    (S, V) => (
                      M(),
                      I(
                        "div",
                        {
                          key: V,
                          class: me([
                            "cal-cell",
                            {
                              "other-month": !S.currentMonth,
                              today: te(S),
                              "has-events": S.events.length > 0,
                            },
                          ]),
                          onClick: (j) => se(S.date),
                        },
                        [
                          d("span", tc, L(S.day), 1),
                          d("div", nc, [
                            (M(!0),
                            I(
                              ue,
                              null,
                              st(
                                S.events.slice(0, 3),
                                (j) => (
                                  M(),
                                  I(
                                    "span",
                                    {
                                      key: j.id,
                                      class: me([
                                        "event-dot",
                                        "dot-" + j.event_type,
                                      ]),
                                    },
                                    L(j.title),
                                    3,
                                  )
                                ),
                              ),
                              128,
                            )),
                            S.events.length > 3
                              ? (M(),
                                I("span", sc, "+" + L(S.events.length - 3), 1))
                              : re("", !0),
                          ]),
                        ],
                        10,
                        ec,
                      )
                    ),
                  ),
                  128,
                )),
              ]),
              K.value.length
                ? (M(),
                  I("div", ic, [
                    d("h3", null, [
                      io("Eventi del " + L(T.value) + " ", 1),
                      d("span", oc, "(" + L(K.value.length) + ")", 1),
                    ]),
                    d("ul", rc, [
                      (M(!0),
                      I(
                        ue,
                        null,
                        st(
                          K.value,
                          (S) => (
                            M(),
                            I(
                              "li",
                              {
                                key: S.id,
                                class: me([
                                  "event-item",
                                  { completed: S.completed },
                                ]),
                              },
                              [
                                d("span", lc, [
                                  d(
                                    "input",
                                    {
                                      type: "checkbox",
                                      checked: S.completed,
                                      onChange: (V) => vt(S),
                                    },
                                    null,
                                    40,
                                    ac,
                                  ),
                                ]),
                                d("span", cc, [
                                  d("strong", uc, L(S.title), 1),
                                  d("span", fc, [
                                    d(
                                      "span",
                                      {
                                        class: me([
                                          "badge",
                                          "badge-" + S.event_type,
                                        ]),
                                      },
                                      L(D(S.event_type)),
                                      3,
                                    ),
                                    S.duration_minutes
                                      ? (M(),
                                        I(
                                          "span",
                                          dc,
                                          L(S.duration_minutes) + " min",
                                          1,
                                        ))
                                      : re("", !0),
                                  ]),
                                  S.description
                                    ? (M(), I("span", pc, L(S.description), 1))
                                    : re("", !0),
                                ]),
                                d("span", hc, [
                                  d(
                                    "button",
                                    {
                                      class: "btn btn-secondary btn-xs",
                                      onClick: (V) => De(S),
                                    },
                                    "Modifica",
                                    8,
                                    gc,
                                  ),
                                  d(
                                    "button",
                                    {
                                      class: "btn btn-danger btn-xs",
                                      onClick: (V) => gt(S.id),
                                    },
                                    "Elimina",
                                    8,
                                    vc,
                                  ),
                                ]),
                              ],
                              2,
                            )
                          ),
                        ),
                        128,
                      )),
                    ]),
                  ]))
                : re("", !0),
            ]),
            d("div", mc, [
              $[13] || ($[13] = d("h2", null, "🎯 Collegamento Obiettivi", -1)),
              d("div", _c, [
                (M(!0),
                I(
                  ue,
                  null,
                  st(
                    k.value,
                    (S) => (
                      M(),
                      I(
                        "div",
                        {
                          class: "obj-card",
                          key: S.label,
                          onClick: (V) => $e(S),
                        },
                        [
                          d("div", yc, L(S.icon), 1),
                          d("div", xc, [
                            d("strong", null, L(S.label), 1),
                            d("small", null, L(S.hint), 1),
                          ]),
                          $[11] ||
                            ($[11] = d(
                              "div",
                              { class: "obj-action" },
                              "+ Aggiungi",
                              -1,
                            )),
                        ],
                        8,
                        bc,
                      )
                    ),
                  ),
                  128,
                )),
              ]),
              f.value
                ? (M(),
                  I("div", Sc, [
                    $[12] ||
                      ($[12] = d(
                        "small",
                        null,
                        "Obiettivi atleta registrati:",
                        -1,
                      )),
                    d("p", null, L(f.value), 1),
                  ]))
                : re("", !0),
            ]),
            r.value
              ? (M(),
                I("div", wc, [
                  d(
                    "h3",
                    null,
                    L(l.value ? "Modifica Evento" : "Nuovo Evento"),
                    1,
                  ),
                  d(
                    "form",
                    { onSubmit: Qn(rt, ["prevent"]), class: "form-grid" },
                    [
                      d("div", $c, [
                        $[14] || ($[14] = d("label", null, "Titolo *", -1)),
                        le(
                          d(
                            "input",
                            {
                              "onUpdate:modelValue":
                                $[1] || ($[1] = (S) => (a.value.title = S)),
                              required: "",
                              maxlength: "200",
                            },
                            null,
                            512,
                          ),
                          [[ve, a.value.title]],
                        ),
                      ]),
                      d("div", Cc, [
                        $[16] || ($[16] = d("label", null, "Tipo", -1)),
                        le(
                          d(
                            "select",
                            {
                              "onUpdate:modelValue":
                                $[2] ||
                                ($[2] = (S) => (a.value.event_type = S)),
                            },
                            [
                              ...($[15] ||
                                ($[15] = [
                                  Ns(
                                    '<option value="training">Allenamento</option><option value="race">Gara</option><option value="recovery">Recupero</option><option value="goal_deadline">Scadenza Obiettivo</option><option value="test">Test</option><option value="other">Altro</option>',
                                    6,
                                  ),
                                ])),
                            ],
                            512,
                          ),
                          [[Zn, a.value.event_type]],
                        ),
                      ]),
                      d("div", Ec, [
                        $[17] || ($[17] = d("label", null, "Data", -1)),
                        le(
                          d(
                            "input",
                            {
                              type: "date",
                              "onUpdate:modelValue":
                                $[3] || ($[3] = (S) => (a.value.date = S)),
                              required: "",
                            },
                            null,
                            512,
                          ),
                          [[ve, a.value.date]],
                        ),
                      ]),
                      d("div", Tc, [
                        $[18] || ($[18] = d("label", null, "Durata (min)", -1)),
                        le(
                          d(
                            "input",
                            {
                              type: "number",
                              "onUpdate:modelValue":
                                $[4] ||
                                ($[4] = (S) => (a.value.duration_minutes = S)),
                              min: "0",
                            },
                            null,
                            512,
                          ),
                          [
                            [
                              ve,
                              a.value.duration_minutes,
                              void 0,
                              { number: !0 },
                            ],
                          ],
                        ),
                      ]),
                      d("div", Ac, [
                        $[19] || ($[19] = d("label", null, "Descrizione", -1)),
                        le(
                          d(
                            "textarea",
                            {
                              "onUpdate:modelValue":
                                $[5] ||
                                ($[5] = (S) => (a.value.description = S)),
                              maxlength: "1000",
                              rows: "3",
                            },
                            null,
                            512,
                          ),
                          [[ve, a.value.description]],
                        ),
                      ]),
                      d("div", Oc, [
                        $[20] ||
                          ($[20] = d(
                            "button",
                            { type: "submit", class: "btn btn-primary" },
                            "Salva",
                            -1,
                          )),
                        d(
                          "button",
                          {
                            type: "button",
                            class: "btn btn-secondary",
                            onClick: $[6] || ($[6] = (S) => (r.value = !1)),
                          },
                          "Annulla",
                        ),
                      ]),
                    ],
                    32,
                  ),
                ]))
              : re("", !0),
          ])
        )
      );
    },
  },
  Mc = { class: "panel" },
  Ic = { key: 0, class: "result-box" },
  Dc = {
    __name: "AdminPanel",
    emits: ["loading"],
    setup(e, { emit: t }) {
      const n = Q("");
      async function s() {
        try {
          const r = await apiGet("/api/v1/admin/stats");
          n.value = JSON.stringify(r, null, 2);
        } catch (r) {
          n.value = "Errore: " + (r.message || r);
        }
      }
      async function i() {
        try {
          (await Tt("/api/v1/admin/backup", {}),
            (n.value = "Backup completato"));
        } catch (r) {
          n.value = "Errore: " + (r.message || r);
        }
      }
      async function o() {
        try {
          (await Tt("/api/v1/admin/indexes", {}), (n.value = "Indici creati"));
        } catch (r) {
          n.value = "Errore: " + (r.message || r);
        }
      }
      return (r, l) => (
        M(),
        I("div", Mc, [
          l[0] || (l[0] = d("h2", null, "⚙️ Amministrazione", -1)),
          d("div", { class: "form-actions" }, [
            d(
              "button",
              { class: "btn btn-primary", onClick: s },
              "📊 Statistiche",
            ),
            d(
              "button",
              { class: "btn btn-secondary", onClick: i },
              "💾 Backup DB",
            ),
            d(
              "button",
              { class: "btn btn-secondary", onClick: o },
              "🗂️ Indici",
            ),
          ]),
          n.value ? (M(), I("div", Ic, L(n.value), 1)) : re("", !0),
        ])
      );
    },
  },
  Rc = {
    id: "toast-container",
    role: "status",
    "aria-live": "polite",
    "aria-atomic": "true",
    class: "toast-root",
  },
  Fc = {
    __name: "ToastContainer",
    setup(e, { expose: t }) {
      const n = Q([]);
      let s = 1;
      function i(r, l = "info", a = 3e3) {
        const f = s++;
        (n.value.push({ id: f, message: r, type: l }),
          setTimeout(() => o(f), a));
      }
      function o(r) {
        n.value = n.value.filter((l) => l.id !== r);
      }
      return (
        t({ add: i }),
        (r, l) => (
          M(),
          I("div", Rc, [
            (M(!0),
            I(
              ue,
              null,
              st(
                n.value,
                (a) => (
                  M(),
                  I(
                    "div",
                    { key: a.id, class: me(["toast", a.type]) },
                    L(a.message),
                    3,
                  )
                ),
              ),
              128,
            )),
          ])
        )
      );
    },
  },
  kc = { class: "app" },
  Nc = { key: 0 },
  Lc = { key: 1 },
  jc = { key: 2 },
  Vc = { key: 3 },
  Uc = { key: 4 },
  Hc = { key: 5 },
  Kc = { key: 6 },
  Bc = {
    __name: "App",
    setup(e) {
      const t = Q("rides"),
        n = Q({
          rides: 0,
          distance_km: 0,
          calories: 0,
          avg_speed_kmh: 0,
          duration_minutes: 0,
        });
      async function s() {
        try {
          const r = await (
            await kl(() => import("./useRides-FJDG_f5k.js"), [])
          )
            .useRides()
            .fetchSummary();
          n.value = {
            rides: r.rides ?? 0,
            distance_km: r.distance_km ?? 0,
            calories: r.calories ?? 0,
            avg_speed_kmh: r.avg_speed_kmh ?? 0,
            duration_minutes: r.duration_minutes ?? 0,
          };
        } catch (i) {
          console.error("summary refresh failed", i);
        }
      }
      return (i, o) => (
        M(),
        I("div", kc, [
          o[1] ||
            (o[1] = d(
              "header",
              { class: "app-header" },
              [
                d("h1", null, "🚴 BikeMaster"),
                d("p", null, "Cycling Performance Intelligence"),
              ],
              -1,
            )),
          oe(
            Ll,
            {
              active: t.value,
              "onUpdate:active": o[0] || (o[0] = (r) => (t.value = r)),
            },
            null,
            8,
            ["active"],
          ),
          oe(Yl, { stats: n.value }, null, 8, ["stats"]),
          d("main", null, [
            t.value === "rides"
              ? (M(), I("section", Nc, [oe(ia, { onSummaryChange: s })]))
              : re("", !0),
            t.value === "import"
              ? (M(), I("section", Lc, [oe(ca, { onSummaryChange: s })]))
              : re("", !0),
            t.value === "athlete"
              ? (M(), I("section", jc, [oe(wa)]))
              : re("", !0),
            t.value === "coach"
              ? (M(), I("section", Vc, [oe(Ua)]))
              : re("", !0),
            t.value === "knowledge"
              ? (M(), I("section", Uc, [oe(Ga)]))
              : re("", !0),
            t.value === "calendar"
              ? (M(), I("section", Hc, [oe(Pc)]))
              : re("", !0),
            t.value === "admin"
              ? (M(), I("section", Kc, [oe(Dc)]))
              : re("", !0),
          ]),
          oe(Fc),
          o[2] ||
            (o[2] = d(
              "footer",
              { class: "footer" },
              "BikeMaster v2 — Vue 3 Dashboard",
              -1,
            )),
        ])
      );
    },
  };
Ml(Bc).mount("#app");
export { ao as a, Tt as b, $t as c };

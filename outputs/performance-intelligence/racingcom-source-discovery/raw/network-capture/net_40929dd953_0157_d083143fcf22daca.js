/*! For license information please see rdc.liveVision.js.LICENSE.txt */
!(function (t, e) {
  'object' == typeof exports && 'object' == typeof module
    ? (module.exports = e(require('React'), require('ReactDOM')))
    : 'function' == typeof define && define.amd
    ? define(['React', 'ReactDOM'], e)
    : 'object' == typeof exports
    ? (exports.rdc = e(require('React'), require('ReactDOM')))
    : ((t.rdc = t.rdc || {}), (t.rdc.liveVision = e(t.React, t.ReactDOM)))
})(self, (t, e) =>
  (self.webpackChunkrdc = self.webpackChunkrdc || []).push([
    [321],
    {
      63743: (t, e, r) => {
        'use strict'
        r.d(e, { Z: () => u })
        var n,
          o,
          i,
          a = r(87778),
          c = (0, r(75506).F4)(
            n ||
              ((o = [
                '\n  0% {\n    color: inherit;\n  }\n  50% {\n    color: transparent;\n  }\n  100% {\n    color: inherit;\n  }\n',
              ]),
              i || (i = o.slice(0)),
              (n = Object.freeze(
                Object.defineProperties(o, { raw: { value: Object.freeze(i) } })
              )))
          )
        const u = (0, a.Z)('div', { target: 'e1bf47j40' })(
          'animation:',
          c,
          " 2s linear infinite;padding-left:6px;&::after{content:'•';}"
        )
      },
      33351: (t, e, r) => {
        'use strict'
        r.d(e, { M: () => h })
        var n = r(66415),
          o = r.n(n),
          i = r(8816),
          a = r.n(i),
          c = r(53568),
          u = r.n(c),
          l = r(24082),
          s = r(1024),
          f = r(86544),
          p = r(24737)
        function y(t, e) {
          ;(null == e || e > t.length) && (e = t.length)
          for (var r = 0, n = new Array(e); r < e; r++) n[r] = t[r]
          return n
        }
        var h = function () {
          var t,
            e,
            r = (0, l.v9)(p.C),
            n =
              ((t = (0, s.useState)(null)),
              (e = 2),
              (function (t) {
                if (Array.isArray(t)) return t
              })(t) ||
                (function (t, e) {
                  var r =
                    null == t
                      ? null
                      : ('undefined' != typeof Symbol && t[Symbol.iterator]) ||
                        t['@@iterator']
                  if (null != r) {
                    var n,
                      o,
                      i,
                      a,
                      c = [],
                      u = !0,
                      l = !1
                    try {
                      if (((i = (r = r.call(t)).next), 0 === e)) {
                        if (Object(r) !== r) return
                        u = !1
                      } else
                        for (
                          ;
                          !(u = (n = i.call(r)).done) &&
                          (c.push(n.value), c.length !== e);
                          u = !0
                        );
                    } catch (t) {
                      ;(l = !0), (o = t)
                    } finally {
                      try {
                        if (
                          !u &&
                          null != r.return &&
                          ((a = r.return()), Object(a) !== a)
                        )
                          return
                      } finally {
                        if (l) throw o
                      }
                    }
                    return c
                  }
                })(t, e) ||
                (function (t, e) {
                  if (t) {
                    if ('string' == typeof t) return y(t, e)
                    var r = Object.prototype.toString.call(t).slice(8, -1)
                    return (
                      'Object' === r &&
                        t.constructor &&
                        (r = t.constructor.name),
                      'Map' === r || 'Set' === r
                        ? Array.from(t)
                        : 'Arguments' === r ||
                          /^(?:Ui|I)nt(?:8|16|32)(?:Clamped)?Array$/.test(r)
                        ? y(t, e)
                        : void 0
                    )
                  }
                })(t, e) ||
                (function () {
                  throw new TypeError(
                    'Invalid attempt to destructure non-iterable instance.\nIn order to be iterable, non-array objects must have a [Symbol.iterator]() method.'
                  )
                })()),
            i = n[0],
            c = n[1]
          return (
            (0, s.useEffect)(
              function () {
                var t
                return (
                  (function e() {
                    if (r) {
                      var n = new Date(),
                        i = a()([
                          o()(function (t) {
                            return new Date(t.onAirDateTime)
                          }),
                          u()(function (t) {
                            return n <= new Date(t.onAirDateTime)
                          }),
                        ])(r)
                      if (-1 !== i)
                        if (0 !== i) {
                          c(r[i - 1])
                          var l = r[i],
                            s = (0, f.Z)(new Date(l.onAirDateTime), n)
                          t = setTimeout(e, s)
                        } else c(null)
                      else c(r[r.length - 1])
                    } else c(null)
                  })(),
                  function () {
                    clearTimeout(t)
                  }
                )
              },
              [r]
            ),
            i
          )
        }
      },
      6436: (t, e, r) => {
        'use strict'
        r.d(e, { ZP: () => b })
        var n = r(94654),
          o = r.n(n),
          i = r(27422),
          a = r(1349),
          c = r(1601)
        function u(t) {
          return (
            (u =
              'function' == typeof Symbol && 'symbol' == typeof Symbol.iterator
                ? function (t) {
                    return typeof t
                  }
                : function (t) {
                    return t &&
                      'function' == typeof Symbol &&
                      t.constructor === Symbol &&
                      t !== Symbol.prototype
                      ? 'symbol'
                      : typeof t
                  }),
            u(t)
          )
        }
        function l() {
          l = function () {
            return e
          }
          var t,
            e = {},
            r = Object.prototype,
            n = r.hasOwnProperty,
            o =
              Object.defineProperty ||
              function (t, e, r) {
                t[e] = r.value
              },
            i = 'function' == typeof Symbol ? Symbol : {},
            a = i.iterator || '@@iterator',
            c = i.asyncIterator || '@@asyncIterator',
            s = i.toStringTag || '@@toStringTag'
          function f(t, e, r) {
            return (
              Object.defineProperty(t, e, {
                value: r,
                enumerable: !0,
                configurable: !0,
                writable: !0,
              }),
              t[e]
            )
          }
          try {
            f({}, '')
          } catch (t) {
            f = function (t, e, r) {
              return (t[e] = r)
            }
          }
          function p(t, e, r, n) {
            var i = e && e.prototype instanceof b ? e : b,
              a = Object.create(i.prototype),
              c = new T(n || [])
            return o(a, '_invoke', { value: P(t, r, c) }), a
          }
          function y(t, e, r) {
            try {
              return { type: 'normal', arg: t.call(e, r) }
            } catch (t) {
              return { type: 'throw', arg: t }
            }
          }
          e.wrap = p
          var h = 'suspendedStart',
            v = 'suspendedYield',
            d = 'executing',
            m = 'completed',
            g = {}
          function b() {}
          function w() {}
          function x() {}
          var O = {}
          f(O, a, function () {
            return this
          })
          var j = Object.getPrototypeOf,
            E = j && j(j(C([])))
          E && E !== r && n.call(E, a) && (O = E)
          var S = (x.prototype = b.prototype = Object.create(O))
          function k(t) {
            ;['next', 'throw', 'return'].forEach(function (e) {
              f(t, e, function (t) {
                return this._invoke(e, t)
              })
            })
          }
          function L(t, e) {
            function r(o, i, a, c) {
              var l = y(t[o], t, i)
              if ('throw' !== l.type) {
                var s = l.arg,
                  f = s.value
                return f && 'object' == u(f) && n.call(f, '__await')
                  ? e.resolve(f.__await).then(
                      function (t) {
                        r('next', t, a, c)
                      },
                      function (t) {
                        r('throw', t, a, c)
                      }
                    )
                  : e.resolve(f).then(
                      function (t) {
                        ;(s.value = t), a(s)
                      },
                      function (t) {
                        return r('throw', t, a, c)
                      }
                    )
              }
              c(l.arg)
            }
            var i
            o(this, '_invoke', {
              value: function (t, n) {
                function o() {
                  return new e(function (e, o) {
                    r(t, n, e, o)
                  })
                }
                return (i = i ? i.then(o, o) : o())
              },
            })
          }
          function P(e, r, n) {
            var o = h
            return function (i, a) {
              if (o === d) throw new Error('Generator is already running')
              if (o === m) {
                if ('throw' === i) throw a
                return { value: t, done: !0 }
              }
              for (n.method = i, n.arg = a; ; ) {
                var c = n.delegate
                if (c) {
                  var u = _(c, n)
                  if (u) {
                    if (u === g) continue
                    return u
                  }
                }
                if ('next' === n.method) n.sent = n._sent = n.arg
                else if ('throw' === n.method) {
                  if (o === h) throw ((o = m), n.arg)
                  n.dispatchException(n.arg)
                } else 'return' === n.method && n.abrupt('return', n.arg)
                o = d
                var l = y(e, r, n)
                if ('normal' === l.type) {
                  if (((o = n.done ? m : v), l.arg === g)) continue
                  return { value: l.arg, done: n.done }
                }
                'throw' === l.type &&
                  ((o = m), (n.method = 'throw'), (n.arg = l.arg))
              }
            }
          }
          function _(e, r) {
            var n = r.method,
              o = e.iterator[n]
            if (o === t)
              return (
                (r.delegate = null),
                ('throw' === n &&
                  e.iterator.return &&
                  ((r.method = 'return'),
                  (r.arg = t),
                  _(e, r),
                  'throw' === r.method)) ||
                  ('return' !== n &&
                    ((r.method = 'throw'),
                    (r.arg = new TypeError(
                      "The iterator does not provide a '" + n + "' method"
                    )))),
                g
              )
            var i = y(o, e.iterator, r.arg)
            if ('throw' === i.type)
              return (
                (r.method = 'throw'), (r.arg = i.arg), (r.delegate = null), g
              )
            var a = i.arg
            return a
              ? a.done
                ? ((r[e.resultName] = a.value),
                  (r.next = e.nextLoc),
                  'return' !== r.method && ((r.method = 'next'), (r.arg = t)),
                  (r.delegate = null),
                  g)
                : a
              : ((r.method = 'throw'),
                (r.arg = new TypeError('iterator result is not an object')),
                (r.delegate = null),
                g)
          }
          function A(t) {
            var e = { tryLoc: t[0] }
            1 in t && (e.catchLoc = t[1]),
              2 in t && ((e.finallyLoc = t[2]), (e.afterLoc = t[3])),
              this.tryEntries.push(e)
          }
          function I(t) {
            var e = t.completion || {}
            ;(e.type = 'normal'), delete e.arg, (t.completion = e)
          }
          function T(t) {
            ;(this.tryEntries = [{ tryLoc: 'root' }]),
              t.forEach(A, this),
              this.reset(!0)
          }
          function C(e) {
            if (e || '' === e) {
              var r = e[a]
              if (r) return r.call(e)
              if ('function' == typeof e.next) return e
              if (!isNaN(e.length)) {
                var o = -1,
                  i = function r() {
                    for (; ++o < e.length; )
                      if (n.call(e, o))
                        return (r.value = e[o]), (r.done = !1), r
                    return (r.value = t), (r.done = !0), r
                  }
                return (i.next = i)
              }
            }
            throw new TypeError(u(e) + ' is not iterable')
          }
          return (
            (w.prototype = x),
            o(S, 'constructor', { value: x, configurable: !0 }),
            o(x, 'constructor', { value: w, configurable: !0 }),
            (w.displayName = f(x, s, 'GeneratorFunction')),
            (e.isGeneratorFunction = function (t) {
              var e = 'function' == typeof t && t.constructor
              return (
                !!e &&
                (e === w || 'GeneratorFunction' === (e.displayName || e.name))
              )
            }),
            (e.mark = function (t) {
              return (
                Object.setPrototypeOf
                  ? Object.setPrototypeOf(t, x)
                  : ((t.__proto__ = x), f(t, s, 'GeneratorFunction')),
                (t.prototype = Object.create(S)),
                t
              )
            }),
            (e.awrap = function (t) {
              return { __await: t }
            }),
            k(L.prototype),
            f(L.prototype, c, function () {
              return this
            }),
            (e.AsyncIterator = L),
            (e.async = function (t, r, n, o, i) {
              void 0 === i && (i = Promise)
              var a = new L(p(t, r, n, o), i)
              return e.isGeneratorFunction(r)
                ? a
                : a.next().then(function (t) {
                    return t.done ? t.value : a.next()
                  })
            }),
            k(S),
            f(S, s, 'Generator'),
            f(S, a, function () {
              return this
            }),
            f(S, 'toString', function () {
              return '[object Generator]'
            }),
            (e.keys = function (t) {
              var e = Object(t),
                r = []
              for (var n in e) r.push(n)
              return (
                r.reverse(),
                function t() {
                  for (; r.length; ) {
                    var n = r.pop()
                    if (n in e) return (t.value = n), (t.done = !1), t
                  }
                  return (t.done = !0), t
                }
              )
            }),
            (e.values = C),
            (T.prototype = {
              constructor: T,
              reset: function (e) {
                if (
                  ((this.prev = 0),
                  (this.next = 0),
                  (this.sent = this._sent = t),
                  (this.done = !1),
                  (this.delegate = null),
                  (this.method = 'next'),
                  (this.arg = t),
                  this.tryEntries.forEach(I),
                  !e)
                )
                  for (var r in this)
                    't' === r.charAt(0) &&
                      n.call(this, r) &&
                      !isNaN(+r.slice(1)) &&
                      (this[r] = t)
              },
              stop: function () {
                this.done = !0
                var t = this.tryEntries[0].completion
                if ('throw' === t.type) throw t.arg
                return this.rval
              },
              dispatchException: function (e) {
                if (this.done) throw e
                var r = this
                function o(n, o) {
                  return (
                    (c.type = 'throw'),
                    (c.arg = e),
                    (r.next = n),
                    o && ((r.method = 'next'), (r.arg = t)),
                    !!o
                  )
                }
                for (var i = this.tryEntries.length - 1; i >= 0; --i) {
                  var a = this.tryEntries[i],
                    c = a.completion
                  if ('root' === a.tryLoc) return o('end')
                  if (a.tryLoc <= this.prev) {
                    var u = n.call(a, 'catchLoc'),
                      l = n.call(a, 'finallyLoc')
                    if (u && l) {
                      if (this.prev < a.catchLoc) return o(a.catchLoc, !0)
                      if (this.prev < a.finallyLoc) return o(a.finallyLoc)
                    } else if (u) {
                      if (this.prev < a.catchLoc) return o(a.catchLoc, !0)
                    } else {
                      if (!l)
                        throw new Error(
                          'try statement without catch or finally'
                        )
                      if (this.prev < a.finallyLoc) return o(a.finallyLoc)
                    }
                  }
                }
              },
              abrupt: function (t, e) {
                for (var r = this.tryEntries.length - 1; r >= 0; --r) {
                  var o = this.tryEntries[r]
                  if (
                    o.tryLoc <= this.prev &&
                    n.call(o, 'finallyLoc') &&
                    this.prev < o.finallyLoc
                  ) {
                    var i = o
                    break
                  }
                }
                i &&
                  ('break' === t || 'continue' === t) &&
                  i.tryLoc <= e &&
                  e <= i.finallyLoc &&
                  (i = null)
                var a = i ? i.completion : {}
                return (
                  (a.type = t),
                  (a.arg = e),
                  i
                    ? ((this.method = 'next'), (this.next = i.finallyLoc), g)
                    : this.complete(a)
                )
              },
              complete: function (t, e) {
                if ('throw' === t.type) throw t.arg
                return (
                  'break' === t.type || 'continue' === t.type
                    ? (this.next = t.arg)
                    : 'return' === t.type
                    ? ((this.rval = this.arg = t.arg),
                      (this.method = 'return'),
                      (this.next = 'end'))
                    : 'normal' === t.type && e && (this.next = e),
                  g
                )
              },
              finish: function (t) {
                for (var e = this.tryEntries.length - 1; e >= 0; --e) {
                  var r = this.tryEntries[e]
                  if (r.finallyLoc === t)
                    return this.complete(r.completion, r.afterLoc), I(r), g
                }
              },
              catch: function (t) {
                for (var e = this.tryEntries.length - 1; e >= 0; --e) {
                  var r = this.tryEntries[e]
                  if (r.tryLoc === t) {
                    var n = r.completion
                    if ('throw' === n.type) {
                      var o = n.arg
                      I(r)
                    }
                    return o
                  }
                }
                throw new Error('illegal catch attempt')
              },
              delegateYield: function (e, r, n) {
                return (
                  (this.delegate = {
                    iterator: C(e),
                    resultName: r,
                    nextLoc: n,
                  }),
                  'next' === this.method && (this.arg = t),
                  g
                )
              },
            }),
            e
          )
        }
        var s = l().mark(v),
          f = l().mark(d),
          p = l().mark(m),
          y = l().mark(g),
          h = l().mark(b)
        function v() {
          var t, e
          return l().wrap(function (r) {
            for (;;)
              switch ((r.prev = r.next)) {
                case 0:
                  return (
                    (r.next = 2), (0, i.RE)(a.uY.get, '/epg/list/0/2/aest/')
                  )
                case 2:
                  return (
                    (t = r.sent),
                    (e = o()(t.data.items, function (t) {
                      return t.programs
                    })),
                    (r.next = 6),
                    (0, i.gz)((0, c.rG)({ programs: e }))
                  )
                case 6:
                case 'end':
                  return r.stop()
              }
          }, s)
        }
        function d() {
          return l().wrap(function (t) {
            for (;;)
              switch ((t.prev = t.next)) {
                case 0:
                  if ('true' !== localStorage.getItem('inlineLiveVision')) {
                    t.next = 4
                    break
                  }
                  return (t.next = 4), (0, i.gz)((0, c.yG)())
                case 4:
                case 'end':
                  return t.stop()
              }
          }, f)
        }
        function m() {
          return l().wrap(function (t) {
            for (;;)
              switch ((t.prev = t.next)) {
                case 0:
                  localStorage.setItem('inlineLiveVision', !0)
                case 1:
                case 'end':
                  return t.stop()
              }
          }, p)
        }
        function g() {
          return l().wrap(function (t) {
            for (;;)
              switch ((t.prev = t.next)) {
                case 0:
                  localStorage.setItem('inlineLiveVision', !1)
                case 1:
                case 'end':
                  return t.stop()
              }
          }, y)
        }
        function b() {
          return l().wrap(function (t) {
            for (;;)
              switch ((t.prev = t.next)) {
                case 0:
                  return (t.next = 2), (0, i.rM)(v)
                case 2:
                  return (t.next = 4), (0, i.rM)(d)
                case 4:
                  return (t.next = 6), (0, i.ib)(c.yG.type, m)
                case 6:
                  return (t.next = 8), (0, i.ib)(c.Sk.type, g)
                case 8:
                case 'end':
                  return t.stop()
              }
          }, h)
        }
      },
      24737: (t, e, r) => {
        'use strict'
        r.d(e, { C: () => o, w: () => i })
        var n = r(1601),
          o = function (t) {
            var e
            return null === (e = t[n.u2]) || void 0 === e ? void 0 : e.programs
          },
          i = function (t) {
            var e
            return null === (e = t[n.u2]) || void 0 === e ? void 0 : e.onAir
          }
      },
      1601: (t, e, r) => {
        'use strict'
        r.d(e, {
          I6: () => s,
          Sk: () => c,
          rG: () => i,
          u2: () => l,
          wR: () => u,
          yG: () => a,
        })
        var n = (0, r(2655).oM)({
            name: 'live-vision',
            initialState: { programs: null, onAir: !1 },
            reducers: {
              updatePrograms: function (t, e) {
                var r = e.payload.programs
                t.programs = r
              },
              playLiveVision: function (t) {
                t.onAir = !0
              },
              stopLiveVision: function (t) {
                t.onAir = !1
              },
              toggleLiveVision: function (t) {
                t.onAir = !t.onAir
              },
            },
          }),
          o = n.actions,
          i = o.updatePrograms,
          a = o.playLiveVision,
          c = o.stopLiveVision,
          u = o.toggleLiveVision,
          l = n.name,
          s = n.reducer
      },
      20817: (t, e, r) => {
        'use strict'
        r.d(e, { hq: () => o })
        r(1024), r(30186)
        var n = r(13980),
          o = (r(62388), { '@media print': { display: 'none !important' } })
        n.PropTypes.node.isRequired, n.PropTypes.node.isRequired
      },
      53817: (t, e, r) => {
        'use strict'
        r(14629), r(25047), r(92556)
      },
      92556: (t, e, r) => {
        r.p = window.rdcWidgetsPath || ''
      },
      30933: (t, e, r) => {
        'use strict'
        r.r(e),
          r.d(e, {
            PlayLiveVision: () => $,
            StopLiveVision: () => Q,
            ToggleLiveVision: () => H,
            default: () => B,
          }),
          r(53817)
        var n = r(1024),
          o = r.n(n),
          i = r(71570),
          a = r(87778),
          c = r(13980),
          u = r.n(c),
          l = r(13295),
          s = r(24082),
          f = r(30186),
          p = r(75506),
          y = r(81987),
          h = r(54951),
          v = r(2738),
          d = r(40163),
          m = r(20817),
          g = r(77450),
          b = function (t) {
            var e = t.type,
              r = t.onClick
            return o().createElement(
              y.Z,
              {
                className: 'live-vision__action-icon',
                variant: 'button.icon',
                sx: {
                  color: 'white',
                  fontSize: '15px',
                  transition: 'color 0.2s ease-out',
                  '&:hover': { color: 'grey-99' },
                },
                onClick: r,
              },
              o().createElement(g.Z, { type: e, inline: !0 })
            )
          }
        b.propTypes = { type: u().string.isRequired, onClick: u().func }
        const w = b
        var x = r(63743),
          O = r(33351),
          j = r(1601),
          E = r(6436),
          S = r(24737),
          k = r(21036)
        function L(t) {
          return (
            (L =
              'function' == typeof Symbol && 'symbol' == typeof Symbol.iterator
                ? function (t) {
                    return typeof t
                  }
                : function (t) {
                    return t &&
                      'function' == typeof Symbol &&
                      t.constructor === Symbol &&
                      t !== Symbol.prototype
                      ? 'symbol'
                      : typeof t
                  }),
            L(t)
          )
        }
        var P,
          _ = ['desktopOnly', 'playerUrl']
        function A() {
          return (
            (A = Object.assign
              ? Object.assign.bind()
              : function (t) {
                  for (var e = 1; e < arguments.length; e++) {
                    var r = arguments[e]
                    for (var n in r)
                      Object.prototype.hasOwnProperty.call(r, n) &&
                        (t[n] = r[n])
                  }
                  return t
                }),
            A.apply(this, arguments)
          )
        }
        function I(t, e) {
          var r = Object.keys(t)
          if (Object.getOwnPropertySymbols) {
            var n = Object.getOwnPropertySymbols(t)
            e &&
              (n = n.filter(function (e) {
                return Object.getOwnPropertyDescriptor(t, e).enumerable
              })),
              r.push.apply(r, n)
          }
          return r
        }
        function T(t) {
          for (var e = 1; e < arguments.length; e++) {
            var r = null != arguments[e] ? arguments[e] : {}
            e % 2
              ? I(Object(r), !0).forEach(function (e) {
                  var n, o, i, a
                  ;(n = t),
                    (o = e),
                    (i = r[e]),
                    (a = (function (t, e) {
                      if ('object' != L(t) || !t) return t
                      var r = t[Symbol.toPrimitive]
                      if (void 0 !== r) {
                        var n = r.call(t, 'string')
                        if ('object' != L(n)) return n
                        throw new TypeError(
                          '@@toPrimitive must return a primitive value.'
                        )
                      }
                      return String(t)
                    })(o)),
                    (o = 'symbol' == L(a) ? a : String(a)) in n
                      ? Object.defineProperty(n, o, {
                          value: i,
                          enumerable: !0,
                          configurable: !0,
                          writable: !0,
                        })
                      : (n[o] = i)
                })
              : Object.getOwnPropertyDescriptors
              ? Object.defineProperties(t, Object.getOwnPropertyDescriptors(r))
              : I(Object(r)).forEach(function (e) {
                  Object.defineProperty(
                    t,
                    e,
                    Object.getOwnPropertyDescriptor(r, e)
                  )
                })
          }
          return t
        }
        function C(t, e) {
          return (
            (function (t) {
              if (Array.isArray(t)) return t
            })(t) ||
            (function (t, e) {
              var r =
                null == t
                  ? null
                  : ('undefined' != typeof Symbol && t[Symbol.iterator]) ||
                    t['@@iterator']
              if (null != r) {
                var n,
                  o,
                  i,
                  a,
                  c = [],
                  u = !0,
                  l = !1
                try {
                  if (((i = (r = r.call(t)).next), 0 === e)) {
                    if (Object(r) !== r) return
                    u = !1
                  } else
                    for (
                      ;
                      !(u = (n = i.call(r)).done) &&
                      (c.push(n.value), c.length !== e);
                      u = !0
                    );
                } catch (t) {
                  ;(l = !0), (o = t)
                } finally {
                  try {
                    if (
                      !u &&
                      null != r.return &&
                      ((a = r.return()), Object(a) !== a)
                    )
                      return
                  } finally {
                    if (l) throw o
                  }
                }
                return c
              }
            })(t, e) ||
            (function (t, e) {
              if (t) {
                if ('string' == typeof t) return R(t, e)
                var r = Object.prototype.toString.call(t).slice(8, -1)
                return (
                  'Object' === r && t.constructor && (r = t.constructor.name),
                  'Map' === r || 'Set' === r
                    ? Array.from(t)
                    : 'Arguments' === r ||
                      /^(?:Ui|I)nt(?:8|16|32)(?:Clamped)?Array$/.test(r)
                    ? R(t, e)
                    : void 0
                )
              }
            })(t, e) ||
            (function () {
              throw new TypeError(
                'Invalid attempt to destructure non-iterable instance.\nIn order to be iterable, non-array objects must have a [Symbol.iterator]() method.'
              )
            })()
          )
        }
        function R(t, e) {
          ;(null == e || e > t.length) && (e = t.length)
          for (var r = 0, n = new Array(e); r < e; r++) n[r] = t[r]
          return n
        }
        var D,
          G,
          V = (0, h.fW)('Live Vision'),
          q = (0, p.F4)(
            P ||
              ((D = [
                '\n  0% {\n    left: 0;\n  }\n  33% {\n    left: 0;\n  }\n  66% {\n    left: -100%;\n  }\n  66.001% {\n    left: 100%;\n  }\n  100% {\n    left: 0;\n  }\n',
              ]),
              G || (G = D.slice(0)),
              (P = Object.freeze(
                Object.defineProperties(D, { raw: { value: Object.freeze(G) } })
              )))
          ),
          N = (0, a.Z)('div', { target: 'e189vvo40' })(
            'width:100%;overflow:visible;position:relative;animation:',
            function (t) {
              return t.scrolling ? (0, p.iv)(q, ' 10s linear infinite') : null
            },
            ';'
          ),
          M = function (t) {
            var e = t.desktopOnly,
              r = t.playerUrl,
              i = (function (t, e) {
                if (null == t) return {}
                var r,
                  n,
                  o = (function (t, e) {
                    if (null == t) return {}
                    var r,
                      n,
                      o = {},
                      i = Object.keys(t)
                    for (n = 0; n < i.length; n++)
                      (r = i[n]), e.indexOf(r) >= 0 || (o[r] = t[r])
                    return o
                  })(t, e)
                if (Object.getOwnPropertySymbols) {
                  var i = Object.getOwnPropertySymbols(t)
                  for (n = 0; n < i.length; n++)
                    (r = i[n]),
                      e.indexOf(r) >= 0 ||
                        (Object.prototype.propertyIsEnumerable.call(t, r) &&
                          (o[r] = t[r]))
                }
                return o
              })(t, _)
            ;(0, l.vp)({ key: j.u2, reducer: j.I6 }),
              (0, l.hb)({ key: j.u2, saga: E.ZP })
            var a = (0, s.I0)(),
              c = (0, d.Ln)(),
              u = (0, s.v9)(S.w),
              p = C((0, n.useState)(u), 2),
              h = p[0],
              g = p[1],
              b = (0, O.M)(),
              L = (0, n.useRef)(null),
              P = C((0, n.useState)(!1), 2),
              I = P[0],
              R = P[1],
              D = (0, k.yv)() ? '5Zaur6qhu' : 'FCT1vQkwI'
            return (
              (0, n.useEffect)(
                function () {
                  L.current && R(L.current.scrollWidth > L.current.offsetWidth)
                },
                [b]
              ),
              (0, n.useEffect)(
                function () {
                  if (!u) {
                    var t,
                      e = document.getElementById('live-vision-iframe')
                    e &&
                      e.contentWindow &&
                      (null === (t = e.contentWindow) ||
                        void 0 === t ||
                        t.postMessage({ type: 'bc.dispose', bcPlayer: D }))
                  }
                  setTimeout(function () {
                    g(u)
                  }, 100)
                },
                [u]
              ),
              e && !c
                ? null
                : b
                ? o().createElement(
                    f.xu,
                    A(
                      {
                        className: 'live-vision',
                        'data-track-class': 'live-vision-bar',
                        sx: T(
                          {
                            position: 'fixed',
                            right: 0,
                            bottom: 0,
                            width: '350px',
                            backgroundColor: 'black',
                            boxShadow: '-1px -1px 5px 1px rgba(0,0,0,0.2)',
                            zIndex: 3,
                          },
                          m.hq
                        ),
                      },
                      i
                    ),
                    o().createElement(
                      f.xu,
                      {
                        className: 'live-vision__view',
                        sx: {
                          width: '100%',
                          height: u ? '247px' : '0',
                          backgroundColor: 'black',
                          transition: 'height 0.3s ease-out',
                          overflow: 'hidden',
                        },
                      },
                      h &&
                        o().createElement('iframe', {
                          id: 'live-vision-iframe',
                          src: r,
                          title: 'live vision',
                          width: '100%',
                          height: '100%',
                          scrolling: 'no',
                          frameBorder: '0',
                          allowFullScreen: !0,
                          'data-rdc-bc-player': D,
                        })
                    ),
                    o().createElement(
                      f.kC,
                      {
                        className: 'live-vision__control-bar',
                        sx: {
                          height: '56px',
                          padding: '18px',
                          backgroundColor: 'grey-33',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          cursor: 'pointer',
                        },
                        onClick: function () {
                          u
                            ? (a((0, j.Sk)()), V('Closed'))
                            : (0, v.Iq)().then(function () {
                                a((0, j.yG)()), V('Opened')
                              })
                        },
                      },
                      o().createElement(
                        y.Z,
                        {
                          className: 'live-vision__toggle',
                          sx: {
                            flex: '0 0 auto',
                            cursor: 'pointer',
                            border: 'none',
                            py: 'sm',
                            px: 'md',
                            borderRadius: '2px',
                            backgroundColor: 'primary',
                            color: 'white',
                            '&:hover': { color: 'white' },
                          },
                        },
                        u
                          ? o().createElement(f.xv, null, 'On Air')
                          : o().createElement(f.xv, null, 'Watch Live'),
                        o().createElement(x.Z, null)
                      ),
                      o().createElement(
                        f.xu,
                        {
                          className: 'live-vision__program',
                          sx: {
                            flex: '1 1 auto',
                            mx: 'md',
                            overflow: 'hidden',
                          },
                        },
                        b &&
                          o().createElement(
                            N,
                            { scrolling: I ? 1 : 0, ref: L },
                            o().createElement(
                              f.xv,
                              {
                                as: 'span',
                                sx: {
                                  color: 'white',
                                  fontSize: '12px',
                                  whiteSpace: 'nowrap',
                                  transition: 'color 0.2s ease-out',
                                  '&:hover': { color: 'grey-99' },
                                },
                              },
                              null == b ? void 0 : b.title
                            )
                          )
                      ),
                      o().createElement(
                        f.xu,
                        { sx: { flex: '0 0 auto' } },
                        u
                          ? o().createElement(
                              o().Fragment,
                              null,
                              o().createElement(w, {
                                type: 'external-link',
                                onClick: function () {
                                  V('Popup')
                                  var t = window.open(
                                    'https://'.concat(
                                      window.location.host,
                                      '/live-vision.aspx'
                                    ),
                                    'Live Vision',
                                    'toolbar=yes, scrollbars=yes, resizable=yes, width='.concat(
                                      840,
                                      ', height=',
                                      620
                                    )
                                  )
                                  window.focus && t.focus()
                                },
                              }),
                              o().createElement(w, { type: 'stop-button' })
                            )
                          : o().createElement(w, { type: 'play-icon' })
                      )
                    )
                  )
                : null
            )
          }
        M.propTypes = {
          desktopOnly: u().bool,
          playerUrl: u().string.isRequired,
        }
        const Z = M
        var F = r(79777),
          z = r(96331),
          W = r(10687),
          U = ['desktopOnly']
        function Y() {
          return (
            (Y = Object.assign
              ? Object.assign.bind()
              : function (t) {
                  for (var e = 1; e < arguments.length; e++) {
                    var r = arguments[e]
                    for (var n in r)
                      Object.prototype.hasOwnProperty.call(r, n) &&
                        (t[n] = r[n])
                  }
                  return t
                }),
            Y.apply(this, arguments)
          )
        }
        const B = (0, i.w)(function (t) {
          var e = t.desktopOnly,
            r = (function (t, e) {
              if (null == t) return {}
              var r,
                n,
                o = (function (t, e) {
                  if (null == t) return {}
                  var r,
                    n,
                    o = {},
                    i = Object.keys(t)
                  for (n = 0; n < i.length; n++)
                    (r = i[n]), e.indexOf(r) >= 0 || (o[r] = t[r])
                  return o
                })(t, e)
              if (Object.getOwnPropertySymbols) {
                var i = Object.getOwnPropertySymbols(t)
                for (n = 0; n < i.length; n++)
                  (r = i[n]),
                    e.indexOf(r) >= 0 ||
                      (Object.prototype.propertyIsEnumerable.call(t, r) &&
                        (o[r] = t[r]))
              }
              return o
            })(t, U)
          return o().createElement(
            z.Z,
            null,
            o().createElement(Z, Y({ desktopOnly: (0, W.Fn)(e) }, r))
          )
        })
        var $ = function () {
            return (0, v.Iq)().then(function () {
              return F.h.dispatch((0, j.yG)())
            })
          },
          Q = function () {
            return F.h.dispatch((0, j.Sk)())
          },
          H = function () {
            return (0, v.Iq)().then(function () {
              return F.h.dispatch((0, j.wR)())
            })
          }
      },
      1024: (e) => {
        'use strict'
        e.exports = t
      },
      30314: (t) => {
        'use strict'
        t.exports = e
      },
    },
    (t) => (t.O(0, [736, 351], () => (30933, t((t.s = 30933)))), t.O()),
  ])
)

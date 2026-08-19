/*! For license information please see rdc.header.js.LICENSE.txt */
!(function (e, t) {
  'object' == typeof exports && 'object' == typeof module
    ? (module.exports = t(require('React'), require('ReactDOM')))
    : 'function' == typeof define && define.amd
    ? define(['React', 'ReactDOM'], t)
    : 'object' == typeof exports
    ? (exports.rdc = t(require('React'), require('ReactDOM')))
    : ((e.rdc = e.rdc || {}), (e.rdc.header = t(e.React, e.ReactDOM)))
})(self, (e, t) =>
  (self.webpackChunkrdc = self.webpackChunkrdc || []).push([
    [19],
    {
      71956: (e, t, n) => {
        'use strict'
        n.d(t, { Z: () => r })
        const r = {
          aws_project_region: 'ap-southeast-2',
          aws_cognito_identity_pool_id:
            'ap-southeast-2:112216cb-7613-476a-b08d-511cd06070dd',
          aws_cognito_region: 'ap-southeast-2',
          oauth: {},
          aws_mobile_analytics_app_id: '6797d1fff5ed4a77a3ccc8c12f1c2f16',
          aws_mobile_analytics_app_region: 'us-west-2',
          appId: '551938d4549248e991f52f1e8409fc86',
        }
      },
      63743: (e, t, n) => {
        'use strict'
        n.d(t, { Z: () => l })
        var r,
          o,
          i,
          a = n(87778),
          c = (0, n(75506).F4)(
            r ||
              ((o = [
                '\n  0% {\n    color: inherit;\n  }\n  50% {\n    color: transparent;\n  }\n  100% {\n    color: inherit;\n  }\n',
              ]),
              i || (i = o.slice(0)),
              (r = Object.freeze(
                Object.defineProperties(o, { raw: { value: Object.freeze(i) } })
              )))
          )
        const l = (0, a.Z)('div', { target: 'e1bf47j40' })(
          'animation:',
          c,
          " 2s linear infinite;padding-left:6px;&::after{content:'•';}"
        )
      },
      33351: (e, t, n) => {
        'use strict'
        n.d(t, { M: () => m })
        var r = n(66415),
          o = n.n(r),
          i = n(8816),
          a = n.n(i),
          c = n(53568),
          l = n.n(c),
          u = n(24082),
          s = n(1024),
          f = n(86544),
          p = n(24737)
        function d(e, t) {
          ;(null == t || t > e.length) && (t = e.length)
          for (var n = 0, r = new Array(t); n < t; n++) r[n] = e[n]
          return r
        }
        var m = function () {
          var e,
            t,
            n = (0, u.v9)(p.C),
            r =
              ((e = (0, s.useState)(null)),
              (t = 2),
              (function (e) {
                if (Array.isArray(e)) return e
              })(e) ||
                (function (e, t) {
                  var n =
                    null == e
                      ? null
                      : ('undefined' != typeof Symbol && e[Symbol.iterator]) ||
                        e['@@iterator']
                  if (null != n) {
                    var r,
                      o,
                      i,
                      a,
                      c = [],
                      l = !0,
                      u = !1
                    try {
                      if (((i = (n = n.call(e)).next), 0 === t)) {
                        if (Object(n) !== n) return
                        l = !1
                      } else
                        for (
                          ;
                          !(l = (r = i.call(n)).done) &&
                          (c.push(r.value), c.length !== t);
                          l = !0
                        );
                    } catch (e) {
                      ;(u = !0), (o = e)
                    } finally {
                      try {
                        if (
                          !l &&
                          null != n.return &&
                          ((a = n.return()), Object(a) !== a)
                        )
                          return
                      } finally {
                        if (u) throw o
                      }
                    }
                    return c
                  }
                })(e, t) ||
                (function (e, t) {
                  if (e) {
                    if ('string' == typeof e) return d(e, t)
                    var n = Object.prototype.toString.call(e).slice(8, -1)
                    return (
                      'Object' === n &&
                        e.constructor &&
                        (n = e.constructor.name),
                      'Map' === n || 'Set' === n
                        ? Array.from(e)
                        : 'Arguments' === n ||
                          /^(?:Ui|I)nt(?:8|16|32)(?:Clamped)?Array$/.test(n)
                        ? d(e, t)
                        : void 0
                    )
                  }
                })(e, t) ||
                (function () {
                  throw new TypeError(
                    'Invalid attempt to destructure non-iterable instance.\nIn order to be iterable, non-array objects must have a [Symbol.iterator]() method.'
                  )
                })()),
            i = r[0],
            c = r[1]
          return (
            (0, s.useEffect)(
              function () {
                var e
                return (
                  (function t() {
                    if (n) {
                      var r = new Date(),
                        i = a()([
                          o()(function (e) {
                            return new Date(e.onAirDateTime)
                          }),
                          l()(function (e) {
                            return r <= new Date(e.onAirDateTime)
                          }),
                        ])(n)
                      if (-1 !== i)
                        if (0 !== i) {
                          c(n[i - 1])
                          var u = n[i],
                            s = (0, f.Z)(new Date(u.onAirDateTime), r)
                          e = setTimeout(t, s)
                        } else c(null)
                      else c(n[n.length - 1])
                    } else c(null)
                  })(),
                  function () {
                    clearTimeout(e)
                  }
                )
              },
              [n]
            ),
            i
          )
        }
      },
      6436: (e, t, n) => {
        'use strict'
        n.d(t, { ZP: () => v })
        var r = n(94654),
          o = n.n(r),
          i = n(27422),
          a = n(1349),
          c = n(1601)
        function l(e) {
          return (
            (l =
              'function' == typeof Symbol && 'symbol' == typeof Symbol.iterator
                ? function (e) {
                    return typeof e
                  }
                : function (e) {
                    return e &&
                      'function' == typeof Symbol &&
                      e.constructor === Symbol &&
                      e !== Symbol.prototype
                      ? 'symbol'
                      : typeof e
                  }),
            l(e)
          )
        }
        function u() {
          u = function () {
            return t
          }
          var e,
            t = {},
            n = Object.prototype,
            r = n.hasOwnProperty,
            o =
              Object.defineProperty ||
              function (e, t, n) {
                e[t] = n.value
              },
            i = 'function' == typeof Symbol ? Symbol : {},
            a = i.iterator || '@@iterator',
            c = i.asyncIterator || '@@asyncIterator',
            s = i.toStringTag || '@@toStringTag'
          function f(e, t, n) {
            return (
              Object.defineProperty(e, t, {
                value: n,
                enumerable: !0,
                configurable: !0,
                writable: !0,
              }),
              e[t]
            )
          }
          try {
            f({}, '')
          } catch (e) {
            f = function (e, t, n) {
              return (e[t] = n)
            }
          }
          function p(e, t, n, r) {
            var i = t && t.prototype instanceof v ? t : v,
              a = Object.create(i.prototype),
              c = new L(r || [])
            return o(a, '_invoke', { value: P(e, n, c) }), a
          }
          function d(e, t, n) {
            try {
              return { type: 'normal', arg: e.call(t, n) }
            } catch (e) {
              return { type: 'throw', arg: e }
            }
          }
          t.wrap = p
          var m = 'suspendedStart',
            y = 'suspendedYield',
            b = 'executing',
            h = 'completed',
            g = {}
          function v() {}
          function w() {}
          function x() {}
          var E = {}
          f(E, a, function () {
            return this
          })
          var O = Object.getPrototypeOf,
            S = O && O(O(T([])))
          S && S !== n && r.call(S, a) && (E = S)
          var j = (x.prototype = v.prototype = Object.create(E))
          function k(e) {
            ;['next', 'throw', 'return'].forEach(function (t) {
              f(e, t, function (e) {
                return this._invoke(t, e)
              })
            })
          }
          function _(e, t) {
            function n(o, i, a, c) {
              var u = d(e[o], e, i)
              if ('throw' !== u.type) {
                var s = u.arg,
                  f = s.value
                return f && 'object' == l(f) && r.call(f, '__await')
                  ? t.resolve(f.__await).then(
                      function (e) {
                        n('next', e, a, c)
                      },
                      function (e) {
                        n('throw', e, a, c)
                      }
                    )
                  : t.resolve(f).then(
                      function (e) {
                        ;(s.value = e), a(s)
                      },
                      function (e) {
                        return n('throw', e, a, c)
                      }
                    )
              }
              c(u.arg)
            }
            var i
            o(this, '_invoke', {
              value: function (e, r) {
                function o() {
                  return new t(function (t, o) {
                    n(e, r, t, o)
                  })
                }
                return (i = i ? i.then(o, o) : o())
              },
            })
          }
          function P(t, n, r) {
            var o = m
            return function (i, a) {
              if (o === b) throw new Error('Generator is already running')
              if (o === h) {
                if ('throw' === i) throw a
                return { value: e, done: !0 }
              }
              for (r.method = i, r.arg = a; ; ) {
                var c = r.delegate
                if (c) {
                  var l = C(c, r)
                  if (l) {
                    if (l === g) continue
                    return l
                  }
                }
                if ('next' === r.method) r.sent = r._sent = r.arg
                else if ('throw' === r.method) {
                  if (o === m) throw ((o = h), r.arg)
                  r.dispatchException(r.arg)
                } else 'return' === r.method && r.abrupt('return', r.arg)
                o = b
                var u = d(t, n, r)
                if ('normal' === u.type) {
                  if (((o = r.done ? h : y), u.arg === g)) continue
                  return { value: u.arg, done: r.done }
                }
                'throw' === u.type &&
                  ((o = h), (r.method = 'throw'), (r.arg = u.arg))
              }
            }
          }
          function C(t, n) {
            var r = n.method,
              o = t.iterator[r]
            if (o === e)
              return (
                (n.delegate = null),
                ('throw' === r &&
                  t.iterator.return &&
                  ((n.method = 'return'),
                  (n.arg = e),
                  C(t, n),
                  'throw' === n.method)) ||
                  ('return' !== r &&
                    ((n.method = 'throw'),
                    (n.arg = new TypeError(
                      "The iterator does not provide a '" + r + "' method"
                    )))),
                g
              )
            var i = d(o, t.iterator, n.arg)
            if ('throw' === i.type)
              return (
                (n.method = 'throw'), (n.arg = i.arg), (n.delegate = null), g
              )
            var a = i.arg
            return a
              ? a.done
                ? ((n[t.resultName] = a.value),
                  (n.next = t.nextLoc),
                  'return' !== n.method && ((n.method = 'next'), (n.arg = e)),
                  (n.delegate = null),
                  g)
                : a
              : ((n.method = 'throw'),
                (n.arg = new TypeError('iterator result is not an object')),
                (n.delegate = null),
                g)
          }
          function A(e) {
            var t = { tryLoc: e[0] }
            1 in e && (t.catchLoc = e[1]),
              2 in e && ((t.finallyLoc = e[2]), (t.afterLoc = e[3])),
              this.tryEntries.push(t)
          }
          function I(e) {
            var t = e.completion || {}
            ;(t.type = 'normal'), delete t.arg, (e.completion = t)
          }
          function L(e) {
            ;(this.tryEntries = [{ tryLoc: 'root' }]),
              e.forEach(A, this),
              this.reset(!0)
          }
          function T(t) {
            if (t || '' === t) {
              var n = t[a]
              if (n) return n.call(t)
              if ('function' == typeof t.next) return t
              if (!isNaN(t.length)) {
                var o = -1,
                  i = function n() {
                    for (; ++o < t.length; )
                      if (r.call(t, o))
                        return (n.value = t[o]), (n.done = !1), n
                    return (n.value = e), (n.done = !0), n
                  }
                return (i.next = i)
              }
            }
            throw new TypeError(l(t) + ' is not iterable')
          }
          return (
            (w.prototype = x),
            o(j, 'constructor', { value: x, configurable: !0 }),
            o(x, 'constructor', { value: w, configurable: !0 }),
            (w.displayName = f(x, s, 'GeneratorFunction')),
            (t.isGeneratorFunction = function (e) {
              var t = 'function' == typeof e && e.constructor
              return (
                !!t &&
                (t === w || 'GeneratorFunction' === (t.displayName || t.name))
              )
            }),
            (t.mark = function (e) {
              return (
                Object.setPrototypeOf
                  ? Object.setPrototypeOf(e, x)
                  : ((e.__proto__ = x), f(e, s, 'GeneratorFunction')),
                (e.prototype = Object.create(j)),
                e
              )
            }),
            (t.awrap = function (e) {
              return { __await: e }
            }),
            k(_.prototype),
            f(_.prototype, c, function () {
              return this
            }),
            (t.AsyncIterator = _),
            (t.async = function (e, n, r, o, i) {
              void 0 === i && (i = Promise)
              var a = new _(p(e, n, r, o), i)
              return t.isGeneratorFunction(n)
                ? a
                : a.next().then(function (e) {
                    return e.done ? e.value : a.next()
                  })
            }),
            k(j),
            f(j, s, 'Generator'),
            f(j, a, function () {
              return this
            }),
            f(j, 'toString', function () {
              return '[object Generator]'
            }),
            (t.keys = function (e) {
              var t = Object(e),
                n = []
              for (var r in t) n.push(r)
              return (
                n.reverse(),
                function e() {
                  for (; n.length; ) {
                    var r = n.pop()
                    if (r in t) return (e.value = r), (e.done = !1), e
                  }
                  return (e.done = !0), e
                }
              )
            }),
            (t.values = T),
            (L.prototype = {
              constructor: L,
              reset: function (t) {
                if (
                  ((this.prev = 0),
                  (this.next = 0),
                  (this.sent = this._sent = e),
                  (this.done = !1),
                  (this.delegate = null),
                  (this.method = 'next'),
                  (this.arg = e),
                  this.tryEntries.forEach(I),
                  !t)
                )
                  for (var n in this)
                    't' === n.charAt(0) &&
                      r.call(this, n) &&
                      !isNaN(+n.slice(1)) &&
                      (this[n] = e)
              },
              stop: function () {
                this.done = !0
                var e = this.tryEntries[0].completion
                if ('throw' === e.type) throw e.arg
                return this.rval
              },
              dispatchException: function (t) {
                if (this.done) throw t
                var n = this
                function o(r, o) {
                  return (
                    (c.type = 'throw'),
                    (c.arg = t),
                    (n.next = r),
                    o && ((n.method = 'next'), (n.arg = e)),
                    !!o
                  )
                }
                for (var i = this.tryEntries.length - 1; i >= 0; --i) {
                  var a = this.tryEntries[i],
                    c = a.completion
                  if ('root' === a.tryLoc) return o('end')
                  if (a.tryLoc <= this.prev) {
                    var l = r.call(a, 'catchLoc'),
                      u = r.call(a, 'finallyLoc')
                    if (l && u) {
                      if (this.prev < a.catchLoc) return o(a.catchLoc, !0)
                      if (this.prev < a.finallyLoc) return o(a.finallyLoc)
                    } else if (l) {
                      if (this.prev < a.catchLoc) return o(a.catchLoc, !0)
                    } else {
                      if (!u)
                        throw new Error(
                          'try statement without catch or finally'
                        )
                      if (this.prev < a.finallyLoc) return o(a.finallyLoc)
                    }
                  }
                }
              },
              abrupt: function (e, t) {
                for (var n = this.tryEntries.length - 1; n >= 0; --n) {
                  var o = this.tryEntries[n]
                  if (
                    o.tryLoc <= this.prev &&
                    r.call(o, 'finallyLoc') &&
                    this.prev < o.finallyLoc
                  ) {
                    var i = o
                    break
                  }
                }
                i &&
                  ('break' === e || 'continue' === e) &&
                  i.tryLoc <= t &&
                  t <= i.finallyLoc &&
                  (i = null)
                var a = i ? i.completion : {}
                return (
                  (a.type = e),
                  (a.arg = t),
                  i
                    ? ((this.method = 'next'), (this.next = i.finallyLoc), g)
                    : this.complete(a)
                )
              },
              complete: function (e, t) {
                if ('throw' === e.type) throw e.arg
                return (
                  'break' === e.type || 'continue' === e.type
                    ? (this.next = e.arg)
                    : 'return' === e.type
                    ? ((this.rval = this.arg = e.arg),
                      (this.method = 'return'),
                      (this.next = 'end'))
                    : 'normal' === e.type && t && (this.next = t),
                  g
                )
              },
              finish: function (e) {
                for (var t = this.tryEntries.length - 1; t >= 0; --t) {
                  var n = this.tryEntries[t]
                  if (n.finallyLoc === e)
                    return this.complete(n.completion, n.afterLoc), I(n), g
                }
              },
              catch: function (e) {
                for (var t = this.tryEntries.length - 1; t >= 0; --t) {
                  var n = this.tryEntries[t]
                  if (n.tryLoc === e) {
                    var r = n.completion
                    if ('throw' === r.type) {
                      var o = r.arg
                      I(n)
                    }
                    return o
                  }
                }
                throw new Error('illegal catch attempt')
              },
              delegateYield: function (t, n, r) {
                return (
                  (this.delegate = {
                    iterator: T(t),
                    resultName: n,
                    nextLoc: r,
                  }),
                  'next' === this.method && (this.arg = e),
                  g
                )
              },
            }),
            t
          )
        }
        var s = u().mark(y),
          f = u().mark(b),
          p = u().mark(h),
          d = u().mark(g),
          m = u().mark(v)
        function y() {
          var e, t
          return u().wrap(function (n) {
            for (;;)
              switch ((n.prev = n.next)) {
                case 0:
                  return (
                    (n.next = 2), (0, i.RE)(a.uY.get, '/epg/list/0/2/aest/')
                  )
                case 2:
                  return (
                    (e = n.sent),
                    (t = o()(e.data.items, function (e) {
                      return e.programs
                    })),
                    (n.next = 6),
                    (0, i.gz)((0, c.rG)({ programs: t }))
                  )
                case 6:
                case 'end':
                  return n.stop()
              }
          }, s)
        }
        function b() {
          return u().wrap(function (e) {
            for (;;)
              switch ((e.prev = e.next)) {
                case 0:
                  if ('true' !== localStorage.getItem('inlineLiveVision')) {
                    e.next = 4
                    break
                  }
                  return (e.next = 4), (0, i.gz)((0, c.yG)())
                case 4:
                case 'end':
                  return e.stop()
              }
          }, f)
        }
        function h() {
          return u().wrap(function (e) {
            for (;;)
              switch ((e.prev = e.next)) {
                case 0:
                  localStorage.setItem('inlineLiveVision', !0)
                case 1:
                case 'end':
                  return e.stop()
              }
          }, p)
        }
        function g() {
          return u().wrap(function (e) {
            for (;;)
              switch ((e.prev = e.next)) {
                case 0:
                  localStorage.setItem('inlineLiveVision', !1)
                case 1:
                case 'end':
                  return e.stop()
              }
          }, d)
        }
        function v() {
          return u().wrap(function (e) {
            for (;;)
              switch ((e.prev = e.next)) {
                case 0:
                  return (e.next = 2), (0, i.rM)(y)
                case 2:
                  return (e.next = 4), (0, i.rM)(b)
                case 4:
                  return (e.next = 6), (0, i.ib)(c.yG.type, h)
                case 6:
                  return (e.next = 8), (0, i.ib)(c.Sk.type, g)
                case 8:
                case 'end':
                  return e.stop()
              }
          }, m)
        }
      },
      24737: (e, t, n) => {
        'use strict'
        n.d(t, { C: () => o, w: () => i })
        var r = n(1601),
          o = function (e) {
            var t
            return null === (t = e[r.u2]) || void 0 === t ? void 0 : t.programs
          },
          i = function (e) {
            var t
            return null === (t = e[r.u2]) || void 0 === t ? void 0 : t.onAir
          }
      },
      1601: (e, t, n) => {
        'use strict'
        n.d(t, {
          I6: () => s,
          Sk: () => c,
          rG: () => i,
          u2: () => u,
          wR: () => l,
          yG: () => a,
        })
        var r = (0, n(2655).oM)({
            name: 'live-vision',
            initialState: { programs: null, onAir: !1 },
            reducers: {
              updatePrograms: function (e, t) {
                var n = t.payload.programs
                e.programs = n
              },
              playLiveVision: function (e) {
                e.onAir = !0
              },
              stopLiveVision: function (e) {
                e.onAir = !1
              },
              toggleLiveVision: function (e) {
                e.onAir = !e.onAir
              },
            },
          }),
          o = r.actions,
          i = o.updatePrograms,
          a = o.playLiveVision,
          c = o.stopLiveVision,
          l = o.toggleLiveVision,
          u = r.name,
          s = r.reducer
      },
      20817: (e, t, n) => {
        'use strict'
        n.d(t, { hq: () => o })
        n(1024), n(30186)
        var r = n(13980),
          o = (n(62388), { '@media print': { display: 'none !important' } })
        r.PropTypes.node.isRequired, r.PropTypes.node.isRequired
      },
      53817: (e, t, n) => {
        'use strict'
        n(14629), n(25047), n(92556)
      },
      92556: (e, t, n) => {
        n.p = window.rdcWidgetsPath || ''
      },
      54249: (e, t, n) => {
        'use strict'
        n.r(t), n.d(t, { default: () => Xn }), n(53817)
        var r = n(1024),
          o = n.n(r),
          i = n(71570),
          a = n(13980),
          c = n.n(a),
          l = n(30186),
          u = n(15252),
          s = n(13295),
          f = n(40163),
          p = n(20817),
          d = (0, r.createContext)()
        d.displayName = 'HeaderConfig'
        var m = n(77450),
          y = n(81987)
        function b(e) {
          return (
            (b =
              'function' == typeof Symbol && 'symbol' == typeof Symbol.iterator
                ? function (e) {
                    return typeof e
                  }
                : function (e) {
                    return e &&
                      'function' == typeof Symbol &&
                      e.constructor === Symbol &&
                      e !== Symbol.prototype
                      ? 'symbol'
                      : typeof e
                  }),
            b(e)
          )
        }
        var h = ['icon', 'onClick', 'sx']
        function g() {
          return (
            (g = Object.assign
              ? Object.assign.bind()
              : function (e) {
                  for (var t = 1; t < arguments.length; t++) {
                    var n = arguments[t]
                    for (var r in n)
                      Object.prototype.hasOwnProperty.call(n, r) &&
                        (e[r] = n[r])
                  }
                  return e
                }),
            g.apply(this, arguments)
          )
        }
        function v(e, t) {
          var n = Object.keys(e)
          if (Object.getOwnPropertySymbols) {
            var r = Object.getOwnPropertySymbols(e)
            t &&
              (r = r.filter(function (t) {
                return Object.getOwnPropertyDescriptor(e, t).enumerable
              })),
              n.push.apply(n, r)
          }
          return n
        }
        function w(e) {
          for (var t = 1; t < arguments.length; t++) {
            var n = null != arguments[t] ? arguments[t] : {}
            t % 2
              ? v(Object(n), !0).forEach(function (t) {
                  var r, o, i, a
                  ;(r = e),
                    (o = t),
                    (i = n[t]),
                    (a = (function (e, t) {
                      if ('object' != b(e) || !e) return e
                      var n = e[Symbol.toPrimitive]
                      if (void 0 !== n) {
                        var r = n.call(e, 'string')
                        if ('object' != b(r)) return r
                        throw new TypeError(
                          '@@toPrimitive must return a primitive value.'
                        )
                      }
                      return String(e)
                    })(o)),
                    (o = 'symbol' == b(a) ? a : String(a)) in r
                      ? Object.defineProperty(r, o, {
                          value: i,
                          enumerable: !0,
                          configurable: !0,
                          writable: !0,
                        })
                      : (r[o] = i)
                })
              : Object.getOwnPropertyDescriptors
              ? Object.defineProperties(e, Object.getOwnPropertyDescriptors(n))
              : v(Object(n)).forEach(function (t) {
                  Object.defineProperty(
                    e,
                    t,
                    Object.getOwnPropertyDescriptor(n, t)
                  )
                })
          }
          return e
        }
        var x = function (e) {
          var t = e.icon,
            n = e.onClick,
            r = e.sx,
            i = (function (e, t) {
              if (null == e) return {}
              var n,
                r,
                o = (function (e, t) {
                  if (null == e) return {}
                  var n,
                    r,
                    o = {},
                    i = Object.keys(e)
                  for (r = 0; r < i.length; r++)
                    (n = i[r]), t.indexOf(n) >= 0 || (o[n] = e[n])
                  return o
                })(e, t)
              if (Object.getOwnPropertySymbols) {
                var i = Object.getOwnPropertySymbols(e)
                for (r = 0; r < i.length; r++)
                  (n = i[r]),
                    t.indexOf(n) >= 0 ||
                      (Object.prototype.propertyIsEnumerable.call(e, n) &&
                        (o[n] = e[n]))
              }
              return o
            })(e, h)
          return o().createElement(
            y.Z,
            g(
              {
                className: 'header__icon',
                variant: 'button.icon',
                sx: w(
                  {
                    color: 'grey-99',
                    fontSize: '21px',
                    transition: 'color 0.3s ease-in-out',
                    '&:hover': { color: 'white' },
                  },
                  r || {}
                ),
                onClick: n,
              },
              i
            ),
            o().createElement(m.Z, { type: t, inline: !0 })
          )
        }
        x.propTypes = {
          icon: a.PropTypes.string.isRequired,
          onClick: a.PropTypes.func,
          sx: a.PropTypes.object,
        }
        const E = x
        var O = n(18838)
        const S = function () {
          return o().createElement(
            l.kC,
            {
              className: 'rdc-logo',
              as: 'a',
              href: 'https://racing.com/',
              sx: {
                backgroundColor: 'primary',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'white',
                padding: ['8px', '', '', '10px'],
                width: '116px',
                cursor: 'pointer',
                mr: ['', '', '', '24px'],
                '&:hover, &:focus': { color: 'white' },
              },
            },
            o().createElement(O.Vd.Logo, {
              style: { width: '100%', height: '15px' },
            })
          )
        }
        var j = n(39577),
          k = n(92742),
          _ = n.n(k),
          P = n(352),
          C = n(24082),
          A = n(1576),
          I = n(98662),
          L = n(88306),
          T = n.n(L)
        function M(e, t) {
          ;(null == t || t > e.length) && (t = e.length)
          for (var n = 0, r = new Array(t); n < t; n++) r[n] = e[n]
          return r
        }
        var N = (0, n(2655).oM)({
            name: 'header',
            initialState: {
              searchSuggestion: null,
              notification: { lastUpdated: null, feeds: [] },
              megaMenu: { mobile: null, desktop: null },
            },
            reducers: {
              loadSearchSuggestion: function () {},
              storeSearchSuggestion: function (e, t) {
                var n = t.payload,
                  r = n.total,
                  o = n.items
                e.searchSuggestion = { total: r, items: o }
              },
              loadMegaMenu: function () {},
              storeMegaMenu: function (e, t) {
                var n = t.payload,
                  r = n.megaMenu,
                  o = n.device
                e.megaMenu[o] = r
              },
              loadNotification: function (e) {},
              mutateNotification: function (e) {},
              storeNotification: function (e, t) {
                var n,
                  r = t.payload,
                  o = r.feeds,
                  i = r.lastUpdated
                ;(e.notification.lastUpdated = i),
                  (e.notification.feeds =
                    (function (e) {
                      if (Array.isArray(e)) return M(e)
                    })((n = o.notifications.feeds)) ||
                    (function (e) {
                      if (
                        ('undefined' != typeof Symbol &&
                          null != e[Symbol.iterator]) ||
                        null != e['@@iterator']
                      )
                        return Array.from(e)
                    })(n) ||
                    (function (e, t) {
                      if (e) {
                        if ('string' == typeof e) return M(e, t)
                        var n = Object.prototype.toString.call(e).slice(8, -1)
                        return (
                          'Object' === n &&
                            e.constructor &&
                            (n = e.constructor.name),
                          'Map' === n || 'Set' === n
                            ? Array.from(e)
                            : 'Arguments' === n ||
                              /^(?:Ui|I)nt(?:8|16|32)(?:Clamped)?Array$/.test(n)
                            ? M(e, t)
                            : void 0
                        )
                      }
                    })(n) ||
                    (function () {
                      throw new TypeError(
                        'Invalid attempt to spread non-iterable instance.\nIn order to be iterable, non-array objects must have a [Symbol.iterator]() method.'
                      )
                    })())
              },
            },
          }),
          D = N.actions,
          F = D.loadSearchSuggestion,
          H = D.storeSearchSuggestion,
          z = D.loadMegaMenu,
          R = D.storeMegaMenu,
          U = D.loadNotification,
          Z = D.mutateNotification,
          q = D.storeNotification,
          B = N.name,
          V = N.reducer,
          W = function (e) {
            var t
            return null === (t = e[B]) || void 0 === t
              ? void 0
              : t.searchSuggestion
          },
          G = T()(function (e) {
            return function (t) {
              var n
              return null === (n = t[B]) || void 0 === n
                ? void 0
                : n.megaMenu[e]
            }
          }),
          Q = function (e) {
            var t
            return null === (t = e[B]) || void 0 === t ? void 0 : t.notification
          }
        function Y(e, t) {
          return (
            (function (e) {
              if (Array.isArray(e)) return e
            })(e) ||
            (function (e, t) {
              var n =
                null == e
                  ? null
                  : ('undefined' != typeof Symbol && e[Symbol.iterator]) ||
                    e['@@iterator']
              if (null != n) {
                var r,
                  o,
                  i,
                  a,
                  c = [],
                  l = !0,
                  u = !1
                try {
                  if (((i = (n = n.call(e)).next), 0 === t)) {
                    if (Object(n) !== n) return
                    l = !1
                  } else
                    for (
                      ;
                      !(l = (r = i.call(n)).done) &&
                      (c.push(r.value), c.length !== t);
                      l = !0
                    );
                } catch (e) {
                  ;(u = !0), (o = e)
                } finally {
                  try {
                    if (
                      !l &&
                      null != n.return &&
                      ((a = n.return()), Object(a) !== a)
                    )
                      return
                  } finally {
                    if (u) throw o
                  }
                }
                return c
              }
            })(e, t) ||
            (function (e, t) {
              if (e) {
                if ('string' == typeof e) return X(e, t)
                var n = Object.prototype.toString.call(e).slice(8, -1)
                return (
                  'Object' === n && e.constructor && (n = e.constructor.name),
                  'Map' === n || 'Set' === n
                    ? Array.from(e)
                    : 'Arguments' === n ||
                      /^(?:Ui|I)nt(?:8|16|32)(?:Clamped)?Array$/.test(n)
                    ? X(e, t)
                    : void 0
                )
              }
            })(e, t) ||
            (function () {
              throw new TypeError(
                'Invalid attempt to destructure non-iterable instance.\nIn order to be iterable, non-array objects must have a [Symbol.iterator]() method.'
              )
            })()
          )
        }
        function X(e, t) {
          ;(null == t || t > e.length) && (t = e.length)
          for (var n = 0, r = new Array(t); n < t; n++) r[n] = e[n]
          return r
        }
        const J = function () {
          var e = Y((0, r.useState)(!1), 2),
            t = e[0],
            n = e[1],
            i = Y((0, r.useState)(''), 2),
            a = i[0],
            c = i[1],
            u = (0, r.useRef)(null),
            s = (0, C.v9)(W),
            f = (0, r.useMemo)(
              function () {
                return Object.entries(
                  (null == s ? void 0 : s.items) || {}
                ).flatMap(function (e) {
                  var t = Y(e, 2)
                  return t[0], t[1]
                })
              },
              [s]
            ),
            p = Y((0, r.useState)(null), 2),
            d = p[0],
            b = p[1]
          ;(0, r.useEffect)(
            function () {
              b(null)
            },
            [a]
          ),
            (0, r.useEffect)(function () {
              var e = function () {
                n(!1)
              }
              return (
                document.addEventListener('click', e),
                function () {
                  return document.removeEventListener('click', e)
                }
              )
            }, [])
          var h = (0, r.useRef)(null),
            g = (0, I.fO)().dispatch
          return (
            (0, r.useEffect)(
              function () {
                return (
                  clearTimeout(h.current),
                  a.length > 2 &&
                    (h.current = setTimeout(function () {
                      g(F({ query: a }))
                    }, 500)),
                  function () {
                    clearTimeout(h.current)
                  }
                )
              },
              [a, g]
            ),
            o().createElement(
              l.xu,
              {
                className: 'search-bar',
                as: 'form',
                method: 'get',
                action: '/search',
                sx: { position: 'relative' },
                onClick: function (e) {
                  e.nativeEvent.stopImmediatePropagation(), e.stopPropagation()
                },
                onSubmit: function (e) {
                  var t
                  '' === _()(a) &&
                    (null === (t = u.current) || void 0 === t || t.focus(),
                    e.preventDefault())
                },
              },
              o().createElement(E, {
                type: 'submit',
                icon: 'search',
                color: t ? 'white' : 'grey-99',
                onClick: function (e) {
                  var r
                  t ||
                    (null === (r = u.current) || void 0 === r || r.focus(),
                    n(!0),
                    e.preventDefault())
                },
              }),
              o().createElement(P.II, {
                ref: u,
                name: 'q',
                autoComplete: 'off',
                className: 'search__input',
                sx: {
                  position: 'absolute',
                  right: '100%',
                  top: '0',
                  bottom: '0',
                  px: t ? '8px' : '0',
                  width: t ? '320px' : '0',
                  opacity: t ? '1' : '0',
                  border: 'none',
                  backgroundColor: 'white',
                  transition: 'all 0.3s ease-out',
                  transitionDelay: !t && s ? '0.3s' : '0',
                  fontSize: 'body',
                  color: 'text',
                  '&:focus': { outline: 'none' },
                },
                placeholder: 'Search...',
                onChange: function (e) {
                  return c(e.target.value)
                },
                onKeyDown: function (e) {
                  var t = f.indexOf(d)
                  switch (e.key) {
                    case 'ArrowUp':
                      ;-1 === t ? (t = f.length - 1) : (t -= 1),
                        e.preventDefault()
                      break
                    case 'ArrowDown':
                      ;-1 === t ? (t = 0) : (t += 1), e.preventDefault()
                      break
                    case 'Enter':
                      if (-1 !== t)
                        return (
                          (window.location.href = d.ContentUrl),
                          void e.preventDefault()
                        )
                      break
                    default:
                      return
                  }
                  b(f[t])
                },
                value: a,
              }),
              '' !== a &&
                o().createElement(
                  y.Z,
                  {
                    className: 'search__btn',
                    variant: 'button.icon',
                    sx: {
                      position: 'absolute',
                      right: 'calc(100% + 4px)',
                      top: '50%',
                      transform: 'translateY(-50%)',
                      opacity: t ? '1' : '0',
                    },
                    onClick: function () {
                      var e
                      null === (e = u.current) || void 0 === e || e.focus(),
                        c('')
                    },
                  },
                  o().createElement(
                    l.xu,
                    { as: 'span', sx: { color: 'grey-66', fontSize: '18px' } },
                    o().createElement(m.Z, { type: 'close-circle', inline: !0 })
                  )
                ),
              o().createElement(
                l.xu,
                {
                  className: 'search__suggestion',
                  sx: {
                    position: 'absolute',
                    right: '100%',
                    top: '100%',
                    width: '320px',
                    zIndex: 99,
                  },
                },
                o().createElement(A.Z, {
                  suggestion: s,
                  selectedSuggestion: d,
                  showSuggestion: t,
                  query: _()(a),
                  onItemClick: function (e, t) {
                    window.location.href = t.ContentUrl
                  },
                  onViewAll: function () {
                    window.location.href = '/search?q='.concat(a)
                  },
                })
              )
            )
          )
        }
        var K = n(70887),
          $ = n(92086),
          ee = n(99032)
        function te(e, t) {
          return (
            (function (e) {
              if (Array.isArray(e)) return e
            })(e) ||
            (function (e, t) {
              var n =
                null == e
                  ? null
                  : ('undefined' != typeof Symbol && e[Symbol.iterator]) ||
                    e['@@iterator']
              if (null != n) {
                var r,
                  o,
                  i,
                  a,
                  c = [],
                  l = !0,
                  u = !1
                try {
                  if (((i = (n = n.call(e)).next), 0 === t)) {
                    if (Object(n) !== n) return
                    l = !1
                  } else
                    for (
                      ;
                      !(l = (r = i.call(n)).done) &&
                      (c.push(r.value), c.length !== t);
                      l = !0
                    );
                } catch (e) {
                  ;(u = !0), (o = e)
                } finally {
                  try {
                    if (
                      !l &&
                      null != n.return &&
                      ((a = n.return()), Object(a) !== a)
                    )
                      return
                  } finally {
                    if (u) throw o
                  }
                }
                return c
              }
            })(e, t) ||
            (function (e, t) {
              if (e) {
                if ('string' == typeof e) return ne(e, t)
                var n = Object.prototype.toString.call(e).slice(8, -1)
                return (
                  'Object' === n && e.constructor && (n = e.constructor.name),
                  'Map' === n || 'Set' === n
                    ? Array.from(e)
                    : 'Arguments' === n ||
                      /^(?:Ui|I)nt(?:8|16|32)(?:Clamped)?Array$/.test(n)
                    ? ne(e, t)
                    : void 0
                )
              }
            })(e, t) ||
            (function () {
              throw new TypeError(
                'Invalid attempt to destructure non-iterable instance.\nIn order to be iterable, non-array objects must have a [Symbol.iterator]() method.'
              )
            })()
          )
        }
        function ne(e, t) {
          ;(null == t || t > e.length) && (t = e.length)
          for (var n = 0, r = new Array(t); n < t; n++) r[n] = e[n]
          return r
        }
        var re = function () {
            var e,
              t = (0, f.Ln)() ? 'desktop' : 'mobile',
              n = (0, C.v9)(G(t)),
              o = (0, r.useContext)(d),
              i =
                null ==
                (null == o || null === (e = o.megaMenuData) || void 0 === e
                  ? void 0
                  : e.megaMenu),
              a = (0, C.I0)()
            return (
              (0, r.useEffect)(
                function () {
                  !n &&
                    i &&
                    a(
                      z({
                        app: (null == o ? void 0 : o.app) || 'tipping',
                        device: t,
                      })
                    )
                },
                [t, a, o, n, i]
              ),
              n
            )
          },
          oe = function () {
            var e = (0, C.I0)(),
              t = te((0, r.useState)(!1), 2),
              n = t[0],
              o = t[1],
              i = te((0, r.useState)(!1), 2),
              a = i[0],
              c = i[1]
            ;(0, r.useEffect)(function () {
              var e = function () {
                o(!1), c(!1)
              }
              return (
                document.addEventListener('click', e),
                function () {
                  return document.removeEventListener('click', e)
                }
              )
            }, [])
            var l = (0, r.useRef)(null)
            return (
              (0, r.useEffect)(function () {
                return function () {
                  l.current && clearTimeout(l.current)
                }
              }, []),
              {
                shouldShowDropdown: n,
                showDropdownHandle: (0, r.useCallback)(function (e) {
                  e.clickToHideDropdown && c(!0), clearTimeout(l.current), o(!0)
                }, []),
                hideDropdownHandle: (0, r.useCallback)(
                  function (t) {
                    a ||
                      (clearTimeout(l.current),
                      (l.current = setTimeout(function () {
                        o(!1), 'string' == typeof t && t && e(U(t))
                      }, 200)))
                  },
                  [e, a]
                ),
              }
            )
          },
          ie = function () {
            var e = (0, C.v9)(Q),
              t = (0, $.J)(
                (0, ee.nI)('Auth0NeedAccessToken', !1),
                (0, ee.nI)('Auth0FeatureToggle', !1),
                {
                  legacyLoginWithPopupUrl: (0, ee.nI)('Auth0LoginEndpoint', ''),
                  legacyLoginWithRedirectUrl: (0, ee.nI)(
                    'Auth0LoginEndpoint',
                    ''
                  ),
                  legacyLogoutUrl: (0, ee.nI)('Auth0LogoutEndpoint', ''),
                }
              ).user
            return (0, r.useMemo)(
              function () {
                var n = e.lastUpdated,
                  r = ''
                t && (r = null == t ? void 0 : t.firstName)
                var o = e.feeds.filter(function (e) {
                    return 0 == !!e.lastRead
                  }),
                  i = e.feeds.filter(function (e) {
                    return 1 == !!e.lastRead
                  })
                return {
                  userId: (null == t ? void 0 : t.email) || '',
                  firstName: r,
                  lastUpdated: n,
                  newFeeds: o,
                  oldFeeds: i,
                  unread: o.length,
                }
              },
              [e, t]
            )
          },
          ae = function (e) {
            var t = e.active
            return o().createElement(l.xu, {
              sx: {
                position: 'absolute',
                right: '50%',
                bottom: '0',
                transform: 'translateX(50%)',
                border: t ? '10px solid transparent' : '0 solid transparent',
                borderBottomColor: 'white',
                transition: 'border ease-out 0.3s',
                pointerEvents: 'none',
              },
            })
          }
        ae.propTypes = { active: c().bool }
        const ce = ae
        var le = ['label']
        function ue() {
          return (
            (ue = Object.assign
              ? Object.assign.bind()
              : function (e) {
                  for (var t = 1; t < arguments.length; t++) {
                    var n = arguments[t]
                    for (var r in n)
                      Object.prototype.hasOwnProperty.call(n, r) &&
                        (e[r] = n[r])
                  }
                  return e
                }),
            ue.apply(this, arguments)
          )
        }
        var se = function (e) {
          var t = e.label,
            n = (function (e, t) {
              if (null == e) return {}
              var n,
                r,
                o = (function (e, t) {
                  if (null == e) return {}
                  var n,
                    r,
                    o = {},
                    i = Object.keys(e)
                  for (r = 0; r < i.length; r++)
                    (n = i[r]), t.indexOf(n) >= 0 || (o[n] = e[n])
                  return o
                })(e, t)
              if (Object.getOwnPropertySymbols) {
                var i = Object.getOwnPropertySymbols(e)
                for (r = 0; r < i.length; r++)
                  (n = i[r]),
                    t.indexOf(n) >= 0 ||
                      (Object.prototype.propertyIsEnumerable.call(e, n) &&
                        (o[n] = e[n]))
              }
              return o
            })(e, le)
          return o().createElement(
            l.xu,
            ue(
              {
                as: 'a',
                mb: 'md',
                sx: {
                  display: 'block',
                  textDecoration: 'none',
                  color: 'black',
                  transition: 'color ease-out 0.3s',
                  '&:hover': { color: 'primary' },
                },
              },
              n
            ),
            t
          )
        }
        se.propTypes = { label: c().string.isRequired }
        var fe = function (e) {
          var t = ue(
              {},
              ((function (e) {
                if (null == e) throw new TypeError('Cannot destructure ' + e)
              })(e),
              e)
            ),
            n = (0, r.useContext)(d),
            i = n.profileLinkLabel,
            a = n.profileLinkUrl,
            c = n.authentication,
            u = c.loginWithRedirect,
            s = c.loginWithPopup,
            f = c.logout,
            p = c.isAuthenticated,
            b = c.isLoading,
            h = n.isRacingPhotos,
            g = n.user,
            v = oe(),
            w = v.shouldShowDropdown,
            x = v.showDropdownHandle,
            E = v.hideDropdownHandle
          return o().createElement(
            l.kC,
            ue(
              {
                sx: {
                  position: 'relative',
                  backgroundColor: h ? '#006da6' : 'grey-33',
                  height: '45px',
                  alignItems: 'center',
                },
              },
              t,
              {
                onClick: function (e) {
                  e.nativeEvent.stopImmediatePropagation(), e.stopPropagation()
                },
                onMouseEnter: x,
                onMouseLeave: E,
              }
            ),
            o().createElement(
              y.Z,
              {
                sx: {
                  fontSize: '14px',
                  padding: '6px 10px 6px 8px',
                  color: 'white',
                  '&:hover, &:focus': { borderColor: 'white', color: 'white' },
                  display: 'flex',
                  alignItems: 'center',
                },
                onClick: function () {
                  p
                    ? x({ clickToHideDropdown: !0 })
                    : !b && u
                    ? u()
                    : !b && s
                    ? s()
                    : console.warn('LoginEndpoint not found.')
                },
              },
              o().createElement(
                l.xu,
                {
                  as: 'span',
                  mr: 'md',
                  sx: { fontSize: '18px', flex: '0 0 auto' },
                },
                o().createElement(m.Z, { inline: !0, type: 'user' })
              ),
              p && g
                ? o().createElement(
                    o().Fragment,
                    null,
                    o().createElement(
                      l.xv,
                      {
                        sx: {
                          flex: '1 1 auto',
                          textAlign: 'left',
                          fontSize: '14px',
                          fontWeight: 'bold',
                        },
                      },
                      (0, K.d)(g.name, { shorten: 8 })
                    ),
                    o().createElement(
                      l.xu,
                      { ml: 'md', sx: { fontSize: '12px', flex: '0 0 auto' } },
                      o().createElement(m.Z, {
                        inline: !0,
                        type: w ? 'up-chev' : 'down-chev',
                      })
                    )
                  )
                : o().createElement(l.xv, null, 'Racing+')
            ),
            p && g && o().createElement(ce, { active: w }),
            p &&
              g &&
              o().createElement(
                l.xu,
                {
                  sx: {
                    position: 'absolute',
                    width: '240px',
                    zIndex: -1,
                    right: 0,
                    bottom: '10px',
                    minHeight: '275px',
                    transform: w
                      ? 'translateY(100%) translateY(10px)'
                      : 'translateY(0)',
                    transition: 'transform ease-out 0.3s',
                    boxShadow: '0px 0px 5px 0px rgba(0,0,0,0.2)',
                    fontFamily: 'circular',
                    fontSize: '14px',
                    fontWeight: 'bold',
                    backgroundColor: 'white',
                    padding: '30px 20px',
                  },
                },
                o().createElement(
                  l.xu,
                  { sx: { color: 'grey-99', fontSize: '18px', mb: '24px' } },
                  (0, K.d)(g.name)
                ),
                o().createElement(
                  l.xu,
                  { sx: { color: 'grey-66' } },
                  o().createElement(se, {
                    icon: 'settings',
                    label: null != i ? i : 'My Preferences',
                    href: null != a ? a : '/plus/profile-management',
                    mb: 'lg',
                  }),
                  o().createElement(se, {
                    icon: 'blackbook',
                    label: 'My Blackbook',
                    href: '/plus/profile-centre#/blackbook',
                    mb: 'lg',
                  }),
                  o().createElement(se, {
                    icon: 'log-out',
                    label: 'Log Out',
                    onClick: function () {
                      return f({
                        logoutParams: { returnTo: window.location.origin },
                      })
                    },
                    mb: 'lg',
                  })
                )
              )
          )
        }
        fe.propTypes = {}
        const pe = fe
        var de = n(75506),
          me = n(12524),
          ye = n.n(me),
          be = n(24734),
          he = n(54951),
          ge = (0, he.fW)('Header'),
          ve = function (e) {
            ge('Mega Menu', 'click', e.label)
          },
          we = function (e) {
            ge('Mega Menu', 'addon', e.alt)
          },
          xe = n(2738)
        function Ee(e) {
          return (
            (Ee =
              'function' == typeof Symbol && 'symbol' == typeof Symbol.iterator
                ? function (e) {
                    return typeof e
                  }
                : function (e) {
                    return e &&
                      'function' == typeof Symbol &&
                      e.constructor === Symbol &&
                      e !== Symbol.prototype
                      ? 'symbol'
                      : typeof e
                  }),
            Ee(e)
          )
        }
        var Oe,
          Se = ['menu', 'active', 'activeLabel'],
          je = ['menu', 'link', 'activeLabel'],
          ke = ['col', 'sx']
        function _e() {
          return (
            (_e = Object.assign
              ? Object.assign.bind()
              : function (e) {
                  for (var t = 1; t < arguments.length; t++) {
                    var n = arguments[t]
                    for (var r in n)
                      Object.prototype.hasOwnProperty.call(n, r) &&
                        (e[r] = n[r])
                  }
                  return e
                }),
            _e.apply(this, arguments)
          )
        }
        function Pe(e, t) {
          var n = Object.keys(e)
          if (Object.getOwnPropertySymbols) {
            var r = Object.getOwnPropertySymbols(e)
            t &&
              (r = r.filter(function (t) {
                return Object.getOwnPropertyDescriptor(e, t).enumerable
              })),
              n.push.apply(n, r)
          }
          return n
        }
        function Ce(e) {
          for (var t = 1; t < arguments.length; t++) {
            var n = null != arguments[t] ? arguments[t] : {}
            t % 2
              ? Pe(Object(n), !0).forEach(function (t) {
                  var r, o, i, a
                  ;(r = e),
                    (o = t),
                    (i = n[t]),
                    (a = (function (e, t) {
                      if ('object' != Ee(e) || !e) return e
                      var n = e[Symbol.toPrimitive]
                      if (void 0 !== n) {
                        var r = n.call(e, 'string')
                        if ('object' != Ee(r)) return r
                        throw new TypeError(
                          '@@toPrimitive must return a primitive value.'
                        )
                      }
                      return String(e)
                    })(o)),
                    (o = 'symbol' == Ee(a) ? a : String(a)) in r
                      ? Object.defineProperty(r, o, {
                          value: i,
                          enumerable: !0,
                          configurable: !0,
                          writable: !0,
                        })
                      : (r[o] = i)
                })
              : Object.getOwnPropertyDescriptors
              ? Object.defineProperties(e, Object.getOwnPropertyDescriptors(n))
              : Pe(Object(n)).forEach(function (t) {
                  Object.defineProperty(
                    e,
                    t,
                    Object.getOwnPropertyDescriptor(n, t)
                  )
                })
          }
          return e
        }
        function Ae(e, t) {
          if (null == e) return {}
          var n,
            r,
            o = (function (e, t) {
              if (null == e) return {}
              var n,
                r,
                o = {},
                i = Object.keys(e)
              for (r = 0; r < i.length; r++)
                (n = i[r]), t.indexOf(n) >= 0 || (o[n] = e[n])
              return o
            })(e, t)
          if (Object.getOwnPropertySymbols) {
            var i = Object.getOwnPropertySymbols(e)
            for (r = 0; r < i.length; r++)
              (n = i[r]),
                t.indexOf(n) >= 0 ||
                  (Object.prototype.propertyIsEnumerable.call(e, n) &&
                    (o[n] = e[n]))
          }
          return o
        }
        function Ie(e, t) {
          ;(null == t || t > e.length) && (t = e.length)
          for (var n = 0, r = new Array(t); n < t; n++) r[n] = e[n]
          return r
        }
        var Le = function () {
          var e,
            t,
            i,
            a,
            c = (0, r.useContext)(d),
            u =
              null !== (e = re()) && void 0 !== e
                ? e
                : null == c || null === (t = c.megaMenuData) || void 0 === t
                ? void 0
                : t.megaMenu,
            s =
              ((i = (0, r.useState)(null)),
              (a = 2),
              (function (e) {
                if (Array.isArray(e)) return e
              })(i) ||
                (function (e, t) {
                  var n =
                    null == e
                      ? null
                      : ('undefined' != typeof Symbol && e[Symbol.iterator]) ||
                        e['@@iterator']
                  if (null != n) {
                    var r,
                      o,
                      i,
                      a,
                      c = [],
                      l = !0,
                      u = !1
                    try {
                      if (((i = (n = n.call(e)).next), 0 === t)) {
                        if (Object(n) !== n) return
                        l = !1
                      } else
                        for (
                          ;
                          !(l = (r = i.call(n)).done) &&
                          (c.push(r.value), c.length !== t);
                          l = !0
                        );
                    } catch (e) {
                      ;(u = !0), (o = e)
                    } finally {
                      try {
                        if (
                          !l &&
                          null != n.return &&
                          ((a = n.return()), Object(a) !== a)
                        )
                          return
                      } finally {
                        if (u) throw o
                      }
                    }
                    return c
                  }
                })(i, a) ||
                (function (e, t) {
                  if (e) {
                    if ('string' == typeof e) return Ie(e, t)
                    var n = Object.prototype.toString.call(e).slice(8, -1)
                    return (
                      'Object' === n &&
                        e.constructor &&
                        (n = e.constructor.name),
                      'Map' === n || 'Set' === n
                        ? Array.from(e)
                        : 'Arguments' === n ||
                          /^(?:Ui|I)nt(?:8|16|32)(?:Clamped)?Array$/.test(n)
                        ? Ie(e, t)
                        : void 0
                    )
                  }
                })(i, a) ||
                (function () {
                  throw new TypeError(
                    'Invalid attempt to destructure non-iterable instance.\nIn order to be iterable, non-array objects must have a [Symbol.iterator]() method.'
                  )
                })()),
            f = s[0],
            p = s[1],
            m = (0, r.useRef)(null)
          return o().createElement(
            l.kC,
            null,
            null == u
              ? void 0
              : u.map(function (e) {
                  return 'MenuLink' === e.type
                    ? o().createElement(ze, {
                        menu: e,
                        link: e.link,
                        activeLabel: f,
                        key: e.id,
                        onMouseEnter: function () {
                          clearTimeout(m.current), p(e.label)
                        },
                        onMouseLeave: function () {
                          clearTimeout(m.current),
                            (m.current = setTimeout(function () {
                              n.g.__debug_mega_menu__, p(null)
                            }, 100))
                        },
                      })
                    : o().createElement(Fe, {
                        menu: e,
                        active: f === e.label,
                        activeLabel: f,
                        key: e.id,
                        onMouseEnter: function () {
                          clearTimeout(m.current), p(e.label)
                        },
                        onMouseLeave: function () {
                          clearTimeout(m.current),
                            (m.current = setTimeout(function () {
                              n.g.__debug_mega_menu__, p(null)
                            }, 100))
                        },
                      })
                })
          )
        }
        Le.propTypes = {}
        const Te = Le
        var Me,
          Ne,
          De = (0, de.F4)(
            Oe ||
              ((Me = [
                '\n    0% {\n      opacity: 0;\n      transform: translateY(-50px);\n    }\n    100% {\n      opacity: 1;\n      transform: translateY(0%);\n    }\n  ',
              ]),
              Ne || (Ne = Me.slice(0)),
              (Oe = Object.freeze(
                Object.defineProperties(Me, {
                  raw: { value: Object.freeze(Ne) },
                })
              )))
          )
        function Fe(e) {
          var t = e.menu,
            n = e.active,
            r = e.activeLabel,
            i = Ae(e, Se)
          return o().createElement(
            l.xu,
            { sx: { pr: '24px' } },
            o().createElement(
              l.kC,
              _e(
                {
                  sx: {
                    position: 'relative',
                    height: '45px',
                    alignItems: 'center',
                    transition: 'color ease-out 0.3s',
                    color: r && r !== t.label ? 'grey-99' : 'white',
                    fontFamily: 'circular',
                    fontWeight: 'bold',
                  },
                },
                i
              ),
              o().createElement(
                l.xv,
                { sx: { fontSize: '16px', cursor: 'pointer' } },
                'more' === t.type
                  ? o().createElement(O.Vd.MoreDots, {
                      width: '32px',
                      height: '32px',
                    })
                  : t.label || 'Menu'
              ),
              o().createElement(ce, { active: n }),
              o().createElement(
                l.kC,
                {
                  alignItems: 'stretch',
                  sx: {
                    position: 'absolute',
                    minWidth: '200px',
                    zIndex: n ? -1 : -2,
                    left: '-25px',
                    bottom: '10px',
                    minHeight: '245px',
                    transform: n
                      ? 'translateY(100%) translateY(10px)'
                      : 'translateY(0)',
                    transition: 'transform ease-out 0.3s',
                    boxShadow: '0px 0px 14px 0px rgba(10,16,23,0.14)',
                    fontFamily: 'circular',
                    fontSize: '14px',
                    fontWeight: 'bold',
                    backgroundColor: 'white',
                    padding: '15px 10px',
                  },
                },
                t.columns.map(function (e, t) {
                  return o().createElement(Re, {
                    col: e,
                    sx: Ce(
                      { flex: '0 0 auto' },
                      n
                        ? {
                            animation: ''.concat(De, ' 0.3s ease-out'),
                            animationFillMode: 'both',
                            animationDelay: ''.concat(0.2 + 0.05 * t, 's'),
                          }
                        : {
                            animation: ''.concat(be.U, ' 0.3s ease-in'),
                            animationFillMode: 'both',
                          }
                    ),
                    key: e.id,
                  })
                })
              )
            )
          )
        }
        Fe.propTypes = {
          menu: c().object.isRequired,
          active: c().bool,
          activeLabel: c().string,
        }
        var He = (0, xe.Tq)().isLoggedIn
        function ze(e) {
          var t = e.menu,
            n = e.link,
            r = e.activeLabel,
            i = Ae(e, je)
          return o().createElement(
            l.xu,
            { sx: { pr: '24px' } },
            o().createElement(
              l.kC,
              _e(
                {
                  sx: {
                    position: 'relative',
                    height: '45px',
                    alignItems: 'center',
                    transition: 'color ease-out 0.3s',
                    color: r && r !== t.label ? 'grey-99' : 'white',
                    '&:hover': { color: 'white' },
                    fontFamily: 'circular',
                    fontWeight: 'bold',
                  },
                },
                i
              ),
              o().createElement(
                l.xv,
                {
                  as: 'a',
                  href:
                    n.checkLoggedIn && !He
                      ? '/plus?forceredirect=true&ref=' +
                        encodeURIComponent(n.link.replace(/^.*\/\/[^/]+/, ''))
                      : n.link,
                  target: n.target,
                  onClick: function () {
                    return ve(n)
                  },
                  sx: {
                    fontSize: '16px',
                    cursor: 'pointer',
                    textDecoration: 'none',
                    transition: 'color ease-out 0.3s',
                    color: r && r !== t.label ? 'grey-99' : 'white',
                    '&:hover': { color: 'white' },
                    '&:focus': {
                      color: r && r !== t.label ? 'grey-99' : 'white',
                    },
                  },
                },
                t.label || 'MenuLink',
                n.external &&
                  o().createElement(
                    l.xu,
                    { as: 'span', sx: { ml: 'sm', fontSize: '12px' } },
                    o().createElement(m.Z, {
                      type: 'external-link',
                      inline: !0,
                    })
                  )
              )
            )
          )
        }
        function Re(e) {
          var t = e.col,
            n = e.sx,
            r = void 0 === n ? {} : n,
            i = Ae(e, ke)
          return o().createElement(
            l.kC,
            _e(
              {
                className: ye()(
                  'rdc-header__menu-col',
                  t.type && 'rdc-header__menu-col--'.concat(t.type)
                ),
                sx: Ce(
                  Ce(
                    { minWidth: '200px', color: 'grey-33', padding: '20px' },
                    'contained' === t.type
                      ? {
                          backgroundColor: 'grey-f7',
                          minHeight: '250px',
                          '.rdc-header__menu-col--contained + &': { ml: 'lg' },
                        }
                      : {}
                  ),
                  r
                ),
              },
              i
            ),
            o().createElement(
              l.xu,
              { sx: { flex: '0 0 auto' } },
              'contained' === t.type &&
                o().createElement(
                  l.xv,
                  {
                    as: 'h3',
                    sx: {
                      whiteSpace: 'nowrap',
                      fontFamily: 'circular',
                      fontWeight: 'bold',
                      fontSize: '18px',
                      color: 'grey-99',
                      mb: '6px',
                    },
                  },
                  t.heading
                ),
              o().createElement(
                l.kC,
                { alignItems: 'flex-start' },
                t.columns.map(function (e) {
                  return o().createElement(
                    l.xu,
                    {
                      sx: { flex: '0 0 auto', '& + &': { ml: '24px' } },
                      key: e.id,
                    },
                    e.links.map(function (e) {
                      switch (e.type) {
                        case 'separator':
                          return o().createElement(l.xu, {
                            key: e.id,
                            sx: { height: '33px' },
                          })
                        case 'image':
                          return o().createElement(
                            l.xu,
                            {
                              key: e.id,
                              as: 'a',
                              href: e.link,
                              onClick: function () {
                                return ve(e)
                              },
                              sx: {
                                display: 'block',
                                width: '120px',
                                mb: 'md',
                                cursor: 'pointer',
                              },
                            },
                            o().createElement(l.Ee, {
                              sx: {
                                display: 'block',
                                width: '100%',
                                height: 'auto',
                              },
                              src: e.image,
                              alt: e.label,
                            })
                          )
                        default:
                          return o().createElement(
                            l.xv,
                            {
                              key: e.id,
                              as: 'a',
                              href: e.link,
                              target: e.target,
                              onClick: function () {
                                return ve(e)
                              },
                              sx: {
                                display: 'block',
                                whiteSpace: 'nowrap',
                                fontSize: '14px',
                                lineHeight: '33px',
                                textDecoration: 'none',
                                transition: 'color ease-out 0.2s',
                                cursor: 'pointer',
                                color: 'grey-33',
                                '&:hover, &:focus': { color: 'primary' },
                              },
                            },
                            e.label,
                            e.external &&
                              o().createElement(
                                l.xu,
                                {
                                  as: 'span',
                                  sx: { ml: 'sm', fontSize: '12px' },
                                },
                                o().createElement(m.Z, {
                                  type: 'external-link',
                                  inline: !0,
                                })
                              ),
                            e.badge &&
                              o().createElement(
                                l.xv,
                                {
                                  as: 'span',
                                  sx: {
                                    display: 'inline-block',
                                    color: 'white',
                                    backgroundColor: e.badge.color,
                                    ml: 'sm',
                                    px: 'sm',
                                    fontSize: '10px',
                                    fontWeight: 'bold',
                                    lineHeight: '14px',
                                    verticalAlign: 'text-bottom',
                                    textTransform: 'uppercase',
                                  },
                                },
                                e.badge.label
                              )
                          )
                      }
                    })
                  )
                })
              )
            ),
            t.addOn &&
              o().createElement(
                l.xu,
                { sx: { flex: '0 0 auto', ml: '24px' } },
                'image' === t.addOn.type &&
                  o().createElement(
                    l.xu,
                    {
                      as: 'a',
                      href: t.addOn.link,
                      target: t.addOn.target || '_blank',
                      onClick: function () {
                        return we(t.addOn)
                      },
                      sx: {
                        display: 'block',
                        width: '300px',
                        textDecoration: 'none',
                      },
                    },
                    o().createElement(l.Ee, {
                      alt: t.addOn.alt,
                      src: t.addOn.src,
                      sx: {
                        display: 'block',
                        width: '300px',
                        height: 'auto',
                        backgroundColor: 'offWhite',
                        transition: 'opacity 0.3s ease-out',
                        '&:hover, &:focus': { opacity: 0.85 },
                      },
                    })
                  )
              )
          )
        }
        ;(ze.propTypes = {
          menu: c().object.isRequired,
          link: c().object.isRequired,
          activeLabel: c().string,
        }),
          (Re.propTypes = { col: c().object.isRequired, sx: c().object })
        var Ue = n(46062),
          Ze = n.n(Ue),
          qe = n(36921),
          Be = {
            injectType: 'singletonStyleTag',
            insert: function (e) {
              var t = document.querySelector('head'),
                n = document.querySelector('#rdc-tailwind-css'),
                r = window._lastElementInsertedByStyleLoader
              r
                ? r.nextSibling
                  ? t.insertBefore(e, r.nextSibling)
                  : t.appendChild(e)
                : t.insertBefore(e, n),
                (window._lastElementInsertedByStyleLoader = e)
            },
            singleton: !0,
          }
        Ze()(qe.Z, Be)
        const Ve = qe.Z.locals || {}
        var We = n(78667),
          Ge = n(12647),
          Qe = n(83048),
          Ye = n(65016),
          Xe = n(21604),
          Je = n(25301),
          Ke = {
            injectType: 'singletonStyleTag',
            insert: function (e) {
              var t = document.querySelector('head'),
                n = document.querySelector('#rdc-tailwind-css'),
                r = window._lastElementInsertedByStyleLoader
              r
                ? r.nextSibling
                  ? t.insertBefore(e, r.nextSibling)
                  : t.appendChild(e)
                : t.insertBefore(e, n),
                (window._lastElementInsertedByStyleLoader = e)
            },
            singleton: !0,
          }
        Ze()(Je.Z, Ke)
        const $e = Je.Z.locals || {}
        var et = n(94132)
        function tt(e) {
          return (
            (tt =
              'function' == typeof Symbol && 'symbol' == typeof Symbol.iterator
                ? function (e) {
                    return typeof e
                  }
                : function (e) {
                    return e &&
                      'function' == typeof Symbol &&
                      e.constructor === Symbol &&
                      e !== Symbol.prototype
                      ? 'symbol'
                      : typeof e
                  }),
            tt(e)
          )
        }
        function nt(e, t, n) {
          var r
          return (
            (r = (function (e, t) {
              if ('object' != tt(e) || !e) return e
              var n = e[Symbol.toPrimitive]
              if (void 0 !== n) {
                var r = n.call(e, 'string')
                if ('object' != tt(r)) return r
                throw new TypeError(
                  '@@toPrimitive must return a primitive value.'
                )
              }
              return String(e)
            })(t)),
            (t = 'symbol' == tt(r) ? r : String(r)) in e
              ? Object.defineProperty(e, t, {
                  value: n,
                  enumerable: !0,
                  configurable: !0,
                  writable: !0,
                })
              : (e[t] = n),
            e
          )
        }
        function rt(e, t) {
          ;(null == t || t > e.length) && (t = e.length)
          for (var n = 0, r = new Array(t); n < t; n++) r[n] = e[n]
          return r
        }
        var ot = function (e) {
          var t,
            n,
            i = e.feed,
            a = e.isNew,
            c =
              ((t = (0, r.useState)(!1)),
              (n = 2),
              (function (e) {
                if (Array.isArray(e)) return e
              })(t) ||
                (function (e, t) {
                  var n =
                    null == e
                      ? null
                      : ('undefined' != typeof Symbol && e[Symbol.iterator]) ||
                        e['@@iterator']
                  if (null != n) {
                    var r,
                      o,
                      i,
                      a,
                      c = [],
                      l = !0,
                      u = !1
                    try {
                      if (((i = (n = n.call(e)).next), 0 === t)) {
                        if (Object(n) !== n) return
                        l = !1
                      } else
                        for (
                          ;
                          !(l = (r = i.call(n)).done) &&
                          (c.push(r.value), c.length !== t);
                          l = !0
                        );
                    } catch (e) {
                      ;(u = !0), (o = e)
                    } finally {
                      try {
                        if (
                          !l &&
                          null != n.return &&
                          ((a = n.return()), Object(a) !== a)
                        )
                          return
                      } finally {
                        if (u) throw o
                      }
                    }
                    return c
                  }
                })(t, n) ||
                (function (e, t) {
                  if (e) {
                    if ('string' == typeof e) return rt(e, t)
                    var n = Object.prototype.toString.call(e).slice(8, -1)
                    return (
                      'Object' === n &&
                        e.constructor &&
                        (n = e.constructor.name),
                      'Map' === n || 'Set' === n
                        ? Array.from(e)
                        : 'Arguments' === n ||
                          /^(?:Ui|I)nt(?:8|16|32)(?:Clamped)?Array$/.test(n)
                        ? rt(e, t)
                        : void 0
                    )
                  }
                })(t, n) ||
                (function () {
                  throw new TypeError(
                    'Invalid attempt to destructure non-iterable instance.\nIn order to be iterable, non-array objects must have a [Symbol.iterator]() method.'
                  )
                })()),
            l = c[0],
            u = c[1],
            s = (0, Xe.e7)(i.avatar)
          return o().createElement(
            'div',
            {
              className: ye()(
                $e['rdc-notification-feed-item'],
                nt(
                  nt({}, $e['rdc-notification-feed-item--new'], a),
                  $e['rdc-notification-feed-item--old'],
                  !a
                )
              ),
            },
            o().createElement(
              'div',
              { className: $e['rdc-notification-feed-item__avatar'] },
              o().createElement('img', {
                style: { maxWidth: '100%' },
                src: s,
                alt: 'avatar',
              })
            ),
            o().createElement(
              'div',
              { className: $e['rdc-notification-feed-item__detail'] },
              o().createElement(
                'a',
                {
                  className: ye()(
                    $e['rdc-notification-feed-item__title'],
                    nt({}, $e['click-disabled'], l)
                  ),
                  onClick: function () {
                    u(!0),
                      (0, he.fW)('Notification', 'Click', i.link),
                      (0, et.Bj)('notificationClicked', i).then(function () {
                        u(!1), (window.location.href = i.link)
                      })
                  },
                },
                o().createElement('span', {
                  dangerouslySetInnerHTML: { __html: i.message },
                })
              ),
              o().createElement(
                'div',
                { className: $e['rdc-notification-feed-item__datetime'] },
                (function (e) {
                  var t = Number.isNaN(new Date(e).getMonth())
                    ? e.replace(' ', 'T')
                    : e
                  if (Number.isNaN(new Date(t).getMonth())) return ''
                  var n = new Date(),
                    r = new Date(t),
                    o = (0, Ge.Z)(n, r)
                  return o < 1
                    ? 'Just now'
                    : o < 60
                    ? ''.concat(o, ' minutes ago')
                    : (0, Ye.Z)(
                        r,
                        (0, Qe.Z)(r) ? "h:mmaaaaa'm" : 'd MMMM, yyyy'
                      )
                })(i.timestamp)
              )
            )
          )
        }
        ot.propTypes = { feed: c().object, isNew: c().bool }
        const it = ot
        function at(e) {
          return (
            (at =
              'function' == typeof Symbol && 'symbol' == typeof Symbol.iterator
                ? function (e) {
                    return typeof e
                  }
                : function (e) {
                    return e &&
                      'function' == typeof Symbol &&
                      e.constructor === Symbol &&
                      e !== Symbol.prototype
                      ? 'symbol'
                      : typeof e
                  }),
            at(e)
          )
        }
        function ct(e, t) {
          var n = Object.keys(e)
          if (Object.getOwnPropertySymbols) {
            var r = Object.getOwnPropertySymbols(e)
            t &&
              (r = r.filter(function (t) {
                return Object.getOwnPropertyDescriptor(e, t).enumerable
              })),
              n.push.apply(n, r)
          }
          return n
        }
        function lt(e) {
          for (var t = 1; t < arguments.length; t++) {
            var n = null != arguments[t] ? arguments[t] : {}
            t % 2
              ? ct(Object(n), !0).forEach(function (t) {
                  ut(e, t, n[t])
                })
              : Object.getOwnPropertyDescriptors
              ? Object.defineProperties(e, Object.getOwnPropertyDescriptors(n))
              : ct(Object(n)).forEach(function (t) {
                  Object.defineProperty(
                    e,
                    t,
                    Object.getOwnPropertyDescriptor(n, t)
                  )
                })
          }
          return e
        }
        function ut(e, t, n) {
          var r
          return (
            (r = (function (e, t) {
              if ('object' != at(e) || !e) return e
              var n = e[Symbol.toPrimitive]
              if (void 0 !== n) {
                var r = n.call(e, 'string')
                if ('object' != at(r)) return r
                throw new TypeError(
                  '@@toPrimitive must return a primitive value.'
                )
              }
              return String(e)
            })(t)),
            (t = 'symbol' == at(r) ? r : String(r)) in e
              ? Object.defineProperty(e, t, {
                  value: n,
                  enumerable: !0,
                  configurable: !0,
                  writable: !0,
                })
              : (e[t] = n),
            e
          )
        }
        function st() {
          return (
            (st = Object.assign
              ? Object.assign.bind()
              : function (e) {
                  for (var t = 1; t < arguments.length; t++) {
                    var n = arguments[t]
                    for (var r in n)
                      Object.prototype.hasOwnProperty.call(n, r) &&
                        (e[r] = n[r])
                  }
                  return e
                }),
            st.apply(this, arguments)
          )
        }
        var ft = function (e) {
          var t,
            n,
            i = st(
              {},
              ((function (e) {
                if (null == e) throw new TypeError('Cannot destructure ' + e)
              })(e),
              e)
            ),
            a = oe(),
            c = a.shouldShowDropdown,
            l = a.showDropdownHandle,
            u = a.hideDropdownHandle,
            s = ie(),
            f = (0, C.I0)(),
            p = (0, r.useRef)(),
            d = (0, We.n)('JockeyAvatar'),
            b = (0, We.n)('TrainerAvatar'),
            h = (0, We.n)('HorseAvatar'),
            g =
              0 ===
                (null == s || null === (t = s.newFeeds) || void 0 === t
                  ? void 0
                  : t.length) &&
              0 ===
                (null == s || null === (n = s.oldFeeds) || void 0 === n
                  ? void 0
                  : n.length),
            v = function (e) {
              var t = e.avatar,
                n = e.message
              return (
                e.avatar ||
                  (t =
                    'Jockey' === e.entityType
                      ? d
                      : 'Trainer' === e.entityType
                      ? b
                      : h),
                (n = (n = n.replace(
                  e.name,
                  '<b>'.concat(e.name, '</b>')
                )).replace(e.type, '<b>'.concat(e.type, '</b>'))),
                lt(lt({}, e), {}, { avatar: t, message: n })
              )
            }
          return (
            (0, r.useEffect)(
              function () {
                return s.newFeeds.length
                  ? (c &&
                      (e = setTimeout(function () {
                        ;(p.current = !0),
                          s.newFeeds.forEach(function (e) {
                            ;(0, et.Bj)('notificationViewed', e)
                          }),
                          (0, he.fW)('Notification', 'Open', null),
                          f(
                            Z({
                              timestamp: +new Date(),
                              newFeeds: s.newFeeds,
                              userId: s.userId,
                            })
                          )
                      }, 100)),
                    function () {
                      clearTimeout(e)
                    })
                  : (c && (0, he.fW)('Notification', 'Open', null),
                    function () {})
                var e
              },
              [f, c, s]
            ),
            s.lastUpdated
              ? o().createElement(
                  'div',
                  st(
                    {
                      className: ye()(
                        Ve['rdc-notification-feed'],
                        ut(
                          ut({}, Ve['rdc-notification-feed--active'], c && !g),
                          Ve['rdc-notification-feed--active-empty'],
                          c && g
                        ),
                        'mr-2'
                      ),
                      onClick: function (e) {
                        e.nativeEvent.stopImmediatePropagation(),
                          e.stopPropagation()
                      },
                      onMouseEnter: l,
                      onMouseLeave: function () {
                        return u(s.userId)
                      },
                    },
                    i
                  ),
                  o().createElement(E, {
                    icon: 'notification',
                    color: c ? 'white' : 'grey-99',
                    onClick: function (e) {
                      l({ clickToHideDropdown: !0 }), e.preventDefault()
                    },
                  }),
                  s.unread > 0 &&
                    o().createElement(
                      'span',
                      { className: Ve['rdc-notification-feed__unread'] },
                      s.unread
                    ),
                  o().createElement(ce, { active: c }),
                  o().createElement(
                    'div',
                    { className: ye()(Ve['rdc-notification-feed__wrap']) },
                    o().createElement(
                      'div',
                      { className: Ve['rdc-notification-feed__content'] },
                      o().createElement(
                        'div',
                        { className: Ve['rdc-notification-feed__title'] },
                        o().createElement('span', null, 'Notifications '),
                        o().createElement(
                          y.Z,
                          st(
                            {
                              className: 'header__icon',
                              variant: 'button.icon',
                              sx: {
                                color: 'grey-99',
                                fontSize: '17px',
                                transition: 'color 0.3s ease-in-out',
                                '&:hover': { color: 'grey-44' },
                              },
                              onClick: function () {
                                window.open(
                                  'https://www.racing.com/notifications'
                                )
                              },
                            },
                            i
                          ),
                          o().createElement(m.Z, {
                            type: 'information',
                            inline: !0,
                          })
                        )
                      ),
                      g &&
                        o().createElement(
                          'div',
                          { className: Ve['rdc-notification-feed__group'] },
                          o().createElement(
                            'h3',
                            {
                              className:
                                Ve['rdc-notification-feed__group-label'],
                            },
                            'Hi ',
                            s.firstName
                          ),
                          o().createElement(
                            'div',
                            {
                              className:
                                Ve['rdc-notification-feed__group-detail'],
                            },
                            'You currently have no Blackbook notifications. ',
                            o().createElement('br', null),
                            o().createElement('div', {
                              style: { height: '10px' },
                            }),
                            "Use the Racing.com mobile app to follow any horses, jockeys or trainers, and you'll see your list of nominations, acceptances, race reminders, and results notifications here."
                          )
                        ),
                      s.newFeeds.length > 0 &&
                        o().createElement(
                          'div',
                          { className: Ve['rdc-notification-feed__group'] },
                          o().createElement(
                            'h3',
                            {
                              className:
                                Ve['rdc-notification-feed__group-label'],
                            },
                            'New'
                          ),
                          s.newFeeds.map(function (e, t) {
                            return o().createElement(it, {
                              key: 'key-header-notification-'
                                .concat(e.entityCode, '-')
                                .concat(e.timestamp, '-')
                                .concat(t),
                              feed: v(e),
                              isNew: !0,
                            })
                          })
                        ),
                      s.oldFeeds.length > 0 &&
                        o().createElement(
                          'div',
                          { className: Ve['rdc-notification-feed__group'] },
                          s.newFeeds.length > 0 &&
                            o().createElement(
                              'h3',
                              {
                                className:
                                  Ve['rdc-notification-feed__group-label'],
                              },
                              'Old'
                            ),
                          s.oldFeeds.map(function (e, t) {
                            return o().createElement(it, {
                              key: 'key-header-notification-'
                                .concat(e.entityCode, '-')
                                .concat(e.timestamp, '-')
                                .concat(t),
                              feed: v(e),
                            })
                          })
                        )
                    )
                  )
                )
              : null
          )
        }
        ft.propTypes = {}
        const pt = ft,
          dt = function () {
            var e = (0, r.useContext)(d),
              t = null == e ? void 0 : e.hideHeaderIcons,
              n = null == e ? void 0 : e.isRacingPhotos,
              i = null == e ? void 0 : e.isLicensedPhotos
            return o().createElement(
              l.kC,
              {
                className: 'header--desktop',
                sx: {
                  height: '45px',
                  alignItems: 'center',
                  backgroundColor: n ? '#006da6' : 'grey-33',
                },
              },
              n
                ? o().createElement(
                    l.kC,
                    { sx: { marginRight: '20px', marginBottom: '10px' } },
                    o().createElement('img', {
                      src: j,
                      alt: 'RacingPhotosLogo',
                      width: 170,
                    })
                  )
                : o().createElement(S, null),
              o().createElement(
                l.xu,
                { className: 'header__padding', sx: { flex: '1 1 auto' } },
                o().createElement(Te, null)
              ),
              o().createElement(
                l.kC,
                {
                  className: 'header__actions',
                  sx: { flex: '0 0 auto', alignItems: 'center' },
                },
                !t &&
                  o().createElement(
                    o().Fragment,
                    null,
                    o().createElement(E, {
                      icon: 'play-icon',
                      mr: '4px',
                      onClick: function () {
                        var t
                        null == e ||
                          null === (t = e.toggleLiveVision) ||
                          void 0 === t ||
                          t.call(e)
                      },
                    }),
                    o().createElement(pt, null),
                    o().createElement(E, {
                      icon: 'radio',
                      mr: '4px',
                      onClick: function () {
                        var t
                        null == e ||
                          null === (t = e.trackEvent) ||
                          void 0 === t ||
                          t.call(e, 'Live Audio', 'header')
                        var n = window.open(
                          'https://www.racing.com/live-audio.html',
                          'Live Audio',
                          'toolbar=yes, scrollbars=yes, resizable=yes, width='.concat(
                            450,
                            ', height=',
                            160
                          )
                        )
                        window.focus && n.focus()
                      },
                    }),
                    o().createElement(J, { mr: '4px' })
                  ),
                n &&
                  o().createElement(
                    o().Fragment,
                    null,
                    !i &&
                      o().createElement(
                        l.rU,
                        {
                          href: '/shop/cart',
                          sx: {
                            mr: '10px',
                            cursor: 'pointer',
                            color: 'darkgray',
                            '&:hover, &:focus': { color: 'white' },
                          },
                        },
                        o().createElement(O.Vd.Cart, null)
                      ),
                    o().createElement(
                      y.Z,
                      {
                        sx: {
                          fontSize: '14px',
                          padding: '9px 10px 9px 10px',
                          color: 'white',
                          '&:hover, &:focus': {
                            borderColor: 'white',
                            color: 'white',
                          },
                          display: 'flex',
                          alignItems: 'center',
                        },
                        onClick: function () {
                          var e = i
                            ? 'https://photos.racing.com'
                            : 'https://licensedphotos.racing.com'
                          window.open(e, '_blank')
                        },
                      },
                      i ? 'Memorabilia' : 'Licenced Photos'
                    )
                  ),
                !(null != e && e.killSwitchActive) &&
                  o().createElement(pe, { ml: 'md' })
              )
            )
          }
        var mt = n(1601),
          yt = n(6436),
          bt = n(70423)
        function ht(e, t) {
          ;(null == t || t > e.length) && (t = e.length)
          for (var n = 0, r = new Array(t); n < t; n++) r[n] = e[n]
          return r
        }
        var gt = function () {
          var e,
            t,
            n = (0, r.useRef)(null),
            i =
              ((e = (0, r.useState)('')),
              (t = 2),
              (function (e) {
                if (Array.isArray(e)) return e
              })(e) ||
                (function (e, t) {
                  var n =
                    null == e
                      ? null
                      : ('undefined' != typeof Symbol && e[Symbol.iterator]) ||
                        e['@@iterator']
                  if (null != n) {
                    var r,
                      o,
                      i,
                      a,
                      c = [],
                      l = !0,
                      u = !1
                    try {
                      if (((i = (n = n.call(e)).next), 0 === t)) {
                        if (Object(n) !== n) return
                        l = !1
                      } else
                        for (
                          ;
                          !(l = (r = i.call(n)).done) &&
                          (c.push(r.value), c.length !== t);
                          l = !0
                        );
                    } catch (e) {
                      ;(u = !0), (o = e)
                    } finally {
                      try {
                        if (
                          !l &&
                          null != n.return &&
                          ((a = n.return()), Object(a) !== a)
                        )
                          return
                      } finally {
                        if (u) throw o
                      }
                    }
                    return c
                  }
                })(e, t) ||
                (function (e, t) {
                  if (e) {
                    if ('string' == typeof e) return ht(e, t)
                    var n = Object.prototype.toString.call(e).slice(8, -1)
                    return (
                      'Object' === n &&
                        e.constructor &&
                        (n = e.constructor.name),
                      'Map' === n || 'Set' === n
                        ? Array.from(e)
                        : 'Arguments' === n ||
                          /^(?:Ui|I)nt(?:8|16|32)(?:Clamped)?Array$/.test(n)
                        ? ht(e, t)
                        : void 0
                    )
                  }
                })(e, t) ||
                (function () {
                  throw new TypeError(
                    'Invalid attempt to destructure non-iterable instance.\nIn order to be iterable, non-array objects must have a [Symbol.iterator]() method.'
                  )
                })()),
            a = i[0],
            c = i[1]
          return o().createElement(
            l.xu,
            {
              className: 'search-bar',
              as: 'form',
              method: 'get',
              action: '/search',
              sx: { position: 'relative' },
              onClick: function (e) {
                e.nativeEvent.stopImmediatePropagation(), e.stopPropagation()
              },
              onSubmit: function (e) {
                var t
                '' === _()(a) &&
                  (null === (t = n.current) || void 0 === t || t.focus(),
                  e.preventDefault())
              },
            },
            o().createElement(P.II, {
              ref: n,
              name: 'q',
              autoComplete: 'off',
              className: 'search__input',
              sx: {
                px: '10px',
                py: '6px',
                width: '100%',
                border: 'none',
                backgroundColor: 'grey-44',
                borderRadius: '4px',
                fontFamily: 'roboto',
                fontWeight: 'bold',
                fontSize: 'body',
                lineHeight: 1.2,
                color: 'grey-99',
                '&::placeholder': { color: 'grey-99', opacity: '1' },
                '&:focus': { outline: 'none' },
              },
              placeholder: 'Search Racing.com',
              onChange: function (e) {
                return c(e.target.value)
              },
              value: a,
            })
          )
        }
        gt.propTypes = {}
        const vt = gt
        function wt(e) {
          return (
            (wt =
              'function' == typeof Symbol && 'symbol' == typeof Symbol.iterator
                ? function (e) {
                    return typeof e
                  }
                : function (e) {
                    return e &&
                      'function' == typeof Symbol &&
                      e.constructor === Symbol &&
                      e !== Symbol.prototype
                      ? 'symbol'
                      : typeof e
                  }),
            wt(e)
          )
        }
        var xt,
          Et = ['menu', 'active', 'onOpen', 'onClose', 'labelSX'],
          Ot = ['menu', 'link', 'labelSX'],
          St = ['col']
        function jt() {
          return (
            (jt = Object.assign
              ? Object.assign.bind()
              : function (e) {
                  for (var t = 1; t < arguments.length; t++) {
                    var n = arguments[t]
                    for (var r in n)
                      Object.prototype.hasOwnProperty.call(n, r) &&
                        (e[r] = n[r])
                  }
                  return e
                }),
            jt.apply(this, arguments)
          )
        }
        function kt(e, t) {
          if (null == e) return {}
          var n,
            r,
            o = (function (e, t) {
              if (null == e) return {}
              var n,
                r,
                o = {},
                i = Object.keys(e)
              for (r = 0; r < i.length; r++)
                (n = i[r]), t.indexOf(n) >= 0 || (o[n] = e[n])
              return o
            })(e, t)
          if (Object.getOwnPropertySymbols) {
            var i = Object.getOwnPropertySymbols(e)
            for (r = 0; r < i.length; r++)
              (n = i[r]),
                t.indexOf(n) >= 0 ||
                  (Object.prototype.propertyIsEnumerable.call(e, n) &&
                    (o[n] = e[n]))
          }
          return o
        }
        function _t(e, t) {
          var n = Object.keys(e)
          if (Object.getOwnPropertySymbols) {
            var r = Object.getOwnPropertySymbols(e)
            t &&
              (r = r.filter(function (t) {
                return Object.getOwnPropertyDescriptor(e, t).enumerable
              })),
              n.push.apply(n, r)
          }
          return n
        }
        function Pt(e) {
          for (var t = 1; t < arguments.length; t++) {
            var n = null != arguments[t] ? arguments[t] : {}
            t % 2
              ? _t(Object(n), !0).forEach(function (t) {
                  var r, o, i, a
                  ;(r = e),
                    (o = t),
                    (i = n[t]),
                    (a = (function (e, t) {
                      if ('object' != wt(e) || !e) return e
                      var n = e[Symbol.toPrimitive]
                      if (void 0 !== n) {
                        var r = n.call(e, 'string')
                        if ('object' != wt(r)) return r
                        throw new TypeError(
                          '@@toPrimitive must return a primitive value.'
                        )
                      }
                      return String(e)
                    })(o)),
                    (o = 'symbol' == wt(a) ? a : String(a)) in r
                      ? Object.defineProperty(r, o, {
                          value: i,
                          enumerable: !0,
                          configurable: !0,
                          writable: !0,
                        })
                      : (r[o] = i)
                })
              : Object.getOwnPropertyDescriptors
              ? Object.defineProperties(e, Object.getOwnPropertyDescriptors(n))
              : _t(Object(n)).forEach(function (t) {
                  Object.defineProperty(
                    e,
                    t,
                    Object.getOwnPropertyDescriptor(n, t)
                  )
                })
          }
          return e
        }
        function Ct(e, t) {
          ;(null == t || t > e.length) && (t = e.length)
          for (var n = 0, r = new Array(t); n < t; n++) r[n] = e[n]
          return r
        }
        var At = (0, de.F4)(
            xt ||
              (xt = (function (e, t) {
                return (
                  t || (t = e.slice(0)),
                  Object.freeze(
                    Object.defineProperties(e, {
                      raw: { value: Object.freeze(t) },
                    })
                  )
                )
              })([
                '\n    0% {\n      opacity: 0;\n      transform: translateX(-50px);\n    }\n    100% {\n      opacity: 1;\n      transform: translateX(0%);\n    }\n  ',
              ]))
          ),
          It = function (e) {
            var t,
              n,
              i,
              a,
              c = e.shouldShowMenu,
              s = e.toggleMenu,
              f = (0, r.useContext)(d),
              p =
                null !== (t = re()) && void 0 !== t
                  ? t
                  : null == f || null === (n = f.megaMenuData) || void 0 === n
                  ? void 0
                  : n.megaMenu,
              m =
                ((i = (0, r.useState)(null)),
                (a = 2),
                (function (e) {
                  if (Array.isArray(e)) return e
                })(i) ||
                  (function (e, t) {
                    var n =
                      null == e
                        ? null
                        : ('undefined' != typeof Symbol &&
                            e[Symbol.iterator]) ||
                          e['@@iterator']
                    if (null != n) {
                      var r,
                        o,
                        i,
                        a,
                        c = [],
                        l = !0,
                        u = !1
                      try {
                        if (((i = (n = n.call(e)).next), 0 === t)) {
                          if (Object(n) !== n) return
                          l = !1
                        } else
                          for (
                            ;
                            !(l = (r = i.call(n)).done) &&
                            (c.push(r.value), c.length !== t);
                            l = !0
                          );
                      } catch (e) {
                        ;(u = !0), (o = e)
                      } finally {
                        try {
                          if (
                            !l &&
                            null != n.return &&
                            ((a = n.return()), Object(a) !== a)
                          )
                            return
                        } finally {
                          if (u) throw o
                        }
                      }
                      return c
                    }
                  })(i, a) ||
                  (function (e, t) {
                    if (e) {
                      if ('string' == typeof e) return Ct(e, t)
                      var n = Object.prototype.toString.call(e).slice(8, -1)
                      return (
                        'Object' === n &&
                          e.constructor &&
                          (n = e.constructor.name),
                        'Map' === n || 'Set' === n
                          ? Array.from(e)
                          : 'Arguments' === n ||
                            /^(?:Ui|I)nt(?:8|16|32)(?:Clamped)?Array$/.test(n)
                          ? Ct(e, t)
                          : void 0
                      )
                    }
                  })(i, a) ||
                  (function () {
                    throw new TypeError(
                      'Invalid attempt to destructure non-iterable instance.\nIn order to be iterable, non-array objects must have a [Symbol.iterator]() method.'
                    )
                  })()),
              y = m[0],
              b = m[1]
            return (
              (0, r.useEffect)(
                function () {
                  c || b(null)
                },
                [c]
              ),
              o().createElement(
                o().Fragment,
                null,
                o().createElement(E, {
                  icon: c ? 'close-circle' : 'hamburger',
                  onClick: function () {
                    s(!c), bt.NY.scrollToTop({ duration: 0 })
                  },
                  sx: { p: 0, mr: '4px' },
                }),
                o().createElement(
                  l.xu,
                  {
                    sx: {
                      position: 'fixed',
                      top: '40px',
                      transform: 'translateX('.concat(c ? 0 : -100, '%)'),
                      transition: 'transform ease-out 0.5s',
                      left: 0,
                      width: '100%',
                      bottom: '0',
                      backgroundColor: 'grey-33',
                      fontFamily: 'roboto',
                      fontSize: '12px',
                      py: 'lg',
                    },
                  },
                  o().createElement(
                    l.xu,
                    {
                      sx: {
                        pb: '16px',
                        borderBottom: '1px solid',
                        borderBottomColor: 'grey-66',
                      },
                    },
                    o().createElement(u.Z, null, o().createElement(vt, null))
                  ),
                  o().createElement(
                    u.Z,
                    null,
                    null == p
                      ? void 0
                      : p.map(function (e, t) {
                          return 'MenuLink' === e.type
                            ? o().createElement(Mt, {
                                menu: e,
                                active: y === e.label,
                                key: e.id,
                                link: e.link,
                                labelSX: Pt(
                                  {},
                                  c
                                    ? {
                                        animation: ''.concat(
                                          At,
                                          ' 0.3s ease-out'
                                        ),
                                        animationFillMode: 'both',
                                        animationDelay: ''.concat(
                                          0.2 + 0.1 * t,
                                          's'
                                        ),
                                      }
                                    : {}
                                ),
                              })
                            : o().createElement(Tt, {
                                menu: e,
                                active: y === e.label,
                                key: e.id,
                                onOpen: function () {
                                  b(e.label)
                                },
                                onClose: function () {
                                  b(null)
                                },
                                labelSX: Pt(
                                  {},
                                  c
                                    ? {
                                        animation: ''.concat(
                                          At,
                                          ' 0.3s ease-out'
                                        ),
                                        animationFillMode: 'both',
                                        animationDelay: ''.concat(
                                          0.2 + 0.1 * t,
                                          's'
                                        ),
                                      }
                                    : {}
                                ),
                              })
                        })
                  )
                )
              )
            )
          }
        It.propTypes = { shouldShowMenu: c().bool, toggleMenu: c().func }
        const Lt = It
        function Tt(e) {
          var t = e.menu,
            n = e.active,
            r = e.onOpen,
            i = e.onClose,
            a = e.labelSX,
            c = void 0 === a ? {} : a,
            s = kt(e, Et)
          return o().createElement(
            l.xu,
            s,
            o().createElement(
              l.kC,
              {
                sx: Pt(
                  {
                    mx: 'md',
                    cursor: 'pointer',
                    color: 'white',
                    borderBottom: '1px solid',
                    borderBottomColor: 'grey-66',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    fontSize: '16px',
                    lineHeight: '30px',
                    py: '6px',
                  },
                  c
                ),
                onClick: r,
              },
              o().createElement(
                l.xv,
                { sx: { fontFamily: 'circular', fontWeight: 'bold' } },
                'more' === t.type
                  ? o().createElement(O.Vd.MoreDots, {
                      width: '32px',
                      height: '32px',
                    })
                  : t.label || 'Menu'
              ),
              o().createElement(m.Z, { type: 'right-chev', inline: !0 })
            ),
            o().createElement(
              l.xu,
              {
                sx: {
                  position: 'fixed',
                  transform: 'translateX('.concat(n ? 0 : -100, '%)'),
                  transition: 'transform ease-out 0.3s',
                  top: '60px',
                  left: 0,
                  width: '100%',
                  bottom: '0',
                  overflowY: 'auto',
                  backgroundColor: 'grey-33',
                  fontFamily: 'roboto',
                  fontSize: '12px',
                  zIndex: '2',
                },
              },
              o().createElement(
                u.Z,
                null,
                o().createElement(
                  l.kC,
                  {
                    sx: {
                      mx: 'md',
                      justifyContent: 'flex-start',
                      alignItems: 'center',
                      fontSize: '16px',
                      lineHeight: '30px',
                      fontFamily: 'circular',
                      fontWeight: 'bold',
                      borderBottom: '1px solid',
                      borderBottomColor: 'grey-66',
                      py: '6px',
                      mb: '16px',
                      cursor: 'pointer',
                    },
                    onClick: i,
                  },
                  o().createElement(m.Z, { type: 'left-chev', inline: !0 }),
                  o().createElement(l.xu, { sx: { mr: 'md' } }),
                  o().createElement(
                    l.xv,
                    null,
                    'more' === t.type
                      ? o().createElement(O.Vd.MoreDots, {
                          width: '32px',
                          height: '32px',
                        })
                      : t.label || 'Menu'
                  )
                ),
                t.columns.map(function (e, t) {
                  return o().createElement(Nt, {
                    col: e,
                    key: e.id,
                    sx: Pt(
                      { mb: '16px' },
                      n
                        ? {
                            animation: ''.concat(At, ' 0.3s ease-out'),
                            animationFillMode: 'both',
                            animationDelay: ''.concat(0.2 + 0.1 * t, 's'),
                          }
                        : {}
                    ),
                  })
                })
              )
            )
          )
        }
        function Mt(e) {
          var t = e.menu,
            n = e.link,
            r = e.labelSX,
            i = void 0 === r ? {} : r,
            a = kt(e, Ot)
          return o().createElement(
            l.xu,
            a,
            o().createElement(
              l.kC,
              jt(
                {
                  sx: Pt(
                    {
                      mx: 'md',
                      cursor: 'pointer',
                      borderBottom: '1px solid',
                      borderBottomColor: 'grey-66',
                      justifyContent: 'space-between',
                      fontSize: '16px',
                      lineHeight: '30px',
                      py: '6px',
                      position: 'relative',
                      height: '45px',
                      alignItems: 'center',
                      transition: 'color ease-out 0.3s',
                      color: 'white',
                      fontFamily: 'circular',
                      fontWeight: 'bold',
                    },
                    i
                  ),
                },
                a
              ),
              o().createElement(
                l.xv,
                {
                  as: 'a',
                  href: n.link,
                  target: n.target,
                  onClick: function () {
                    return ve(n)
                  },
                  sx: {
                    fontSize: '16px',
                    cursor: 'pointer',
                    textDecoration: 'none',
                    transition: 'color ease-out 0.3s',
                    color: 'white',
                    '&:hover': { color: 'white' },
                    '&:focus': { color: 'white' },
                  },
                },
                t.label || 'MenuLink',
                n.external &&
                  o().createElement(
                    l.xu,
                    { as: 'span', sx: { ml: 'sm', fontSize: '16px' } },
                    o().createElement(m.Z, {
                      type: 'external-link',
                      inline: !0,
                    })
                  )
              )
            )
          )
        }
        function Nt(e) {
          var t = e.col,
            n = kt(e, St)
          return o().createElement(
            l.xu,
            n,
            'contained' === t.type &&
              o().createElement(
                l.xv,
                {
                  as: 'h3',
                  sx: {
                    mx: 'md',
                    justifyContent: 'flex-start',
                    alignItems: 'center',
                    fontSize: '16px',
                    lineHeight: '30px',
                    color: 'grey-99',
                    fontFamily: 'circular',
                    fontWeight: 'bold',
                    borderBottom: '1px solid',
                    borderBottomColor: 'grey-66',
                    py: '6px',
                    mb: '16px',
                  },
                },
                t.heading
              ),
            t.columns.map(function (e) {
              return o().createElement(
                l.xu,
                { sx: { mb: 'md' }, key: e.id },
                e.links.map(function (e) {
                  return 'separator' === e.type
                    ? o().createElement(l.xu, {
                        key: e.id,
                        className: 'rdc-header__mega-link',
                        sx: { height: '22px' },
                      })
                    : o().createElement(
                        l.xv,
                        {
                          key: e.id,
                          as: 'a',
                          href: e.link,
                          onClick: function () {
                            return ve(e)
                          },
                          className: 'rdc-header__mega-link',
                          sx: {
                            display: 'block',
                            whiteSpace: 'nowrap',
                            fontSize: '12px',
                            lineHeight: '22px',
                            textDecoration: 'none',
                            color: 'white',
                            mx: 'md',
                            '&:hover, &:focus': { color: 'primary' },
                            '.rdc-header__mega-link + &': { mt: '1em' },
                          },
                        },
                        e.label,
                        e.external &&
                          o().createElement(
                            l.xu,
                            { as: 'span', sx: { ml: 'sm', fontSize: '14px' } },
                            o().createElement(m.Z, {
                              type: 'external-link',
                              inline: !0,
                            })
                          ),
                        e.badge &&
                          o().createElement(
                            l.xv,
                            {
                              as: 'span',
                              sx: {
                                display: 'inline-block',
                                color: 'white',
                                backgroundColor: e.badge.color,
                                ml: 'sm',
                                px: 'sm',
                                fontSize: '10px',
                                fontWeight: 'bold',
                                lineHeight: '14px',
                                verticalAlign: 'text-bottom',
                                textTransform: 'uppercase',
                              },
                            },
                            e.badge.label
                          )
                      )
                })
              )
            })
          )
        }
        ;(Tt.propTypes = {
          menu: c().object.isRequired,
          active: c().bool,
          onOpen: c().func,
          onClose: c().func,
          labelSX: c().object,
        }),
          (Mt.propTypes = {
            menu: c().object.isRequired,
            link: c().object.isRequired,
            labelSX: c().object,
          }),
          (Nt.propTypes = { col: c().object.isRequired })
        var Dt = n(33351),
          Ft = n(63743),
          Ht = ['label', 'blur'],
          zt = ['profileLinkLabel', 'profileLinkUrl', 'authentication', 'user']
        function Rt(e, t) {
          ;(null == t || t > e.length) && (t = e.length)
          for (var n = 0, r = new Array(t); n < t; n++) r[n] = e[n]
          return r
        }
        function Ut() {
          return (
            (Ut = Object.assign
              ? Object.assign.bind()
              : function (e) {
                  for (var t = 1; t < arguments.length; t++) {
                    var n = arguments[t]
                    for (var r in n)
                      Object.prototype.hasOwnProperty.call(n, r) &&
                        (e[r] = n[r])
                  }
                  return e
                }),
            Ut.apply(this, arguments)
          )
        }
        function Zt(e, t) {
          if (null == e) return {}
          var n,
            r,
            o = (function (e, t) {
              if (null == e) return {}
              var n,
                r,
                o = {},
                i = Object.keys(e)
              for (r = 0; r < i.length; r++)
                (n = i[r]), t.indexOf(n) >= 0 || (o[n] = e[n])
              return o
            })(e, t)
          if (Object.getOwnPropertySymbols) {
            var i = Object.getOwnPropertySymbols(e)
            for (r = 0; r < i.length; r++)
              (n = i[r]),
                t.indexOf(n) >= 0 ||
                  (Object.prototype.propertyIsEnumerable.call(e, n) &&
                    (o[n] = e[n]))
          }
          return o
        }
        var qt = function (e) {
          var t = e.label,
            n = e.blur,
            r = Zt(e, Ht)
          return o().createElement(
            l.xu,
            Ut(
              {
                as: 'a',
                sx: {
                  display: 'block',
                  fontSize: '12px',
                  textDecoration: 'none',
                  transition: 'color ease-out 0.3s',
                  color: n ? 'grey-99' : 'white',
                },
              },
              r
            ),
            t
          )
        }
        qt.propTypes = { label: c().string.isRequired, blur: c().bool }
        var Bt = function (e) {
          var t,
            n,
            i = e.shouldShowMenu,
            a = e.toggleMenu,
            c = (0, r.useContext)(d),
            s = c.profileLinkLabel,
            f = c.profileLinkUrl,
            p = c.authentication,
            m = p.loginWithPopup,
            y = p.logout,
            b = c.user,
            h = Zt(c, zt),
            g = (0, Dt.M)(),
            v =
              ((t = (0, r.useState)(null)),
              (n = 2),
              (function (e) {
                if (Array.isArray(e)) return e
              })(t) ||
                (function (e, t) {
                  var n =
                    null == e
                      ? null
                      : ('undefined' != typeof Symbol && e[Symbol.iterator]) ||
                        e['@@iterator']
                  if (null != n) {
                    var r,
                      o,
                      i,
                      a,
                      c = [],
                      l = !0,
                      u = !1
                    try {
                      if (((i = (n = n.call(e)).next), 0 === t)) {
                        if (Object(n) !== n) return
                        l = !1
                      } else
                        for (
                          ;
                          !(l = (r = i.call(n)).done) &&
                          (c.push(r.value), c.length !== t);
                          l = !0
                        );
                    } catch (e) {
                      ;(u = !0), (o = e)
                    } finally {
                      try {
                        if (
                          !l &&
                          null != n.return &&
                          ((a = n.return()), Object(a) !== a)
                        )
                          return
                      } finally {
                        if (u) throw o
                      }
                    }
                    return c
                  }
                })(t, n) ||
                (function (e, t) {
                  if (e) {
                    if ('string' == typeof e) return Rt(e, t)
                    var n = Object.prototype.toString.call(e).slice(8, -1)
                    return (
                      'Object' === n &&
                        e.constructor &&
                        (n = e.constructor.name),
                      'Map' === n || 'Set' === n
                        ? Array.from(e)
                        : 'Arguments' === n ||
                          /^(?:Ui|I)nt(?:8|16|32)(?:Clamped)?Array$/.test(n)
                        ? Rt(e, t)
                        : void 0
                    )
                  }
                })(t, n) ||
                (function () {
                  throw new TypeError(
                    'Invalid attempt to destructure non-iterable instance.\nIn order to be iterable, non-array objects must have a [Symbol.iterator]() method.'
                  )
                })()),
            w = v[0],
            x = v[1]
          return o().createElement(
            o().Fragment,
            null,
            o().createElement(E, {
              icon: i ? 'close-circle' : 'user',
              onClick: function () {
                b
                  ? (a(!i), bt.NY.scrollToTop({ duration: 0 }))
                  : window.location.reload()
              },
              sx: { p: 0, mr: '4px' },
            }),
            o().createElement(
              l.xu,
              {
                sx: {
                  position: 'fixed',
                  top: '40px',
                  transform: 'translateX('.concat(i ? 0 : 100, '%)'),
                  transition: 'transform ease-out 0.5s',
                  left: 0,
                  width: '100%',
                  bottom: '0',
                  backgroundColor: 'grey-33',
                  fontFamily: 'roboto',
                  fontSize: '12px',
                },
              },
              o().createElement(
                l.xu,
                { sx: { py: 'lg', px: '20px' } },
                o().createElement(
                  u.Z,
                  { padding: !1 },
                  o().createElement(
                    l.xu,
                    {
                      sx: {
                        fontSize: '16px',
                        fontFamily: 'circular',
                        fontWeight: 'bold',
                        color: b ? 'grey-99' : 'white',
                        pb: '14px',
                        borderBottom: '1px solid',
                        borderBottomColor: 'grey-66',
                        mb: '21px',
                      },
                    },
                    b ? (0, K.d)(b.name, { shorten: 16 }) : 'Racing+'
                  ),
                  g &&
                    o().createElement(
                      l.xu,
                      {
                        as: 'a',
                        sx: {
                          display: 'flex',
                          fontSize: '12px',
                          textDecoration: 'none',
                          transition: 'color ease-out 0.3s',
                          color: w && 'live' !== w ? 'grey-99' : 'white',
                          mb: 'lg',
                        },
                        target: '_blank',
                        href: 'https://www.racing.com/live-vision.aspx',
                        onMouseEnter: function () {
                          x('live')
                        },
                        onMouseLeave: function () {
                          x(null)
                        },
                        onClick: function () {
                          var e
                          null == h ||
                            null === (e = h.trackEvent) ||
                            void 0 === e ||
                            e.call(h, 'Live Vision', 'mobile')
                        },
                      },
                      'Watch Live',
                      ' ',
                      o().createElement(
                        l.xu,
                        { sx: { color: 'primary' } },
                        o().createElement(Ft.Z, null)
                      ),
                      ' ',
                      o().createElement(
                        l.xv,
                        {
                          sx: {
                            ml: 'md',
                            whiteSpace: 'nowrap',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                          },
                        },
                        g.title
                      )
                    ),
                  b &&
                    o().createElement(qt, {
                      label: null != s ? s : 'My Preferences',
                      mb: 'lg',
                      href: null != f ? f : '/plus/profile-management',
                      blur: w && 'preference' !== w,
                      onMouseEnter: function () {
                        x('preference')
                      },
                      onMouseLeave: function () {
                        x(null)
                      },
                    }),
                  b
                    ? o().createElement(qt, {
                        label: 'Logout',
                        mb: 'lg',
                        onClick: y,
                        blur: w && 'logout' !== w,
                        onMouseEnter: function () {
                          x('logout')
                        },
                        onMouseLeave: function () {
                          x(null)
                        },
                      })
                    : o().createElement(
                        o().Fragment,
                        null,
                        o().createElement(qt, {
                          label: 'Login',
                          mb: 'lg',
                          onClick: m,
                          blur: w && 'login' !== w,
                          onMouseEnter: function () {
                            x('login')
                          },
                          onMouseLeave: function () {
                            x(null)
                          },
                        }),
                        o().createElement(qt, {
                          label: 'Signup',
                          mb: 'lg',
                          onClick: m,
                          blur: w && 'signup' !== w,
                          onMouseEnter: function () {
                            x('signup')
                          },
                          onMouseLeave: function () {
                            x(null)
                          },
                        })
                      )
                )
              )
            )
          )
        }
        Bt.propTypes = { shouldShowMenu: c().bool, toggleMenu: c().func }
        const Vt = Bt
        var Wt = n(79548),
          Gt = {
            injectType: 'singletonStyleTag',
            insert: function (e) {
              var t = document.querySelector('head'),
                n = document.querySelector('#rdc-tailwind-css'),
                r = window._lastElementInsertedByStyleLoader
              r
                ? r.nextSibling
                  ? t.insertBefore(e, r.nextSibling)
                  : t.appendChild(e)
                : t.insertBefore(e, n),
                (window._lastElementInsertedByStyleLoader = e)
            },
            singleton: !0,
          }
        Ze()(Wt.Z, Gt)
        const Qt = Wt.Z.locals || {}
        var Yt = ['shouldShowMenu', 'toggleMenu']
        function Xt(e) {
          return (
            (Xt =
              'function' == typeof Symbol && 'symbol' == typeof Symbol.iterator
                ? function (e) {
                    return typeof e
                  }
                : function (e) {
                    return e &&
                      'function' == typeof Symbol &&
                      e.constructor === Symbol &&
                      e !== Symbol.prototype
                      ? 'symbol'
                      : typeof e
                  }),
            Xt(e)
          )
        }
        function Jt() {
          return (
            (Jt = Object.assign
              ? Object.assign.bind()
              : function (e) {
                  for (var t = 1; t < arguments.length; t++) {
                    var n = arguments[t]
                    for (var r in n)
                      Object.prototype.hasOwnProperty.call(n, r) &&
                        (e[r] = n[r])
                  }
                  return e
                }),
            Jt.apply(this, arguments)
          )
        }
        function Kt(e, t) {
          var n = Object.keys(e)
          if (Object.getOwnPropertySymbols) {
            var r = Object.getOwnPropertySymbols(e)
            t &&
              (r = r.filter(function (t) {
                return Object.getOwnPropertyDescriptor(e, t).enumerable
              })),
              n.push.apply(n, r)
          }
          return n
        }
        function $t(e) {
          for (var t = 1; t < arguments.length; t++) {
            var n = null != arguments[t] ? arguments[t] : {}
            t % 2
              ? Kt(Object(n), !0).forEach(function (t) {
                  en(e, t, n[t])
                })
              : Object.getOwnPropertyDescriptors
              ? Object.defineProperties(e, Object.getOwnPropertyDescriptors(n))
              : Kt(Object(n)).forEach(function (t) {
                  Object.defineProperty(
                    e,
                    t,
                    Object.getOwnPropertyDescriptor(n, t)
                  )
                })
          }
          return e
        }
        function en(e, t, n) {
          var r
          return (
            (r = (function (e, t) {
              if ('object' != Xt(e) || !e) return e
              var n = e[Symbol.toPrimitive]
              if (void 0 !== n) {
                var r = n.call(e, 'string')
                if ('object' != Xt(r)) return r
                throw new TypeError(
                  '@@toPrimitive must return a primitive value.'
                )
              }
              return String(e)
            })(t)),
            (t = 'symbol' == Xt(r) ? r : String(r)) in e
              ? Object.defineProperty(e, t, {
                  value: n,
                  enumerable: !0,
                  configurable: !0,
                  writable: !0,
                })
              : (e[t] = n),
            e
          )
        }
        var tn = (0, We.n)('JockeyAvatar'),
          nn = (0, We.n)('TrainerAvatar'),
          rn = (0, We.n)('HorseAvatar'),
          on = function (e) {
            var t = e.avatar,
              n = e.message
            return (
              e.avatar ||
                (t =
                  'Jockey' === e.entityType
                    ? tn
                    : 'Trainer' === e.entityType
                    ? nn
                    : rn),
              (n = (n = n.replace(
                e.name,
                '<b>'.concat(e.name, '</b>')
              )).replace(e.type, '<b>'.concat(e.type, '</b>'))),
              $t($t({}, e), {}, { avatar: t, message: n })
            )
          },
          an = function (e) {
            var t = e.shouldShowMenu,
              n = e.toggleMenu,
              i = (function (e, t) {
                if (null == e) return {}
                var n,
                  r,
                  o = (function (e, t) {
                    if (null == e) return {}
                    var n,
                      r,
                      o = {},
                      i = Object.keys(e)
                    for (r = 0; r < i.length; r++)
                      (n = i[r]), t.indexOf(n) >= 0 || (o[n] = e[n])
                    return o
                  })(e, t)
                if (Object.getOwnPropertySymbols) {
                  var i = Object.getOwnPropertySymbols(e)
                  for (r = 0; r < i.length; r++)
                    (n = i[r]),
                      t.indexOf(n) >= 0 ||
                        (Object.prototype.propertyIsEnumerable.call(e, n) &&
                          (o[n] = e[n]))
                }
                return o
              })(e, Yt),
              a = ie(),
              c = (0, C.I0)(),
              l = (0, r.useRef)()
            function u() {
              n(!t), c(U(a.userId))
            }
            return (
              (0, r.useEffect)(
                function () {
                  return a.newFeeds.length
                    ? (t &&
                        (e = setTimeout(function () {
                          ;(l.current = !0),
                            a.newFeeds.forEach(function (e) {
                              ;(0, et.Bj)('notificationViewed', e)
                            }),
                            (0, he.fW)('Notification', 'Open', null),
                            c(
                              Z({
                                timestamp: +new Date(),
                                newFeeds: a.newFeeds,
                                userId: a.userId,
                              })
                            )
                        }, 100)),
                      function () {
                        clearTimeout(e)
                      })
                    : (t && (0, he.fW)('Notification', 'Open', null),
                      function () {})
                  var e
                },
                [c, t, a]
              ),
              a.lastUpdated
                ? o().createElement(
                    'div',
                    Jt(
                      {
                        className: ye()(
                          Qt['rdc-notification-feed'],
                          en({}, Qt['rdc-notification-feed--active'], t),
                          'mr-2'
                        ),
                      },
                      i
                    ),
                    o().createElement(E, {
                      icon: 'notification',
                      onClick: function (e) {
                        u(), e.preventDefault()
                      },
                    }),
                    a.unread > 0 &&
                      o().createElement(
                        'span',
                        { className: Qt['rdc-notification-feed__unread'] },
                        a.unread
                      ),
                    o().createElement(
                      'div',
                      { className: Qt['rdc-notification-feed__wrap'] },
                      o().createElement(
                        'div',
                        { style: { position: 'absolute', right: 10, top: 2 } },
                        o().createElement(
                          y.Z,
                          Jt(
                            {
                              className: 'header__icon',
                              variant: 'button.icon',
                              sx: {
                                color: 'grey-44',
                                fontSize: '21px',
                                transition: 'color 0.3s ease-in-out',
                                '&:hover': { color: 'black' },
                              },
                              onClick: u,
                            },
                            i
                          ),
                          o().createElement(m.Z, {
                            type: 'close-circle',
                            inline: !0,
                          })
                        )
                      ),
                      o().createElement(
                        'div',
                        { className: Qt['rdc-notification-feed__content'] },
                        o().createElement(
                          'div',
                          { className: Qt['rdc-notification-feed__title'] },
                          o().createElement('span', null, 'Notifications '),
                          o().createElement(
                            y.Z,
                            Jt(
                              {
                                className: 'header__icon',
                                variant: 'button.icon',
                                sx: {
                                  color: 'grey-99',
                                  fontSize: '17px',
                                  transition: 'color 0.3s ease-in-out',
                                  '&:hover': { color: 'grey-44' },
                                },
                                onClick: function () {
                                  window.open(
                                    'https://www.racing.com/notifications'
                                  )
                                },
                              },
                              i
                            ),
                            o().createElement(m.Z, {
                              type: 'information',
                              inline: !0,
                            })
                          )
                        ),
                        0 === a.newFeeds.length &&
                          0 === a.oldFeeds.length &&
                          o().createElement(
                            'div',
                            { className: Qt['rdc-notification-feed__group'] },
                            o().createElement(
                              'h3',
                              {
                                className:
                                  Qt['rdc-notification-feed__group-label'],
                              },
                              'Hi ',
                              a.firstName
                            ),
                            o().createElement(
                              'div',
                              {
                                className:
                                  Qt['rdc-notification-feed__group-detail'],
                              },
                              'You currently have no Blackbook notifications. ',
                              o().createElement('br', null),
                              o().createElement('div', {
                                style: { height: '10px' },
                              }),
                              "Use the Racing.com mobile app to follow any horses, jockeys or trainers, and you'll see your list of nominations, acceptances, race reminders, and results notifications here."
                            )
                          ),
                        a.newFeeds.length > 0 &&
                          o().createElement(
                            'div',
                            { className: Qt['rdc-notification-feed__group'] },
                            o().createElement(
                              'h3',
                              {
                                className:
                                  Qt['rdc-notification-feed__group-label'],
                              },
                              'New'
                            ),
                            a.newFeeds.map(function (e, t) {
                              return o().createElement(it, {
                                feed: on(e),
                                isNew: !0,
                                key: 'key-header-notification-'
                                  .concat(e.entityCode, '-')
                                  .concat(e.timestamp, '-')
                                  .concat(t),
                              })
                            })
                          ),
                        a.oldFeeds.length > 0 &&
                          o().createElement(
                            'div',
                            { className: Qt['rdc-notification-feed__group'] },
                            a.newFeeds.length > 0 &&
                              o().createElement(
                                'h3',
                                {
                                  className:
                                    Qt['rdc-notification-feed__group-label'],
                                },
                                'Old'
                              ),
                            a.oldFeeds.map(function (e, t) {
                              return o().createElement(it, {
                                feed: on(e),
                                key: 'key-header-notification-'
                                  .concat(e.entityCode, '-')
                                  .concat(e.timestamp, '-')
                                  .concat(t),
                              })
                            })
                          )
                      )
                    )
                  )
                : null
            )
          }
        an.propTypes = { shouldShowMenu: c().bool, toggleMenu: c().func }
        const cn = an
        function ln(e, t) {
          ;(null == t || t > e.length) && (t = e.length)
          for (var n = 0, r = new Array(t); n < t; n++) r[n] = e[n]
          return r
        }
        const un = function () {
          ;(0, s.vp)({ key: mt.u2, reducer: mt.I6 }),
            (0, s.hb)({ key: mt.u2, saga: yt.ZP })
          var e,
            t,
            n =
              ((e = (0, r.useState)(null)),
              (t = 2),
              (function (e) {
                if (Array.isArray(e)) return e
              })(e) ||
                (function (e, t) {
                  var n =
                    null == e
                      ? null
                      : ('undefined' != typeof Symbol && e[Symbol.iterator]) ||
                        e['@@iterator']
                  if (null != n) {
                    var r,
                      o,
                      i,
                      a,
                      c = [],
                      l = !0,
                      u = !1
                    try {
                      if (((i = (n = n.call(e)).next), 0 === t)) {
                        if (Object(n) !== n) return
                        l = !1
                      } else
                        for (
                          ;
                          !(l = (r = i.call(n)).done) &&
                          (c.push(r.value), c.length !== t);
                          l = !0
                        );
                    } catch (e) {
                      ;(u = !0), (o = e)
                    } finally {
                      try {
                        if (
                          !l &&
                          null != n.return &&
                          ((a = n.return()), Object(a) !== a)
                        )
                          return
                      } finally {
                        if (u) throw o
                      }
                    }
                    return c
                  }
                })(e, t) ||
                (function (e, t) {
                  if (e) {
                    if ('string' == typeof e) return ln(e, t)
                    var n = Object.prototype.toString.call(e).slice(8, -1)
                    return (
                      'Object' === n &&
                        e.constructor &&
                        (n = e.constructor.name),
                      'Map' === n || 'Set' === n
                        ? Array.from(e)
                        : 'Arguments' === n ||
                          /^(?:Ui|I)nt(?:8|16|32)(?:Clamped)?Array$/.test(n)
                        ? ln(e, t)
                        : void 0
                    )
                  }
                })(e, t) ||
                (function () {
                  throw new TypeError(
                    'Invalid attempt to destructure non-iterable instance.\nIn order to be iterable, non-array objects must have a [Symbol.iterator]() method.'
                  )
                })()),
            i = n[0],
            a = n[1]
          ;(0, r.useEffect)(
            function () {
              i
                ? document.body.classList.add('ReactModal__Body--open')
                : document.body.classList.remove('ReactModal__Body--open')
            },
            [i]
          )
          var c = (0, r.useContext)(d)
          return o().createElement(
            l.kC,
            {
              className: 'header--mobile',
              sx: {
                position: 'relative',
                height: '40px',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'white',
                fontSize: '24px',
                py: '5px',
              },
            },
            o().createElement(
              l.kC,
              { sx: { alignItems: 'center', position: 'absolute', left: '0' } },
              o().createElement(Lt, {
                shouldShowMenu: 'mega' === i,
                toggleMenu: function (e) {
                  return a(e ? 'mega' : null)
                },
              })
            ),
            o().createElement(S, null),
            o().createElement(
              l.kC,
              {
                sx: { alignItems: 'center', position: 'absolute', right: '0' },
              },
              o().createElement(cn, {
                shouldShowMenu: 'notification-feed' === i,
                toggleMenu: function (e) {
                  return a(e ? 'notification-feed' : null)
                },
              }),
              !(null != c && c.killSwitchActive) &&
                o().createElement(Vt, {
                  shouldShowMenu: 'profile' === i,
                  toggleMenu: function (e) {
                    return a(e ? 'profile' : null)
                  },
                })
            )
          )
        }
        var sn,
          fn,
          pn,
          dn = n(27422),
          mn = n(59006),
          yn = n(1349),
          bn = n(38847),
          hn = function (e) {
            var t = e % 20,
              n = Math.floor(e / 20)
            return t > 0 ? n + 1 : n
          },
          gn = n(67834)
        function vn(e, t) {
          return (
            t || (t = e.slice(0)),
            Object.freeze(
              Object.defineProperties(e, { raw: { value: Object.freeze(t) } })
            )
          )
        }
        var wn = (0, gn.Ps)(
            sn ||
              (sn = vn([
                '\n  query GetNotifications($userId: String!) {\n    notifications: getNotificationsForUser(UserId: $userId) {\n      feeds: items {\n        entityCode: EntityCode\n        entityType: EntityType\n        meetCode: MeetCode\n        meetDate: MeetDate\n        date: NotificationDate\n        name: Name\n        timestamp: NotificationDate\n        type: NotificationType\n        raceNumer: RaceNumber\n        trackName: Venue\n        link: MeetUrl\n        message: Notification\n        avatar: Avatar\n        lastRead: LastRead\n        token: Token\n        eventType: EventType\n      }\n    }\n  }\n',
              ]))
          ),
          xn = (0, gn.Ps)(
            fn ||
              (fn = vn([
                '\n  mutation UpdateNotificationMutation($list: [NotificationInput]) {\n    updateNotifications(input: $list) {\n      NotificationDate\n      UserId\n      EntityCode\n      Name\n      MeetCode\n      MeetDate\n      MeetUrl\n      NotificationType\n      RaceNumber\n      Venue\n      EntityType\n      Token\n      Notification\n      Avatar\n      LastRead\n      EventType\n    }\n  }\n',
              ]))
          )
        function En(e) {
          return (
            (En =
              'function' == typeof Symbol && 'symbol' == typeof Symbol.iterator
                ? function (e) {
                    return typeof e
                  }
                : function (e) {
                    return e &&
                      'function' == typeof Symbol &&
                      e.constructor === Symbol &&
                      e !== Symbol.prototype
                      ? 'symbol'
                      : typeof e
                  }),
            En(e)
          )
        }
        function On(e, t) {
          if (e) {
            if ('string' == typeof e) return Sn(e, t)
            var n = Object.prototype.toString.call(e).slice(8, -1)
            return (
              'Object' === n && e.constructor && (n = e.constructor.name),
              'Map' === n || 'Set' === n
                ? Array.from(e)
                : 'Arguments' === n ||
                  /^(?:Ui|I)nt(?:8|16|32)(?:Clamped)?Array$/.test(n)
                ? Sn(e, t)
                : void 0
            )
          }
        }
        function Sn(e, t) {
          ;(null == t || t > e.length) && (t = e.length)
          for (var n = 0, r = new Array(t); n < t; n++) r[n] = e[n]
          return r
        }
        function jn(e, t) {
          var n = Object.keys(e)
          if (Object.getOwnPropertySymbols) {
            var r = Object.getOwnPropertySymbols(e)
            t &&
              (r = r.filter(function (t) {
                return Object.getOwnPropertyDescriptor(e, t).enumerable
              })),
              n.push.apply(n, r)
          }
          return n
        }
        function kn(e) {
          for (var t = 1; t < arguments.length; t++) {
            var n = null != arguments[t] ? arguments[t] : {}
            t % 2
              ? jn(Object(n), !0).forEach(function (t) {
                  _n(e, t, n[t])
                })
              : Object.getOwnPropertyDescriptors
              ? Object.defineProperties(e, Object.getOwnPropertyDescriptors(n))
              : jn(Object(n)).forEach(function (t) {
                  Object.defineProperty(
                    e,
                    t,
                    Object.getOwnPropertyDescriptor(n, t)
                  )
                })
          }
          return e
        }
        function _n(e, t, n) {
          var r
          return (
            (r = (function (e, t) {
              if ('object' != En(e) || !e) return e
              var n = e[Symbol.toPrimitive]
              if (void 0 !== n) {
                var r = n.call(e, 'string')
                if ('object' != En(r)) return r
                throw new TypeError(
                  '@@toPrimitive must return a primitive value.'
                )
              }
              return String(e)
            })(t)),
            (t = 'symbol' == En(r) ? r : String(r)) in e
              ? Object.defineProperty(e, t, {
                  value: n,
                  enumerable: !0,
                  configurable: !0,
                  writable: !0,
                })
              : (e[t] = n),
            e
          )
        }
        function Pn() {
          Pn = function () {
            return t
          }
          var e,
            t = {},
            n = Object.prototype,
            r = n.hasOwnProperty,
            o =
              Object.defineProperty ||
              function (e, t, n) {
                e[t] = n.value
              },
            i = 'function' == typeof Symbol ? Symbol : {},
            a = i.iterator || '@@iterator',
            c = i.asyncIterator || '@@asyncIterator',
            l = i.toStringTag || '@@toStringTag'
          function u(e, t, n) {
            return (
              Object.defineProperty(e, t, {
                value: n,
                enumerable: !0,
                configurable: !0,
                writable: !0,
              }),
              e[t]
            )
          }
          try {
            u({}, '')
          } catch (e) {
            u = function (e, t, n) {
              return (e[t] = n)
            }
          }
          function s(e, t, n, r) {
            var i = t && t.prototype instanceof h ? t : h,
              a = Object.create(i.prototype),
              c = new A(r || [])
            return o(a, '_invoke', { value: k(e, n, c) }), a
          }
          function f(e, t, n) {
            try {
              return { type: 'normal', arg: e.call(t, n) }
            } catch (e) {
              return { type: 'throw', arg: e }
            }
          }
          t.wrap = s
          var p = 'suspendedStart',
            d = 'suspendedYield',
            m = 'executing',
            y = 'completed',
            b = {}
          function h() {}
          function g() {}
          function v() {}
          var w = {}
          u(w, a, function () {
            return this
          })
          var x = Object.getPrototypeOf,
            E = x && x(x(I([])))
          E && E !== n && r.call(E, a) && (w = E)
          var O = (v.prototype = h.prototype = Object.create(w))
          function S(e) {
            ;['next', 'throw', 'return'].forEach(function (t) {
              u(e, t, function (e) {
                return this._invoke(t, e)
              })
            })
          }
          function j(e, t) {
            function n(o, i, a, c) {
              var l = f(e[o], e, i)
              if ('throw' !== l.type) {
                var u = l.arg,
                  s = u.value
                return s && 'object' == En(s) && r.call(s, '__await')
                  ? t.resolve(s.__await).then(
                      function (e) {
                        n('next', e, a, c)
                      },
                      function (e) {
                        n('throw', e, a, c)
                      }
                    )
                  : t.resolve(s).then(
                      function (e) {
                        ;(u.value = e), a(u)
                      },
                      function (e) {
                        return n('throw', e, a, c)
                      }
                    )
              }
              c(l.arg)
            }
            var i
            o(this, '_invoke', {
              value: function (e, r) {
                function o() {
                  return new t(function (t, o) {
                    n(e, r, t, o)
                  })
                }
                return (i = i ? i.then(o, o) : o())
              },
            })
          }
          function k(t, n, r) {
            var o = p
            return function (i, a) {
              if (o === m) throw new Error('Generator is already running')
              if (o === y) {
                if ('throw' === i) throw a
                return { value: e, done: !0 }
              }
              for (r.method = i, r.arg = a; ; ) {
                var c = r.delegate
                if (c) {
                  var l = _(c, r)
                  if (l) {
                    if (l === b) continue
                    return l
                  }
                }
                if ('next' === r.method) r.sent = r._sent = r.arg
                else if ('throw' === r.method) {
                  if (o === p) throw ((o = y), r.arg)
                  r.dispatchException(r.arg)
                } else 'return' === r.method && r.abrupt('return', r.arg)
                o = m
                var u = f(t, n, r)
                if ('normal' === u.type) {
                  if (((o = r.done ? y : d), u.arg === b)) continue
                  return { value: u.arg, done: r.done }
                }
                'throw' === u.type &&
                  ((o = y), (r.method = 'throw'), (r.arg = u.arg))
              }
            }
          }
          function _(t, n) {
            var r = n.method,
              o = t.iterator[r]
            if (o === e)
              return (
                (n.delegate = null),
                ('throw' === r &&
                  t.iterator.return &&
                  ((n.method = 'return'),
                  (n.arg = e),
                  _(t, n),
                  'throw' === n.method)) ||
                  ('return' !== r &&
                    ((n.method = 'throw'),
                    (n.arg = new TypeError(
                      "The iterator does not provide a '" + r + "' method"
                    )))),
                b
              )
            var i = f(o, t.iterator, n.arg)
            if ('throw' === i.type)
              return (
                (n.method = 'throw'), (n.arg = i.arg), (n.delegate = null), b
              )
            var a = i.arg
            return a
              ? a.done
                ? ((n[t.resultName] = a.value),
                  (n.next = t.nextLoc),
                  'return' !== n.method && ((n.method = 'next'), (n.arg = e)),
                  (n.delegate = null),
                  b)
                : a
              : ((n.method = 'throw'),
                (n.arg = new TypeError('iterator result is not an object')),
                (n.delegate = null),
                b)
          }
          function P(e) {
            var t = { tryLoc: e[0] }
            1 in e && (t.catchLoc = e[1]),
              2 in e && ((t.finallyLoc = e[2]), (t.afterLoc = e[3])),
              this.tryEntries.push(t)
          }
          function C(e) {
            var t = e.completion || {}
            ;(t.type = 'normal'), delete t.arg, (e.completion = t)
          }
          function A(e) {
            ;(this.tryEntries = [{ tryLoc: 'root' }]),
              e.forEach(P, this),
              this.reset(!0)
          }
          function I(t) {
            if (t || '' === t) {
              var n = t[a]
              if (n) return n.call(t)
              if ('function' == typeof t.next) return t
              if (!isNaN(t.length)) {
                var o = -1,
                  i = function n() {
                    for (; ++o < t.length; )
                      if (r.call(t, o))
                        return (n.value = t[o]), (n.done = !1), n
                    return (n.value = e), (n.done = !0), n
                  }
                return (i.next = i)
              }
            }
            throw new TypeError(En(t) + ' is not iterable')
          }
          return (
            (g.prototype = v),
            o(O, 'constructor', { value: v, configurable: !0 }),
            o(v, 'constructor', { value: g, configurable: !0 }),
            (g.displayName = u(v, l, 'GeneratorFunction')),
            (t.isGeneratorFunction = function (e) {
              var t = 'function' == typeof e && e.constructor
              return (
                !!t &&
                (t === g || 'GeneratorFunction' === (t.displayName || t.name))
              )
            }),
            (t.mark = function (e) {
              return (
                Object.setPrototypeOf
                  ? Object.setPrototypeOf(e, v)
                  : ((e.__proto__ = v), u(e, l, 'GeneratorFunction')),
                (e.prototype = Object.create(O)),
                e
              )
            }),
            (t.awrap = function (e) {
              return { __await: e }
            }),
            S(j.prototype),
            u(j.prototype, c, function () {
              return this
            }),
            (t.AsyncIterator = j),
            (t.async = function (e, n, r, o, i) {
              void 0 === i && (i = Promise)
              var a = new j(s(e, n, r, o), i)
              return t.isGeneratorFunction(n)
                ? a
                : a.next().then(function (e) {
                    return e.done ? e.value : a.next()
                  })
            }),
            S(O),
            u(O, l, 'Generator'),
            u(O, a, function () {
              return this
            }),
            u(O, 'toString', function () {
              return '[object Generator]'
            }),
            (t.keys = function (e) {
              var t = Object(e),
                n = []
              for (var r in t) n.push(r)
              return (
                n.reverse(),
                function e() {
                  for (; n.length; ) {
                    var r = n.pop()
                    if (r in t) return (e.value = r), (e.done = !1), e
                  }
                  return (e.done = !0), e
                }
              )
            }),
            (t.values = I),
            (A.prototype = {
              constructor: A,
              reset: function (t) {
                if (
                  ((this.prev = 0),
                  (this.next = 0),
                  (this.sent = this._sent = e),
                  (this.done = !1),
                  (this.delegate = null),
                  (this.method = 'next'),
                  (this.arg = e),
                  this.tryEntries.forEach(C),
                  !t)
                )
                  for (var n in this)
                    't' === n.charAt(0) &&
                      r.call(this, n) &&
                      !isNaN(+n.slice(1)) &&
                      (this[n] = e)
              },
              stop: function () {
                this.done = !0
                var e = this.tryEntries[0].completion
                if ('throw' === e.type) throw e.arg
                return this.rval
              },
              dispatchException: function (t) {
                if (this.done) throw t
                var n = this
                function o(r, o) {
                  return (
                    (c.type = 'throw'),
                    (c.arg = t),
                    (n.next = r),
                    o && ((n.method = 'next'), (n.arg = e)),
                    !!o
                  )
                }
                for (var i = this.tryEntries.length - 1; i >= 0; --i) {
                  var a = this.tryEntries[i],
                    c = a.completion
                  if ('root' === a.tryLoc) return o('end')
                  if (a.tryLoc <= this.prev) {
                    var l = r.call(a, 'catchLoc'),
                      u = r.call(a, 'finallyLoc')
                    if (l && u) {
                      if (this.prev < a.catchLoc) return o(a.catchLoc, !0)
                      if (this.prev < a.finallyLoc) return o(a.finallyLoc)
                    } else if (l) {
                      if (this.prev < a.catchLoc) return o(a.catchLoc, !0)
                    } else {
                      if (!u)
                        throw new Error(
                          'try statement without catch or finally'
                        )
                      if (this.prev < a.finallyLoc) return o(a.finallyLoc)
                    }
                  }
                }
              },
              abrupt: function (e, t) {
                for (var n = this.tryEntries.length - 1; n >= 0; --n) {
                  var o = this.tryEntries[n]
                  if (
                    o.tryLoc <= this.prev &&
                    r.call(o, 'finallyLoc') &&
                    this.prev < o.finallyLoc
                  ) {
                    var i = o
                    break
                  }
                }
                i &&
                  ('break' === e || 'continue' === e) &&
                  i.tryLoc <= t &&
                  t <= i.finallyLoc &&
                  (i = null)
                var a = i ? i.completion : {}
                return (
                  (a.type = e),
                  (a.arg = t),
                  i
                    ? ((this.method = 'next'), (this.next = i.finallyLoc), b)
                    : this.complete(a)
                )
              },
              complete: function (e, t) {
                if ('throw' === e.type) throw e.arg
                return (
                  'break' === e.type || 'continue' === e.type
                    ? (this.next = e.arg)
                    : 'return' === e.type
                    ? ((this.rval = this.arg = e.arg),
                      (this.method = 'return'),
                      (this.next = 'end'))
                    : 'normal' === e.type && t && (this.next = t),
                  b
                )
              },
              finish: function (e) {
                for (var t = this.tryEntries.length - 1; t >= 0; --t) {
                  var n = this.tryEntries[t]
                  if (n.finallyLoc === e)
                    return this.complete(n.completion, n.afterLoc), C(n), b
                }
              },
              catch: function (e) {
                for (var t = this.tryEntries.length - 1; t >= 0; --t) {
                  var n = this.tryEntries[t]
                  if (n.tryLoc === e) {
                    var r = n.completion
                    if ('throw' === r.type) {
                      var o = r.arg
                      C(n)
                    }
                    return o
                  }
                }
                throw new Error('illegal catch attempt')
              },
              delegateYield: function (t, n, r) {
                return (
                  (this.delegate = {
                    iterator: I(t),
                    resultName: n,
                    nextLoc: r,
                  }),
                  'next' === this.method && (this.arg = e),
                  b
                )
              },
            }),
            t
          )
        }
        ;(0, gn.Ps)(
          pn ||
            (pn = vn([
              '\n  query GetNotifications($name: String!, $userId: String!) {\n    notification: getTempnotifications(Name: $name, UserId: $userId) {\n      EntityCode\n      EntityType\n      MeetDate\n      Name\n      RaceNumber\n      Type: Status\n      UserId\n      Venue\n    }\n  }\n',
            ]))
        )
        var Cn = Pn().mark(Nn),
          An = Pn().mark(Dn),
          In = Pn().mark(Fn),
          Ln = Pn().mark(Hn),
          Tn = Pn().mark(Rn),
          Mn = Pn().mark(Un)
        function Nn(e) {
          var t, n, r, o, i
          return Pn().wrap(
            function (a) {
              for (;;)
                switch ((a.prev = a.next)) {
                  case 0:
                    return (
                      (a.prev = 0),
                      (t = e.payload),
                      (n = t.app),
                      (r = t.device),
                      (a.next = 4),
                      (0, dn.RE)(
                        yn.YA.get,
                        '/megamenu/'.concat(n, '/GetMenu/').concat(r)
                      )
                    )
                  case 4:
                    return (
                      (o = a.sent),
                      (i = o.data.megaMenu),
                      (a.next = 8),
                      (0, dn.gz)(R({ megaMenu: i, device: r }))
                    )
                  case 8:
                    a.next = 13
                    break
                  case 10:
                    ;(a.prev = 10), (a.t0 = a.catch(0)), console.warn(a.t0)
                  case 13:
                  case 'end':
                    return a.stop()
                }
            },
            Cn,
            null,
            [[0, 10]]
          )
        }
        function Dn(e) {
          var t, n, r, o
          return Pn().wrap(function (i) {
            for (;;)
              switch ((i.prev = i.next)) {
                case 0:
                  return (
                    (t = e.payload.query),
                    (i.next = 3),
                    (0, dn.RE)(
                      yn.YA.get,
                      '/search/quicksearch/all/1/8/?q='.concat(t, '&s=website')
                    )
                  )
                case 3:
                  return (
                    (n = i.sent),
                    (r = n.data.Items.reduce(function (e, t) {
                      return kn(
                        kn({}, e),
                        {},
                        _n(
                          {},
                          t.SiteUrl,
                          [].concat(
                            (function (e) {
                              if (Array.isArray(e)) return Sn(e)
                            })((n = e[t.SiteUrl] || [])) ||
                              (function (e) {
                                if (
                                  ('undefined' != typeof Symbol &&
                                    null != e[Symbol.iterator]) ||
                                  null != e['@@iterator']
                                )
                                  return Array.from(e)
                              })(n) ||
                              On(n) ||
                              (function () {
                                throw new TypeError(
                                  'Invalid attempt to spread non-iterable instance.\nIn order to be iterable, non-array objects must have a [Symbol.iterator]() method.'
                                )
                              })(),
                            [t]
                          )
                        )
                      )
                      var n
                    }, {})),
                    (o = Object.entries(r).reduce(function (e, t) {
                      var n,
                        r,
                        o =
                          ((r = 2),
                          (function (e) {
                            if (Array.isArray(e)) return e
                          })((n = t)) ||
                            (function (e, t) {
                              var n =
                                null == e
                                  ? null
                                  : ('undefined' != typeof Symbol &&
                                      e[Symbol.iterator]) ||
                                    e['@@iterator']
                              if (null != n) {
                                var r,
                                  o,
                                  i,
                                  a,
                                  c = [],
                                  l = !0,
                                  u = !1
                                try {
                                  if (((i = (n = n.call(e)).next), 0 === t)) {
                                    if (Object(n) !== n) return
                                    l = !1
                                  } else
                                    for (
                                      ;
                                      !(l = (r = i.call(n)).done) &&
                                      (c.push(r.value), c.length !== t);
                                      l = !0
                                    );
                                } catch (e) {
                                  ;(u = !0), (o = e)
                                } finally {
                                  try {
                                    if (
                                      !l &&
                                      null != n.return &&
                                      ((a = n.return()), Object(a) !== a)
                                    )
                                      return
                                  } finally {
                                    if (u) throw o
                                  }
                                }
                                return c
                              }
                            })(n, r) ||
                            On(n, r) ||
                            (function () {
                              throw new TypeError(
                                'Invalid attempt to destructure non-iterable instance.\nIn order to be iterable, non-array objects must have a [Symbol.iterator]() method.'
                              )
                            })()),
                        i = o[0],
                        a = o[1]
                      return kn(
                        kn({}, e),
                        {},
                        _n(
                          {},
                          i,
                          a.sort(function (e, t) {
                            return t.IsClubItem - e.IsClubItem
                          })
                        )
                      )
                    }, {})),
                    (i.next = 8),
                    (0, dn.gz)(
                      H({ total: n.data.TotalSearchResults, items: o })
                    )
                  )
                case 8:
                  return i.abrupt('return', n.data)
                case 9:
                case 'end':
                  return i.stop()
              }
          }, An)
        }
        function Fn(e) {
          var t, n, r, o
          return Pn().wrap(function (i) {
            for (;;)
              switch ((i.prev = i.next)) {
                case 0:
                  return (
                    (t = e.payload),
                    (n = (0, xe.tV)()),
                    (i.next = 4),
                    (0, dn.RE)(bn.I, {
                      query: wn,
                      variables: { userId: t },
                      fetchPolicy: 'network-only',
                      context: {
                        usePinpoint: !0,
                        token: null == n ? void 0 : n.AccessToken,
                      },
                    })
                  )
                case 4:
                  return (
                    (r = i.sent),
                    (o = r.data),
                    (i.next = 8),
                    (0, dn.gz)(q({ feeds: o, lastUpdated: +new Date() }))
                  )
                case 8:
                case 'end':
                  return i.stop()
              }
          }, In)
        }
        function Hn(e) {
          var t, n, r, o, i, a, c, l, u
          return Pn().wrap(
            function (s) {
              for (;;)
                switch ((s.prev = s.next)) {
                  case 0:
                    ;(t = (0, xe.tV)()),
                      (n = null == t ? void 0 : t.AccessToken),
                      (r = e.payload.userId),
                      (o = e.payload.timestamp),
                      (i = hn(e.payload.newFeeds.length)),
                      (a = 0)
                  case 6:
                    if (!(a < i)) {
                      s.next = 22
                      break
                    }
                    return (
                      (c = 20 * a),
                      (l = []),
                      (l =
                        a !== i - 1
                          ? e.payload.newFeeds.slice(c, 20)
                          : e.payload.newFeeds.slice(c)),
                      (u = l.map(function (e) {
                        return {
                          NotificationDate: e.date,
                          UserId: r,
                          Notification: e.message,
                          MeetCode: e.meetCode,
                          MeetDate: e.meetDate,
                          Avatar: e.avatar,
                          LastRead: o,
                          Venue: e.trackName,
                          EntityType: e.entityType,
                          Token: e.token,
                          EntityCode: e.entityCode,
                          MeetUrl: e.link,
                          NotificationType: e.type,
                          RaceNumber: e.raceNumer,
                          Name: e.name,
                          EventType: e.eventType,
                        }
                      })),
                      (s.prev = 11),
                      (s.next = 14),
                      (0, dn.RE)(bn.J, {
                        mutation: xn,
                        variables: { list: u },
                        context: { usePinpoint: !0, token: n },
                      })
                    )
                  case 14:
                    s.next = 19
                    break
                  case 16:
                    ;(s.prev = 16), (s.t0 = s.catch(11)), console.warn(s.t0)
                  case 19:
                    ;(a += 1), (s.next = 6)
                    break
                  case 22:
                  case 'end':
                    return s.stop()
                }
            },
            Ln,
            null,
            [[11, 16]]
          )
        }
        function zn(e) {
          return (0, mn.GG)(function (t) {
            var n = document.hidden,
              r = function () {
                n = document.hidden
              }
            window.addEventListener('visibilitychange', r)
            var o = setInterval(function () {
              n || t('pull')
            }, e)
            return function () {
              window.removeEventListener('visibilitychange', r),
                clearInterval(o)
            }
          })
        }
        function Rn() {
          var e, t, n, r
          return Pn().wrap(
            function (o) {
              for (;;)
                switch ((o.prev = o.next)) {
                  case 0:
                    if (
                      ((e = (0, xe.Tq)()), (t = e.isLoggedIn), (n = e.email), t)
                    ) {
                      o.next = 3
                      break
                    }
                    return o.abrupt('return')
                  case 3:
                    return (o.next = 5), (0, dn.RE)(zn, 45e3)
                  case 5:
                    ;(r = o.sent), (o.prev = 6)
                  case 7:
                    return (o.next = 10), (0, dn.gz)(U(n))
                  case 10:
                    return (o.next = 12), (0, dn.qn)(r)
                  case 12:
                    o.next = 7
                    break
                  case 14:
                    return (o.prev = 14), (o.next = 17), (0, dn.By)()
                  case 17:
                    if (!o.sent) {
                      o.next = 19
                      break
                    }
                    r.close()
                  case 19:
                    return o.finish(14)
                  case 20:
                  case 'end':
                    return o.stop()
                }
            },
            Tn,
            null,
            [[6, , 14, 20]]
          )
        }
        function Un() {
          return Pn().wrap(function (e) {
            for (;;)
              switch ((e.prev = e.next)) {
                case 0:
                  return (e.next = 2), (0, dn.rM)(Rn)
                case 2:
                  return (e.next = 4), (0, dn.ib)(z.type, Nn)
                case 4:
                  return (e.next = 6), (0, I.W0)(F.type, Dn)
                case 6:
                  return (e.next = 8), (0, dn.ib)(U.type, Fn)
                case 8:
                  return (e.next = 10), (0, dn.ib)(Z.type, Hn)
                case 10:
                case 'end':
                  return e.stop()
              }
          }, Mn)
        }
        function Zn(e) {
          return (
            (Zn =
              'function' == typeof Symbol && 'symbol' == typeof Symbol.iterator
                ? function (e) {
                    return typeof e
                  }
                : function (e) {
                    return e &&
                      'function' == typeof Symbol &&
                      e.constructor === Symbol &&
                      e !== Symbol.prototype
                      ? 'symbol'
                      : typeof e
                  }),
            Zn(e)
          )
        }
        var qn = ['user']
        function Bn(e, t) {
          var n = Object.keys(e)
          if (Object.getOwnPropertySymbols) {
            var r = Object.getOwnPropertySymbols(e)
            t &&
              (r = r.filter(function (t) {
                return Object.getOwnPropertyDescriptor(e, t).enumerable
              })),
              n.push.apply(n, r)
          }
          return n
        }
        function Vn(e) {
          for (var t = 1; t < arguments.length; t++) {
            var n = null != arguments[t] ? arguments[t] : {}
            t % 2
              ? Bn(Object(n), !0).forEach(function (t) {
                  var r, o, i, a
                  ;(r = e),
                    (o = t),
                    (i = n[t]),
                    (a = (function (e, t) {
                      if ('object' != Zn(e) || !e) return e
                      var n = e[Symbol.toPrimitive]
                      if (void 0 !== n) {
                        var r = n.call(e, 'string')
                        if ('object' != Zn(r)) return r
                        throw new TypeError(
                          '@@toPrimitive must return a primitive value.'
                        )
                      }
                      return String(e)
                    })(o)),
                    (o = 'symbol' == Zn(a) ? a : String(a)) in r
                      ? Object.defineProperty(r, o, {
                          value: i,
                          enumerable: !0,
                          configurable: !0,
                          writable: !0,
                        })
                      : (r[o] = i)
                })
              : Object.getOwnPropertyDescriptors
              ? Object.defineProperties(e, Object.getOwnPropertyDescriptors(n))
              : Bn(Object(n)).forEach(function (t) {
                  Object.defineProperty(
                    e,
                    t,
                    Object.getOwnPropertyDescriptor(n, t)
                  )
                })
          }
          return e
        }
        var Wn = function (e) {
          var t = e.config,
            n = void 0 === t ? {} : t,
            r = (0, $.J)(
              (0, We.n)('Auth0NeedAccessToken', !1),
              (0, We.n)('Auth0FeatureToggle', !1),
              {
                legacyLoginWithPopupUrl: (0, We.n)('Auth0LoginEndpoint', ''),
                legacyLoginWithRedirectUrl: (0, We.n)('Auth0LoginEndpoint', ''),
                legacyLogoutUrl: (0, We.n)('Auth0LogoutEndpoint', ''),
              }
            ),
            i = r.user,
            a = (function (e, t) {
              if (null == e) return {}
              var n,
                r,
                o = (function (e, t) {
                  if (null == e) return {}
                  var n,
                    r,
                    o = {},
                    i = Object.keys(e)
                  for (r = 0; r < i.length; r++)
                    (n = i[r]), t.indexOf(n) >= 0 || (o[n] = e[n])
                  return o
                })(e, t)
              if (Object.getOwnPropertySymbols) {
                var i = Object.getOwnPropertySymbols(e)
                for (r = 0; r < i.length; r++)
                  (n = i[r]),
                    t.indexOf(n) >= 0 ||
                      (Object.prototype.propertyIsEnumerable.call(e, n) &&
                        (o[n] = e[n]))
              }
              return o
            })(r, qn)
          n.authentication || (n.authentication = a),
            n.user || (n.user = i),
            (0, s.vp)({ key: B, reducer: V }),
            (0, s.hb)({ key: B, saga: Un })
          var c = (0, f.Ln)(),
            m = null == n ? void 0 : n.isRacingPhotos
          return o().createElement(
            d.Provider,
            { value: n },
            o().createElement(
              l.xu,
              {
                as: 'header',
                sx: Vn({ position: 'relative', zIndex: 100 }, p.hq),
              },
              o().createElement(
                l.xu,
                { sx: { backgroundColor: m ? '#006da6' : 'grey-33' } },
                o().createElement(
                  u.Z,
                  null,
                  c ? o().createElement(dt, null) : o().createElement(un, null)
                )
              )
            )
          )
        }
        Wn.propTypes = { config: c().object }
        const Gn = Wn
        var Qn = n(96331)
        function Yn() {
          return (
            (Yn = Object.assign
              ? Object.assign.bind()
              : function (e) {
                  for (var t = 1; t < arguments.length; t++) {
                    var n = arguments[t]
                    for (var r in n)
                      Object.prototype.hasOwnProperty.call(n, r) &&
                        (e[r] = n[r])
                  }
                  return e
                }),
            Yn.apply(this, arguments)
          )
        }
        const Xn = (0, i.w)(function (e) {
          var t = Yn(
            {},
            ((function (e) {
              if (null == e) throw new TypeError('Cannot destructure ' + e)
            })(e),
            e)
          )
          return o().createElement(Qn.Z, null, o().createElement(Gn, t))
        })
      },
      25301: (e, t, n) => {
        'use strict'
        n.d(t, { Z: () => i })
        var r = n(82609),
          o = n.n(r)()(function (e) {
            return e[1]
          })
        o.push([
          e.id,
          '.NJ\\+nwev9aLWuuE9gXIAmrg\\=\\={display:flex;align-items:flex-start;justify-content:flex-start}.ljCSqeAfhGqAroslX21geQ\\=\\={margin-right:1rem;display:block;height:3rem;width:3rem;overflow:hidden;border-radius:9999px;flex:0 0 auto;background-color:#f5f5f5}._4XMVdWL2R2zgnXcG\\+ZMU5g\\=\\={flex:1 1 auto;--tw-text-opacity:1;color:rgba(51,51,51,var(--tw-text-opacity))}.oUFLmoy4yLGa0SH0V9h9Aw\\=\\={margin-bottom:.5rem;display:block;line-height:1.25;font-family:Roboto,Helvetica Neue,Helvetica,Arial,sans-serif;--tw-text-opacity:1;color:rgba(51,51,51,var(--tw-text-opacity))}.oUFLmoy4yLGa0SH0V9h9Aw\\=\\=:hover{--tw-text-opacity:1;color:rgba(237,28,36,var(--tw-text-opacity))}.oUFLmoy4yLGa0SH0V9h9Aw\\=\\={transition-property:background-color,border-color,color,fill,stroke;transition-timing-function:cubic-bezier(.4,0,.2,1);transition-duration:.15s;transition-duration:.3s;transition-timing-function:cubic-bezier(0,0,.2,1);font-size:12px;cursor:pointer}.MDH99Y4HKeV5IsrdsVIDZw\\=\\={font-size:10px;}.HvFzF5cqSIBPZphhwVBh5g\\=\\= .MDH99Y4HKeV5IsrdsVIDZw\\=\\={--tw-text-opacity:1;color:rgba(237,28,36,var(--tw-text-opacity));}.HvFzF5cqSIBPZphhwVBh5g\\=\\= .MDH99Y4HKeV5IsrdsVIDZw\\=\\=:after{margin-left:.5rem;display:inline-block;border-radius:9999px;--tw-bg-opacity:1;background-color:rgba(237,28,36,var(--tw-bg-opacity));content:"";width:8px;height:8px}._8Ane\\+bvIRrfKOUH4hb6PFQ\\=\\= .MDH99Y4HKeV5IsrdsVIDZw\\=\\={color:#999!important}.jfO9DxCma8G3OiCUvDFW3g\\=\\={pointer-events:none;cursor:pointer}',
          '',
        ]),
          (o.locals = {
            'rdc-notification-feed-item': 'NJ+nwev9aLWuuE9gXIAmrg==',
            'rdc-notification-feed-item__avatar': 'ljCSqeAfhGqAroslX21geQ==',
            'rdc-notification-feed-item__detail': '_4XMVdWL2R2zgnXcG+ZMU5g==',
            'rdc-notification-feed-item__title': 'oUFLmoy4yLGa0SH0V9h9Aw==',
            'rdc-notification-feed-item__datetime': 'MDH99Y4HKeV5IsrdsVIDZw==',
            'rdc-notification-feed-item--new': 'HvFzF5cqSIBPZphhwVBh5g==',
            'rdc-notification-feed-item--old': '_8Ane+bvIRrfKOUH4hb6PFQ==',
            'click-disabled': 'jfO9DxCma8G3OiCUvDFW3g==',
          })
        const i = o
      },
      36921: (e, t, n) => {
        'use strict'
        n.d(t, { Z: () => i })
        var r = n(82609),
          o = n.n(r)()(function (e) {
            return e[1]
          })
        o.push([
          e.id,
          '.vMAMiuaVfmxzKexZLK3KjA\\=\\={display:flex;align-items:center;position:relative;height:45px;padding-right:5px}.QBmDiHXv8DEwPdyfpoTLjQ\\=\\={pointer-events:none;top:1rem;right:0;height:1.5rem;width:1.5rem;position:absolute;display:inline-flex;align-items:center;justify-content:center;border-radius:9999px;--tw-bg-opacity:1;background-color:rgba(237,28,36,var(--tw-bg-opacity));--tw-text-opacity:1;color:rgba(255,255,255,var(--tw-text-opacity));font-family:Circular,Helvetica Neue,Helvetica,Arial,sans-serif;font-size:10px}.U3Iw6dnFq1yEHHw\\+uA0hDA\\=\\={--tw-bg-opacity:1;background-color:rgba(255,255,255,var(--tw-bg-opacity));position:absolute;transition-property:background-color,border-color,color,fill,stroke,opacity,box-shadow,transform,filter,-webkit-backdrop-filter;transition-property:background-color,border-color,color,fill,stroke,opacity,box-shadow,transform,filter,backdrop-filter;transition-property:background-color,border-color,color,fill,stroke,opacity,box-shadow,transform,filter,backdrop-filter,-webkit-backdrop-filter;transition-timing-function:cubic-bezier(.4,0,.2,1);transition-duration:.15s;transition-duration:.3s;transition-timing-function:cubic-bezier(0,0,.2,1);width:400px;z-index:-1;right:-150px;bottom:10px;box-shadow:0 0 5px 0 rgba(0,0,0,.2);transform:translateY(0);}.JSItdX7dg4flWTrpgDfiqQ\\=\\= .U3Iw6dnFq1yEHHw\\+uA0hDA\\=\\=,.K-0O1-EikQrSCB4IxYZ3VQ\\=\\= .U3Iw6dnFq1yEHHw\\+uA0hDA\\=\\={transform:translateY(100%) translateY(10px)}.K-0O1-EikQrSCB4IxYZ3VQ\\=\\= .U3Iw6dnFq1yEHHw\\+uA0hDA\\=\\={max-height:240px}.U3Iw6dnFq1yEHHw\\+uA0hDA\\=\\=:after{right:0;bottom:0;left:0;display:block;height:4rem;position:absolute;background:linear-gradient(180deg,hsla(0,0%,100%,0) 0,#fff);content:""}.Z0VJ67lbRmb8X7jhg8HB5Q\\=\\={padding:3rem 2rem;min-height:275px;max-height:calc(100vh - 200px);overflow-y:auto}._8w21-oWiqtNOyp5-39jOCQ\\=\\={margin-bottom:2rem;display:flex;align-items:center;font-family:Roboto,Helvetica Neue,Helvetica,Arial,sans-serif;font-weight:700;--tw-text-opacity:1;color:rgba(153,153,153,var(--tw-text-opacity));font-size:20px}.SePbJE-tdda8eEj3GKCtZQ\\=\\=>:not([hidden])~:not([hidden]){--tw-space-y-reverse:0;margin-top:calc(1.5rem*(1 - var(--tw-space-y-reverse)));margin-bottom:calc(1.5rem*var(--tw-space-y-reverse))}.SePbJE-tdda8eEj3GKCtZQ\\=\\=+.SePbJE-tdda8eEj3GKCtZQ\\=\\={margin-top:2rem}.Y3Pf3ou0nNxVWNlJbOCtJw\\=\\={font-family:Circular,Helvetica Neue,Helvetica,Arial,sans-serif;font-weight:700;--tw-text-opacity:1;color:rgba(102,102,102,var(--tw-text-opacity));font-size:14px}.kM88Dc8WfGIARLdWMZBjUQ\\=\\={flex:1 1 auto;--tw-text-opacity:1;color:rgba(51,51,51,var(--tw-text-opacity));font-size:12px}',
          '',
        ]),
          (o.locals = {
            'rdc-notification-feed': 'vMAMiuaVfmxzKexZLK3KjA==',
            'rdc-notification-feed__unread': 'QBmDiHXv8DEwPdyfpoTLjQ==',
            'rdc-notification-feed__wrap': 'U3Iw6dnFq1yEHHw+uA0hDA==',
            'rdc-notification-feed--active': 'JSItdX7dg4flWTrpgDfiqQ==',
            'rdc-notification-feed--active-empty': 'K-0O1-EikQrSCB4IxYZ3VQ==',
            'rdc-notification-feed__content': 'Z0VJ67lbRmb8X7jhg8HB5Q==',
            'rdc-notification-feed__title': '_8w21-oWiqtNOyp5-39jOCQ==',
            'rdc-notification-feed__group': 'SePbJE-tdda8eEj3GKCtZQ==',
            'rdc-notification-feed__group-label': 'Y3Pf3ou0nNxVWNlJbOCtJw==',
            'rdc-notification-feed__group-detail': 'kM88Dc8WfGIARLdWMZBjUQ==',
          })
        const i = o
      },
      79548: (e, t, n) => {
        'use strict'
        n.d(t, { Z: () => i })
        var r = n(82609),
          o = n.n(r)()(function (e) {
            return e[1]
          })
        o.push([
          e.id,
          '.HA0irlDG1vt5FXxSm2UjcA\\=\\={display:flex;align-items:center;position:relative;height:45px;padding-right:5px}.-YHgP9o-epztG4HDVz95eQ\\=\\={pointer-events:none;top:1rem;right:0;height:1.5rem;width:1.5rem;position:absolute;display:inline-flex;align-items:center;justify-content:center;border-radius:9999px;--tw-bg-opacity:1;background-color:rgba(237,28,36,var(--tw-bg-opacity));--tw-text-opacity:1;color:rgba(255,255,255,var(--tw-text-opacity));font-family:Circular,Helvetica Neue,Helvetica,Arial,sans-serif;font-size:10px}.BDDphbmjxoUTHEjwmf3TEQ\\=\\={bottom:0;left:0;width:100%;--tw-bg-opacity:1;background-color:rgba(255,255,255,var(--tw-bg-opacity));padding-top:3.5rem;position:fixed;transition-property:background-color,border-color,color,fill,stroke,opacity,box-shadow,transform,filter,-webkit-backdrop-filter;transition-property:background-color,border-color,color,fill,stroke,opacity,box-shadow,transform,filter,backdrop-filter;transition-property:background-color,border-color,color,fill,stroke,opacity,box-shadow,transform,filter,backdrop-filter,-webkit-backdrop-filter;transition-timing-function:cubic-bezier(.4,0,.2,1);transition-duration:.15s;transition-duration:.5s;transition-timing-function:cubic-bezier(0,0,.2,1);z-index:-1;top:40px;transform:translateX(100%);}._8yzvCLA5XaPxc-IArOGQqQ\\=\\= .BDDphbmjxoUTHEjwmf3TEQ\\=\\={transform:translateX(0)}.BDDphbmjxoUTHEjwmf3TEQ\\=\\=:after{right:0;bottom:0;left:0;display:block;height:4rem;position:absolute;background:linear-gradient(180deg,hsla(0,0%,100%,0) 0,#fff);content:""}._5To5FtNbpSdv157ru66BjQ\\=\\={height:100%;padding-left:2rem;padding-right:2rem;padding-bottom:3rem;overflow-y:auto}.qgxY3hv3BUu9pCwKl-2MgQ\\=\\={margin-bottom:2rem;display:flex;align-items:center;font-family:Roboto,Helvetica Neue,Helvetica,Arial,sans-serif;font-weight:700;--tw-text-opacity:1;color:rgba(153,153,153,var(--tw-text-opacity));font-size:20px}.fDRJEqlduu8jkW46rurl\\+Q\\=\\=>:not([hidden])~:not([hidden]){--tw-space-y-reverse:0;margin-top:calc(1.5rem*(1 - var(--tw-space-y-reverse)));margin-bottom:calc(1.5rem*var(--tw-space-y-reverse))}.fDRJEqlduu8jkW46rurl\\+Q\\=\\=+.fDRJEqlduu8jkW46rurl\\+Q\\=\\={margin-top:2rem}.HTjyrnFmy8FPZOqSuku0kA\\=\\={font-family:Circular,Helvetica Neue,Helvetica,Arial,sans-serif;font-weight:700;--tw-text-opacity:1;color:rgba(102,102,102,var(--tw-text-opacity));font-size:14px}._2Rb\\+w7lhseRlyjwCU4HkVQ\\=\\={flex:1 1 auto;--tw-text-opacity:1;color:rgba(51,51,51,var(--tw-text-opacity));font-size:12px}',
          '',
        ]),
          (o.locals = {
            'rdc-notification-feed': 'HA0irlDG1vt5FXxSm2UjcA==',
            'rdc-notification-feed__unread': '-YHgP9o-epztG4HDVz95eQ==',
            'rdc-notification-feed__wrap': 'BDDphbmjxoUTHEjwmf3TEQ==',
            'rdc-notification-feed--active': '_8yzvCLA5XaPxc-IArOGQqQ==',
            'rdc-notification-feed__content': '_5To5FtNbpSdv157ru66BjQ==',
            'rdc-notification-feed__title': 'qgxY3hv3BUu9pCwKl-2MgQ==',
            'rdc-notification-feed__group': 'fDRJEqlduu8jkW46rurl+Q==',
            'rdc-notification-feed__group-label': 'HTjyrnFmy8FPZOqSuku0kA==',
            'rdc-notification-feed__group-detail': '_2Rb+w7lhseRlyjwCU4HkVQ==',
          })
        const i = o
      },
      1024: (t) => {
        'use strict'
        t.exports = e
      },
      30314: (e) => {
        'use strict'
        e.exports = t
      },
      66538: () => {},
      50633: () => {},
      53260: () => {},
    },
    (e) => (e.O(0, [736, 351], () => (54249, e((e.s = 54249)))), e.O()),
  ])
)

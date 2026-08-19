/*! For license information please see rdc.blackbookTopRunners.js.LICENSE.txt */
!(function (t, e) {
  'object' == typeof exports && 'object' == typeof module
    ? (module.exports = e(require('React'), require('ReactDOM')))
    : 'function' == typeof define && define.amd
    ? define(['React', 'ReactDOM'], e)
    : 'object' == typeof exports
    ? (exports.rdc = e(require('React'), require('ReactDOM')))
    : ((t.rdc = t.rdc || {}),
      (t.rdc.blackbookTopRunners = e(t.React, t.ReactDOM)))
})(self, (t, e) =>
  (self.webpackChunkrdc = self.webpackChunkrdc || []).push([
    [723],
    {
      58253: (t, e, r) => {
        'use strict'
        r.d(e, { Z: () => b })
        var n = r(1024),
          o = r.n(n),
          a = r(85226),
          i = r(71701),
          s = r(46062),
          c = r.n(s),
          l = r(75759),
          u = {
            injectType: 'singletonStyleTag',
            insert: function (t) {
              var e = document.querySelector('head'),
                r = document.querySelector('#rdc-tailwind-css'),
                n = window._lastElementInsertedByStyleLoader
              n
                ? n.nextSibling
                  ? e.insertBefore(t, n.nextSibling)
                  : e.appendChild(t)
                : e.insertBefore(t, r),
                (window._lastElementInsertedByStyleLoader = t)
            },
            singleton: !0,
          }
        c()(l.Z, u), l.Z.locals
        const d = function (t) {
          var e = t.isSmallSize,
            r = void 0 !== e && e,
            n = t.isFavourite,
            a = t.isMover
          return n
            ? o().createElement(
                'div',
                {
                  className:
                    'flex justify-center box-border bg-grey-66 '.concat(
                      r ? 'h-3' : 'h-4'
                    ),
                },
                o().createElement(
                  i.Z,
                  {
                    tx: {
                      root: ''.concat(
                        r
                          ? 'form2__odds-box__badge-fav--tablet-portrait'
                          : 'form2__odds-box__badge-fav'
                      ),
                    },
                  },
                  'FAVOURITE'
                )
              )
            : a
            ? o().createElement(
                'div',
                { className: 'flex justify-center box-border bg-grey-88 h-4' },
                o().createElement(
                  i.Z,
                  {
                    tx: {
                      root: ''.concat(
                        r
                          ? 'form2__odds-box__badge-mov--tablet-portrait'
                          : 'form2__odds-box__badge-mov'
                      ),
                    },
                  },
                  'MOVER'
                )
              )
            : null
        }
        var f = r(12524),
          h = r.n(f),
          p = r(32367),
          y = {
            injectType: 'singletonStyleTag',
            insert: function (t) {
              var e = document.querySelector('head'),
                r = document.querySelector('#rdc-tailwind-css'),
                n = window._lastElementInsertedByStyleLoader
              n
                ? n.nextSibling
                  ? e.insertBefore(t, n.nextSibling)
                  : e.appendChild(t)
                : e.insertBefore(t, r),
                (window._lastElementInsertedByStyleLoader = t)
            },
            singleton: !0,
          }
        c()(p.Z, y)
        const m = p.Z.locals || {},
          b = function (t) {
            var e = t.isSmallSize,
              r = void 0 !== e && e,
              n = t.scratched,
              s = t.oddsIsFavouriteWin,
              c = t.oddsIsMarketMover,
              l = void 0 !== c && c,
              u = t.oddsWin,
              f = t.oddsPlace,
              p = t.oddsLink,
              y = t.noBorder,
              b = void 0 !== y && y,
              v = t.noBold,
              g = void 0 !== v && v,
              j = null != p
            function w() {
              trackCustomAction('Sportsbet', 'Tipstabform', null, 'betclick'),
                j && window.open(p, '_blank')
            }
            var x = !s && l
            return n
              ? o().createElement(
                  'div',
                  {
                    className: ''.concat(
                      r
                        ? h()(m['rdc-odds-box__scratched1--tablet-portrait'])
                        : h()(m['rdc-odds-box'], 'w-32')
                    ),
                  },
                  o().createElement(
                    'div',
                    {
                      className: ''.concat(
                        r
                          ? m['rdc-odds-box__scratched2--tablet-portrait']
                          : m['rdc-odds-box__scratched']
                      ),
                    },
                    o().createElement(
                      i.Z,
                      { tx: { root: 'text-xl' } },
                      o().createElement('strong', null, 'SCR')
                    )
                  )
                )
              : o().createElement(
                  'div',
                  {
                    className: h()(m['rdc-odds-box'], 'w-32'),
                    style: { position: 'relative' },
                  },
                  o().createElement(
                    a.Z,
                    {
                      condition: j,
                      wrapper: function (t) {
                        return o().createElement(
                          'a',
                          {
                            style: { cursor: 'pointer' },
                            onClick: w,
                            rel: 'noreferrer',
                          },
                          t
                        )
                      },
                    },
                    (!s && !x) || b
                      ? null
                      : o().createElement(
                          'div',
                          {
                            className: ''.concat(
                              r
                                ? m['rdc-odds-box__badge--tablet-portrait']
                                : m['rdc-odds-box__badge']
                            ),
                          },
                          o().createElement(d, {
                            isSmallSize: r,
                            isMover: x,
                            isFavourite: s,
                          })
                        ),
                    o().createElement(
                      'div',
                      {
                        className: ''
                          .concat(
                            r
                              ? m['rdc-odds-box--tablet-portrait']
                              : m['rdc-odds-box'],
                            ' '
                          )
                          .concat(b ? m['rdc-odds-box--no-border'] : '', ' ')
                          .concat(
                            s && !b ? m['rdc-odds-box__favorite'] : '',
                            ' '
                          )
                          .concat(x && !b ? m['rdc-odds-box__mover'] : ''),
                      },
                      o().createElement(
                        'div',
                        { className: 'mx-2 flex' },
                        o().createElement(
                          'div',
                          {
                            className:
                              'w-full text-left' + (g ? '' : ' font-bold'),
                          },
                          o().createElement(
                            i.Z,
                            { tx: { root: m['rdc-odds-box__text'] } },
                            'W'
                          )
                        ),
                        o().createElement(
                          'div',
                          { className: 'w-full text-right' },
                          u
                            ? o().createElement(
                                i.Z,
                                {
                                  tx: {
                                    root: h()(
                                      'font-bold',
                                      m['rdc-odds-box__text']
                                    ),
                                  },
                                },
                                u
                              )
                            : o().createElement(i.Z, null, '–')
                        )
                      ),
                      o().createElement(
                        'div',
                        { className: 'mx-2 flex' },
                        o().createElement(
                          'div',
                          { className: 'w-full text-left' },
                          o().createElement(
                            i.Z,
                            { tx: { root: m['rdc-odds-box__text'] } },
                            'P'
                          )
                        ),
                        o().createElement(
                          'div',
                          { className: 'w-full text-right' },
                          f
                            ? o().createElement(
                                i.Z,
                                { tx: { root: m['rdc-odds-box__text'] } },
                                f
                              )
                            : o().createElement(i.Z, null, '–')
                        )
                      )
                    )
                  )
                )
          }
      },
      81150: (t, e, r) => {
        'use strict'
        r.r(e), r.d(e, { default: () => Y })
        var n,
          o,
          a,
          i = r(1024),
          s = r.n(i),
          c = r(71570),
          l = r(96331),
          u = r(13295),
          d = r(98662),
          f = r(27422),
          h = r(38847),
          p = r(2738),
          y = r(67834)
        function m(t, e) {
          return (
            e || (e = t.slice(0)),
            Object.freeze(
              Object.defineProperties(t, { raw: { value: Object.freeze(e) } })
            )
          )
        }
        var b = (0, y.Ps)(
          n ||
            (n = m([
              '\n  query getBlackbook_PP($email: String!) {\n    getNotificationsFollowsForUser(Email: $email) {\n      items {\n        Email\n        EntityCode\n        EntityType\n        EntityType_EntityCode\n      }\n    }\n  }\n',
            ]))
        )
        function v(t) {
          return (
            (v =
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
            v(t)
          )
        }
        function g() {
          g = function () {
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
            a = 'function' == typeof Symbol ? Symbol : {},
            i = a.iterator || '@@iterator',
            s = a.asyncIterator || '@@asyncIterator',
            c = a.toStringTag || '@@toStringTag'
          function l(t, e, r) {
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
            l({}, '')
          } catch (t) {
            l = function (t, e, r) {
              return (t[e] = r)
            }
          }
          function u(t, e, r, n) {
            var a = e && e.prototype instanceof b ? e : b,
              i = Object.create(a.prototype),
              s = new A(n || [])
            return o(i, '_invoke', { value: S(t, r, s) }), i
          }
          function d(t, e, r) {
            try {
              return { type: 'normal', arg: t.call(e, r) }
            } catch (t) {
              return { type: 'throw', arg: t }
            }
          }
          e.wrap = u
          var f = 'suspendedStart',
            h = 'suspendedYield',
            p = 'executing',
            y = 'completed',
            m = {}
          function b() {}
          function j() {}
          function w() {}
          var x = {}
          l(x, i, function () {
            return this
          })
          var E = Object.getPrototypeOf,
            k = E && E(E(F([])))
          k && k !== r && n.call(k, i) && (x = k)
          var _ = (w.prototype = b.prototype = Object.create(x))
          function O(t) {
            ;['next', 'throw', 'return'].forEach(function (e) {
              l(t, e, function (t) {
                return this._invoke(e, t)
              })
            })
          }
          function L(t, e) {
            function r(o, a, i, s) {
              var c = d(t[o], t, a)
              if ('throw' !== c.type) {
                var l = c.arg,
                  u = l.value
                return u && 'object' == v(u) && n.call(u, '__await')
                  ? e.resolve(u.__await).then(
                      function (t) {
                        r('next', t, i, s)
                      },
                      function (t) {
                        r('throw', t, i, s)
                      }
                    )
                  : e.resolve(u).then(
                      function (t) {
                        ;(l.value = t), i(l)
                      },
                      function (t) {
                        return r('throw', t, i, s)
                      }
                    )
              }
              s(c.arg)
            }
            var a
            o(this, '_invoke', {
              value: function (t, n) {
                function o() {
                  return new e(function (e, o) {
                    r(t, n, e, o)
                  })
                }
                return (a = a ? a.then(o, o) : o())
              },
            })
          }
          function S(e, r, n) {
            var o = f
            return function (a, i) {
              if (o === p) throw new Error('Generator is already running')
              if (o === y) {
                if ('throw' === a) throw i
                return { value: t, done: !0 }
              }
              for (n.method = a, n.arg = i; ; ) {
                var s = n.delegate
                if (s) {
                  var c = N(s, n)
                  if (c) {
                    if (c === m) continue
                    return c
                  }
                }
                if ('next' === n.method) n.sent = n._sent = n.arg
                else if ('throw' === n.method) {
                  if (o === f) throw ((o = y), n.arg)
                  n.dispatchException(n.arg)
                } else 'return' === n.method && n.abrupt('return', n.arg)
                o = p
                var l = d(e, r, n)
                if ('normal' === l.type) {
                  if (((o = n.done ? y : h), l.arg === m)) continue
                  return { value: l.arg, done: n.done }
                }
                'throw' === l.type &&
                  ((o = y), (n.method = 'throw'), (n.arg = l.arg))
              }
            }
          }
          function N(e, r) {
            var n = r.method,
              o = e.iterator[n]
            if (o === t)
              return (
                (r.delegate = null),
                ('throw' === n &&
                  e.iterator.return &&
                  ((r.method = 'return'),
                  (r.arg = t),
                  N(e, r),
                  'throw' === r.method)) ||
                  ('return' !== n &&
                    ((r.method = 'throw'),
                    (r.arg = new TypeError(
                      "The iterator does not provide a '" + n + "' method"
                    )))),
                m
              )
            var a = d(o, e.iterator, r.arg)
            if ('throw' === a.type)
              return (
                (r.method = 'throw'), (r.arg = a.arg), (r.delegate = null), m
              )
            var i = a.arg
            return i
              ? i.done
                ? ((r[e.resultName] = i.value),
                  (r.next = e.nextLoc),
                  'return' !== r.method && ((r.method = 'next'), (r.arg = t)),
                  (r.delegate = null),
                  m)
                : i
              : ((r.method = 'throw'),
                (r.arg = new TypeError('iterator result is not an object')),
                (r.delegate = null),
                m)
          }
          function P(t) {
            var e = { tryLoc: t[0] }
            1 in t && (e.catchLoc = t[1]),
              2 in t && ((e.finallyLoc = t[2]), (e.afterLoc = t[3])),
              this.tryEntries.push(e)
          }
          function z(t) {
            var e = t.completion || {}
            ;(e.type = 'normal'), delete e.arg, (t.completion = e)
          }
          function A(t) {
            ;(this.tryEntries = [{ tryLoc: 'root' }]),
              t.forEach(P, this),
              this.reset(!0)
          }
          function F(e) {
            if (e || '' === e) {
              var r = e[i]
              if (r) return r.call(e)
              if ('function' == typeof e.next) return e
              if (!isNaN(e.length)) {
                var o = -1,
                  a = function r() {
                    for (; ++o < e.length; )
                      if (n.call(e, o))
                        return (r.value = e[o]), (r.done = !1), r
                    return (r.value = t), (r.done = !0), r
                  }
                return (a.next = a)
              }
            }
            throw new TypeError(v(e) + ' is not iterable')
          }
          return (
            (j.prototype = w),
            o(_, 'constructor', { value: w, configurable: !0 }),
            o(w, 'constructor', { value: j, configurable: !0 }),
            (j.displayName = l(w, c, 'GeneratorFunction')),
            (e.isGeneratorFunction = function (t) {
              var e = 'function' == typeof t && t.constructor
              return (
                !!e &&
                (e === j || 'GeneratorFunction' === (e.displayName || e.name))
              )
            }),
            (e.mark = function (t) {
              return (
                Object.setPrototypeOf
                  ? Object.setPrototypeOf(t, w)
                  : ((t.__proto__ = w), l(t, c, 'GeneratorFunction')),
                (t.prototype = Object.create(_)),
                t
              )
            }),
            (e.awrap = function (t) {
              return { __await: t }
            }),
            O(L.prototype),
            l(L.prototype, s, function () {
              return this
            }),
            (e.AsyncIterator = L),
            (e.async = function (t, r, n, o, a) {
              void 0 === a && (a = Promise)
              var i = new L(u(t, r, n, o), a)
              return e.isGeneratorFunction(r)
                ? i
                : i.next().then(function (t) {
                    return t.done ? t.value : i.next()
                  })
            }),
            O(_),
            l(_, c, 'Generator'),
            l(_, i, function () {
              return this
            }),
            l(_, 'toString', function () {
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
            (e.values = F),
            (A.prototype = {
              constructor: A,
              reset: function (e) {
                if (
                  ((this.prev = 0),
                  (this.next = 0),
                  (this.sent = this._sent = t),
                  (this.done = !1),
                  (this.delegate = null),
                  (this.method = 'next'),
                  (this.arg = t),
                  this.tryEntries.forEach(z),
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
                    (s.type = 'throw'),
                    (s.arg = e),
                    (r.next = n),
                    o && ((r.method = 'next'), (r.arg = t)),
                    !!o
                  )
                }
                for (var a = this.tryEntries.length - 1; a >= 0; --a) {
                  var i = this.tryEntries[a],
                    s = i.completion
                  if ('root' === i.tryLoc) return o('end')
                  if (i.tryLoc <= this.prev) {
                    var c = n.call(i, 'catchLoc'),
                      l = n.call(i, 'finallyLoc')
                    if (c && l) {
                      if (this.prev < i.catchLoc) return o(i.catchLoc, !0)
                      if (this.prev < i.finallyLoc) return o(i.finallyLoc)
                    } else if (c) {
                      if (this.prev < i.catchLoc) return o(i.catchLoc, !0)
                    } else {
                      if (!l)
                        throw new Error(
                          'try statement without catch or finally'
                        )
                      if (this.prev < i.finallyLoc) return o(i.finallyLoc)
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
                    var a = o
                    break
                  }
                }
                a &&
                  ('break' === t || 'continue' === t) &&
                  a.tryLoc <= e &&
                  e <= a.finallyLoc &&
                  (a = null)
                var i = a ? a.completion : {}
                return (
                  (i.type = t),
                  (i.arg = e),
                  a
                    ? ((this.method = 'next'), (this.next = a.finallyLoc), m)
                    : this.complete(i)
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
                  m
                )
              },
              finish: function (t) {
                for (var e = this.tryEntries.length - 1; e >= 0; --e) {
                  var r = this.tryEntries[e]
                  if (r.finallyLoc === t)
                    return this.complete(r.completion, r.afterLoc), z(r), m
                }
              },
              catch: function (t) {
                for (var e = this.tryEntries.length - 1; e >= 0; --e) {
                  var r = this.tryEntries[e]
                  if (r.tryLoc === t) {
                    var n = r.completion
                    if ('throw' === n.type) {
                      var o = n.arg
                      z(r)
                    }
                    return o
                  }
                }
                throw new Error('illegal catch attempt')
              },
              delegateYield: function (e, r, n) {
                return (
                  (this.delegate = {
                    iterator: F(e),
                    resultName: r,
                    nextLoc: n,
                  }),
                  'next' === this.method && (this.arg = t),
                  m
                )
              },
            }),
            e
          )
        }
        ;(0, y.Ps)(
          o ||
            (o = m([
              '\n  mutation createBlackbook_PP($input: CreateNotificationsFollowInput!) {\n    createNotificationsFollow(input: $input) {\n      EntityType\n      EntityCode\n      Email\n      EntityType_EntityCode\n    }\n  }\n',
            ]))
        ),
          (0, y.Ps)(
            a ||
              (a = m([
                '\n  mutation deleteBlackbook_PP($input: DeleteNotificationsFollowInput!) {\n    deleteNotificationsFollow(input: $input) {\n      EntityType\n      EntityCode\n      Email\n      EntityType_EntityCode\n    }\n  }\n',
              ]))
          )
        var j = g().mark(E),
          w = g().mark(k),
          x = 'BlackbookTopRunners/LoadBlackbook'
        function E(t) {
          var e, r, n, o, a
          return g().wrap(function (i) {
            for (;;)
              switch ((i.prev = i.next)) {
                case 0:
                  return (
                    (r = t.payload.email),
                    (n = (0, p.tV)()),
                    (i.next = 4),
                    (0, f.RE)(h.I, {
                      query: b,
                      variables: { email: r },
                      fetchPolicy: 'network-only',
                      context: {
                        useBlackbook: !0,
                        token: null == n ? void 0 : n.AccessToken,
                      },
                    })
                  )
                case 4:
                  return (
                    (o = i.sent),
                    (a = o.data),
                    i.abrupt('return', {
                      data:
                        null == a ||
                        null === (e = a.getNotificationsFollowsForUser) ||
                        void 0 === e
                          ? void 0
                          : e.items,
                    })
                  )
                case 7:
                case 'end':
                  return i.stop()
              }
          }, j)
        }
        function k() {
          return g().wrap(function (t) {
            for (;;)
              switch ((t.prev = t.next)) {
                case 0:
                  return (t.next = 2), (0, d.W0)(x, E)
                case 2:
                case 'end':
                  return t.stop()
              }
          }, w)
        }
        var _ = r(85814),
          O = r(30186),
          L = r(44962),
          S = r(40163),
          N = r(1349)
        function P(t) {
          return (
            (P =
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
            P(t)
          )
        }
        function z() {
          z = function () {
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
            a = 'function' == typeof Symbol ? Symbol : {},
            i = a.iterator || '@@iterator',
            s = a.asyncIterator || '@@asyncIterator',
            c = a.toStringTag || '@@toStringTag'
          function l(t, e, r) {
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
            l({}, '')
          } catch (t) {
            l = function (t, e, r) {
              return (t[e] = r)
            }
          }
          function u(t, e, r, n) {
            var a = e && e.prototype instanceof b ? e : b,
              i = Object.create(a.prototype),
              s = new A(n || [])
            return o(i, '_invoke', { value: O(t, r, s) }), i
          }
          function d(t, e, r) {
            try {
              return { type: 'normal', arg: t.call(e, r) }
            } catch (t) {
              return { type: 'throw', arg: t }
            }
          }
          e.wrap = u
          var f = 'suspendedStart',
            h = 'suspendedYield',
            p = 'executing',
            y = 'completed',
            m = {}
          function b() {}
          function v() {}
          function g() {}
          var j = {}
          l(j, i, function () {
            return this
          })
          var w = Object.getPrototypeOf,
            x = w && w(w(F([])))
          x && x !== r && n.call(x, i) && (j = x)
          var E = (g.prototype = b.prototype = Object.create(j))
          function k(t) {
            ;['next', 'throw', 'return'].forEach(function (e) {
              l(t, e, function (t) {
                return this._invoke(e, t)
              })
            })
          }
          function _(t, e) {
            function r(o, a, i, s) {
              var c = d(t[o], t, a)
              if ('throw' !== c.type) {
                var l = c.arg,
                  u = l.value
                return u && 'object' == P(u) && n.call(u, '__await')
                  ? e.resolve(u.__await).then(
                      function (t) {
                        r('next', t, i, s)
                      },
                      function (t) {
                        r('throw', t, i, s)
                      }
                    )
                  : e.resolve(u).then(
                      function (t) {
                        ;(l.value = t), i(l)
                      },
                      function (t) {
                        return r('throw', t, i, s)
                      }
                    )
              }
              s(c.arg)
            }
            var a
            o(this, '_invoke', {
              value: function (t, n) {
                function o() {
                  return new e(function (e, o) {
                    r(t, n, e, o)
                  })
                }
                return (a = a ? a.then(o, o) : o())
              },
            })
          }
          function O(e, r, n) {
            var o = f
            return function (a, i) {
              if (o === p) throw new Error('Generator is already running')
              if (o === y) {
                if ('throw' === a) throw i
                return { value: t, done: !0 }
              }
              for (n.method = a, n.arg = i; ; ) {
                var s = n.delegate
                if (s) {
                  var c = L(s, n)
                  if (c) {
                    if (c === m) continue
                    return c
                  }
                }
                if ('next' === n.method) n.sent = n._sent = n.arg
                else if ('throw' === n.method) {
                  if (o === f) throw ((o = y), n.arg)
                  n.dispatchException(n.arg)
                } else 'return' === n.method && n.abrupt('return', n.arg)
                o = p
                var l = d(e, r, n)
                if ('normal' === l.type) {
                  if (((o = n.done ? y : h), l.arg === m)) continue
                  return { value: l.arg, done: n.done }
                }
                'throw' === l.type &&
                  ((o = y), (n.method = 'throw'), (n.arg = l.arg))
              }
            }
          }
          function L(e, r) {
            var n = r.method,
              o = e.iterator[n]
            if (o === t)
              return (
                (r.delegate = null),
                ('throw' === n &&
                  e.iterator.return &&
                  ((r.method = 'return'),
                  (r.arg = t),
                  L(e, r),
                  'throw' === r.method)) ||
                  ('return' !== n &&
                    ((r.method = 'throw'),
                    (r.arg = new TypeError(
                      "The iterator does not provide a '" + n + "' method"
                    )))),
                m
              )
            var a = d(o, e.iterator, r.arg)
            if ('throw' === a.type)
              return (
                (r.method = 'throw'), (r.arg = a.arg), (r.delegate = null), m
              )
            var i = a.arg
            return i
              ? i.done
                ? ((r[e.resultName] = i.value),
                  (r.next = e.nextLoc),
                  'return' !== r.method && ((r.method = 'next'), (r.arg = t)),
                  (r.delegate = null),
                  m)
                : i
              : ((r.method = 'throw'),
                (r.arg = new TypeError('iterator result is not an object')),
                (r.delegate = null),
                m)
          }
          function S(t) {
            var e = { tryLoc: t[0] }
            1 in t && (e.catchLoc = t[1]),
              2 in t && ((e.finallyLoc = t[2]), (e.afterLoc = t[3])),
              this.tryEntries.push(e)
          }
          function N(t) {
            var e = t.completion || {}
            ;(e.type = 'normal'), delete e.arg, (t.completion = e)
          }
          function A(t) {
            ;(this.tryEntries = [{ tryLoc: 'root' }]),
              t.forEach(S, this),
              this.reset(!0)
          }
          function F(e) {
            if (e || '' === e) {
              var r = e[i]
              if (r) return r.call(e)
              if ('function' == typeof e.next) return e
              if (!isNaN(e.length)) {
                var o = -1,
                  a = function r() {
                    for (; ++o < e.length; )
                      if (n.call(e, o))
                        return (r.value = e[o]), (r.done = !1), r
                    return (r.value = t), (r.done = !0), r
                  }
                return (a.next = a)
              }
            }
            throw new TypeError(P(e) + ' is not iterable')
          }
          return (
            (v.prototype = g),
            o(E, 'constructor', { value: g, configurable: !0 }),
            o(g, 'constructor', { value: v, configurable: !0 }),
            (v.displayName = l(g, c, 'GeneratorFunction')),
            (e.isGeneratorFunction = function (t) {
              var e = 'function' == typeof t && t.constructor
              return (
                !!e &&
                (e === v || 'GeneratorFunction' === (e.displayName || e.name))
              )
            }),
            (e.mark = function (t) {
              return (
                Object.setPrototypeOf
                  ? Object.setPrototypeOf(t, g)
                  : ((t.__proto__ = g), l(t, c, 'GeneratorFunction')),
                (t.prototype = Object.create(E)),
                t
              )
            }),
            (e.awrap = function (t) {
              return { __await: t }
            }),
            k(_.prototype),
            l(_.prototype, s, function () {
              return this
            }),
            (e.AsyncIterator = _),
            (e.async = function (t, r, n, o, a) {
              void 0 === a && (a = Promise)
              var i = new _(u(t, r, n, o), a)
              return e.isGeneratorFunction(r)
                ? i
                : i.next().then(function (t) {
                    return t.done ? t.value : i.next()
                  })
            }),
            k(E),
            l(E, c, 'Generator'),
            l(E, i, function () {
              return this
            }),
            l(E, 'toString', function () {
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
            (e.values = F),
            (A.prototype = {
              constructor: A,
              reset: function (e) {
                if (
                  ((this.prev = 0),
                  (this.next = 0),
                  (this.sent = this._sent = t),
                  (this.done = !1),
                  (this.delegate = null),
                  (this.method = 'next'),
                  (this.arg = t),
                  this.tryEntries.forEach(N),
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
                    (s.type = 'throw'),
                    (s.arg = e),
                    (r.next = n),
                    o && ((r.method = 'next'), (r.arg = t)),
                    !!o
                  )
                }
                for (var a = this.tryEntries.length - 1; a >= 0; --a) {
                  var i = this.tryEntries[a],
                    s = i.completion
                  if ('root' === i.tryLoc) return o('end')
                  if (i.tryLoc <= this.prev) {
                    var c = n.call(i, 'catchLoc'),
                      l = n.call(i, 'finallyLoc')
                    if (c && l) {
                      if (this.prev < i.catchLoc) return o(i.catchLoc, !0)
                      if (this.prev < i.finallyLoc) return o(i.finallyLoc)
                    } else if (c) {
                      if (this.prev < i.catchLoc) return o(i.catchLoc, !0)
                    } else {
                      if (!l)
                        throw new Error(
                          'try statement without catch or finally'
                        )
                      if (this.prev < i.finallyLoc) return o(i.finallyLoc)
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
                    var a = o
                    break
                  }
                }
                a &&
                  ('break' === t || 'continue' === t) &&
                  a.tryLoc <= e &&
                  e <= a.finallyLoc &&
                  (a = null)
                var i = a ? a.completion : {}
                return (
                  (i.type = t),
                  (i.arg = e),
                  a
                    ? ((this.method = 'next'), (this.next = a.finallyLoc), m)
                    : this.complete(i)
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
                  m
                )
              },
              finish: function (t) {
                for (var e = this.tryEntries.length - 1; e >= 0; --e) {
                  var r = this.tryEntries[e]
                  if (r.finallyLoc === t)
                    return this.complete(r.completion, r.afterLoc), N(r), m
                }
              },
              catch: function (t) {
                for (var e = this.tryEntries.length - 1; e >= 0; --e) {
                  var r = this.tryEntries[e]
                  if (r.tryLoc === t) {
                    var n = r.completion
                    if ('throw' === n.type) {
                      var o = n.arg
                      N(r)
                    }
                    return o
                  }
                }
                throw new Error('illegal catch attempt')
              },
              delegateYield: function (e, r, n) {
                return (
                  (this.delegate = {
                    iterator: F(e),
                    resultName: r,
                    nextLoc: n,
                  }),
                  'next' === this.method && (this.arg = t),
                  m
                )
              },
            }),
            e
          )
        }
        var A = z().mark(T),
          F = z().mark(Q),
          I = 'BlackbookTopRunners/BlackbookCardGrid'
        function T(t) {
          var e, r, n
          return z().wrap(function (o) {
            for (;;)
              switch ((o.prev = o.next)) {
                case 0:
                  return (
                    (e = t.payload.referral),
                    (o.next = 3),
                    (0, f.RE)(N.dq.get, '/', {
                      headers: {},
                      params: { referral: escape(e) },
                    })
                  )
                case 3:
                  return (
                    (r = o.sent), (n = r.data), o.abrupt('return', { data: n })
                  )
                case 6:
                case 'end':
                  return o.stop()
              }
          }, A)
        }
        function Q() {
          return z().wrap(function (t) {
            for (;;)
              switch ((t.prev = t.next)) {
                case 0:
                  return (t.next = 2), (0, d.W0)(I, T)
                case 2:
                case 'end':
                  return t.stop()
              }
          }, F)
        }
        var C = r(13980),
          W = r.n(C),
          M = [
            'loggedInEmail',
            'embeddedInArticle',
            'withOdds',
            'blackbooks',
            'tx',
          ]
        var G = function (t) {
          var e = t.loggedInEmail,
            r = t.embeddedInArticle,
            n = t.withOdds,
            o = t.blackbooks
          t.tx,
            (function (t, e) {
              if (null == t) return {}
              var r,
                n,
                o = (function (t, e) {
                  if (null == t) return {}
                  var r,
                    n,
                    o = {},
                    a = Object.keys(t)
                  for (n = 0; n < a.length; n++)
                    (r = a[n]), e.indexOf(r) >= 0 || (o[r] = t[r])
                  return o
                })(t, e)
              if (Object.getOwnPropertySymbols) {
                var a = Object.getOwnPropertySymbols(t)
                for (n = 0; n < a.length; n++)
                  (r = a[n]),
                    e.indexOf(r) >= 0 ||
                      (Object.prototype.propertyIsEnumerable.call(t, r) &&
                        (o[r] = t[r]))
              }
            })(t, M),
            (0, u.hb)({ key: 'blackbook-top-runners-grid', saga: Q })
          var a = (0, d.fO)(),
            c = a.dispatch,
            l = a.status,
            f = l.loading,
            h = (l.error, l.data)
          ;(0, i.useEffect)(
            function () {
              c({
                type: I,
                payload: {
                  referral: window.location.href.replace(
                    window.location.search,
                    ''
                  ),
                },
              })
            },
            [c, o]
          )
          var p,
            y,
            m = (0, S.Ln)(),
            b = m ? 2 : 1,
            v = null == h ? void 0 : h.data,
            g =
              ((y = b),
              null == (p = v)
                ? void 0
                : p.reduce(function (t, e, r) {
                    var n = Math.floor(r / y)
                    return t[n] || (t[n] = []), t[n].push(e), t
                  }, []))
          return f || !v
            ? s().createElement(_.Z, null)
            : s().createElement(
                s().Fragment,
                null,
                s().createElement(
                  O.xu,
                  { className: 'blackbook-top-runners' },
                  g &&
                    g.map(function (t, a) {
                      return s().createElement(
                        'div',
                        {
                          key: a,
                          style: {
                            display: 'grid',
                            gridTemplateColumns: m ? '2fr 15px 2fr' : '',
                          },
                        },
                        t.map(function (t, a) {
                          return s().createElement(
                            s().Fragment,
                            null,
                            s().createElement(L.Z, {
                              loggedInEmail: e,
                              blackbooks: o,
                              horseDetail: t,
                              embeddedInArticle: r,
                              withOdds: n,
                            }),
                            a - 1 !== b && s().createElement('div', null, ' ')
                          )
                        })
                      )
                    })
                )
              )
        }
        G.propTypes = {
          loggedInEmail: W().string,
          embeddedInArticle: W().bool,
          withOdds: W().bool,
          blackbooks: W().array,
        }
        const Z = G
        var B = ['title', 'embeddedInArticle', 'withOdds', 'tx']
        function q() {
          return (
            (q = Object.assign
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
            q.apply(this, arguments)
          )
        }
        function D(t, e) {
          ;(null == e || e > t.length) && (e = t.length)
          for (var r = 0, n = new Array(e); r < e; r++) n[r] = t[r]
          return n
        }
        const V = function (t) {
          var e = t.title,
            r =
              (t.embeddedInArticle,
              t.withOdds,
              t.tx,
              (function (t, e) {
                if (null == t) return {}
                var r,
                  n,
                  o = (function (t, e) {
                    if (null == t) return {}
                    var r,
                      n,
                      o = {},
                      a = Object.keys(t)
                    for (n = 0; n < a.length; n++)
                      (r = a[n]), e.indexOf(r) >= 0 || (o[r] = t[r])
                    return o
                  })(t, e)
                if (Object.getOwnPropertySymbols) {
                  var a = Object.getOwnPropertySymbols(t)
                  for (n = 0; n < a.length; n++)
                    (r = a[n]),
                      e.indexOf(r) >= 0 ||
                        (Object.prototype.propertyIsEnumerable.call(t, r) &&
                          (o[r] = t[r]))
                }
                return o
              })(t, B))
          ;(0, u.hb)({ key: 'blackbook-top-runners', saga: k })
          var n,
            o,
            a = (0, d.fO)(),
            c = a.dispatch,
            l = a.status,
            f = l.loading,
            h = (l.error, l.data),
            y =
              ((n = (0, i.useState)(f)),
              (o = 2),
              (function (t) {
                if (Array.isArray(t)) return t
              })(n) ||
                (function (t, e) {
                  var r =
                    null == t
                      ? null
                      : ('undefined' != typeof Symbol && t[Symbol.iterator]) ||
                        t['@@iterator']
                  if (null != r) {
                    var n,
                      o,
                      a,
                      i,
                      s = [],
                      c = !0,
                      l = !1
                    try {
                      if (((a = (r = r.call(t)).next), 0 === e)) {
                        if (Object(r) !== r) return
                        c = !1
                      } else
                        for (
                          ;
                          !(c = (n = a.call(r)).done) &&
                          (s.push(n.value), s.length !== e);
                          c = !0
                        );
                    } catch (t) {
                      ;(l = !0), (o = t)
                    } finally {
                      try {
                        if (
                          !c &&
                          null != r.return &&
                          ((i = r.return()), Object(i) !== i)
                        )
                          return
                      } finally {
                        if (l) throw o
                      }
                    }
                    return s
                  }
                })(n, o) ||
                (function (t, e) {
                  if (t) {
                    if ('string' == typeof t) return D(t, e)
                    var r = Object.prototype.toString.call(t).slice(8, -1)
                    return (
                      'Object' === r &&
                        t.constructor &&
                        (r = t.constructor.name),
                      'Map' === r || 'Set' === r
                        ? Array.from(t)
                        : 'Arguments' === r ||
                          /^(?:Ui|I)nt(?:8|16|32)(?:Clamped)?Array$/.test(r)
                        ? D(t, e)
                        : void 0
                    )
                  }
                })(n, o) ||
                (function () {
                  throw new TypeError(
                    'Invalid attempt to destructure non-iterable instance.\nIn order to be iterable, non-array objects must have a [Symbol.iterator]() method.'
                  )
                })()),
            m = y[0],
            b = y[1],
            v = (0, p.Tq)().email
          ;(0, i.useEffect)(
            function () {
              v ? c({ type: x, payload: { email: v } }) : b(!1)
            },
            [c, v]
          )
          var g = null == h ? void 0 : h.data
          return m
            ? s().createElement(_.Z, null)
            : s().createElement(
                s().Fragment,
                null,
                e && s().createElement('h3', null, e),
                s().createElement(Z, q({ loggedInEmail: v, blackbooks: g }, r))
              )
        }
        function U() {
          return (
            (U = Object.assign
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
            U.apply(this, arguments)
          )
        }
        const Y = (0, c.w)(function (t) {
          var e = U(
            {},
            ((function (t) {
              if (null == t) throw new TypeError('Cannot destructure ' + t)
            })(t),
            t)
          )
          return s().createElement(l.Z, null, s().createElement(V, e))
        })
      },
      75759: (t, e, r) => {
        'use strict'
        r.d(e, { Z: () => a })
        var n = r(82609),
          o = r.n(n)()(function (t) {
            return t[1]
          })
        o.push([
          t.id,
          '.j8L\\+uIQs1m833lgQUiGDyQ\\=\\={font-size:.9rem}.j8L\\+uIQs1m833lgQUiGDyQ\\=\\=,.SE1nQi0ViCMaY4MNdMs5MA\\=\\={font-weight:700;--tw-text-opacity:1;color:rgba(247,247,247,var(--tw-text-opacity))}.SE1nQi0ViCMaY4MNdMs5MA\\=\\={font-size:7px}.PFO-uJyOACqCsgPQC-\\+5Jw\\=\\={font-size:.9rem}.PFO-uJyOACqCsgPQC-\\+5Jw\\=\\=,.NdyttWeWFFPrVVmHfleWyA\\=\\={font-weight:700;--tw-text-opacity:1;color:rgba(51,51,51,var(--tw-text-opacity))}.NdyttWeWFFPrVVmHfleWyA\\=\\={font-size:7px}',
          '',
        ]),
          (o.locals = {
            'form2__odds-box__badge-fav': 'j8L+uIQs1m833lgQUiGDyQ==',
            'form2__odds-box__badge-fav--tablet-portrait':
              'SE1nQi0ViCMaY4MNdMs5MA==',
            'form2__odds-box__badge-mov': 'PFO-uJyOACqCsgPQC-+5Jw==',
            'form2__odds-box__badge-mov--tablet-portrait':
              'NdyttWeWFFPrVVmHfleWyA==',
          })
        const a = o
      },
      32367: (t, e, r) => {
        'use strict'
        r.d(e, { Z: () => a })
        var n = r(82609),
          o = r.n(n)()(function (t) {
            return t[1]
          })
        o.push([
          t.id,
          '._8FTTUW\\+rsFpYm578dhHxew\\=\\={display:block;width:100%;position:absolute;top:-10px}.KKO8Tj5AWu8BE7wyY6lUDQ\\=\\={display:block;position:absolute;top:-7px;width:54px}.uDslDo0soA68dspEu92yPA\\=\\={box-sizing:border-box;border-radius:.375rem;border-width:1px;height:38px;margin-left:auto}.klj9-PWp9B4hMp7rQU4isg\\=\\={line-height:18px}.YKiu6ypzjwk-Zu3-b28PWQ\\=\\={box-sizing:border-box;border-radius:.375rem;border-width:1px;height:26px;width:54px}.zRWZ6FdeFgmJv\\+QlfZEELw\\=\\={border:none;padding:0 1px}.YKiu6ypzjwk-Zu3-b28PWQ\\=\\= .klj9-PWp9B4hMp7rQU4isg\\=\\={margin-top:-2px;font-size:10px;margin-left:-2px;margin-right:-3px}.gj7j6i1W4-VpS9V8fDBbVA\\=\\={border-color:rgba(102,102,102,var(--tw-border-opacity))}.gj7j6i1W4-VpS9V8fDBbVA\\=\\=,.GU2kIqlJGQiXYzrNQM3mhQ\\=\\={--tw-border-opacity:1;border-radius:0 0 .375rem .375rem}.GU2kIqlJGQiXYzrNQM3mhQ\\=\\={border-color:rgba(222,222,222,var(--tw-border-opacity))}.xO2Dd8Cl\\+ejqW5wSAzK65Q\\=\\={box-sizing:border-box;display:flex;align-items:center;justify-content:center;border-radius:.375rem;border-width:2px;height:55px}.Dc-L7GWH01nWg5-rLce6sA\\=\\={width:7rem}.AGqYk\\+INcCe6h3TL9NMISA\\=\\={box-sizing:border-box;display:flex;align-items:center;justify-content:center;border-radius:.375rem;border-width:2px;width:54px;height:26px}',
          '',
        ]),
          (o.locals = {
            'rdc-odds-box__badge': '_8FTTUW+rsFpYm578dhHxew==',
            'rdc-odds-box__badge--tablet-portrait': 'KKO8Tj5AWu8BE7wyY6lUDQ==',
            'rdc-odds-box': 'uDslDo0soA68dspEu92yPA==',
            'rdc-odds-box__text': 'klj9-PWp9B4hMp7rQU4isg==',
            'rdc-odds-box--tablet-portrait': 'YKiu6ypzjwk-Zu3-b28PWQ==',
            'rdc-odds-box--no-border': 'zRWZ6FdeFgmJv+QlfZEELw==',
            'rdc-odds-box__favorite': 'gj7j6i1W4-VpS9V8fDBbVA==',
            'rdc-odds-box__mover': 'GU2kIqlJGQiXYzrNQM3mhQ==',
            'rdc-odds-box__scratched': 'xO2Dd8Cl+ejqW5wSAzK65Q==',
            'rdc-odds-box__scratched1--tablet-portrait':
              'Dc-L7GWH01nWg5-rLce6sA==',
            'rdc-odds-box__scratched2--tablet-portrait':
              'AGqYk+INcCe6h3TL9NMISA==',
          })
        const a = o
      },
      96616: (t, e, r) => {
        var n = {
          './af': 95191,
          './af.js': 95191,
          './ar': 54358,
          './ar-dz': 71727,
          './ar-dz.js': 71727,
          './ar-kw': 98279,
          './ar-kw.js': 98279,
          './ar-ly': 87895,
          './ar-ly.js': 87895,
          './ar-ma': 11987,
          './ar-ma.js': 11987,
          './ar-ps': 10969,
          './ar-ps.js': 10969,
          './ar-sa': 52796,
          './ar-sa.js': 52796,
          './ar-tn': 12386,
          './ar-tn.js': 12386,
          './ar.js': 54358,
          './az': 57452,
          './az.js': 57452,
          './be': 79053,
          './be.js': 79053,
          './bg': 65428,
          './bg.js': 65428,
          './bm': 21569,
          './bm.js': 21569,
          './bn': 56212,
          './bn-bd': 24635,
          './bn-bd.js': 24635,
          './bn.js': 56212,
          './bo': 13667,
          './bo.js': 13667,
          './br': 192,
          './br.js': 192,
          './bs': 51802,
          './bs.js': 51802,
          './ca': 19118,
          './ca.js': 19118,
          './cs': 39990,
          './cs.js': 39990,
          './cv': 30557,
          './cv.js': 30557,
          './cy': 4227,
          './cy.js': 4227,
          './da': 95406,
          './da.js': 95406,
          './de': 87994,
          './de-at': 44139,
          './de-at.js': 44139,
          './de-ch': 86591,
          './de-ch.js': 86591,
          './de.js': 87994,
          './dv': 94649,
          './dv.js': 94649,
          './el': 14453,
          './el.js': 14453,
          './en-au': 48428,
          './en-au.js': 48428,
          './en-ca': 36972,
          './en-ca.js': 36972,
          './en-gb': 13224,
          './en-gb.js': 13224,
          './en-ie': 18843,
          './en-ie.js': 18843,
          './en-il': 32732,
          './en-il.js': 32732,
          './en-in': 76579,
          './en-in.js': 76579,
          './en-nz': 29851,
          './en-nz.js': 29851,
          './en-sg': 70442,
          './en-sg.js': 70442,
          './eo': 10654,
          './eo.js': 10654,
          './es': 63621,
          './es-do': 68791,
          './es-do.js': 68791,
          './es-mx': 67278,
          './es-mx.js': 67278,
          './es-us': 60717,
          './es-us.js': 60717,
          './es.js': 63621,
          './et': 72404,
          './et.js': 72404,
          './eu': 62944,
          './eu.js': 62944,
          './fa': 30496,
          './fa.js': 30496,
          './fi': 98137,
          './fi.js': 98137,
          './fil': 32872,
          './fil.js': 32872,
          './fo': 6545,
          './fo.js': 6545,
          './fr': 49090,
          './fr-ca': 13049,
          './fr-ca.js': 13049,
          './fr-ch': 12338,
          './fr-ch.js': 12338,
          './fr.js': 49090,
          './fy': 95088,
          './fy.js': 95088,
          './ga': 77812,
          './ga.js': 77812,
          './gd': 8374,
          './gd.js': 8374,
          './gl': 63649,
          './gl.js': 63649,
          './gom-deva': 52674,
          './gom-deva.js': 52674,
          './gom-latn': 44948,
          './gom-latn.js': 44948,
          './gu': 24033,
          './gu.js': 24033,
          './he': 10175,
          './he.js': 10175,
          './hi': 58055,
          './hi.js': 58055,
          './hr': 41678,
          './hr.js': 41678,
          './hu': 85111,
          './hu.js': 85111,
          './hy-am': 26530,
          './hy-am.js': 26530,
          './id': 38928,
          './id.js': 38928,
          './is': 11696,
          './is.js': 11696,
          './it': 98710,
          './it-ch': 38821,
          './it-ch.js': 38821,
          './it.js': 98710,
          './ja': 93974,
          './ja.js': 93974,
          './jv': 70648,
          './jv.js': 70648,
          './ka': 54731,
          './ka.js': 54731,
          './kk': 43501,
          './kk.js': 43501,
          './km': 84398,
          './km.js': 84398,
          './kn': 91825,
          './kn.js': 91825,
          './ko': 13729,
          './ko.js': 13729,
          './ku': 19670,
          './ku-kmr': 26890,
          './ku-kmr.js': 26890,
          './ku.js': 19670,
          './ky': 78797,
          './ky.js': 78797,
          './lb': 50627,
          './lb.js': 50627,
          './lo': 65859,
          './lo.js': 65859,
          './lt': 80355,
          './lt.js': 80355,
          './lv': 16594,
          './lv.js': 16594,
          './me': 45324,
          './me.js': 45324,
          './mi': 11689,
          './mi.js': 11689,
          './mk': 61308,
          './mk.js': 61308,
          './ml': 85241,
          './ml.js': 85241,
          './mn': 76320,
          './mn.js': 76320,
          './mr': 96771,
          './mr.js': 96771,
          './ms': 20503,
          './ms-my': 77748,
          './ms-my.js': 77748,
          './ms.js': 20503,
          './mt': 55534,
          './mt.js': 55534,
          './my': 62727,
          './my.js': 62727,
          './nb': 7550,
          './nb.js': 7550,
          './ne': 49899,
          './ne.js': 49899,
          './nl': 41228,
          './nl-be': 31225,
          './nl-be.js': 31225,
          './nl.js': 41228,
          './nn': 97130,
          './nn.js': 97130,
          './oc-lnc': 93130,
          './oc-lnc.js': 93130,
          './pa-in': 42027,
          './pa-in.js': 42027,
          './pl': 28190,
          './pl.js': 28190,
          './pt': 41549,
          './pt-br': 78135,
          './pt-br.js': 78135,
          './pt.js': 41549,
          './ro': 307,
          './ro.js': 307,
          './ru': 89272,
          './ru.js': 89272,
          './sd': 79248,
          './sd.js': 79248,
          './se': 74969,
          './se.js': 74969,
          './si': 65522,
          './si.js': 65522,
          './sk': 61581,
          './sk.js': 61581,
          './sl': 17034,
          './sl.js': 17034,
          './sq': 34611,
          './sq.js': 34611,
          './sr': 19821,
          './sr-cyrl': 20185,
          './sr-cyrl.js': 20185,
          './sr.js': 19821,
          './ss': 35029,
          './ss.js': 35029,
          './sv': 80939,
          './sv.js': 80939,
          './sw': 73107,
          './sw.js': 73107,
          './ta': 72304,
          './ta.js': 72304,
          './te': 72550,
          './te.js': 72550,
          './tet': 99717,
          './tet.js': 99717,
          './tg': 87669,
          './tg.js': 87669,
          './th': 94959,
          './th.js': 94959,
          './tk': 92661,
          './tk.js': 92661,
          './tl-ph': 52234,
          './tl-ph.js': 52234,
          './tlh': 94120,
          './tlh.js': 94120,
          './tr': 81111,
          './tr.js': 81111,
          './tzl': 53080,
          './tzl.js': 53080,
          './tzm': 88246,
          './tzm-latn': 25385,
          './tzm-latn.js': 25385,
          './tzm.js': 88246,
          './ug-cn': 48777,
          './ug-cn.js': 48777,
          './uk': 2014,
          './uk.js': 2014,
          './ur': 45953,
          './ur.js': 45953,
          './uz': 89716,
          './uz-latn': 87791,
          './uz-latn.js': 87791,
          './uz.js': 89716,
          './vi': 99816,
          './vi.js': 99816,
          './x-pseudo': 94450,
          './x-pseudo.js': 94450,
          './yo': 22556,
          './yo.js': 22556,
          './zh-cn': 7414,
          './zh-cn.js': 7414,
          './zh-hk': 50824,
          './zh-hk.js': 50824,
          './zh-mo': 88589,
          './zh-mo.js': 88589,
          './zh-tw': 63285,
          './zh-tw.js': 63285,
        }
        function o(t) {
          var e = a(t)
          return r(e)
        }
        function a(t) {
          if (!r.o(n, t)) {
            var e = new Error("Cannot find module '" + t + "'")
            throw ((e.code = 'MODULE_NOT_FOUND'), e)
          }
          return n[t]
        }
        ;(o.keys = function () {
          return Object.keys(n)
        }),
          (o.resolve = a),
          (t.exports = o),
          (o.id = 96616)
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
    (t) => (t.O(0, [736, 351], () => (81150, t((t.s = 81150)))), t.O()),
  ])
)

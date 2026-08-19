/*! For license information please see rdc.commons.js.LICENSE.txt */
'use strict'
;(self.webpackChunkrdc = self.webpackChunkrdc || []).push([
  [351],
  {
    56877: (e, t, r) => {
      r.d(t, { I: () => v })
      var n = r(1024),
        o = r.n(n),
        i = r(30186),
        a = r(13980),
        c = r(72112),
        l = r.n(c),
        u = r(62388),
        s = r(78667)
      var f = r(21036),
        p = r(54951),
        d = ['winPrice']
      function y() {
        return (
          (y = Object.assign
            ? Object.assign.bind()
            : function (e) {
                for (var t = 1; t < arguments.length; t++) {
                  var r = arguments[t]
                  for (var n in r)
                    Object.prototype.hasOwnProperty.call(r, n) && (e[n] = r[n])
                }
                return e
              }),
          y.apply(this, arguments)
        )
      }
      var m = function (e) {
          var t = (0, n.useContext)(u.$f).provider
          return o().createElement(
            i.kC,
            y(
              {
                className: 'bet-now__wrap',
                sx: {
                  flexDirection: 'column',
                  alignItems: 'stretch',
                  width: ['60px', '', '', '72px'],
                  height: 1,
                  borderRadius: '4px',
                  border: '1px solid',
                  borderColor: 'grey-de',
                  textAlign: 'center',
                  lineHeight: '1',
                  textDecoration: 'none',
                  fontFamily: 'roboto',
                  padding: 0,
                  cursor: 'pointer',
                  backgroundColor: 'white',
                  transition: 'border-color 0.3s ease-in-out',
                  outline: 'none',
                  '&:hover': { borderColor: t || 'beteasy' },
                },
              },
              e
            )
          )
        },
        b = function (e) {
          var t = e.winPrice
          return o().createElement(
            i.xv,
            {
              className: 'bet-now__amount',
              sx: {
                flex: '1 1 auto',
                fontSize: 'body',
                fontWeight: 'bold',
                paddingTop: '2px',
                color: 'grey-33',
              },
            },
            l().formatMoney(null == t ? void 0 : t.price)
          )
        }
      b.propTypes = { winPrice: a.PropTypes.object.isRequired }
      var h = function () {
          var e = (0, n.useContext)(u.$f).provider
          return o().createElement(
            i.xv,
            {
              className: 'bet-now__action',
              sx: {
                flex: '1 1 auto',
                fontSize: 'sm',
                fontWeight: 'bold',
                color: 'grey-33',
                width: '100%',
                backgroundColor: 'grey-de',
                textTransform: 'uppercase',
                paddingTop: '3px',
                transition: 'all 0.3s ease-in-out',
                '.bet-now__wrap:hover &': {
                  backgroundColor: e || 'sportsbet',
                  color: 'white',
                },
              },
            },
            'Bet Now'
          )
        },
        v = function (e) {
          var t = e.winPrice,
            r = (function (e, t) {
              if (null == e) return {}
              var r,
                n,
                o = (function (e, t) {
                  if (null == e) return {}
                  var r,
                    n,
                    o = {},
                    i = Object.keys(e)
                  for (n = 0; n < i.length; n++)
                    (r = i[n]), t.indexOf(r) >= 0 || (o[r] = e[r])
                  return o
                })(e, t)
              if (Object.getOwnPropertySymbols) {
                var i = Object.getOwnPropertySymbols(e)
                for (n = 0; n < i.length; n++)
                  (r = i[n]),
                    t.indexOf(r) >= 0 ||
                      (Object.prototype.propertyIsEnumerable.call(e, r) &&
                        (o[r] = e[r]))
              }
              return o
            })(e, d),
            i = (0, n.useContext)(u.$f).provider,
            a =
              'appv2' === (0, s.n)('device', '').toLowerCase() ||
              -1 !== window.location.hash.indexOf('/embed'),
            c = (0, n.useMemo)(
              function () {
                return a
                  ? null == t
                    ? void 0
                    : t.url
                  : (function (e) {
                      if (!e) return null
                      var t = (0, s.n)('SportsBetTrackId')
                      if (
                        t &&
                        -1 !== e.indexOf('record.sportsbetaffiliates.com.au')
                      ) {
                        var r = new URL(e),
                          n = r.pathname.split('/')
                        return (
                          (n[1] = t), (r.pathname = n.join('/')), r.toString()
                        )
                      }
                      return e
                    })(null == t ? void 0 : t.url)
              },
              [t, a]
            ),
            l = (0, f.dJ)()
          return t.price
            ? o().createElement(
                m,
                y(
                  {
                    as: 'a',
                    href: c,
                    target: '_blank',
                    onClick: function (e) {
                      e.stopPropagation(),
                        (function (e, t) {
                          ;['tips', 'news'].includes(e) &&
                            'sportsbet' === t &&
                            (0, p.JN)(
                              'Sportsbet',
                              'tips' === e ? 'Tippinghub' : 'Articletips',
                              null,
                              'betclick'
                            )
                        })(l, i),
                        window.open(c, '_blank')
                    },
                  },
                  r
                ),
                o().createElement(b, { winPrice: t }),
                o().createElement(h, null)
              )
            : null
        }
      v.propTypes = { winPrice: a.PropTypes.object.isRequired }
    },
    44962: (e, t, r) => {
      r.d(t, { Z: () => X })
      var n,
        o,
        i,
        a = r(1024),
        c = r.n(a),
        l = r(33189),
        u = r(77450),
        s = r(13295),
        f = r(27422),
        p = r(38847),
        d = r(2738),
        y = r(67834)
      function m(e, t) {
        return (
          t || (t = e.slice(0)),
          Object.freeze(
            Object.defineProperties(e, { raw: { value: Object.freeze(t) } })
          )
        )
      }
      ;(0, y.Ps)(
        n ||
          (n = m([
            '\n  query getBlackbook_PP($email: String!) {\n    getNotificationsFollowsForUser(Email: $email) {\n      items {\n        Email\n        EntityCode\n        EntityType\n        EntityType_EntityCode\n      }\n    }\n  }\n',
          ]))
      )
      var b = (0, y.Ps)(
          o ||
            (o = m([
              '\n  mutation createBlackbook_PP($input: CreateNotificationsFollowInput!) {\n    createNotificationsFollow(input: $input) {\n      EntityType\n      EntityCode\n      Email\n      EntityType_EntityCode\n    }\n  }\n',
            ]))
        ),
        h = (0, y.Ps)(
          i ||
            (i = m([
              '\n  mutation deleteBlackbook_PP($input: DeleteNotificationsFollowInput!) {\n    deleteNotificationsFollow(input: $input) {\n      EntityType\n      EntityCode\n      Email\n      EntityType_EntityCode\n    }\n  }\n',
            ]))
        )
      function v(e) {
        return (
          (v =
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
          v(e)
        )
      }
      function g() {
        g = function () {
          return t
        }
        var e,
          t = {},
          r = Object.prototype,
          n = r.hasOwnProperty,
          o =
            Object.defineProperty ||
            function (e, t, r) {
              e[t] = r.value
            },
          i = 'function' == typeof Symbol ? Symbol : {},
          a = i.iterator || '@@iterator',
          c = i.asyncIterator || '@@asyncIterator',
          l = i.toStringTag || '@@toStringTag'
        function u(e, t, r) {
          return (
            Object.defineProperty(e, t, {
              value: r,
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
          u = function (e, t, r) {
            return (e[t] = r)
          }
        }
        function s(e, t, r, n) {
          var i = t && t.prototype instanceof h ? t : h,
            a = Object.create(i.prototype),
            c = new L(n || [])
          return o(a, '_invoke', { value: C(e, r, c) }), a
        }
        function f(e, t, r) {
          try {
            return { type: 'normal', arg: e.call(t, r) }
          } catch (e) {
            return { type: 'throw', arg: e }
          }
        }
        t.wrap = s
        var p = 'suspendedStart',
          d = 'suspendedYield',
          y = 'executing',
          m = 'completed',
          b = {}
        function h() {}
        function w() {}
        function x() {}
        var O = {}
        u(O, a, function () {
          return this
        })
        var j = Object.getPrototypeOf,
          S = j && j(j(N([])))
        S && S !== r && n.call(S, a) && (O = S)
        var E = (x.prototype = h.prototype = Object.create(O))
        function k(e) {
          ;['next', 'throw', 'return'].forEach(function (t) {
            u(e, t, function (e) {
              return this._invoke(t, e)
            })
          })
        }
        function P(e, t) {
          function r(o, i, a, c) {
            var l = f(e[o], e, i)
            if ('throw' !== l.type) {
              var u = l.arg,
                s = u.value
              return s && 'object' == v(s) && n.call(s, '__await')
                ? t.resolve(s.__await).then(
                    function (e) {
                      r('next', e, a, c)
                    },
                    function (e) {
                      r('throw', e, a, c)
                    }
                  )
                : t.resolve(s).then(
                    function (e) {
                      ;(u.value = e), a(u)
                    },
                    function (e) {
                      return r('throw', e, a, c)
                    }
                  )
            }
            c(l.arg)
          }
          var i
          o(this, '_invoke', {
            value: function (e, n) {
              function o() {
                return new t(function (t, o) {
                  r(e, n, t, o)
                })
              }
              return (i = i ? i.then(o, o) : o())
            },
          })
        }
        function C(t, r, n) {
          var o = p
          return function (i, a) {
            if (o === y) throw new Error('Generator is already running')
            if (o === m) {
              if ('throw' === i) throw a
              return { value: e, done: !0 }
            }
            for (n.method = i, n.arg = a; ; ) {
              var c = n.delegate
              if (c) {
                var l = A(c, n)
                if (l) {
                  if (l === b) continue
                  return l
                }
              }
              if ('next' === n.method) n.sent = n._sent = n.arg
              else if ('throw' === n.method) {
                if (o === p) throw ((o = m), n.arg)
                n.dispatchException(n.arg)
              } else 'return' === n.method && n.abrupt('return', n.arg)
              o = y
              var u = f(t, r, n)
              if ('normal' === u.type) {
                if (((o = n.done ? m : d), u.arg === b)) continue
                return { value: u.arg, done: n.done }
              }
              'throw' === u.type &&
                ((o = m), (n.method = 'throw'), (n.arg = u.arg))
            }
          }
        }
        function A(t, r) {
          var n = r.method,
            o = t.iterator[n]
          if (o === e)
            return (
              (r.delegate = null),
              ('throw' === n &&
                t.iterator.return &&
                ((r.method = 'return'),
                (r.arg = e),
                A(t, r),
                'throw' === r.method)) ||
                ('return' !== n &&
                  ((r.method = 'throw'),
                  (r.arg = new TypeError(
                    "The iterator does not provide a '" + n + "' method"
                  )))),
              b
            )
          var i = f(o, t.iterator, r.arg)
          if ('throw' === i.type)
            return (r.method = 'throw'), (r.arg = i.arg), (r.delegate = null), b
          var a = i.arg
          return a
            ? a.done
              ? ((r[t.resultName] = a.value),
                (r.next = t.nextLoc),
                'return' !== r.method && ((r.method = 'next'), (r.arg = e)),
                (r.delegate = null),
                b)
              : a
            : ((r.method = 'throw'),
              (r.arg = new TypeError('iterator result is not an object')),
              (r.delegate = null),
              b)
        }
        function T(e) {
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
            e.forEach(T, this),
            this.reset(!0)
        }
        function N(t) {
          if (t || '' === t) {
            var r = t[a]
            if (r) return r.call(t)
            if ('function' == typeof t.next) return t
            if (!isNaN(t.length)) {
              var o = -1,
                i = function r() {
                  for (; ++o < t.length; )
                    if (n.call(t, o)) return (r.value = t[o]), (r.done = !1), r
                  return (r.value = e), (r.done = !0), r
                }
              return (i.next = i)
            }
          }
          throw new TypeError(v(t) + ' is not iterable')
        }
        return (
          (w.prototype = x),
          o(E, 'constructor', { value: x, configurable: !0 }),
          o(x, 'constructor', { value: w, configurable: !0 }),
          (w.displayName = u(x, l, 'GeneratorFunction')),
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
                : ((e.__proto__ = x), u(e, l, 'GeneratorFunction')),
              (e.prototype = Object.create(E)),
              e
            )
          }),
          (t.awrap = function (e) {
            return { __await: e }
          }),
          k(P.prototype),
          u(P.prototype, c, function () {
            return this
          }),
          (t.AsyncIterator = P),
          (t.async = function (e, r, n, o, i) {
            void 0 === i && (i = Promise)
            var a = new P(s(e, r, n, o), i)
            return t.isGeneratorFunction(r)
              ? a
              : a.next().then(function (e) {
                  return e.done ? e.value : a.next()
                })
          }),
          k(E),
          u(E, l, 'Generator'),
          u(E, a, function () {
            return this
          }),
          u(E, 'toString', function () {
            return '[object Generator]'
          }),
          (t.keys = function (e) {
            var t = Object(e),
              r = []
            for (var n in t) r.push(n)
            return (
              r.reverse(),
              function e() {
                for (; r.length; ) {
                  var n = r.pop()
                  if (n in t) return (e.value = n), (e.done = !1), e
                }
                return (e.done = !0), e
              }
            )
          }),
          (t.values = N),
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
                for (var r in this)
                  't' === r.charAt(0) &&
                    n.call(this, r) &&
                    !isNaN(+r.slice(1)) &&
                    (this[r] = e)
            },
            stop: function () {
              this.done = !0
              var e = this.tryEntries[0].completion
              if ('throw' === e.type) throw e.arg
              return this.rval
            },
            dispatchException: function (t) {
              if (this.done) throw t
              var r = this
              function o(n, o) {
                return (
                  (c.type = 'throw'),
                  (c.arg = t),
                  (r.next = n),
                  o && ((r.method = 'next'), (r.arg = e)),
                  !!o
                )
              }
              for (var i = this.tryEntries.length - 1; i >= 0; --i) {
                var a = this.tryEntries[i],
                  c = a.completion
                if ('root' === a.tryLoc) return o('end')
                if (a.tryLoc <= this.prev) {
                  var l = n.call(a, 'catchLoc'),
                    u = n.call(a, 'finallyLoc')
                  if (l && u) {
                    if (this.prev < a.catchLoc) return o(a.catchLoc, !0)
                    if (this.prev < a.finallyLoc) return o(a.finallyLoc)
                  } else if (l) {
                    if (this.prev < a.catchLoc) return o(a.catchLoc, !0)
                  } else {
                    if (!u)
                      throw new Error('try statement without catch or finally')
                    if (this.prev < a.finallyLoc) return o(a.finallyLoc)
                  }
                }
              }
            },
            abrupt: function (e, t) {
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
                var r = this.tryEntries[t]
                if (r.finallyLoc === e)
                  return this.complete(r.completion, r.afterLoc), I(r), b
              }
            },
            catch: function (e) {
              for (var t = this.tryEntries.length - 1; t >= 0; --t) {
                var r = this.tryEntries[t]
                if (r.tryLoc === e) {
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
            delegateYield: function (t, r, n) {
              return (
                (this.delegate = { iterator: N(t), resultName: r, nextLoc: n }),
                'next' === this.method && (this.arg = e),
                b
              )
            },
          }),
          t
        )
      }
      var w = g().mark(j),
        x = g().mark(S),
        O = 'BlackbookButton/mutateBlackbook'
      function j(e) {
        var t, r, n, o, i
        return g().wrap(
          function (a) {
            for (;;)
              switch ((a.prev = a.next)) {
                case 0:
                  return (
                    (t = (0, d.tV)()),
                    (r = null == t ? void 0 : t.AccessToken),
                    (n = e.payload),
                    (o = n.input),
                    (i = n.type),
                    (a.prev = 3),
                    (a.next = 6),
                    (0, f.RE)(p.J, {
                      mutation: 'create' === i ? b : h,
                      variables: { input: o },
                      context: { useBlackbook: !0, token: r },
                    })
                  )
                case 6:
                  a.next = 11
                  break
                case 8:
                  ;(a.prev = 8), (a.t0 = a.catch(3)), console.warn(a.t0)
                case 11:
                case 'end':
                  return a.stop()
              }
          },
          w,
          null,
          [[3, 8]]
        )
      }
      function S() {
        return g().wrap(function (e) {
          for (;;)
            switch ((e.prev = e.next)) {
              case 0:
                return (e.next = 2), (0, f.ib)(O, j)
              case 2:
              case 'end':
                return e.stop()
            }
        }, x)
      }
      var E = r(98662),
        k = r(13980),
        P = r.n(k),
        C = r(46062),
        A = r.n(C),
        T = r(81699),
        I = {
          injectType: 'singletonStyleTag',
          insert: function (e) {
            var t = document.querySelector('head'),
              r = document.querySelector('#rdc-tailwind-css'),
              n = window._lastElementInsertedByStyleLoader
            n
              ? n.nextSibling
                ? t.insertBefore(e, n.nextSibling)
                : t.appendChild(e)
              : t.insertBefore(e, r),
              (window._lastElementInsertedByStyleLoader = e)
          },
          singleton: !0,
        }
      A()(T.Z, I)
      const L = T.Z.locals || {}
      function N(e) {
        return (
          (N =
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
          N(e)
        )
      }
      function _(e, t) {
        var r = Object.keys(e)
        if (Object.getOwnPropertySymbols) {
          var n = Object.getOwnPropertySymbols(e)
          t &&
            (n = n.filter(function (t) {
              return Object.getOwnPropertyDescriptor(e, t).enumerable
            })),
            r.push.apply(r, n)
        }
        return r
      }
      function B(e) {
        for (var t = 1; t < arguments.length; t++) {
          var r = null != arguments[t] ? arguments[t] : {}
          t % 2
            ? _(Object(r), !0).forEach(function (t) {
                var n, o, i, a
                ;(n = e),
                  (o = t),
                  (i = r[t]),
                  (a = (function (e, t) {
                    if ('object' != N(e) || !e) return e
                    var r = e[Symbol.toPrimitive]
                    if (void 0 !== r) {
                      var n = r.call(e, 'string')
                      if ('object' != N(n)) return n
                      throw new TypeError(
                        '@@toPrimitive must return a primitive value.'
                      )
                    }
                    return String(e)
                  })(o)),
                  (o = 'symbol' == N(a) ? a : String(a)) in n
                    ? Object.defineProperty(n, o, {
                        value: i,
                        enumerable: !0,
                        configurable: !0,
                        writable: !0,
                      })
                    : (n[o] = i)
              })
            : Object.getOwnPropertyDescriptors
            ? Object.defineProperties(e, Object.getOwnPropertyDescriptors(r))
            : _(Object(r)).forEach(function (t) {
                Object.defineProperty(
                  e,
                  t,
                  Object.getOwnPropertyDescriptor(r, t)
                )
              })
        }
        return e
      }
      function F(e, t) {
        ;(null == t || t > e.length) && (t = e.length)
        for (var r = 0, n = new Array(t); r < t; r++) n[r] = e[r]
        return n
      }
      var D = function (e) {
        var t = e.loggedInEmail,
          r = e.horseCode,
          n = e.blackbook
        ;(0, s.hb)({ key: 'blackbook-buttom', saga: S })
        var o,
          i,
          l = (0, E.fO)(),
          f = l.dispatch,
          p = l.status,
          d =
            (p.loading,
            p.error,
            p.data,
            (o = (0, a.useState)(
              n ? B(B({}, n), {}, { type: 'create' }) : null
            )),
            (i = 2),
            (function (e) {
              if (Array.isArray(e)) return e
            })(o) ||
              (function (e, t) {
                var r =
                  null == e
                    ? null
                    : ('undefined' != typeof Symbol && e[Symbol.iterator]) ||
                      e['@@iterator']
                if (null != r) {
                  var n,
                    o,
                    i,
                    a,
                    c = [],
                    l = !0,
                    u = !1
                  try {
                    if (((i = (r = r.call(e)).next), 0 === t)) {
                      if (Object(r) !== r) return
                      l = !1
                    } else
                      for (
                        ;
                        !(l = (n = i.call(r)).done) &&
                        (c.push(n.value), c.length !== t);
                        l = !0
                      );
                  } catch (e) {
                    ;(u = !0), (o = e)
                  } finally {
                    try {
                      if (
                        !l &&
                        null != r.return &&
                        ((a = r.return()), Object(a) !== a)
                      )
                        return
                    } finally {
                      if (u) throw o
                    }
                  }
                  return c
                }
              })(o, i) ||
              (function (e, t) {
                if (e) {
                  if ('string' == typeof e) return F(e, t)
                  var r = Object.prototype.toString.call(e).slice(8, -1)
                  return (
                    'Object' === r && e.constructor && (r = e.constructor.name),
                    'Map' === r || 'Set' === r
                      ? Array.from(e)
                      : 'Arguments' === r ||
                        /^(?:Ui|I)nt(?:8|16|32)(?:Clamped)?Array$/.test(r)
                      ? F(e, t)
                      : void 0
                  )
                }
              })(o, i) ||
              (function () {
                throw new TypeError(
                  'Invalid attempt to destructure non-iterable instance.\nIn order to be iterable, non-array objects must have a [Symbol.iterator]() method.'
                )
              })()),
          y = d[0],
          m = d[1],
          b = { Email: t, EntityType: '0', EntityCode: r }
        function h(e) {
          return 'create' === (null == e ? void 0 : e.type)
        }
        var v = h(y)
        return c().createElement(
          'div',
          {
            style: { marginLeft: '8px', color: 'rgb(237, 28, 36)' },
            onClick: function (e) {
              e.stopPropagation(),
                t &&
                  (h(y)
                    ? (f({ type: O, payload: { type: 'delete', input: b } }),
                      m(B(B({}, y), {}, { type: 'delete' })))
                    : (f({ type: O, payload: { type: 'create', input: b } }),
                      m(B(B({}, y), {}, { type: 'create' }))))
            },
          },
          c().createElement(u.Z, {
            tx: {
              'rdc-icon': ''.concat(
                v
                  ? 'text-brand'
                  : ''.concat(L['blackbook-hover'], ' text-grey-66'),
                ' text-3xl pl-2'
              ),
            },
            type: ''.concat(v ? 'blackbook-filled' : 'blackbook'),
          })
        )
      }
      D.propTypes = {
        loggedInEmail: P().any.isRequired,
        horseCode: P().string.isRequired,
        blackbook: P().any,
      }
      const M = D
      var G = r(81165),
        W = {
          injectType: 'singletonStyleTag',
          insert: function (e) {
            var t = document.querySelector('head'),
              r = document.querySelector('#rdc-tailwind-css'),
              n = window._lastElementInsertedByStyleLoader
            n
              ? n.nextSibling
                ? t.insertBefore(e, n.nextSibling)
                : t.appendChild(e)
              : t.insertBefore(e, r),
              (window._lastElementInsertedByStyleLoader = e)
          },
          singleton: !0,
        }
      A()(G.Z, W)
      const R = G.Z.locals || {},
        U = function (e) {
          var t = e.imgUrl,
            r = e.horseName,
            n = e.trainerName,
            o = e.jockeyName,
            i = e.horseUrl,
            a = e.jockeyUrl,
            l = e.trainerUrl,
            u = e.barrierNumber,
            s = ''.concat(location.protocol, '//').concat(location.host, '/')
          function f(e) {
            return e
              .replace(/[^\w\- ]/, '')
              .split(' ')
              .join('-')
              .toLowerCase()
          }
          return c().createElement(
            'div',
            { className: R['horse-detail'] },
            c().createElement('img', { src: t, className: R['horse-image'] }),
            c().createElement(
              'div',
              { className: R.detail },
              c().createElement(
                'div',
                {
                  className: R['horse-name'],
                  onClick: function () {
                    var e = i || ''.concat(s, 'horses/').concat(f(r))
                    window.open(e)
                  },
                },
                ''.concat(u ? ''.concat(u, '.') : '', ' ').concat(r)
              ),
              c().createElement(
                'div',
                { className: R['trainer-jockey'] },
                'T:',
                ' ',
                c().createElement(
                  'a',
                  {
                    onClick: function () {
                      var e = l || ''.concat(s, 'trainers/').concat(f(n))
                      window.open(e)
                    },
                    style: {
                      cursor: 'pointer',
                      fontWeight: 'inherit',
                      color: '#666',
                      textDecoration: 'inherit',
                    },
                  },
                  n
                ),
                '  J:',
                ' ',
                c().createElement(
                  'a',
                  {
                    onClick: function () {
                      var e = a || ''.concat(s, 'jockeys/').concat(f(o))
                      window.open(e)
                    },
                    style: {
                      cursor: 'pointer',
                      fontWeight: 'inherit',
                      color: '#666',
                      textDecoration: 'inherit',
                    },
                  },
                  o
                )
              )
            )
          )
        }
      var Y = r(58253),
        Z = r(80008),
        q = r.n(Z),
        z = function (e, t, r) {
          return q()(new Date(e), t).format(r)
        },
        H = r(30186),
        J = r(98771),
        Q = {
          injectType: 'singletonStyleTag',
          insert: function (e) {
            var t = document.querySelector('head'),
              r = document.querySelector('#rdc-tailwind-css'),
              n = window._lastElementInsertedByStyleLoader
            n
              ? n.nextSibling
                ? t.insertBefore(e, n.nextSibling)
                : t.appendChild(e)
              : t.insertBefore(e, r),
              (window._lastElementInsertedByStyleLoader = e)
          },
          singleton: !0,
        }
      A()(J.Z, Q)
      const K = J.Z.locals || {}
      var V = function (e) {
        var t = e.horseDetail,
          r = e.loggedInEmail,
          n = e.blackbooks,
          o = void 0 === n ? null : n,
          i = e.withOdds,
          a = void 0 !== i && i,
          u = (e.embeddedInArticle, e.isNominated),
          s = void 0 !== u && u,
          f = e.isStable,
          p = (function (e, t, r) {
            return t
              ? 'Last Race '
                  .concat(
                    z(r.race_time, 'YYYY-MM-DD hh:mm:ss', 'DD/MM/YY'),
                    '  '
                  )
                  .concat(r.venueabbr, '  Race ')
                  .concat(null == r ? void 0 : r.race_number, '  ')
                  .concat(r.finishingposition, '/')
                  .concat(null == r ? void 0 : r.runnerscount)
              : e
              ? 'Race '
                  .concat(
                    z(r.race_time, 'YYYY-MM-DD hh:mm:ss', 'DD/MM/YY'),
                    '  '
                  )
                  .concat(r.venueabbr, '  Race ')
                  .concat(null == r ? void 0 : r.race_number)
              : 'Race '
                  .concat(
                    z(r.race_time, 'YYYY-MM-DD hh:mm:ss', 'DD/MM/YY'),
                    '  '
                  )
                  .concat(r.venueabbr, '  Race ')
                  .concat(null == r ? void 0 : r.race_number, '  ')
                  .concat(z(r.race_time, 'YYYY-MM-DD hh:mm:ss', 'hh:mma'))
          })(s, void 0 !== f && f, t),
          d = {
            id: '13367067-SB2',
            providerCode: 'SB2',
            oddsPlace: '$3.40',
            oddsWin: '$11.00',
            oddsIsFavouriteWin: !1,
            oddsIsMarketMover: !1,
            deepLinkWin:
              'https://ad.doubleclick.net/ddm/trackclk/N7629.1917039RACING.COM/B26056835.343664763;dc_trk_aid=535143173;dc_trk_cid=142873052;dc_lat=;dc_rdid=;tag_for_child_directed_treatment=;tfua=;ltd=?https://record.sportsbetaffiliates.com.au/_1FfuSerjMqOoh1SpH8Gdo2Nd7ZgqdRLk/1/horse-racing/australia-nz/venue/race-6-6814541',
            deepLinkPlace:
              'https://ad.doubleclick.net/ddm/trackclk/N7629.1917039RACING.COM/B26056835.343664763;dc_trk_aid=535143173;dc_trk_cid=142873052;dc_lat=;dc_rdid=;tag_for_child_directed_treatment=;tfua=;ltd=?https://record.sportsbetaffiliates.com.au/_1FfuSerjMqOoh1SpH8Gdo2Nd7ZgqdRLk/1/horse-racing/australia-nz/venue/race-6-6814541',
            deepLinkRace:
              'https://ad.doubleclick.net/ddm/trackclk/N7629.1917039RACING.COM/B26056835.343664763;dc_trk_aid=535143173;dc_trk_cid=142873052;dc_lat=;dc_rdid=;tag_for_child_directed_treatment=;tfua=;ltd=?https://record.sportsbetaffiliates.com.au/_1FfuSerjMqOoh1SpH8Gdo2Nd7ZgqdRLk/1/horse-racing/australia-nz/venue/race-6-6814541',
            flucsWin: [
              { updateTime: 1663567468, amount: '$9.00' },
              { updateTime: 1663567659, amount: '$9.50' },
              { updateTime: 1663573585, amount: '$10.00' },
              { updateTime: 1663641378, amount: '$11.00' },
            ],
          },
          y = (function (e, t) {
            return null == e
              ? void 0
              : e.filter(function (e) {
                  return e.EntityCode == t
                })[0]
          })(o, t.horse_code)
        return c().createElement(
          H.xu,
          { className: K['blackbook-card'] },
          c().createElement(
            'div',
            { className: K.upper },
            c().createElement(U, {
              imgUrl: t.silkurl,
              horseName: t.horsename,
              trainerName: t.trainername,
              jockeyName: t.jockeyname,
              horseUrl: t.horseurl,
              jockeyUrl: t.jockeyurl,
              trainerUrl: t.trainerurl,
              barrierNumber: t.barrier_number,
            }),
            a &&
              c().createElement(Y.Z, {
                scratched: !1,
                oddsWin: null == d ? void 0 : d.oddsWin,
                oddsLink:
                  (null == d ? void 0 : d.deepLinkWin) ||
                  (null == d ? void 0 : d.deepLinkPlace),
                oddsPlace: null == d ? void 0 : d.oddsPlace,
              }),
            c().createElement(
              'div',
              { style: { marginLeft: a ? '10px' : 'auto' } },
              c().createElement(M, {
                loggedInEmail: r,
                horseCode: t.horse_code,
                blackbook: y,
              })
            )
          ),
          c().createElement(
            'div',
            { className: K.lower },
            c().createElement(
              l.Z,
              {
                onClick: function () {
                  var e = t.race_url
                    ? t.race_url
                    : ''
                        .concat(location.protocol, '//')
                        .concat(location.host, '/form/')
                        .concat(
                          z(t.race_time, 'YYYY-MM-DD hh:mm:ss', 'YYYY-MM-DD'),
                          '/'
                        )
                        .concat(
                          t.venue.split(' ').join('-').toLowerCase(),
                          '/race/'
                        )
                        .concat(t.race_number)
                  window.open(e)
                },
                tx: { 'rdc-button': 'py-0' },
                style: {
                  marginLeft: 'auto',
                  height: '28px',
                  width: '100%',
                  fontSize: '12px',
                  whiteSpace: 'nowrap',
                  backgroundColor: 'transparent',
                  backgroundImage: 'none',
                  lineHeight: '0px',
                },
              },
              p
            )
          )
        )
      }
      V.propTypes = {
        horseDetail: P().any.isRequired,
        loggedInEmail: P().string.isRequired,
        blackbooks: P().array,
        withOdds: P().bool,
        embeddedInArticle: P().bool,
        isNominated: P().bool,
        isStable: P().bool,
      }
      const X = V
    },
    92551: (e, t, r) => {
      r.d(t, { Z: () => h })
      var n = r(1024),
        o = r.n(n),
        i = r(13980),
        a = r.n(i),
        c = r(30186),
        l = r(78667),
        u = r(40163)
      function s(e, t) {
        ;(null == t || t > e.length) && (t = e.length)
        for (var r = 0, n = new Array(t); r < t; r++) n[r] = e[r]
        return n
      }
      const f = r.p + '653b583d6ac4a1421729.jpg',
        p = r.p + '0826ed05897e43e7483b.jpg'
      var d = [
        'linius',
        'playerId',
        'videoId',
        'videoTime',
        'onExitFullscreen',
        'trackEvent',
        'autoplay',
      ]
      function y() {
        return (
          (y = Object.assign
            ? Object.assign.bind()
            : function (e) {
                for (var t = 1; t < arguments.length; t++) {
                  var r = arguments[t]
                  for (var n in r)
                    Object.prototype.hasOwnProperty.call(r, n) && (e[n] = r[n])
                }
                return e
              }),
          y.apply(this, arguments)
        )
      }
      function m(e, t) {
        ;(null == t || t > e.length) && (t = e.length)
        for (var r = 0, n = new Array(t); r < t; r++) n[r] = e[r]
        return n
      }
      var b = function (e) {
        var t = e.linius,
          r = e.playerId,
          i = e.videoId,
          a = e.videoTime,
          b = e.onExitFullscreen,
          h = e.trackEvent,
          v = e.autoplay,
          g = void 0 === v || v,
          w = (function (e, t) {
            if (null == e) return {}
            var r,
              n,
              o = (function (e, t) {
                if (null == e) return {}
                var r,
                  n,
                  o = {},
                  i = Object.keys(e)
                for (n = 0; n < i.length; n++)
                  (r = i[n]), t.indexOf(r) >= 0 || (o[r] = e[r])
                return o
              })(e, t)
            if (Object.getOwnPropertySymbols) {
              var i = Object.getOwnPropertySymbols(e)
              for (n = 0; n < i.length; n++)
                (r = i[n]),
                  t.indexOf(r) >= 0 ||
                    (Object.prototype.propertyIsEnumerable.call(e, r) &&
                      (o[r] = e[r]))
            }
            return o
          })(e, d),
          x = (0, n.useRef)(null),
          O = (0, u.Ln)()
        return (
          (0, n.useEffect)(
            function () {
              var e = x.current,
                n = g,
                o =
                  -1 !== navigator.userAgent.toLowerCase().indexOf('iphone') ||
                  -1 !== navigator.userAgent.toLowerCase().indexOf('ipad') ||
                  -1 !== navigator.userAgent.toLowerCase().indexOf('android'),
                c =
                  -1 !== navigator.userAgent.toLowerCase().indexOf('safari') &&
                  -1 !== navigator.userAgent.toLowerCase().indexOf('version')
              ;(0, l.n)('ConfigClickToPlay', !1) && (n = !o && !c && g)
              var u,
                d,
                y = null
              return (
                null != t &&
                  t.adTags &&
                  ((u = t.adTags),
                  (y = encodeURIComponent(
                    Object.entries(u)
                      .map(function (e) {
                        var t,
                          r,
                          n =
                            ((r = 2),
                            (function (e) {
                              if (Array.isArray(e)) return e
                            })((t = e)) ||
                              (function (e, t) {
                                var r =
                                  null == e
                                    ? null
                                    : ('undefined' != typeof Symbol &&
                                        e[Symbol.iterator]) ||
                                      e['@@iterator']
                                if (null != r) {
                                  var n,
                                    o,
                                    i,
                                    a,
                                    c = [],
                                    l = !0,
                                    u = !1
                                  try {
                                    if (((i = (r = r.call(e)).next), 0 === t)) {
                                      if (Object(r) !== r) return
                                      l = !1
                                    } else
                                      for (
                                        ;
                                        !(l = (n = i.call(r)).done) &&
                                        (c.push(n.value), c.length !== t);
                                        l = !0
                                      );
                                  } catch (e) {
                                    ;(u = !0), (o = e)
                                  } finally {
                                    try {
                                      if (
                                        !l &&
                                        null != r.return &&
                                        ((a = r.return()), Object(a) !== a)
                                      )
                                        return
                                    } finally {
                                      if (u) throw o
                                    }
                                  }
                                  return c
                                }
                              })(t, r) ||
                              (function (e, t) {
                                if (e) {
                                  if ('string' == typeof e) return s(e, t)
                                  var r = Object.prototype.toString
                                    .call(e)
                                    .slice(8, -1)
                                  return (
                                    'Object' === r &&
                                      e.constructor &&
                                      (r = e.constructor.name),
                                    'Map' === r || 'Set' === r
                                      ? Array.from(e)
                                      : 'Arguments' === r ||
                                        /^(?:Ui|I)nt(?:8|16|32)(?:Clamped)?Array$/.test(
                                          r
                                        )
                                      ? s(e, t)
                                      : void 0
                                  )
                                }
                              })(t, r) ||
                              (function () {
                                throw new TypeError(
                                  'Invalid attempt to destructure non-iterable instance.\nIn order to be iterable, non-array objects must have a [Symbol.iterator]() method.'
                                )
                              })()),
                          o = n[0],
                          i = n[1]
                        return ''.concat(o, '=').concat(i)
                      })
                      .join('&')
                  ))),
                e &&
                  (d = setTimeout(function () {
                    var o = e.contentWindow
                    o.addEventListener('message', function (e) {
                      var t
                      'exitFullscreen' ===
                        (null === (t = e.data) || void 0 === t
                          ? void 0
                          : t.type) &&
                        (null == b || b())
                    })
                    var c,
                      u,
                      s = o.document,
                      d = s.body,
                      v = s.createElement('style')
                    if (
                      ((v.innerHTML =
                        '\n          html, body, .video-js { width: 100%; height: 100%; }\n          body { margin: 0; background: #000000; overflow: hidden; }\n          .video-js .vjs-big-play-button:before,\n          .video-js.vjs-ima3-not-playing-yet .vjs-big-play-button:before {\n              display: block;\n          }\n          .video-js .vjs-big-play-button .vjs-icon-placeholder {\n              display: none;\n          }\n          .video-js:not(.vjs-has-started) .vjs-poster,\n          .video-js:not(.vjs-has-started) .vjs-tech {\n            opacity: 0.4!important;\n          }\n          @media only screen and (max-width: 629px) {\n            .video-js:not(.vjs-has-started) .vjs-poster,\n            .video-js:not(.vjs-has-started) .vjs-tech {\n              opacity: 0.4!important;\n            }\n          }'),
                      d.appendChild(v),
                      r)
                    ) {
                      var g = s.createElement('video'),
                        w =
                          ((c = r.split('_')),
                          (u = 2),
                          (function (e) {
                            if (Array.isArray(e)) return e
                          })(c) ||
                            (function (e, t) {
                              var r =
                                null == e
                                  ? null
                                  : ('undefined' != typeof Symbol &&
                                      e[Symbol.iterator]) ||
                                    e['@@iterator']
                              if (null != r) {
                                var n,
                                  o,
                                  i,
                                  a,
                                  c = [],
                                  l = !0,
                                  u = !1
                                try {
                                  if (((i = (r = r.call(e)).next), 0 === t)) {
                                    if (Object(r) !== r) return
                                    l = !1
                                  } else
                                    for (
                                      ;
                                      !(l = (n = i.call(r)).done) &&
                                      (c.push(n.value), c.length !== t);
                                      l = !0
                                    );
                                } catch (e) {
                                  ;(u = !0), (o = e)
                                } finally {
                                  try {
                                    if (
                                      !l &&
                                      null != r.return &&
                                      ((a = r.return()), Object(a) !== a)
                                    )
                                      return
                                  } finally {
                                    if (u) throw o
                                  }
                                }
                                return c
                              }
                            })(c, u) ||
                            (function (e, t) {
                              if (e) {
                                if ('string' == typeof e) return m(e, t)
                                var r = Object.prototype.toString
                                  .call(e)
                                  .slice(8, -1)
                                return (
                                  'Object' === r &&
                                    e.constructor &&
                                    (r = e.constructor.name),
                                  'Map' === r || 'Set' === r
                                    ? Array.from(e)
                                    : 'Arguments' === r ||
                                      /^(?:Ui|I)nt(?:8|16|32)(?:Clamped)?Array$/.test(
                                        r
                                      )
                                    ? m(e, t)
                                    : void 0
                                )
                              }
                            })(c, u) ||
                            (function () {
                              throw new TypeError(
                                'Invalid attempt to destructure non-iterable instance.\nIn order to be iterable, non-array objects must have a [Symbol.iterator]() method.'
                              )
                            })()),
                        x = w[0],
                        j = w[1]
                      ;(g.className = 'video-js vjs-fluid'),
                        g.setAttribute('data-account', '3461375237001'),
                        g.setAttribute('data-player', x),
                        g.setAttribute('data-embed', j),
                        g.setAttribute('data-application-id', 'true'),
                        g.setAttribute('playsinline', ''),
                        g.setAttribute('controls', ''),
                        i && g.setAttribute('data-video-id', i),
                        d.appendChild(g)
                      var S = s.createElement('script')
                      ;(S.src = 'https://players.brightcove.net/3461375237001/'
                        .concat(r, '/index')
                        .concat(
                          (0, l.n)('isProduction', !0) ? '.min.js' : '.js'
                        )),
                        (S.onload = function () {
                          var e = function (e) {
                            var r = s.createElement('script')
                            ;(r.innerHTML = '\n              '
                              .concat(
                                y
                                  ? "var customParamsForBrightcovePlayer = '".concat(
                                      y,
                                      "';"
                                    )
                                  : '',
                                '\n              var playerContainer = document.querySelector(\'.video-js\');\n              var player = bc(playerContainer);\n              \n              player.ready(function() {\n                if (window.frameElement && window.parent) {\n                  if (window.parent.loadBrightcovePlayerIntoPage) {\n                    window.parent.loadBrightcovePlayerIntoPage(this);\n                  }\n                } else {\n                  if (window.loadBrightcovePlayerIntoPage) {\n                    window.loadBrightcovePlayerIntoPage(this);\n                  }\n                }\n              });\n\n              player.on( "loadeddata", function(event){\n                var videoStartTime = '
                              )
                              .concat(a, ' < 0 ? player.duration() + ')
                              .concat(a, ' : ')
                              .concat(a, ';\n                ')
                              .concat(
                                a && a > 0
                                  ? "player.currentTime('".concat(a, "');")
                                  : '',
                                '\n                '
                              )
                              .concat(
                                a && a < 0
                                  ? 'player.currentTime(player.duration() +'.concat(
                                      a,
                                      ');'
                                    )
                                  : '',
                                "\n              });\n              \n              player.on('fullscreenchange', function() {\n                if (!player.isFullscreen()){\n                    window.postMessage({type:'exitFullscreen'})\n                }\n              });\n              "
                              )
                              .concat(
                                e ? "player.poster('".concat(e, "');") : '',
                                '\n              player.autoplay('
                              )
                              .concat(
                                n ? 'true' : 'false',
                                ');\n              '
                              )
                              .concat(
                                t
                                  ? "\n                    player.errors({ timeout: 1000 * 60 * 60 });\n                    player.src({type: '"
                                      .concat(t.type, "', src: '")
                                      .concat(
                                        t.src,
                                        "'});\n                    "
                                      )
                                  : '',
                                '\n            '
                              )),
                              d.appendChild(r)
                          }
                          null != t && t.poster
                            ? fetch(t.poster, { mode: 'cors' })
                                .then(function (r) {
                                  if (!r.ok)
                                    throw new Error('poster is invalid')
                                  e(t.poster)
                                })
                                .catch(function () {
                                  e(O ? p : f),
                                    null == h || h('Invalid poster', t.poster)
                                })
                            : t
                            ? e(O ? p : f)
                            : e()
                        }),
                        d.appendChild(S)
                    } else console.warn('BrightCovePlayer: playerId is not provided')
                  }, 100)),
                function () {
                  d && clearTimeout(d)
                }
              )
            },
            [r, i, a, t, b, O, h, g]
          ),
          o().createElement(
            c.xu,
            y(
              {
                sx: {
                  position: 'relative',
                  '&::before': {
                    content: '""',
                    display: 'block',
                    width: '100%',
                    paddingBottom: '56.25%',
                  },
                  '& > iframe': {
                    position: 'absolute',
                    top: '0',
                    left: '0',
                    width: '100%',
                    height: '100%',
                  },
                },
              },
              w
            ),
            o().createElement('iframe', { allowFullScreen: !1, ref: x })
          )
        )
      }
      b.propTypes = {
        linius: a().shape({
          type: a().string,
          src: a().string,
          poster: a().string,
          adTags: a().object,
        }),
        playerId: a().string,
        videoId: a().string,
        videoTime: a().number,
        onExitFullscreen: a().func,
        trackEvent: a().func,
        autoplay: a().bool,
      }
      const h = b
    },
    81987: (e, t, r) => {
      r.d(t, { Z: () => y })
      var n = r(1024),
        o = r.n(n),
        i = r(13980),
        a = r.n(i),
        c = r(30186)
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
      var u = ['sx']
      function s() {
        return (
          (s = Object.assign
            ? Object.assign.bind()
            : function (e) {
                for (var t = 1; t < arguments.length; t++) {
                  var r = arguments[t]
                  for (var n in r)
                    Object.prototype.hasOwnProperty.call(r, n) && (e[n] = r[n])
                }
                return e
              }),
          s.apply(this, arguments)
        )
      }
      function f(e, t) {
        var r = Object.keys(e)
        if (Object.getOwnPropertySymbols) {
          var n = Object.getOwnPropertySymbols(e)
          t &&
            (n = n.filter(function (t) {
              return Object.getOwnPropertyDescriptor(e, t).enumerable
            })),
            r.push.apply(r, n)
        }
        return r
      }
      function p(e) {
        for (var t = 1; t < arguments.length; t++) {
          var r = null != arguments[t] ? arguments[t] : {}
          t % 2
            ? f(Object(r), !0).forEach(function (t) {
                var n, o, i, a
                ;(n = e),
                  (o = t),
                  (i = r[t]),
                  (a = (function (e, t) {
                    if ('object' != l(e) || !e) return e
                    var r = e[Symbol.toPrimitive]
                    if (void 0 !== r) {
                      var n = r.call(e, 'string')
                      if ('object' != l(n)) return n
                      throw new TypeError(
                        '@@toPrimitive must return a primitive value.'
                      )
                    }
                    return String(e)
                  })(o)),
                  (o = 'symbol' == l(a) ? a : String(a)) in n
                    ? Object.defineProperty(n, o, {
                        value: i,
                        enumerable: !0,
                        configurable: !0,
                        writable: !0,
                      })
                    : (n[o] = i)
              })
            : Object.getOwnPropertyDescriptors
            ? Object.defineProperties(e, Object.getOwnPropertyDescriptors(r))
            : f(Object(r)).forEach(function (t) {
                Object.defineProperty(
                  e,
                  t,
                  Object.getOwnPropertyDescriptor(r, t)
                )
              })
        }
        return e
      }
      var d = function (e) {
        var t = e.sx,
          r = void 0 === t ? {} : t,
          n = (function (e, t) {
            if (null == e) return {}
            var r,
              n,
              o = (function (e, t) {
                if (null == e) return {}
                var r,
                  n,
                  o = {},
                  i = Object.keys(e)
                for (n = 0; n < i.length; n++)
                  (r = i[n]), t.indexOf(r) >= 0 || (o[r] = e[r])
                return o
              })(e, t)
            if (Object.getOwnPropertySymbols) {
              var i = Object.getOwnPropertySymbols(e)
              for (n = 0; n < i.length; n++)
                (r = i[n]),
                  t.indexOf(r) >= 0 ||
                    (Object.prototype.propertyIsEnumerable.call(e, r) &&
                      (o[r] = e[r]))
            }
            return o
          })(e, u)
        return o().createElement(
          c.xu,
          s(
            {
              className: 'button',
              as: 'button',
              type: 'button',
              variant: 'button.normal',
              sx: p(
                {
                  appearance: 'none',
                  cursor: 'pointer',
                  display: 'inline-flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontFamily: 'circular',
                  fontWeight: '600',
                  lineHeight: '1',
                  textDecoration: 'none',
                  backgroundColor: 'transparent',
                  outline: 'none',
                  '.button + &': { ml: 'sm' },
                },
                r
              ),
            },
            n
          )
        )
      }
      d.propTypes = { sx: a().object }
      const y = d
    },
    85814: (e, t, r) => {
      r.d(t, { Z: () => v })
      var n = r(1024),
        o = r.n(n),
        i = r(13980),
        a = r(30186),
        c = r(75506),
        l = r(77450),
        u = r(24734),
        s = r(18838)
      function f(e) {
        return (
          (f =
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
          f(e)
        )
      }
      var p = ['sx']
      function d() {
        return (
          (d = Object.assign
            ? Object.assign.bind()
            : function (e) {
                for (var t = 1; t < arguments.length; t++) {
                  var r = arguments[t]
                  for (var n in r)
                    Object.prototype.hasOwnProperty.call(r, n) && (e[n] = r[n])
                }
                return e
              }),
          d.apply(this, arguments)
        )
      }
      function y(e, t) {
        var r = Object.keys(e)
        if (Object.getOwnPropertySymbols) {
          var n = Object.getOwnPropertySymbols(e)
          t &&
            (n = n.filter(function (t) {
              return Object.getOwnPropertyDescriptor(e, t).enumerable
            })),
            r.push.apply(r, n)
        }
        return r
      }
      function m(e) {
        for (var t = 1; t < arguments.length; t++) {
          var r = null != arguments[t] ? arguments[t] : {}
          t % 2
            ? y(Object(r), !0).forEach(function (t) {
                var n, o, i, a
                ;(n = e),
                  (o = t),
                  (i = r[t]),
                  (a = (function (e, t) {
                    if ('object' != f(e) || !e) return e
                    var r = e[Symbol.toPrimitive]
                    if (void 0 !== r) {
                      var n = r.call(e, 'string')
                      if ('object' != f(n)) return n
                      throw new TypeError(
                        '@@toPrimitive must return a primitive value.'
                      )
                    }
                    return String(e)
                  })(o)),
                  (o = 'symbol' == f(a) ? a : String(a)) in n
                    ? Object.defineProperty(n, o, {
                        value: i,
                        enumerable: !0,
                        configurable: !0,
                        writable: !0,
                      })
                    : (n[o] = i)
              })
            : Object.getOwnPropertyDescriptors
            ? Object.defineProperties(e, Object.getOwnPropertyDescriptors(r))
            : y(Object(r)).forEach(function (t) {
                Object.defineProperty(
                  e,
                  t,
                  Object.getOwnPropertyDescriptor(r, t)
                )
              })
        }
        return e
      }
      var b = function (e) {
          var t = e.sx,
            r = void 0 === t ? {} : t,
            n = (function (e, t) {
              if (null == e) return {}
              var r,
                n,
                o = (function (e, t) {
                  if (null == e) return {}
                  var r,
                    n,
                    o = {},
                    i = Object.keys(e)
                  for (n = 0; n < i.length; n++)
                    (r = i[n]), t.indexOf(r) >= 0 || (o[r] = e[r])
                  return o
                })(e, t)
              if (Object.getOwnPropertySymbols) {
                var i = Object.getOwnPropertySymbols(e)
                for (n = 0; n < i.length; n++)
                  (r = i[n]),
                    t.indexOf(r) >= 0 ||
                      (Object.prototype.propertyIsEnumerable.call(e, r) &&
                        (o[r] = e[r]))
              }
              return o
            })(e, p)
          return o().createElement(
            a.kC,
            d(
              {
                className: 'loading',
                sx: m(
                  {
                    position: 'absolute',
                    left: 0,
                    right: 0,
                    top: 0,
                    bottom: 0,
                    alignItems: 'center',
                    justifyContent: 'center',
                    minHeight: '128px',
                    overflow: 'auto',
                  },
                  r
                ),
              },
              n
            )
          )
        },
        h = function (e) {
          var t = e.loading,
            r = e.data,
            n = e.error,
            i = e.children
          return t
            ? o().createElement(
                b,
                null,
                o().createElement(s.Vd.Loader, {
                  width: '48px',
                  height: '48px',
                })
              )
            : n
            ? o().createElement(
                b,
                {
                  sx: {
                    alignItems: 'flex-start',
                    border: '1px dashed',
                    borderColor: 'grey-33',
                    position: 'static',
                    height: '220px',
                  },
                },
                o().createElement(
                  a.xu,
                  { p: 'lg', sx: { textAlign: 'center', color: 'grey-66' } },
                  o().createElement(
                    a.X6,
                    {
                      sx: {
                        fontSize: '20px',
                        lineHeight: '1.4',
                        fontFamily: 'roboto',
                        fontWeight: 'body',
                        mb: 'lg',
                      },
                    },
                    'Something went wrong'
                  ),
                  o().createElement(
                    a.xu,
                    { sx: { fontSize: '80px' } },
                    o().createElement(l.Z, { inline: !0, type: 'exclamation' })
                  ),
                  o().createElement(
                    a.xv,
                    { sx: { fontSize: '14px', lineHeight: '1.6' } },
                    o().createElement(
                      'b',
                      null,
                      'Please refresh the page and try again,'
                    ),
                    o().createElement('br', null),
                    ' If this persists ',
                    o().createElement('b', null, 'contact support')
                  ),
                  o().createElement(
                    a.xv,
                    {
                      as: 'pre',
                      sx: {
                        mt: '20px',
                        whiteSpace: 'pre-wrap',
                        textAlign: 'left',
                        display: 'none',
                      },
                    },
                    ''.concat(n)
                  )
                )
              )
            : r
            ? o().createElement(
                a.xu,
                { sx: { animation: (0, c.iv)(u.J, ' 1s ease-out') } },
                i
              )
            : null
        }
      h.propTypes = {
        loading: i.PropTypes.bool,
        data: i.PropTypes.object,
        error: i.PropTypes.object,
        children: i.PropTypes.node,
      }
      const v = h
    },
    90570: (e, t, r) => {
      r.d(t, { ZP: () => _, YG: () => L })
      var n = r(89734),
        o = r.n(n),
        i = r(1024),
        a = r.n(i),
        c = r(30186),
        l = r(13980),
        u = r(12524),
        s = r.n(u),
        f = ['isScratched'],
        p = ['texture', 'isScratched', 'alt']
      function d(e, t) {
        ;(null == t || t > e.length) && (t = e.length)
        for (var r = 0, n = new Array(t); r < t; r++) n[r] = e[r]
        return n
      }
      function y() {
        return (
          (y = Object.assign
            ? Object.assign.bind()
            : function (e) {
                for (var t = 1; t < arguments.length; t++) {
                  var r = arguments[t]
                  for (var n in r)
                    Object.prototype.hasOwnProperty.call(r, n) && (e[n] = r[n])
                }
                return e
              }),
          y.apply(this, arguments)
        )
      }
      function m(e, t) {
        if (null == e) return {}
        var r,
          n,
          o = (function (e, t) {
            if (null == e) return {}
            var r,
              n,
              o = {},
              i = Object.keys(e)
            for (n = 0; n < i.length; n++)
              (r = i[n]), t.indexOf(r) >= 0 || (o[r] = e[r])
            return o
          })(e, t)
        if (Object.getOwnPropertySymbols) {
          var i = Object.getOwnPropertySymbols(e)
          for (n = 0; n < i.length; n++)
            (r = i[n]),
              t.indexOf(r) >= 0 ||
                (Object.prototype.propertyIsEnumerable.call(e, r) &&
                  (o[r] = e[r]))
        }
        return o
      }
      var b = function (e) {
          var t = e.isScratched,
            r = m(e, f)
          return a().createElement(
            c.xu,
            y(
              {
                className: 'scratch-decorator',
                sx: {
                  display: 'inline-block',
                  position: 'relative',
                  '&:after': t
                    ? {
                        content: '"src"',
                        textTransform: 'uppercase',
                        position: 'absolute',
                        left: '50%',
                        top: '50%',
                        whiteSpace: 'nowrap',
                        transform: 'translate(-50%, -50%)',
                        fontFamily: 'roboto',
                        fontWeight: 'bold',
                        fontSize: '14px',
                        color: 'src',
                      }
                    : null,
                },
              },
              r
            )
          )
        },
        h = function (e) {
          var t,
            r,
            n = e.texture,
            o = e.isScratched,
            l = e.alt,
            u = m(e, p),
            f =
              ((t = (0, i.useState)(n)),
              (r = 2),
              (function (e) {
                if (Array.isArray(e)) return e
              })(t) ||
                (function (e, t) {
                  var r =
                    null == e
                      ? null
                      : ('undefined' != typeof Symbol && e[Symbol.iterator]) ||
                        e['@@iterator']
                  if (null != r) {
                    var n,
                      o,
                      i,
                      a,
                      c = [],
                      l = !0,
                      u = !1
                    try {
                      if (((i = (r = r.call(e)).next), 0 === t)) {
                        if (Object(r) !== r) return
                        l = !1
                      } else
                        for (
                          ;
                          !(l = (n = i.call(r)).done) &&
                          (c.push(n.value), c.length !== t);
                          l = !0
                        );
                    } catch (e) {
                      ;(u = !0), (o = e)
                    } finally {
                      try {
                        if (
                          !l &&
                          null != r.return &&
                          ((a = r.return()), Object(a) !== a)
                        )
                          return
                      } finally {
                        if (u) throw o
                      }
                    }
                    return c
                  }
                })(t, r) ||
                (function (e, t) {
                  if (e) {
                    if ('string' == typeof e) return d(e, t)
                    var r = Object.prototype.toString.call(e).slice(8, -1)
                    return (
                      'Object' === r &&
                        e.constructor &&
                        (r = e.constructor.name),
                      'Map' === r || 'Set' === r
                        ? Array.from(e)
                        : 'Arguments' === r ||
                          /^(?:Ui|I)nt(?:8|16|32)(?:Clamped)?Array$/.test(r)
                        ? d(e, t)
                        : void 0
                    )
                  }
                })(t, r) ||
                (function () {
                  throw new TypeError(
                    'Invalid attempt to destructure non-iterable instance.\nIn order to be iterable, non-array objects must have a [Symbol.iterator]() method.'
                  )
                })()),
            h = f[0],
            v = f[1]
          return (
            (0, i.useEffect)(
              function () {
                if (n) {
                  var e = new window.Image()
                  ;(e.src = n),
                    (e.onerror = function () {
                      v(null)
                    })
                }
              },
              [n]
            ),
            h
              ? a().createElement(
                  b,
                  y({ isScratched: o }, u),
                  a().createElement(c.Ee, {
                    className: 'silk-icon',
                    src: h,
                    sx: {
                      width: '30px',
                      height: '30px',
                      opacity: o ? '0.3' : '1',
                    },
                  })
                )
              : a().createElement(
                  b,
                  y(
                    { className: s()('silk-sprite--no-silk'), isScratched: o },
                    u
                  ),
                  a().createElement(c.Ee, {
                    src: 'https://s3-ap-southeast-2.amazonaws.com/racevic.silks/nosilk.png',
                    alt: l,
                    sx: {
                      width: '30px',
                      height: '30px',
                      opacity: o ? '0.3' : '1',
                    },
                  })
                )
          )
        }
      h.propTypes = {
        texture: l.PropTypes.string.isRequired,
        isScratched: l.PropTypes.bool,
        alt: l.PropTypes.string.isRequired,
      }
      const v = (0, i.memo)(h)
      var g = r(96921),
        w = r(75506),
        x = r(24734),
        O = r(18838),
        j = ['indicators', 'delayFn']
      function S() {
        return (
          (S = Object.assign
            ? Object.assign.bind()
            : function (e) {
                for (var t = 1; t < arguments.length; t++) {
                  var r = arguments[t]
                  for (var n in r)
                    Object.prototype.hasOwnProperty.call(r, n) && (e[n] = r[n])
                }
                return e
              }),
          S.apply(this, arguments)
        )
      }
      function E(e, t) {
        ;(null == t || t > e.length) && (t = e.length)
        for (var r = 0, n = new Array(t); r < t; r++) n[r] = e[r]
        return n
      }
      var k = function (e) {
        var t,
          r,
          n = e.indicators,
          o = e.delayFn,
          l = (function (e, t) {
            if (null == e) return {}
            var r,
              n,
              o = (function (e, t) {
                if (null == e) return {}
                var r,
                  n,
                  o = {},
                  i = Object.keys(e)
                for (n = 0; n < i.length; n++)
                  (r = i[n]), t.indexOf(r) >= 0 || (o[r] = e[r])
                return o
              })(e, t)
            if (Object.getOwnPropertySymbols) {
              var i = Object.getOwnPropertySymbols(e)
              for (n = 0; n < i.length; n++)
                (r = i[n]),
                  t.indexOf(r) >= 0 ||
                    (Object.prototype.propertyIsEnumerable.call(e, r) &&
                      (o[r] = e[r]))
            }
            return o
          })(e, j),
          u =
            ((t = (0, i.useState)(!1)),
            (r = 2),
            (function (e) {
              if (Array.isArray(e)) return e
            })(t) ||
              (function (e, t) {
                var r =
                  null == e
                    ? null
                    : ('undefined' != typeof Symbol && e[Symbol.iterator]) ||
                      e['@@iterator']
                if (null != r) {
                  var n,
                    o,
                    i,
                    a,
                    c = [],
                    l = !0,
                    u = !1
                  try {
                    if (((i = (r = r.call(e)).next), 0 === t)) {
                      if (Object(r) !== r) return
                      l = !1
                    } else
                      for (
                        ;
                        !(l = (n = i.call(r)).done) &&
                        (c.push(n.value), c.length !== t);
                        l = !0
                      );
                  } catch (e) {
                    ;(u = !0), (o = e)
                  } finally {
                    try {
                      if (
                        !l &&
                        null != r.return &&
                        ((a = r.return()), Object(a) !== a)
                      )
                        return
                    } finally {
                      if (u) throw o
                    }
                  }
                  return c
                }
              })(t, r) ||
              (function (e, t) {
                if (e) {
                  if ('string' == typeof e) return E(e, t)
                  var r = Object.prototype.toString.call(e).slice(8, -1)
                  return (
                    'Object' === r && e.constructor && (r = e.constructor.name),
                    'Map' === r || 'Set' === r
                      ? Array.from(e)
                      : 'Arguments' === r ||
                        /^(?:Ui|I)nt(?:8|16|32)(?:Clamped)?Array$/.test(r)
                      ? E(e, t)
                      : void 0
                  )
                }
              })(t, r) ||
              (function () {
                throw new TypeError(
                  'Invalid attempt to destructure non-iterable instance.\nIn order to be iterable, non-array objects must have a [Symbol.iterator]() method.'
                )
              })()),
          s = u[0],
          f = u[1],
          p = (0, i.useRef)(null)
        return null != n && n.length
          ? a().createElement(
              c.kC,
              S(
                {
                  className: 'race-indicator',
                  sx: { position: 'relative', cursor: 'pointer' },
                  onMouseEnter: function () {
                    clearTimeout(p.current), f(!0)
                  },
                  onMouseLeave: function () {
                    clearTimeout(p.current),
                      (p.current = setTimeout(function () {
                        return f(!1)
                      }, 200))
                  },
                },
                l
              ),
              n.map(function (e, t) {
                return a().createElement(c.xu, {
                  className: 'race-indicator__item',
                  sx: {
                    flex: '0 0 auto',
                    width: '10px',
                    height: '10px',
                    borderRadius: '50%',
                    backgroundColor: e.positive
                      ? 'indicator.positive'
                      : 'indicator.negetive',
                    '&:not(:first-of-type)': { marginLeft: 'sm' },
                    animation: (0, w.iv)(x.J, ' ease-out 0.3s backwards'),
                    animationDelay: ''.concat(o ? o(t) : 0, 's'),
                  },
                  key: t,
                })
              }),
              s
                ? a().createElement(
                    c.xu,
                    {
                      className: 'race-indicator__detail',
                      sx: {
                        position: 'absolute',
                        left: '50%',
                        top: '100%',
                        transform: 'translateX(-50%)',
                        marginTop: '11px',
                        backgroundColor: 'grey-33',
                        padding: '10px',
                        transition: 'opacity ease-in 0.2s',
                        animation: (0, w.iv)(x.J, ' ease-out 0.5s backwards'),
                        zIndex: '1',
                        '.speed-map__entry:nth-last-of-type(-n+3) &': {
                          top: 'auto',
                          bottom: 'calc(100% + 30px)',
                        },
                        '.race-indicator:not(:hover) &': { opacity: 0 },
                      },
                    },
                    a().createElement(c.xu, {
                      className: 'race-indicator__detail-tip',
                      sx: {
                        position: 'absolute',
                        top: '-11px',
                        left: '50%',
                        transform: 'translateX(-50%)',
                        border: 'solid 11px transparent',
                        borderTopWidth: '0',
                        borderBottomColor: 'grey-33',
                        '.speed-map__entry:nth-last-of-type(-n+3) &': {
                          borderTopWidth: '11px',
                          borderTopColor: 'grey-33',
                          borderBottomWidth: '0',
                          borderBottomColor: 'transparent',
                          top: 'auto',
                          bottom: '-11px',
                        },
                      },
                    }),
                    a().createElement(
                      c.xu,
                      null,
                      a().createElement(
                        c.xu,
                        { sx: { width: '100px', color: 'white', mb: 'md' } },
                        a().createElement(O.Vd.FormAnalystMono, {
                          style: { width: '100%', height: '23px' },
                        })
                      ),
                      a().createElement(
                        c.kC,
                        {
                          sx: {
                            justifyContent: 'space-between',
                            width: '320px',
                            maxWidth: '320px',
                          },
                        },
                        n.map(function (e, t) {
                          return a().createElement(
                            c.kC,
                            {
                              sx: {
                                flex: '1 1 auto',
                                alignItems: 'center',
                                justifyContent: 'center',
                                width: '33%',
                                padding: 'md',
                                border: '2px solid',
                                borderColor: e.positive
                                  ? 'indicator.positive'
                                  : 'indicator.negetive',
                                '&:not(:first-of-type)': { marginLeft: 'md' },
                              },
                              key: t,
                            },
                            a().createElement(
                              c.xv,
                              {
                                className: 'race-indicator__detail-item',
                                sx: {
                                  textAlign: 'center',
                                  fontSize: 'body',
                                  color: 'white',
                                },
                              },
                              e.key
                            )
                          )
                        })
                      )
                    )
                  )
                : null
            )
          : null
      }
      k.propTypes = {
        indicators: l.PropTypes.arrayOf(l.PropTypes.object),
        delayFn: l.PropTypes.func,
      }
      const P = k
      var C = r(62388),
        A = [
          'raceEntry',
          'suggestedBets',
          'isHighlighted',
          'betAction',
          'delayFn',
        ]
      function T() {
        return (
          (T = Object.assign
            ? Object.assign.bind()
            : function (e) {
                for (var t = 1; t < arguments.length; t++) {
                  var r = arguments[t]
                  for (var n in r)
                    Object.prototype.hasOwnProperty.call(r, n) && (e[n] = r[n])
                }
                return e
              }),
          T.apply(this, arguments)
        )
      }
      function I(e, t) {
        ;(null == t || t > e.length) && (t = e.length)
        for (var r = 0, n = new Array(t); r < t; r++) n[r] = e[r]
        return n
      }
      var L = function (e) {
          var t =
            arguments.length > 1 && void 0 !== arguments[1]
              ? arguments[1]
              : { sort: !0 }
          return (0, i.useMemo)(
            function () {
              var r = o()(e.selections, 'position'),
                n = t.sort ? r : e.selections,
                i = n
                  .filter(function (e) {
                    return e.tipBetType
                  })
                  .map(function (e) {
                    return { horseName: e.horseName, tipBetType: e.tipBetType }
                  })
              return { raceEntries: n, suggestedBets: i }
            },
            [t.sort, e.selections]
          )
        },
        N = function (e) {
          var t,
            r,
            n = e.raceEntry,
            o = e.suggestedBets,
            l = e.isHighlighted,
            u = e.betAction,
            s = e.delayFn,
            f = (function (e, t) {
              if (null == e) return {}
              var r,
                n,
                o = (function (e, t) {
                  if (null == e) return {}
                  var r,
                    n,
                    o = {},
                    i = Object.keys(e)
                  for (n = 0; n < i.length; n++)
                    (r = i[n]), t.indexOf(r) >= 0 || (o[r] = e[r])
                  return o
                })(e, t)
              if (Object.getOwnPropertySymbols) {
                var i = Object.getOwnPropertySymbols(e)
                for (n = 0; n < i.length; n++)
                  (r = i[n]),
                    t.indexOf(r) >= 0 ||
                      (Object.prototype.propertyIsEnumerable.call(e, r) &&
                        (o[r] = e[r]))
              }
              return o
            })(e, A),
            p = (function (e, t, r) {
              return (0, i.useMemo)(
                function () {
                  return null == r
                    ? void 0
                    : r.filter(function (r) {
                        var n
                        return (
                          String(r.raceNumber) === String(e.raceNumber) &&
                          String(
                            null === (n = r.horse) || void 0 === n
                              ? void 0
                              : n.outcomeId
                          ) === String(t.outcomeId)
                        )
                      })
                },
                [e, t, r]
              )
            })(
              ((t = (0, i.useContext)(C.Rl)),
              (r = 1),
              (function (e) {
                if (Array.isArray(e)) return e
              })(t) ||
                (function (e, t) {
                  var r =
                    null == e
                      ? null
                      : ('undefined' != typeof Symbol && e[Symbol.iterator]) ||
                        e['@@iterator']
                  if (null != r) {
                    var n,
                      o,
                      i,
                      a,
                      c = [],
                      l = !0,
                      u = !1
                    try {
                      if (((i = (r = r.call(e)).next), 0 === t)) {
                        if (Object(r) !== r) return
                        l = !1
                      } else
                        for (
                          ;
                          !(l = (n = i.call(r)).done) &&
                          (c.push(n.value), c.length !== t);
                          l = !0
                        );
                    } catch (e) {
                      ;(u = !0), (o = e)
                    } finally {
                      try {
                        if (
                          !l &&
                          null != r.return &&
                          ((a = r.return()), Object(a) !== a)
                        )
                          return
                      } finally {
                        if (u) throw o
                      }
                    }
                    return c
                  }
                })(t, r) ||
                (function (e, t) {
                  if (e) {
                    if ('string' == typeof e) return I(e, t)
                    var r = Object.prototype.toString.call(e).slice(8, -1)
                    return (
                      'Object' === r &&
                        e.constructor &&
                        (r = e.constructor.name),
                      'Map' === r || 'Set' === r
                        ? Array.from(e)
                        : 'Arguments' === r ||
                          /^(?:Ui|I)nt(?:8|16|32)(?:Clamped)?Array$/.test(r)
                        ? I(e, t)
                        : void 0
                    )
                  }
                })(t, r) ||
                (function () {
                  throw new TypeError(
                    'Invalid attempt to destructure non-iterable instance.\nIn order to be iterable, non-array objects must have a [Symbol.iterator]() method.'
                  )
                })())[0],
              n,
              o
            )
          return a().createElement(
            c.kC,
            T(
              {
                className: 'race-entry',
                sx: {
                  lineHeight: 1.5,
                  alignItems: 'center',
                  padding: '8px 12px',
                  transition: 'background-color ease-out 0.3s',
                  backgroundColor: l ? 'grey-de' : 'transparent',
                  '.race-card--form-analyst-tips &': { padding: '5px 12px' },
                },
              },
              f
            ),
            n.silkUrl &&
              a().createElement(v, {
                texture: n.silkUrl,
                isScratched: n.isScratched,
                alt: ''.concat(n.outcomeId),
                flex: '0 0 auto',
                width: 1,
                height: 1,
                mr: 'sm',
              }),
            a().createElement(
              c.xu,
              {
                sx: { flex: '1 1 auto', opacity: n.isScratched ? '0.3' : '1' },
              },
              a().createElement(
                c.kC,
                { sx: { alignItems: 'center', flexWrap: 'wrap' } },
                a().createElement(
                  c.xv,
                  {
                    className: 'race-entry__info',
                    sx: {
                      flex: '0 0 auto',
                      fontSize: 'body',
                      fontFamily: 'roboto',
                      fontWeight: 'bold',
                      color: 'grey-33',
                      marginRight: 'sm',
                      '.race-card--form-analyst-tips &': { color: 'grey-66' },
                    },
                  },
                  ''.concat(n.outcomeId, '.'),
                  ' ',
                  n.horseName,
                  ' ',
                  n.barrierNumber && '('.concat(n.barrierNumber, ')')
                ),
                a().createElement(P, {
                  py: 'sm',
                  marginRight: 'sm',
                  indicators: n.highlights,
                  delayFn: s,
                }),
                null == p
                  ? void 0
                  : p.map(function (e) {
                      return a().createElement(
                        c.xv,
                        {
                          className: 'race-entry__bet',
                          sx: {
                            fontSize: 'sm',
                            textTransform: 'uppercase',
                            lineHeight: 1,
                            padding: '2px',
                            borderRadius: '3px',
                            border: '1px solid',
                            borderColor: 'bets.'.concat(e.type),
                            color: 'bets.'.concat(e.type),
                          },
                          key: e.type,
                        },
                        (0, g.Tk)(e.type)
                      )
                    })
              ),
              (n.trainerName || n.jockeyName) &&
                a().createElement(
                  c.kC,
                  {
                    className: 'race-entry__names',
                    sx: {
                      justifyContent: 'flex-start',
                      fontSize: 'sm',
                      fontFamily: 'roboto',
                      color: 'grey-66',
                      '.race-card--form-analyst-tips &': { color: 'grey-99' },
                    },
                  },
                  n.trainerName &&
                    a().createElement(
                      c.xv,
                      {
                        sx: {
                          flex: '0 1 auto',
                          whiteSpace: 'nowrap',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          mr: 'sm',
                        },
                      },
                      a().createElement('b', null, 'T:'),
                      ' ',
                      (0, g.n1)(n)
                    ),
                  n.jockeyName &&
                    a().createElement(
                      c.xv,
                      {
                        sx: {
                          flex: '0 1 auto',
                          whiteSpace: 'nowrap',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                        },
                      },
                      a().createElement('b', null, 'J:'),
                      ' ',
                      (0, g.ZT)(n)
                    )
                )
            ),
            null == u ? void 0 : u()
          )
        }
      N.propTypes = {
        raceEntry: l.PropTypes.object.isRequired,
        suggestedBets: l.PropTypes.arrayOf(l.PropTypes.object),
        betAction: l.PropTypes.func,
        delayFn: l.PropTypes.func,
        isHighlighted: l.PropTypes.bool,
      }
      const _ = N
    },
    1576: (e, t, r) => {
      r.d(t, { Z: () => w })
      var n = r(1024),
        o = r.n(n),
        i = r(13980),
        a = r.n(i),
        c = r(30186),
        l = r(12524),
        u = r.n(l),
        s = r(77450),
        f = r(81987)
      function p(e) {
        return (
          (p =
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
          p(e)
        )
      }
      var d = ['hoverStylePrimary', 'selected']
      function y(e, t) {
        ;(null == t || t > e.length) && (t = e.length)
        for (var r = 0, n = new Array(t); r < t; r++) n[r] = e[r]
        return n
      }
      function m() {
        return (
          (m = Object.assign
            ? Object.assign.bind()
            : function (e) {
                for (var t = 1; t < arguments.length; t++) {
                  var r = arguments[t]
                  for (var n in r)
                    Object.prototype.hasOwnProperty.call(r, n) && (e[n] = r[n])
                }
                return e
              }),
          m.apply(this, arguments)
        )
      }
      function b(e, t) {
        var r = Object.keys(e)
        if (Object.getOwnPropertySymbols) {
          var n = Object.getOwnPropertySymbols(e)
          t &&
            (n = n.filter(function (t) {
              return Object.getOwnPropertyDescriptor(e, t).enumerable
            })),
            r.push.apply(r, n)
        }
        return r
      }
      function h(e) {
        for (var t = 1; t < arguments.length; t++) {
          var r = null != arguments[t] ? arguments[t] : {}
          t % 2
            ? b(Object(r), !0).forEach(function (t) {
                var n, o, i, a
                ;(n = e),
                  (o = t),
                  (i = r[t]),
                  (a = (function (e, t) {
                    if ('object' != p(e) || !e) return e
                    var r = e[Symbol.toPrimitive]
                    if (void 0 !== r) {
                      var n = r.call(e, 'string')
                      if ('object' != p(n)) return n
                      throw new TypeError(
                        '@@toPrimitive must return a primitive value.'
                      )
                    }
                    return String(e)
                  })(o)),
                  (o = 'symbol' == p(a) ? a : String(a)) in n
                    ? Object.defineProperty(n, o, {
                        value: i,
                        enumerable: !0,
                        configurable: !0,
                        writable: !0,
                      })
                    : (n[o] = i)
              })
            : Object.getOwnPropertyDescriptors
            ? Object.defineProperties(e, Object.getOwnPropertyDescriptors(r))
            : b(Object(r)).forEach(function (t) {
                Object.defineProperty(
                  e,
                  t,
                  Object.getOwnPropertyDescriptor(r, t)
                )
              })
        }
        return e
      }
      var v = function (e) {
        var t = e.hoverStylePrimary,
          r = e.selected,
          n = (function (e, t) {
            if (null == e) return {}
            var r,
              n,
              o = (function (e, t) {
                if (null == e) return {}
                var r,
                  n,
                  o = {},
                  i = Object.keys(e)
                for (n = 0; n < i.length; n++)
                  (r = i[n]), t.indexOf(r) >= 0 || (o[r] = e[r])
                return o
              })(e, t)
            if (Object.getOwnPropertySymbols) {
              var i = Object.getOwnPropertySymbols(e)
              for (n = 0; n < i.length; n++)
                (r = i[n]),
                  t.indexOf(r) >= 0 ||
                    (Object.prototype.propertyIsEnumerable.call(e, r) &&
                      (o[r] = e[r]))
            }
            return o
          })(e, d)
        return o().createElement(
          c.kC,
          m(
            {
              className: u()('search-suggestion__item', {
                'search-suggestion__item--selected': r,
              }),
              sx: h(
                {
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  backgroundColor: r ? 'offWhite' : 'white',
                  borderTop: '1px solid',
                  borderTopColor: 'grey-de',
                  p: '8px',
                  color: r ? 'grey-33' : 'grey-99',
                  fontSize: '12px',
                  lineHeight: 2,
                  cursor: 'pointer',
                  '&:hover': { backgroundColor: 'offWhite', color: 'grey-33' },
                },
                t && {
                  backgroundColor: 'white',
                  color: r ? 'primary' : 'grey-99',
                  '&:hover': { backgroundColor: 'white', color: 'primary' },
                }
              ),
            },
            n
          )
        )
      }
      v.propTypes = { selected: a().bool, hoverStylePrimary: a().bool }
      var g = function (e) {
        var t = e.suggestion,
          r = e.selectedSuggestion,
          n = e.showSuggestion,
          i = e.query,
          a = e.onItemClick,
          l = e.onViewAll,
          u = e.viewAllHidden,
          p = e.iconHidden,
          d = e.headerHidden,
          m = e.hoverStylePrimary,
          b = n && (null == t ? void 0 : t.total) && i.length > 2
        return (
          t &&
          o().createElement(
            c.xu,
            {
              className: 'search-suggestion',
              sx: {
                width: '100%',
                overflow: 'hidden',
                backgroundColor: 'white',
                transition: 'all 0.3s ease-out',
                transitionDelay: n ? '0.3s' : '0',
                maxHeight: b ? '650px' : '0',
                boxShadow: b
                  ? '0px 5px 5px 0px rgba(0,0,0,0.2)'
                  : '0 0 0 0 rgba(0,0,0,0.2)',
              },
            },
            Object.entries(t.items).map(function (e) {
              var t,
                n,
                i =
                  ((n = 2),
                  (function (e) {
                    if (Array.isArray(e)) return e
                  })((t = e)) ||
                    (function (e, t) {
                      var r =
                        null == e
                          ? null
                          : ('undefined' != typeof Symbol &&
                              e[Symbol.iterator]) ||
                            e['@@iterator']
                      if (null != r) {
                        var n,
                          o,
                          i,
                          a,
                          c = [],
                          l = !0,
                          u = !1
                        try {
                          if (((i = (r = r.call(e)).next), 0 === t)) {
                            if (Object(r) !== r) return
                            l = !1
                          } else
                            for (
                              ;
                              !(l = (n = i.call(r)).done) &&
                              (c.push(n.value), c.length !== t);
                              l = !0
                            );
                        } catch (e) {
                          ;(u = !0), (o = e)
                        } finally {
                          try {
                            if (
                              !l &&
                              null != r.return &&
                              ((a = r.return()), Object(a) !== a)
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
                        if ('string' == typeof e) return y(e, t)
                        var r = Object.prototype.toString.call(e).slice(8, -1)
                        return (
                          'Object' === r &&
                            e.constructor &&
                            (r = e.constructor.name),
                          'Map' === r || 'Set' === r
                            ? Array.from(e)
                            : 'Arguments' === r ||
                              /^(?:Ui|I)nt(?:8|16|32)(?:Clamped)?Array$/.test(r)
                            ? y(e, t)
                            : void 0
                        )
                      }
                    })(t, n) ||
                    (function () {
                      throw new TypeError(
                        'Invalid attempt to destructure non-iterable instance.\nIn order to be iterable, non-array objects must have a [Symbol.iterator]() method.'
                      )
                    })()),
                l = i[0],
                u = i[1]
              return o().createElement(
                o().Fragment,
                { key: l },
                !d &&
                  o().createElement(
                    c.xu,
                    {
                      className: 'search-suggestion__group-title',
                      sx: {
                        borderTop: '1px solid',
                        borderTopColor: 'grey-de',
                        px: '10px',
                        color: 'grey-99',
                        fontSize: 'sm',
                        lineHeight: '20px',
                        backgroundColor: 'offWhite',
                        fontWeight: 'bold',
                        textTransform: 'uppercase',
                        textAlign: 'right',
                      },
                    },
                    l,
                    ' Results'
                  ),
                u.map(function (e) {
                  return o().createElement(
                    v,
                    {
                      selected: r === e,
                      onClick: function (t) {
                        return a(t, e)
                      },
                      key: e.ContentId,
                      hoverStylePrimary: m,
                    },
                    o().createElement(
                      c.xu,
                      { sx: { flex: '1 1 auto' } },
                      o().createElement(c.xv, null, e.ContentTitle),
                      e.ContentDate &&
                        o().createElement(
                          c.xv,
                          { fontSize: 'sm' },
                          e.ContentDate
                        )
                    ),
                    'Horse' === e.ContentType &&
                      o().createElement(
                        f.Z,
                        {
                          as: 'a',
                          href: 'https://www.racing.com/replays/#/replay-hub/search/'.concat(
                            e.ContentTitle
                          ),
                          sx: { padding: '6px 8px 6px 10px' },
                        },
                        'Replays',
                        o().createElement(
                          c.xu,
                          { sx: { ml: '4px', fontSize: '16px' } },
                          o().createElement(s.Z, {
                            type: 'replay-icon',
                            inline: !0,
                          })
                        )
                      ),
                    !p &&
                      o().createElement(
                        c.xu,
                        {
                          as: 'span',
                          className: 'search-suggestion__type icon',
                          sx: {
                            flex: '0 0 auto',
                            ml: '10px',
                            fontSize: '20px',
                            '.search-suggestion__item:hover &': {
                              transition: 'all 0.3s ease-out',
                              transform: 'rotate(360deg)',
                            },
                            '.search-suggestion__item--selected &': {
                              transition: 'all 0.3s ease-out',
                              transform: 'rotate(360deg)',
                            },
                          },
                        },
                        o().createElement(s.Z, {
                          type: { l: 'article', n: 'horse-shoe', f: 'photo' }[
                            e.CategoryIcon
                          ],
                          inline: !0,
                        })
                      )
                  )
                })
              )
            }),
            !u &&
              o().createElement(
                v,
                { selected: !r, justifyContent: 'center', onClick: l },
                'View all ',
                t.total,
                ' results'
              )
          )
        )
      }
      g.propTypes = {
        onViewAll: a().func,
        onItemClick: a().func.isRequired,
        selectedSuggestion: a().object,
        showSuggestion: a().bool,
        suggestion: a().object,
        query: a().string.isRequired,
        viewAllHidden: a().bool,
        iconHidden: a().bool,
        headerHidden: a().bool,
        hoverStylePrimary: a().bool,
      }
      const w = g
    },
    54253: (e, t, r) => {
      r.d(t, { Z: () => m })
      var n = r(1024),
        o = r.n(n),
        i = r(13980),
        a = r.n(i),
        c = r(30186),
        l = r(40163)
      function u(e) {
        return (
          (u =
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
          u(e)
        )
      }
      var s = ['active']
      function f() {
        return (
          (f = Object.assign
            ? Object.assign.bind()
            : function (e) {
                for (var t = 1; t < arguments.length; t++) {
                  var r = arguments[t]
                  for (var n in r)
                    Object.prototype.hasOwnProperty.call(r, n) && (e[n] = r[n])
                }
                return e
              }),
          f.apply(this, arguments)
        )
      }
      function p(e, t) {
        var r = Object.keys(e)
        if (Object.getOwnPropertySymbols) {
          var n = Object.getOwnPropertySymbols(e)
          t &&
            (n = n.filter(function (t) {
              return Object.getOwnPropertyDescriptor(e, t).enumerable
            })),
            r.push.apply(r, n)
        }
        return r
      }
      function d(e) {
        for (var t = 1; t < arguments.length; t++) {
          var r = null != arguments[t] ? arguments[t] : {}
          t % 2
            ? p(Object(r), !0).forEach(function (t) {
                var n, o, i, a
                ;(n = e),
                  (o = t),
                  (i = r[t]),
                  (a = (function (e, t) {
                    if ('object' != u(e) || !e) return e
                    var r = e[Symbol.toPrimitive]
                    if (void 0 !== r) {
                      var n = r.call(e, 'string')
                      if ('object' != u(n)) return n
                      throw new TypeError(
                        '@@toPrimitive must return a primitive value.'
                      )
                    }
                    return String(e)
                  })(o)),
                  (o = 'symbol' == u(a) ? a : String(a)) in n
                    ? Object.defineProperty(n, o, {
                        value: i,
                        enumerable: !0,
                        configurable: !0,
                        writable: !0,
                      })
                    : (n[o] = i)
              })
            : Object.getOwnPropertyDescriptors
            ? Object.defineProperties(e, Object.getOwnPropertyDescriptors(r))
            : p(Object(r)).forEach(function (t) {
                Object.defineProperty(
                  e,
                  t,
                  Object.getOwnPropertyDescriptor(r, t)
                )
              })
        }
        return e
      }
      var y = function (e) {
        var t = e.active,
          r = (function (e, t) {
            if (null == e) return {}
            var r,
              n,
              o = (function (e, t) {
                if (null == e) return {}
                var r,
                  n,
                  o = {},
                  i = Object.keys(e)
                for (n = 0; n < i.length; n++)
                  (r = i[n]), t.indexOf(r) >= 0 || (o[r] = e[r])
                return o
              })(e, t)
            if (Object.getOwnPropertySymbols) {
              var i = Object.getOwnPropertySymbols(e)
              for (n = 0; n < i.length; n++)
                (r = i[n]),
                  t.indexOf(r) >= 0 ||
                    (Object.prototype.propertyIsEnumerable.call(e, r) &&
                      (o[r] = e[r]))
            }
            return o
          })(e, s),
          n = (0, l.Ln)()
        return o().createElement(
          c.xv,
          f(
            {
              as: 'a',
              sx: d(
                {
                  display: 'block',
                  width: 'auto',
                  fontSize: 'body',
                  fontFamily: 'link',
                  fontWeight: 'bold',
                  cursor: 'pointer',
                },
                n
                  ? {
                      color: function () {
                        return t ? 'link.active' : 'link.normal'
                      },
                      lineHeight: '1.2',
                      borderBottom: 'solid',
                      borderBottomColor: t ? 'link.active' : 'link.normal',
                      borderBottomWidth: t ? '2px' : '0',
                      transition:
                        'border-bottom-width 0.1s ease-in-out, color 0.2s ease-out',
                      ':hover': { borderBottomWidth: '2px' },
                      '.rdc-mini-calendar &': {
                        color: function () {
                          return t ? 'tab.active' : 'tab.normal'
                        },
                        borderBottomColor: t ? 'tab.active' : 'transparent',
                        ':hover': {
                          borderBottomWidth: '2px',
                          color: 'tab.active',
                        },
                      },
                      '.replay-hub__module &': {
                        color: 'link.normal',
                        borderBottomColor: 'link.normal',
                      },
                    }
                  : {
                      py: 'sm',
                      px: function () {
                        return t ? 1 : 0
                      },
                      color: function () {
                        return t ? 'white' : 'grey-33'
                      },
                      backgroundColor: function () {
                        return t ? 'primary' : 'transparent'
                      },
                      '.rdc-mini-calendar &': {
                        py: '0',
                        px: '0',
                        color: function () {
                          return t ? 'tab.active' : 'tab.normal'
                        },
                        backgroundColor: 'transparent',
                        lineHeight: '1.2',
                        borderBottom: 'solid',
                        borderBottomColor: t ? 'tab.active' : 'transparent',
                        borderBottomWidth: t ? '2px' : '0',
                        transition:
                          'border-bottom-width 0.1s ease-in-out, color 0.2s ease-out',
                        ':hover, :focus': {
                          borderBottomWidth: '2px',
                          color: 'tab.active',
                        },
                      },
                    }
              ),
            },
            r
          )
        )
      }
      y.propTypes = { active: a().bool }
      const m = y
    },
    55834: (e, t, r) => {
      r.d(t, { Z: () => d })
      var n = r(1024),
        o = r.n(n),
        i = r(13980),
        a = r.n(i),
        c = r(30186)
      const l =
        'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAGQAAABkCAIAAAD/gAIDAAAAGXRFWHRTb2Z0d2FyZQBBZG9iZSBJbWFnZVJlYWR5ccllPAAACRhJREFUeNrsnHuMFdUdx+ecMzP3te8nLHd3EXZVruwDaFHbP7TYmLaiNaGJiba1CSTa2gcNobWohRrahpIqrbbalqixRkilAVs04iKWEloTXR5bZdnlZcs+QLjLvu5r5pw5/R2wYWOAnbM7c/deek5uNstycmfmM7/z/T3ObwbFow2aGu4GVggULAVLwVKwFCwFSyFQsBQsBUvBUrAULIVAwVKwFCwF6+ocei6eFOeX/jtC/8ewAAp8HIdTpjEKv5wngjUCH4IwFnTgM3YO/A4TDB3punZhwlUOi1JuWRpjyDS1cBgVREh1Na6tJdEaPH0aqihHxUUI/h4IaBeIcM4zGW1k1InHnZ5edvQ46z7i9PXxoWGezmgBU3zPVQWLMXHBYB2GjqsqjeYm/TM36q0teFo1KivFpaVgSlK4ndMfsZM99O3dmVe3s64jYGIoHPLb0JDfuzs8mYRFhMrKjJsWGp+9mTQ2kLkxsCDPvn94xN69J7Nlq/X6Gxqs0VAwb2FRai6521x0K5nXQq6Z6etdsd58K/XEr+g/3kFFRT6ZmJ+wQLAxLv57m9+YLlrZ0FBi1erMpj+hUEiIXT7FWbD6CgtQJJI1z4GKiwt+syG0/Ds8kbxs/JGbsDiluDaKK8qz7GzDP/5R8IGlfHQ0ryzLtvXmJj+Ww/i81jyitzbzVCp/YCGkL5g/JdEuaFbkFz8TynUh0M11WCBYRYV689wpS00Wfsq4+UaeSucDLMZwZSWuq53CbCpw/1c1jDxUer9gcYBVXo4i4SmEZSy6BWJgkM6cT3cow3VRieDQtp0zZ+HD4efQkAa5EXO0YADyITJ7Fq6ZPjHl0mNzMl3dXiWPvsHiDmltcT899fQzqSee+jhnZux/awch00ClJZBmBx9cFlhytzSvqkoPNd4fWJyjQFCf3yohcZ3dfHAIfIIoNoy1R8A3NELP7B9d+k3W1R1e9QM5lSkq1LwLTv3RLAhHp1WR66517zqdnh5YdJcoUcE/dSIqNuFQav2T1mtvyJ2JWIC5LfDctknDbFxW6pZV/yl27AQyjCtNIkRzuCgtSN424J3bluU4OBqVWIOHOp14fPxYnxA+PCx32xKJnI+zHI5nSPgv2r5fmMD4rpMjQ86v8XODItTKaVg6ITfEJGB1fKBhF5VSxoR3kwqNT/bI1WCzDQvC0bJSfW7M/Xzn1Cng6yIQwJDBSNh3Tx/rPOxhhd57WKDueGY9js5wO394GAQLjXf/eSqlf3qBcftt7s/E2vGmc/pMblsWZWRmvftTZCc+hKh9nPkQWNo09L2HRCHBPay/vOYhKX9ggSuUyU7ovgNiU+MK6k4pH02EVq00F39RQgw+OEQPdCCI3XIaFkIifXUP6719lyUFmEZGIaSI/HRN+IcrpM4iuXYdHx7xtvSoe25WYtO0ucmtYKXT9N12zbIEFAi1+ZjAHSNcWRm4957gsm+QOddLnYX99m6rbZfnNQ+vYUGiM7OezJ7ldj4hkXVrnfiAWImptNipBnkyDEgScXU1uFT3juLi/ertS6xchXzY3PcYFrhCPTbH/S2FFMf4/CIvTyCZSjy6hh05ioqLPd/g8VqzmEOaYtpUDcaSj6y2tmwV+6x5sBUGQlM7NaVkWMiJFQ+nn38RlZT4dAhPlyHcTNOcgMp44Ff6T40+8G17z15UUODfUbC3qwBXlEuou0cjs/mVodsX23vfEaT8bKTx0rKEujc24MqKrGGy/7Yn/YfnrB07NYJFy5HPw9NlSKne2pKdbjyIpDKbXrG2vw7uDyK77BzU02VIiFTdfVKw2naBlosetsKCrDVLegfL4ZDlQkSanfMOLn9IiKOnu/NZhMUdFIlkrWcGV1UZi26FNZhNWJ5pFqeU1EyHbM59ZSbz0iYcjeKKMi0Y1Fua4Pqljhha8V27badoxfK0DpMVgbdtMjemGW6/kB38V/Lxn4vEiBCeSge/fl/Bs7+WU8jZs8y7Fqd//xwqLfEjXvd1GWrGgnlSYSSQQoWFKBzGJcXg1+jBDmnlenAZrp2hQfqdT5rFOQgWmSexX8+6ui96MbHHNZLZvEXa/TY2hFZ+39v9Lv9hUYqrKkh9vfv5tON9beyuajhk79wluy0ojOtr9wbu+QofHMwbWJw5qLwMFRW6Nav/nHQ+/Ld4pGRMrYYdOZp+4SV51dUjG9abd97BRe+NlQ+WxSiuqXFfw2Ud7ztgC5/wYoZpbdkqWmgkB6SEhS9ujDy5HtdFeTLJRxNiYdo0V4t/zAHfLzG987Bov/rENQdMdrjL2tFmfukLE7Cv4NL7A0u+TPcf5AMDXEN221vWn7dBUJJjsM5XZvT5Eq6Q9fVfYlcdIU5Z+tmNE4F14QtKSozP3fKxKu7eA6EfyrllKNpHK0jsOom44TK76igUtN9rp3v/Odnbl8nQfQc0r58W8wCWiN1nXYOr3cbfztk4O3b80g1GoHqWnVi9dpKNoKLX8vRHyOvI3gvLgrihLuq+DQqEiV9+Vx2ycdq+P7Ptr5NK6s/GRRrktcB7Acvh0lvQVuYKVwJKn1yzFmKLiZ/R8RM8nfL84Q4vvo5gEpsjIXGgJle+DNN0evsTj/1EuP+J5anvtsMtzL04SzxJUaQ33eB+Puvt04g+TvJUWGC9uj257pcTOyUGaaah5xws0T5aV0vq69zOh4gxPoDI+MeFHDu14en0xhekWbnpUJ0aywJYYFaunbQDic4Zdz1TGCPTSDz8WOq3v5OLZI4ddwbO5eTDmZzrMYmuDXqwQzwJ6PJKCAFeyUcfH/3WctES4/J+QMRLbT8K85OGhTFpbJRyhXKFOuAVDmVe3jx855L0xufdlCWcnl6favOTfkaaMfOuO/CMGpcIrG3bnf5+TZdWX55Og3MkseuNmxbq81r0+a1wUPFMseiPd+B/+cA5drKHHerM/PFl1n1U80GzPHigXHQLUbelAlFHBlITrgJbFj9fhxE9SaIoVKSZBhydJxJ8cJAPjfBMGkHyDBrqQ6EZ5etbu2GhMcbhp3jhCozzL2Xx+YUrupanAws0WX6Rj3ollIKlYClYCpaCpYaCpWApWAqWgqVgqaFgKVgKloKlYClYaihYCpY/478CDAAVgKohwnYJmAAAAABJRU5ErkJggg=='
      var u = ['src']
      function s() {
        return (
          (s = Object.assign
            ? Object.assign.bind()
            : function (e) {
                for (var t = 1; t < arguments.length; t++) {
                  var r = arguments[t]
                  for (var n in r)
                    Object.prototype.hasOwnProperty.call(r, n) && (e[n] = r[n])
                }
                return e
              }),
          s.apply(this, arguments)
        )
      }
      function f(e, t) {
        ;(null == t || t > e.length) && (t = e.length)
        for (var r = 0, n = new Array(t); r < t; r++) n[r] = e[r]
        return n
      }
      var p = function (e) {
        var t,
          r,
          i = e.src,
          a = (function (e, t) {
            if (null == e) return {}
            var r,
              n,
              o = (function (e, t) {
                if (null == e) return {}
                var r,
                  n,
                  o = {},
                  i = Object.keys(e)
                for (n = 0; n < i.length; n++)
                  (r = i[n]), t.indexOf(r) >= 0 || (o[r] = e[r])
                return o
              })(e, t)
            if (Object.getOwnPropertySymbols) {
              var i = Object.getOwnPropertySymbols(e)
              for (n = 0; n < i.length; n++)
                (r = i[n]),
                  t.indexOf(r) >= 0 ||
                    (Object.prototype.propertyIsEnumerable.call(e, r) &&
                      (o[r] = e[r]))
            }
            return o
          })(e, u),
          p =
            ((t = (0, n.useState)()),
            (r = 2),
            (function (e) {
              if (Array.isArray(e)) return e
            })(t) ||
              (function (e, t) {
                var r =
                  null == e
                    ? null
                    : ('undefined' != typeof Symbol && e[Symbol.iterator]) ||
                      e['@@iterator']
                if (null != r) {
                  var n,
                    o,
                    i,
                    a,
                    c = [],
                    l = !0,
                    u = !1
                  try {
                    if (((i = (r = r.call(e)).next), 0 === t)) {
                      if (Object(r) !== r) return
                      l = !1
                    } else
                      for (
                        ;
                        !(l = (n = i.call(r)).done) &&
                        (c.push(n.value), c.length !== t);
                        l = !0
                      );
                  } catch (e) {
                    ;(u = !0), (o = e)
                  } finally {
                    try {
                      if (
                        !l &&
                        null != r.return &&
                        ((a = r.return()), Object(a) !== a)
                      )
                        return
                    } finally {
                      if (u) throw o
                    }
                  }
                  return c
                }
              })(t, r) ||
              (function (e, t) {
                if (e) {
                  if ('string' == typeof e) return f(e, t)
                  var r = Object.prototype.toString.call(e).slice(8, -1)
                  return (
                    'Object' === r && e.constructor && (r = e.constructor.name),
                    'Map' === r || 'Set' === r
                      ? Array.from(e)
                      : 'Arguments' === r ||
                        /^(?:Ui|I)nt(?:8|16|32)(?:Clamped)?Array$/.test(r)
                      ? f(e, t)
                      : void 0
                  )
                }
              })(t, r) ||
              (function () {
                throw new TypeError(
                  'Invalid attempt to destructure non-iterable instance.\nIn order to be iterable, non-array objects must have a [Symbol.iterator]() method.'
                )
              })()),
          d = p[0],
          y = p[1]
        return (
          (0, n.useEffect)(
            function () {
              y(i || l)
            },
            [i]
          ),
          o().createElement(
            c.Ee,
            s(
              {
                className: 'tipster-avatar',
                src: d,
                onError: function () {
                  y(l)
                },
              },
              a
            )
          )
        )
      }
      p.propTypes = { src: a().string }
      const d = p
    },
    37309: (e, t, r) => {
      r.d(t, { PZ: () => y, ZP: () => p, lg: () => d })
      var n = r(1024),
        o = r.n(n),
        i = r(13980),
        a = r.n(i),
        c = r(30186),
        l = r(77450),
        u = (r(18838), ['shadow'])
      function s() {
        return (
          (s = Object.assign
            ? Object.assign.bind()
            : function (e) {
                for (var t = 1; t < arguments.length; t++) {
                  var r = arguments[t]
                  for (var n in r)
                    Object.prototype.hasOwnProperty.call(r, n) && (e[n] = r[n])
                }
                return e
              }),
          s.apply(this, arguments)
        )
      }
      var f = function (e) {
        var t = e.shadow,
          r = void 0 === t || t,
          i = (function (e, t) {
            if (null == e) return {}
            var r,
              n,
              o = (function (e, t) {
                if (null == e) return {}
                var r,
                  n,
                  o = {},
                  i = Object.keys(e)
                for (n = 0; n < i.length; n++)
                  (r = i[n]), t.indexOf(r) >= 0 || (o[r] = e[r])
                return o
              })(e, t)
            if (Object.getOwnPropertySymbols) {
              var i = Object.getOwnPropertySymbols(e)
              for (n = 0; n < i.length; n++)
                (r = i[n]),
                  t.indexOf(r) >= 0 ||
                    (Object.prototype.propertyIsEnumerable.call(e, r) &&
                      (o[r] = e[r]))
            }
            return o
          })(e, u)
        return (
          (0, n.useEffect)(function () {
            window.loadBrightcovePlayerIntoPage =
              window.loadBrightcovePlayerIntoPage ||
              function (e) {
                ;(window.rdcBcPlayers = window.rdcBcPlayers || {}),
                  (window.rdcBcPlayers[e.bcinfo.playerId] = e)
              }
          }),
          o().createElement(
            c.xu,
            s(
              {
                sx: {
                  position: 'relative',
                  maxWidth: ''.concat((16 / 9) * 100, 'vh'),
                  width: '100%',
                  margin: '0 auto',
                  backgroundColor: 'grey-33',
                  boxShadow: r && '4px 4px 80px #000',
                },
              },
              i
            )
          )
        )
      }
      f.propTypes = { shadow: a().bool }
      const p = f
      var d = function (e) {
          if (window.rdcBcPlayers) {
            var t = window.rdcBcPlayers[e]
            t && (t.dispose(), (window.rdcBcPlayers[e] = null))
          }
        },
        y = function (e) {
          return o().createElement(
            c.xu,
            s(
              {
                as: 'button',
                type: 'button',
                sx: {
                  appearance: 'none',
                  background: 'transparent',
                  border: 'none',
                  position: 'absolute',
                  top: ['-80px', '', '', '10px'],
                  right: ['calc(100% - 80px)', '', '', '10px'],
                  color: 'rgba(255, 255, 255, 0.8)',
                  fontSize: ['32px', '', '', '18px'],
                  '&:focus': { outline: 'none' },
                },
              },
              e
            ),
            o().createElement(l.Z, { type: 'close-circle' })
          )
        }
    },
    1349: (e, t, r) => {
      r.d(t, {
        K2: () => f,
        NA: () => c,
        YA: () => l,
        dq: () => s,
        uY: () => a,
        w$: () => u,
      })
      var n = r(89644),
        o = r.n(n),
        i = r(78667),
        a = o().create({ baseURL: 'https://api.racing.com/v1/en-au' }),
        c = o().create({ baseURL: 'https://api.racing.com/api' }),
        l = o().create({ baseURL: '/services' }),
        u = o().create({
          baseURL: (0, i.n)(
            'LiniusReplay',
            'https://d20khqxhsh8k6o.cloudfront.net'
          ),
        }),
        s = o().create({
          baseURL: (0, i.n)(
            'BlackbookRecommendationsEndPoint',
            'https://recommandations-bb.racing.com/'
          ),
          withCredentials: !1,
        }),
        f = o().create({
          baseURL: (0, i.n)(
            'BlackbookWidgetDetailsEndPoint',
            'https://api-bb.racing.com/widgetdetails/'
          ),
          withCredentials: !1,
        })
    },
    54951: (e, t, r) => {
      r.d(t, { JN: () => x, fW: () => O })
      var n = r(40087),
        o = r.n(n),
        i = r(67773),
        a = r(15005),
        c = r(61877),
        l = r(32462),
        u = r.n(l),
        s = r(78667),
        f = r(2738),
        p = r(21036),
        d = r(36808),
        y = r.n(d)
      function m(e) {
        return (
          (m =
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
          m(e)
        )
      }
      function b(e, t) {
        var r = Object.keys(e)
        if (Object.getOwnPropertySymbols) {
          var n = Object.getOwnPropertySymbols(e)
          t &&
            (n = n.filter(function (t) {
              return Object.getOwnPropertyDescriptor(e, t).enumerable
            })),
            r.push.apply(r, n)
        }
        return r
      }
      function h(e) {
        for (var t = 1; t < arguments.length; t++) {
          var r = null != arguments[t] ? arguments[t] : {}
          t % 2
            ? b(Object(r), !0).forEach(function (t) {
                var n, o, i, a
                ;(n = e),
                  (o = t),
                  (i = r[t]),
                  (a = (function (e, t) {
                    if ('object' != m(e) || !e) return e
                    var r = e[Symbol.toPrimitive]
                    if (void 0 !== r) {
                      var n = r.call(e, 'string')
                      if ('object' != m(n)) return n
                      throw new TypeError(
                        '@@toPrimitive must return a primitive value.'
                      )
                    }
                    return String(e)
                  })(o)),
                  (o = 'symbol' == m(a) ? a : String(a)) in n
                    ? Object.defineProperty(n, o, {
                        value: i,
                        enumerable: !0,
                        configurable: !0,
                        writable: !0,
                      })
                    : (n[o] = i)
              })
            : Object.getOwnPropertyDescriptors
            ? Object.defineProperties(e, Object.getOwnPropertyDescriptors(r))
            : b(Object(r)).forEach(function (t) {
                Object.defineProperty(
                  e,
                  t,
                  Object.getOwnPropertyDescriptor(r, t)
                )
              })
        }
        return e
      }
      var v,
        g = null == (v = (0, f.et)()) ? void 0 : v.analyticsId,
        w = function e() {
          if (window.gtag) {
            var t = (0, f.et)()
            y().get('rvfirstlogin') &&
              (y().remove('rvfirstlogin'),
              O('R+ 2.0', 'First_login', 'Auth0_login', {
                user_Id: null == t ? void 0 : t.analyticsId,
              }))
          } else
            'function' != typeof window.trackGAFirstLogin &&
              (window.trackGAFirstLogin = e),
              setTimeout(function () {
                window.trackGAFirstLogin()
              }, 500)
        },
        x = function (e, t, r) {
          O(
            e,
            arguments.length > 3 && void 0 !== arguments[3]
              ? arguments[3]
              : 'click',
            t
          )
        },
        O = o()(function (e, t, r) {
          var n =
            arguments.length > 3 && void 0 !== arguments[3] ? arguments[3] : {}
          a.ZP.event(h({ category: e, action: t, label: r }, n)),
            c.ZP.event(h({ category: e, action: t, label: r }, n))
        }, 2)
      ;(0, i.Cd)(function () {
        var e
        ;(null !== (e = window.dataLayer) &&
          void 0 !== e &&
          e.find(function (e) {
            return e['gtm.start']
          })) ||
          u().initialize({
            gtmId: (0, p.yv)() ? (0, s.n)('GTM', 'GTM-NJJTCC') : 'GTM-NJJTCC',
            dataLayer: {
              user_id: g,
              application_name: (0, s.n)('GTMProject', 'racing.com'),
            },
          }),
          window.ga ||
            (a.ZP.initialize(
              (0, p.yv)()
                ? (0, s.n)('GA', 'UA-51692869-1')
                : (0, s.n)('GA', 'UA-248873596-2'),
              { standardImplementation: (0, s.n)('StandardGA', !1) }
            ),
            g && a.ZP.set({ userId: g })),
          window.gtag ||
            c.ZP.initialize(
              (0, p.yv)()
                ? (0, s.n)('GA4', 'G-D09593FEJ7')
                : (0, s.n)('GA4', 'G-G7XB7Y919G'),
              {
                gtagOptions: {
                  user_id: null != g ? g : void 0,
                  application_alias: (0, s.n)(
                    'GAApplicationAlias',
                    'racing-widgets=new'
                  ),
                  campaign_source: (0, s.n)(
                    'GACampaignSource',
                    'racing-widgets'
                  ),
                  campaign_medium: (0, s.n)('GACampaignMedium', 'desktop'),
                  campaign_content: (0, s.n)(
                    'GACampaignContent',
                    'racing-widgets'
                  ),
                  campaign_name: (0, s.n)('GACampaignName', 'racing-widgets'),
                },
              }
            ),
          w()
      })
    },
    94132: (e, t, r) => {
      r.d(t, { Bj: () => u })
      var n = r(71956),
        o = r(66962),
        i = r(77451),
        a = r(76533),
        c = r(2738),
        l = r(67773),
        u = function (e, t) {
          return a.c.record({ name: e, attributes: t, immediate: !0 })
        }
      ;(0, l.Cd)(function () {
        var e,
          t,
          r = (0, c.Tq)()
        null != r &&
          r.isLoggedIn &&
          !window.rdcAwsAnalytics &&
          ((window.rdcAwsAnalytics = !0),
          (e = r.email),
          (t = {
            disabled: !1,
            AWSPinpoint: {
              appId: n.Z.appId,
              region: n.Z.aws_project_region,
              mandatorySignIn: !1,
              userId: e,
            },
          }),
          o.dQ.configure({
            Auth: {
              identityPoolId: n.Z.aws_cognito_identity_pool_id,
              region: n.Z.aws_project_region,
              identityPoolRegion: n.Z.aws_cognito_region,
            },
            Analytics: {
              AWSPinpoint: { appId: n.Z.appId, region: n.Z.aws_project_region },
            },
          }),
          i.g.configure(n.Z),
          a.c.configure(t))
      })
    },
    79777: (e, t, r) => {
      r.d(t, { h: () => f })
      var n = r(2655),
        o = r(13295),
        i = r(59006),
        a = r(18717)
      function c(e) {
        return (
          (c =
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
          c(e)
        )
      }
      function l(e, t) {
        var r = Object.keys(e)
        if (Object.getOwnPropertySymbols) {
          var n = Object.getOwnPropertySymbols(e)
          t &&
            (n = n.filter(function (t) {
              return Object.getOwnPropertyDescriptor(e, t).enumerable
            })),
            r.push.apply(r, n)
        }
        return r
      }
      function u() {
        var e =
          arguments.length > 0 && void 0 !== arguments[0] ? arguments[0] : {}
        return (0, a.UY)(
          (function (e) {
            for (var t = 1; t < arguments.length; t++) {
              var r = null != arguments[t] ? arguments[t] : {}
              t % 2
                ? l(Object(r), !0).forEach(function (t) {
                    var n, o, i, a
                    ;(n = e),
                      (o = t),
                      (i = r[t]),
                      (a = (function (e, t) {
                        if ('object' != c(e) || !e) return e
                        var r = e[Symbol.toPrimitive]
                        if (void 0 !== r) {
                          var n = r.call(e, 'string')
                          if ('object' != c(n)) return n
                          throw new TypeError(
                            '@@toPrimitive must return a primitive value.'
                          )
                        }
                        return String(e)
                      })(o)),
                      (o = 'symbol' == c(a) ? a : String(a)) in n
                        ? Object.defineProperty(n, o, {
                            value: i,
                            enumerable: !0,
                            configurable: !0,
                            writable: !0,
                          })
                        : (n[o] = i)
                  })
                : Object.getOwnPropertyDescriptors
                ? Object.defineProperties(
                    e,
                    Object.getOwnPropertyDescriptors(r)
                  )
                : l(Object(r)).forEach(function (t) {
                    Object.defineProperty(
                      e,
                      t,
                      Object.getOwnPropertyDescriptor(r, t)
                    )
                  })
            }
            return e
          })({}, e)
        )
      }
      function s(e, t) {
        ;(null == t || t > e.length) && (t = e.length)
        for (var r = 0, n = new Array(t); r < t; r++) n[r] = e[r]
        return n
      }
      var f = (function () {
        var e,
          t =
            arguments.length > 0 && void 0 !== arguments[0] ? arguments[0] : {},
          r = (0, i.ZP)({}),
          a = r.run,
          c = [r],
          l = [(0, o.Ky)({ createReducer: u, runSaga: a })],
          f = (0, n.xC)({
            devTools: !1,
            reducer: u({
              rdc: function () {
                return arguments.length > 0 && void 0 !== arguments[0]
                  ? arguments[0]
                  : {}
              },
            }),
            preloadedState: t,
            middleware: [].concat(
              ((e = (0, n.Bx)({ serializableCheck: !1 })),
              (function (e) {
                if (Array.isArray(e)) return s(e)
              })(e) ||
                (function (e) {
                  if (
                    ('undefined' != typeof Symbol &&
                      null != e[Symbol.iterator]) ||
                    null != e['@@iterator']
                  )
                    return Array.from(e)
                })(e) ||
                (function (e, t) {
                  if (e) {
                    if ('string' == typeof e) return s(e, t)
                    var r = Object.prototype.toString.call(e).slice(8, -1)
                    return (
                      'Object' === r &&
                        e.constructor &&
                        (r = e.constructor.name),
                      'Map' === r || 'Set' === r
                        ? Array.from(e)
                        : 'Arguments' === r ||
                          /^(?:Ui|I)nt(?:8|16|32)(?:Clamped)?Array$/.test(r)
                        ? s(e, t)
                        : void 0
                    )
                  }
                })(e) ||
                (function () {
                  throw new TypeError(
                    'Invalid attempt to spread non-iterable instance.\nIn order to be iterable, non-array objects must have a [Symbol.iterator]() method.'
                  )
                })()),
              c
            ),
            enhancers: l,
          })
        return f
      })({})
    },
    39744: (e, t, r) => {
      var n = r(78592),
        o = r(98678)
      n.Z.use([o.W_, o.tl])
    },
    96331: (e, t, r) => {
      r.d(t, { Z: () => f })
      var n = r(1024),
        o = r.n(n),
        i = r(13980),
        a = r(24082),
        c = r(43352),
        l = r(79777),
        u = r(90567),
        s = function (e) {
          var t = e.children
          return o().createElement(
            a.zt,
            { store: l.h },
            o().createElement(c.f6, { theme: u.Z }, t)
          )
        }
      s.propTypes = { children: i.PropTypes.node }
      const f = s
    },
    90567: (e, t, r) => {
      r.d(t, { Z: () => l })
      var n = ['40em', '52em', '64em']
      ;(n.sm = n[0]), (n.md = n[1]), (n.lg = n[2])
      var o = [0, 4, 8, 16, 32]
      ;(o.zero = o[0]), (o.sm = o[1]), (o.md = o[2]), (o.lg = o[3])
      var i = [0, 32, 64]
      ;(i.avatar = 32), (i.silk = 30)
      var a = [10, 12, 14, 16, 20, 30]
      ;(a.sm = a[0]),
        (a.md = a[1]),
        (a.body = a[1]),
        (a.lg = a[2]),
        (a.h5 = a[1]),
        (a.h4 = a[2]),
        (a.h3 = a[3]),
        (a.h2 = a[4]),
        (a.h1 = a[5])
      var c = {
        roboto: "Roboto, 'Helvetica Neue', Helvetica, Arial, sans-serif",
        circular: "Circular, 'Helvetica Neue', Helvetica, Arial, sans-serif",
        icon: 'racing20',
      }
      ;(c.body = c.roboto), (c.heading = c.circular), (c.link = c.circular)
      const l = {
        breakpoints: n,
        space: o,
        sizes: i,
        fonts: c,
        fontSizes: a,
        fontWeights: { body: 400, bold: 700, heading: 700, black: 900 },
        colors: {
          black: 'black',
          white: 'white',
          'grey-f7': '#f7f7f7',
          'grey-f1': '#f1f1f1',
          'grey-de': '#dedede',
          'grey-99': '#999999',
          'grey-66': '#666666',
          'grey-4f': '#4f4f4f',
          'grey-44': '#444444',
          'grey-33': '#333333',
          primary: '#ed1c24',
          offWhite: '#faf9f7',
          purple: '#71668d',
          green: '#80c88d',
          blue: '#5181ac',
          orange: '#f2622e',
          text: '#333333',
          src: '#ab3933',
          firstStarter: 'beige',
          beteasy: '#8935c0',
          sportsbet: '#1c75bc',
          speedmap: { light: '#46AE44', dark: '#40A242' },
          link: { normal: '#333333', active: '#ed1c24' },
          tab: { normal: '#999999', active: '#333333' },
          meeting: { metro: '#006da6', country: '#91c039' },
          message: {
            dark: { error: '#e06158', success: '#4ba000' },
            light: { error: '#ffeeee', success: '#f5fae5' },
          },
          clubs: {
            crv: '#008542',
            vrc: '#201547',
            mvrc: '#ffc032',
            prc: '#c7982c',
            mrc: '#ccbb7b',
          },
          bets: {
            BEST_BET: '#ED1C24',
            NEXT_BEST: '#046DA6',
            BEST_ROUGHIE: '#F96234',
            BEST_VALUE: '#91C039',
          },
          indicator: { positive: '#91C039', negetive: '#ED1C24' },
        },
        variants: {
          link: {},
          button: {
            normal: {
              padding: 'md',
              border: '1px solid',
              borderColor: 'grey-99',
              fontSize: 'body',
              color: 'grey-99',
              transition: 'all 0.3s ease-in-out',
              '&:hover': { borderColor: 'grey-66', color: 'grey-66' },
            },
            icon: { cursor: 'pointer', border: 'none', p: 'sm' },
            homepage: {
              padding: '6px 12px',
              lineHeight: '1.4',
              fontSize: '14px',
              fontWeight: 'bold',
              border: '1px solid',
              borderColor: 'grey-99',
              color: 'grey-66',
              transition: 'all 0.25s ease-in-out',
              '&:hover': { borderColor: 'grey-33', color: 'grey-33' },
              '&:active': {
                color: 'grey-33',
                boxShadow: 'inset 0 3px 5px rgba(0,0,0,0.125)',
              },
              '&:focus': { backgroundColor: 'grey-66', color: 'white' },
            },
          },
        },
      }
    },
    24734: (e, t, r) => {
      r.d(t, { J: () => c, U: () => l })
      var n,
        o,
        i = r(75506)
      function a(e, t) {
        return (
          t || (t = e.slice(0)),
          Object.freeze(
            Object.defineProperties(e, { raw: { value: Object.freeze(t) } })
          )
        )
      }
      var c = (0, i.F4)(
          n ||
            (n = a([
              '\n  0% {\n    opacity: 0;\n  }\n  100% {\n    opacity: 1;\n  }\n',
            ]))
        ),
        l = (0, i.F4)(
          o ||
            (o = a([
              '\n  0% {\n    opacity: 1;\n  }\n  100% {\n    opacity: 0;\n  }\n',
            ]))
        )
    },
    38847: (e, t, r) => {
      r.d(t, { J: () => h, I: () => b })
      var n = r(1608),
        o = r(29162),
        i = r(89274),
        a = r(44107),
        c = r(25554),
        l = r(78667),
        u = function (e) {
          e.setContext({
            headers: { Authorization: ''.concat(e.getContext().token) },
          })
        },
        s = (0, i.L)({
          uri: (0, l.n)('GraphqlEndpoint'),
          credentials: 'same-origin',
          useGETForQueries: !0,
        }),
        f = (0, i.L)({
          uri: (0, l.n)('ChampionDataEndpoint'),
          credentials: 'same-origin',
          useGETForQueries: !0,
        }),
        p = (0, i.L)({
          uri: (0, l.n)('PinpointNotificationsEndpoint'),
          credentials: 'same-origin',
          useGETForQueries: !0,
        }),
        d = (0, i.L)({
          uri: (0, l.n)(
            'BlackbookAppSyncEndPoint',
            'https://appsync-bb.racing.com/graphql/'
          ),
          credentials: 'same-origin',
          useGETForQueries: !0,
        }),
        y = n.i.split(
          function (e) {
            return !!e.getContext().usePinpoint && (u(e), !0)
          },
          p,
          s
        )
      const m = new o.f({
        link: n.i.from([
          (0, a.q)(function (e) {
            var t = e.graphQLErrors,
              r = e.networkError
            t &&
              t.forEach(function (e) {
                var t = e.message,
                  r = e.locations,
                  n = e.path
                return console.log(
                  '[GraphQL error]: Message: '
                    .concat(t, ', Location: ')
                    .concat(r, ', Path: ')
                    .concat(n)
                )
              }),
              r && console.log('[Network error]: '.concat(r))
          }),
          n.i.split(
            function (e) {
              return (
                !!e.getContext().useChampionData &&
                ((function (e, t) {
                  e.setContext({
                    headers: {
                      'x-api-key': (0, l.n)('ChampionDataEndpointKey'),
                    },
                  })
                })(e),
                !0)
              )
            },
            f,
            n.i.split(
              function (e) {
                return !!e.getContext().useBlackbook && (u(e), !0)
              },
              d,
              y
            )
          ),
        ]),
        cache: new c.h(),
      })
      var b = m.query,
        h = m.mutate
    },
    78667: (e, t, r) => {
      r.d(t, { n: () => n })
      var n = function (e, t) {
        var n, o, i, a, c, l, u, s, f
        return (
          (n = window).global || (n.global = window),
          null !==
            (o =
              null !==
                (i =
                  null !==
                    (a =
                      null !==
                        (c =
                          null === (l = r.g) ||
                          void 0 === l ||
                          null === (l = l.rdc) ||
                          void 0 === l ||
                          null === (l = l.config) ||
                          void 0 === l
                            ? void 0
                            : l[e]) && void 0 !== c
                        ? c
                        : null === (u = r.g) ||
                          void 0 === u ||
                          null === (u = u.sitecore) ||
                          void 0 === u ||
                          null === (u = u.tippingHub) ||
                          void 0 === u
                        ? void 0
                        : u[e]) && void 0 !== a
                    ? a
                    : null === (s = r.g) ||
                      void 0 === s ||
                      null === (s = s.sitecore) ||
                      void 0 === s
                    ? void 0
                    : s[e]) && void 0 !== i
                ? i
                : null === (f = r.g) ||
                  void 0 === f ||
                  null === (f = f.siteConfig) ||
                  void 0 === f
                ? void 0
                : f[e]) && void 0 !== o
            ? o
            : t
        )
      }
    },
    62388: (e, t, r) => {
      r.d(t, {
        $f: () => c,
        Rl: () => i,
        ZF: () => l,
        cp: () => o,
        fr: () => a,
      })
      var n = r(1024),
        o = (0, n.createContext)()
      ;(o.displayName = 'Meeting Context'),
        ((0, n.createContext)().displayName = 'Tipster Context')
      var i = (0, n.createContext)()
      i.displayName = 'Race Context'
      var a = (0, n.createContext)()
      a.displayName = 'Printable Context'
      var c = (0, n.createContext)({})
      c.displayName = 'Bet Context'
      var l = (0, n.createContext)({})
      l.displayName = 'Playlist Context'
    },
    21604: (e, t, r) => {
      r.d(t, { Rr: () => n, e7: () => o })
      var n = function (e) {
          var t
          return (null === (t = location.hostname.match(/racing\.com/i)) ||
          void 0 === t
            ? void 0
            : t.index) > 0
            ? e
            : e.replace(
                /.+\.com/,
                ''.concat(location.protocol, '//').concat(location.host)
              )
        },
        o = function (e) {
          return null == e
            ? void 0
            : e.replace(
                's3-ap-southeast-2.amazonaws.com/racevic.silks',
                'cdn.silks.racing.com'
              )
        }
    },
    36007: (e, t, r) => {
      r.d(t, { J: () => i })
      var n = r(36808),
        o = r.n(n),
        i = function (e, t) {
          var r
          e(((r = o().get('ga_rdc_ab')) ? r.split('.')[1] : null) || t)
        }
    },
    69416: (e, t, r) => {
      r.d(t, { L: () => a, f: () => i })
      var n = r(5246),
        o = r.n(n),
        i = function () {
          document.body.style.paddingRight = ''.concat(o()(), 'px')
        },
        a = function () {
          document.body.style.paddingRight = ''
        }
    },
    11594: (e, t, r) => {
      r.d(t, { OY: () => c, Wp: () => i, c: () => a })
      var n = r(36808),
        o = r.n(n),
        i = 'rdcStatesFilter',
        a = function () {
          return c()
        },
        c = function () {
          var e =
            !(arguments.length > 0 && void 0 !== arguments[0]) || arguments[0]
          return o().get(i) || (e ? 'QLD|SA|NSW|ACT|WA|NT|TAS' : null)
        }
    },
    2738: (e, t, r) => {
      r.d(t, { Iq: () => l, Tq: () => c, et: () => a, tV: () => u })
      var n = r(36808),
        o = r.n(n),
        i = r(78667),
        a = function () {
          try {
            var e = o().get('rvprofile')
            if (!e) return null
            var t = JSON.parse(decodeURIComponent(e))
            return (
              null != t &&
                t.firstName &&
                null != t &&
                t.firstName.includes('+') &&
                (t.firstName = t.firstName.replace(/\+/g, ' ')),
              t
            )
          } catch (e) {
            return console.warn('Invalid user profile'), null
          }
        },
        c = function () {
          var e = a()
          return {
            isLoggedIn: !!e,
            allowUserAccess:
              'Confirmed' === (null == e ? void 0 : e.confirmationStatus) ||
              (null == e ? void 0 : e.isUnconfirmedWithinGracePeriod),
            killSwitchActive: (0, i.n)('KillSwitchActive', !1),
            email: null == e ? void 0 : e.email,
          }
        },
        l = function () {
          var e,
            t = (
              arguments.length > 0 && void 0 !== arguments[0]
                ? arguments[0]
                : {}
            ).requireAccess,
            r = void 0 === t || t
          return (
            (null === (e = window.rdc) ||
            void 0 === e ||
            null === (e = e.login) ||
            void 0 === e
              ? void 0
              : e.Authorize({ requireAccess: r })) ||
            (function () {
              var e = (
                  arguments.length > 0 && void 0 !== arguments[0]
                    ? arguments[0]
                    : {}
                ).requireAccess,
                t = void 0 === e || e,
                r = c(),
                n = r.isLoggedIn,
                o = r.allowUserAccess,
                i = r.killSwitchActive
              return new Promise(function (e) {
                var r, a
                if (i) e()
                else {
                  var c = document.querySelector(
                      '[ng-controller=loginController]'
                    ),
                    l =
                      null === (r = window.angular) ||
                      void 0 === r ||
                      null === (r = r.element(c)) ||
                      void 0 === r ||
                      null === (r = r.injector()) ||
                      void 0 === r
                        ? void 0
                        : r.get('pubsub')
                  c && l && (!n || (!o && t))
                    ? null === (a = l.publish) ||
                      void 0 === a ||
                      a.call(l, 'ShowModal', ['login'])
                    : e()
                }
              })
            })()
          )
        },
        u = function () {
          try {
            var e = o().get('rvtoken')
            return e ? JSON.parse(decodeURIComponent(e)) : null
          } catch (e) {
            return console.warn('Invalid user profile'), null
          }
        }
    },
    10687: (e, t, r) => {
      r.d(t, { Fn: () => n, SH: () => o }), r(68929)
      var n = function (e) {
          return 'boolean' == typeof e ? e : void 0 !== e
        },
        o = function (e) {
          return 'number' == typeof e ? e : parseInt(e, 10)
        }
    },
    61173: (e, t, r) => {
      r.d(t, { R: () => n })
      var n = function (e) {
        return null == e ? void 0 : e.replace('http://', 'https://')
      }
    },
    40163: (e, t, r) => {
      r.d(t, { Ln: () => i })
      var n = r(17160),
        o = r(90567),
        i = function () {
          return (0, n.useMediaQuery)({
            query: 'screen and (min-width: '.concat(o.Z.breakpoints.lg, ')'),
          })
        }
    },
    69285: (e, t, r) => {
      r.d(t, { A: () => i })
      var n = r(27422),
        o = r(78667),
        i = function (e) {
          return (0, n.gw)(null != e ? e : (0, o.n)('SimulateDelay', 0))
        }
    },
    98662: (e, t, r) => {
      r.d(t, { W0: () => h, fO: () => m })
      var n = r(1024),
        o = r(27422),
        i = r(47677),
        a = r.n(i),
        c = r(79777)
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
          r = Object.prototype,
          n = r.hasOwnProperty,
          o =
            Object.defineProperty ||
            function (e, t, r) {
              e[t] = r.value
            },
          i = 'function' == typeof Symbol ? Symbol : {},
          a = i.iterator || '@@iterator',
          c = i.asyncIterator || '@@asyncIterator',
          s = i.toStringTag || '@@toStringTag'
        function f(e, t, r) {
          return (
            Object.defineProperty(e, t, {
              value: r,
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
          f = function (e, t, r) {
            return (e[t] = r)
          }
        }
        function p(e, t, r, n) {
          var i = t && t.prototype instanceof g ? t : g,
            a = Object.create(i.prototype),
            c = new L(n || [])
          return o(a, '_invoke', { value: C(e, r, c) }), a
        }
        function d(e, t, r) {
          try {
            return { type: 'normal', arg: e.call(t, r) }
          } catch (e) {
            return { type: 'throw', arg: e }
          }
        }
        t.wrap = p
        var y = 'suspendedStart',
          m = 'suspendedYield',
          b = 'executing',
          h = 'completed',
          v = {}
        function g() {}
        function w() {}
        function x() {}
        var O = {}
        f(O, a, function () {
          return this
        })
        var j = Object.getPrototypeOf,
          S = j && j(j(N([])))
        S && S !== r && n.call(S, a) && (O = S)
        var E = (x.prototype = g.prototype = Object.create(O))
        function k(e) {
          ;['next', 'throw', 'return'].forEach(function (t) {
            f(e, t, function (e) {
              return this._invoke(t, e)
            })
          })
        }
        function P(e, t) {
          function r(o, i, a, c) {
            var u = d(e[o], e, i)
            if ('throw' !== u.type) {
              var s = u.arg,
                f = s.value
              return f && 'object' == l(f) && n.call(f, '__await')
                ? t.resolve(f.__await).then(
                    function (e) {
                      r('next', e, a, c)
                    },
                    function (e) {
                      r('throw', e, a, c)
                    }
                  )
                : t.resolve(f).then(
                    function (e) {
                      ;(s.value = e), a(s)
                    },
                    function (e) {
                      return r('throw', e, a, c)
                    }
                  )
            }
            c(u.arg)
          }
          var i
          o(this, '_invoke', {
            value: function (e, n) {
              function o() {
                return new t(function (t, o) {
                  r(e, n, t, o)
                })
              }
              return (i = i ? i.then(o, o) : o())
            },
          })
        }
        function C(t, r, n) {
          var o = y
          return function (i, a) {
            if (o === b) throw new Error('Generator is already running')
            if (o === h) {
              if ('throw' === i) throw a
              return { value: e, done: !0 }
            }
            for (n.method = i, n.arg = a; ; ) {
              var c = n.delegate
              if (c) {
                var l = A(c, n)
                if (l) {
                  if (l === v) continue
                  return l
                }
              }
              if ('next' === n.method) n.sent = n._sent = n.arg
              else if ('throw' === n.method) {
                if (o === y) throw ((o = h), n.arg)
                n.dispatchException(n.arg)
              } else 'return' === n.method && n.abrupt('return', n.arg)
              o = b
              var u = d(t, r, n)
              if ('normal' === u.type) {
                if (((o = n.done ? h : m), u.arg === v)) continue
                return { value: u.arg, done: n.done }
              }
              'throw' === u.type &&
                ((o = h), (n.method = 'throw'), (n.arg = u.arg))
            }
          }
        }
        function A(t, r) {
          var n = r.method,
            o = t.iterator[n]
          if (o === e)
            return (
              (r.delegate = null),
              ('throw' === n &&
                t.iterator.return &&
                ((r.method = 'return'),
                (r.arg = e),
                A(t, r),
                'throw' === r.method)) ||
                ('return' !== n &&
                  ((r.method = 'throw'),
                  (r.arg = new TypeError(
                    "The iterator does not provide a '" + n + "' method"
                  )))),
              v
            )
          var i = d(o, t.iterator, r.arg)
          if ('throw' === i.type)
            return (r.method = 'throw'), (r.arg = i.arg), (r.delegate = null), v
          var a = i.arg
          return a
            ? a.done
              ? ((r[t.resultName] = a.value),
                (r.next = t.nextLoc),
                'return' !== r.method && ((r.method = 'next'), (r.arg = e)),
                (r.delegate = null),
                v)
              : a
            : ((r.method = 'throw'),
              (r.arg = new TypeError('iterator result is not an object')),
              (r.delegate = null),
              v)
        }
        function T(e) {
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
            e.forEach(T, this),
            this.reset(!0)
        }
        function N(t) {
          if (t || '' === t) {
            var r = t[a]
            if (r) return r.call(t)
            if ('function' == typeof t.next) return t
            if (!isNaN(t.length)) {
              var o = -1,
                i = function r() {
                  for (; ++o < t.length; )
                    if (n.call(t, o)) return (r.value = t[o]), (r.done = !1), r
                  return (r.value = e), (r.done = !0), r
                }
              return (i.next = i)
            }
          }
          throw new TypeError(l(t) + ' is not iterable')
        }
        return (
          (w.prototype = x),
          o(E, 'constructor', { value: x, configurable: !0 }),
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
              (e.prototype = Object.create(E)),
              e
            )
          }),
          (t.awrap = function (e) {
            return { __await: e }
          }),
          k(P.prototype),
          f(P.prototype, c, function () {
            return this
          }),
          (t.AsyncIterator = P),
          (t.async = function (e, r, n, o, i) {
            void 0 === i && (i = Promise)
            var a = new P(p(e, r, n, o), i)
            return t.isGeneratorFunction(r)
              ? a
              : a.next().then(function (e) {
                  return e.done ? e.value : a.next()
                })
          }),
          k(E),
          f(E, s, 'Generator'),
          f(E, a, function () {
            return this
          }),
          f(E, 'toString', function () {
            return '[object Generator]'
          }),
          (t.keys = function (e) {
            var t = Object(e),
              r = []
            for (var n in t) r.push(n)
            return (
              r.reverse(),
              function e() {
                for (; r.length; ) {
                  var n = r.pop()
                  if (n in t) return (e.value = n), (e.done = !1), e
                }
                return (e.done = !0), e
              }
            )
          }),
          (t.values = N),
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
                for (var r in this)
                  't' === r.charAt(0) &&
                    n.call(this, r) &&
                    !isNaN(+r.slice(1)) &&
                    (this[r] = e)
            },
            stop: function () {
              this.done = !0
              var e = this.tryEntries[0].completion
              if ('throw' === e.type) throw e.arg
              return this.rval
            },
            dispatchException: function (t) {
              if (this.done) throw t
              var r = this
              function o(n, o) {
                return (
                  (c.type = 'throw'),
                  (c.arg = t),
                  (r.next = n),
                  o && ((r.method = 'next'), (r.arg = e)),
                  !!o
                )
              }
              for (var i = this.tryEntries.length - 1; i >= 0; --i) {
                var a = this.tryEntries[i],
                  c = a.completion
                if ('root' === a.tryLoc) return o('end')
                if (a.tryLoc <= this.prev) {
                  var l = n.call(a, 'catchLoc'),
                    u = n.call(a, 'finallyLoc')
                  if (l && u) {
                    if (this.prev < a.catchLoc) return o(a.catchLoc, !0)
                    if (this.prev < a.finallyLoc) return o(a.finallyLoc)
                  } else if (l) {
                    if (this.prev < a.catchLoc) return o(a.catchLoc, !0)
                  } else {
                    if (!u)
                      throw new Error('try statement without catch or finally')
                    if (this.prev < a.finallyLoc) return o(a.finallyLoc)
                  }
                }
              }
            },
            abrupt: function (e, t) {
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
                ('break' === e || 'continue' === e) &&
                i.tryLoc <= t &&
                t <= i.finallyLoc &&
                (i = null)
              var a = i ? i.completion : {}
              return (
                (a.type = e),
                (a.arg = t),
                i
                  ? ((this.method = 'next'), (this.next = i.finallyLoc), v)
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
                v
              )
            },
            finish: function (e) {
              for (var t = this.tryEntries.length - 1; t >= 0; --t) {
                var r = this.tryEntries[t]
                if (r.finallyLoc === e)
                  return this.complete(r.completion, r.afterLoc), I(r), v
              }
            },
            catch: function (e) {
              for (var t = this.tryEntries.length - 1; t >= 0; --t) {
                var r = this.tryEntries[t]
                if (r.tryLoc === e) {
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
            delegateYield: function (t, r, n) {
              return (
                (this.delegate = { iterator: N(t), resultName: r, nextLoc: n }),
                'next' === this.method && (this.arg = e),
                v
              )
            },
          }),
          t
        )
      }
      function s(e, t) {
        if (e) {
          if ('string' == typeof e) return f(e, t)
          var r = Object.prototype.toString.call(e).slice(8, -1)
          return (
            'Object' === r && e.constructor && (r = e.constructor.name),
            'Map' === r || 'Set' === r
              ? Array.from(e)
              : 'Arguments' === r ||
                /^(?:Ui|I)nt(?:8|16|32)(?:Clamped)?Array$/.test(r)
              ? f(e, t)
              : void 0
          )
        }
      }
      function f(e, t) {
        ;(null == t || t > e.length) && (t = e.length)
        for (var r = 0, n = new Array(t); r < t; r++) n[r] = e[r]
        return n
      }
      function p(e, t) {
        var r = Object.keys(e)
        if (Object.getOwnPropertySymbols) {
          var n = Object.getOwnPropertySymbols(e)
          t &&
            (n = n.filter(function (t) {
              return Object.getOwnPropertyDescriptor(e, t).enumerable
            })),
            r.push.apply(r, n)
        }
        return r
      }
      function d(e) {
        for (var t = 1; t < arguments.length; t++) {
          var r = null != arguments[t] ? arguments[t] : {}
          t % 2
            ? p(Object(r), !0).forEach(function (t) {
                var n, o, i, a
                ;(n = e),
                  (o = t),
                  (i = r[t]),
                  (a = (function (e, t) {
                    if ('object' != l(e) || !e) return e
                    var r = e[Symbol.toPrimitive]
                    if (void 0 !== r) {
                      var n = r.call(e, 'string')
                      if ('object' != l(n)) return n
                      throw new TypeError(
                        '@@toPrimitive must return a primitive value.'
                      )
                    }
                    return String(e)
                  })(o)),
                  (o = 'symbol' == l(a) ? a : String(a)) in n
                    ? Object.defineProperty(n, o, {
                        value: i,
                        enumerable: !0,
                        configurable: !0,
                        writable: !0,
                      })
                    : (n[o] = i)
              })
            : Object.getOwnPropertyDescriptors
            ? Object.defineProperties(e, Object.getOwnPropertyDescriptors(r))
            : p(Object(r)).forEach(function (t) {
                Object.defineProperty(
                  e,
                  t,
                  Object.getOwnPropertyDescriptor(r, t)
                )
              })
        }
        return e
      }
      var y = { loading: !1, error: null, data: null },
        m = function () {
          var e,
            t,
            r =
              ((e = (0, n.useState)(y)),
              (t = 2),
              (function (e) {
                if (Array.isArray(e)) return e
              })(e) ||
                (function (e, t) {
                  var r =
                    null == e
                      ? null
                      : ('undefined' != typeof Symbol && e[Symbol.iterator]) ||
                        e['@@iterator']
                  if (null != r) {
                    var n,
                      o,
                      i,
                      a,
                      c = [],
                      l = !0,
                      u = !1
                    try {
                      if (((i = (r = r.call(e)).next), 0 === t)) {
                        if (Object(r) !== r) return
                        l = !1
                      } else
                        for (
                          ;
                          !(l = (n = i.call(r)).done) &&
                          (c.push(n.value), c.length !== t);
                          l = !0
                        );
                    } catch (e) {
                      ;(u = !0), (o = e)
                    } finally {
                      try {
                        if (
                          !l &&
                          null != r.return &&
                          ((a = r.return()), Object(a) !== a)
                        )
                          return
                      } finally {
                        if (u) throw o
                      }
                    }
                    return c
                  }
                })(e, t) ||
                s(e, t) ||
                (function () {
                  throw new TypeError(
                    'Invalid attempt to destructure non-iterable instance.\nIn order to be iterable, non-array objects must have a [Symbol.iterator]() method.'
                  )
                })()),
            o = r[0],
            i = r[1],
            a = (0, n.useRef)(!0)
          ;(0, n.useEffect)(function () {
            return function () {
              a.current = !1
            }
          }, [])
          var l = function (e) {
              return a.current && i({ loading: !1, error: null, data: e }), e
            },
            u = function (e) {
              return a.current && i({ loading: !1, data: null, error: e }), e
            },
            f = (0, n.useCallback)(function (e) {
              return (
                a.current && i({ loading: !0, error: null, data: null }),
                (function (e) {
                  return new Promise(function (t, r) {
                    var n = d(
                      d({}, e),
                      {},
                      { promise: { resolve: t, reject: r } }
                    )
                    c.h.dispatch(n)
                  })
                })(e).then(l, u)
              )
            }, []),
            p = (0, n.useCallback)(function () {
              i(y)
            }, [])
          return (0, n.useMemo)(
            function () {
              return { status: o, reset: p, dispatch: f }
            },
            [f, p, o]
          )
        }
      function b(e) {
        return u().mark(function t(r) {
          var n, i, c, l
          return u().wrap(
            function (t) {
              for (;;)
                switch ((t.prev = t.next)) {
                  case 0:
                    return (
                      a()(
                        r.promise,
                        'A saga request action must provide promise handlers'
                      ),
                      (n = r.promise),
                      (i = n.resolve),
                      (c = n.reject),
                      (t.prev = 2),
                      (t.next = 5),
                      e(r)
                    )
                  case 5:
                    return (l = t.sent), (t.next = 8), (0, o.RE)(i, l)
                  case 8:
                    t.next = 15
                    break
                  case 10:
                    return (
                      (t.prev = 10),
                      (t.t0 = t.catch(2)),
                      (t.next = 15),
                      (0, o.RE)(c, t.t0)
                    )
                  case 15:
                  case 'end':
                    return t.stop()
                }
            },
            t,
            null,
            [[2, 10]]
          )
        })
      }
      var h = function (e, t) {
        for (
          var r =
              !(arguments.length > 2 && void 0 !== arguments[2]) ||
              arguments[2],
            n = arguments.length,
            i = new Array(n > 3 ? n - 3 : 0),
            a = 3;
          a < n;
          a++
        )
          i[a - 3] = arguments[a]
        return (0, o.rM)(
          u().mark(function n() {
            var a, c
            return u().wrap(function (n) {
              for (;;)
                switch ((n.prev = n.next)) {
                  case 0:
                    return (n.next = 3), (0, o.qn)(e)
                  case 3:
                    if (((c = n.sent), r || !a)) {
                      n.next = 7
                      break
                    }
                    return (n.next = 7), (0, o.al)(a)
                  case 7:
                    return (
                      (n.next = 9),
                      o.rM.apply(
                        void 0,
                        [b(t)].concat(
                          (function (e) {
                            if (Array.isArray(e)) return f(e)
                          })((l = i.concat(c))) ||
                            (function (e) {
                              if (
                                ('undefined' != typeof Symbol &&
                                  null != e[Symbol.iterator]) ||
                                null != e['@@iterator']
                              )
                                return Array.from(e)
                            })(l) ||
                            s(l) ||
                            (function () {
                              throw new TypeError(
                                'Invalid attempt to spread non-iterable instance.\nIn order to be iterable, non-array objects must have a [Symbol.iterator]() method.'
                              )
                            })()
                        )
                      )
                    )
                  case 9:
                    ;(a = n.sent), (n.next = 0)
                    break
                  case 12:
                  case 'end':
                    return n.stop()
                }
              var l
            }, n)
          })
        )
      }
    },
    70887: (e, t, r) => {
      r.d(t, { J: () => c, d: () => l })
      var n = r(7334),
        o = r.n(n),
        i = r(48403),
        a = r.n(i),
        c = function (e, t) {
          return o()(e) === o()(t)
        },
        l = function (e) {
          var t = (
              arguments.length > 1 && void 0 !== arguments[1]
                ? arguments[1]
                : { shorten: 0 }
            ).shorten,
            r =
              t && (null == e ? void 0 : e.length) > t
                ? ''.concat(e.substr(0, t), '...')
                : e
          return a()(r)
        }
    },
    21036: (e, t, r) => {
      r.d(t, { dJ: () => o, yv: () => n })
      var n = function () {
          var e
          return (
            (null === (e = location.hostname.match(/\.com/i)) || void 0 === e
              ? void 0
              : e.index) >= 0
          )
        },
        o = function () {
          try {
            var e
            return null === (e = window.location) || void 0 === e
              ? void 0
              : e.pathname.split('/')[1].toLowerCase()
          } catch (e) {}
          return ''
        }
    },
    81699: (e, t, r) => {
      r.d(t, { Z: () => i })
      var n = r(82609),
        o = r.n(n)()(function (e) {
          return e[1]
        })
      o.push([
        e.id,
        '.VQXJpX8zT0QN1Ti4qGG0MA\\=\\=:hover{transition:all .2s ease;color:inherit!important}',
        '',
      ]),
        (o.locals = { 'blackbook-hover': 'VQXJpX8zT0QN1Ti4qGG0MA==' })
      const i = o
    },
    98771: (e, t, r) => {
      r.d(t, { Z: () => i })
      var n = r(82609),
        o = r.n(n)()(function (e) {
          return e[1]
        })
      o.push([
        e.id,
        '.xICY3bxHRKK8BEFai8Ck2w\\=\\={align-items:center;width:100%;height:100px;border:1px solid #dedede;padding:12px;margin-bottom:15px!important;}.xICY3bxHRKK8BEFai8Ck2w\\=\\= ._6Eaouig9Ese41HATb1a4dw\\=\\={display:flex;align-items:center}.xICY3bxHRKK8BEFai8Ck2w\\=\\= .O6WmhSEGKQH5n9fj1XVChg\\=\\={display:flex;margin-top:10px}',
        '',
      ]),
        (o.locals = {
          'blackbook-card': 'xICY3bxHRKK8BEFai8Ck2w==',
          upper: '_6Eaouig9Ese41HATb1a4dw==',
          lower: 'O6WmhSEGKQH5n9fj1XVChg==',
        })
      const i = o
    },
    81165: (e, t, r) => {
      r.d(t, { Z: () => i })
      var n = r(82609),
        o = r.n(n)()(function (e) {
          return e[1]
        })
      o.push([
        e.id,
        '.xjYV69r\\+qgxpLyVdUkfxJQ\\=\\={display:flex;align-items:center;}.xjYV69r\\+qgxpLyVdUkfxJQ\\=\\= .y9Mw4mUoGQjlUDnuPTu9AQ\\=\\={width:33px;height:37px}.xjYV69r\\+qgxpLyVdUkfxJQ\\=\\= .b\\+ogrlQNuzgKx4xLtoGHWw\\=\\={font-family:Roboto,Helvetica Neue,Helvetica,Arial,sans-serif;font-weight:700;height:28px;margin-left:9px;line-height:1.75;}.xjYV69r\\+qgxpLyVdUkfxJQ\\=\\= .b\\+ogrlQNuzgKx4xLtoGHWw\\=\\= .DkeWJv1x7JH2zDrdK8tETg\\=\\={margin-top:-4px;font-size:12px;color:#333;cursor:pointer;}.xjYV69r\\+qgxpLyVdUkfxJQ\\=\\= .b\\+ogrlQNuzgKx4xLtoGHWw\\=\\= .DkeWJv1x7JH2zDrdK8tETg\\=\\=:hover{transition:all .2s ease;color:#ed1c24!important}.xjYV69r\\+qgxpLyVdUkfxJQ\\=\\= .b\\+ogrlQNuzgKx4xLtoGHWw\\=\\= .Ufu6n9RKUC\\+JlzN61SNSuQ\\=\\={font-size:10px;color:#666;cursor:pointer}',
        '',
      ]),
        (o.locals = {
          'horse-detail': 'xjYV69r+qgxpLyVdUkfxJQ==',
          'horse-image': 'y9Mw4mUoGQjlUDnuPTu9AQ==',
          detail: 'b+ogrlQNuzgKx4xLtoGHWw==',
          'horse-name': 'DkeWJv1x7JH2zDrdK8tETg==',
          'trainer-jockey': 'Ufu6n9RKUC+JlzN61SNSuQ==',
        })
      const i = o
    },
    96921: (e, t, r) => {
      r.d(t, { LU: () => u, Tk: () => o, ZT: () => a, n1: () => c })
      var n = r(96486),
        o =
          (r(19034),
          function (e) {
            return (0, n.startCase)(null == e ? void 0 : e.toLowerCase())
          }),
        i = function (e, t, r) {
          return function (n) {
            return n[e]
              ? [n[e].replace(/\s/g, '.'), n[t]].join('.')
              : n[r]
                  .split('&')
                  .map(function (e) {
                    var t = e.match(/\b\w+\b/g),
                      r = t.length - 2
                    return (
                      t.length > 1 &&
                        t[r].length > 2 &&
                        (t[r] = t[r].substring(0, 1).toUpperCase()),
                      t.join('.')
                    )
                  })
                  .join(' & ')
          }
        },
        a = i('jockeyInitials', 'jockeySurname', 'jockeyName'),
        c = i('trainerInitials', 'trainerSurname', 'trainerName'),
        l = function (e) {
          return Number.isNaN(e) ? '' : e < 10 ? '0'.concat(e) : e
        },
        u = function (e) {
          var t = Math.floor(e / 60),
            r = Math.floor(t / 60),
            n = t % 60,
            o = e % 60
          return ''
            .concat(r > 0 ? ''.concat(r, ':') : '')
            .concat(l(n), ':')
            .concat(l(o))
        }
    },
  },
])

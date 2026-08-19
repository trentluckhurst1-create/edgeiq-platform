/*! For license information please see rdc.liniusReplay.js.LICENSE.txt */
!(function (t, e) {
  'object' == typeof exports && 'object' == typeof module
    ? (module.exports = e(require('React'), require('ReactDOM')))
    : 'function' == typeof define && define.amd
    ? define(['React', 'ReactDOM'], e)
    : 'object' == typeof exports
    ? (exports.rdc = e(require('React'), require('ReactDOM')))
    : ((t.rdc = t.rdc || {}), (t.rdc.liniusReplay = e(t.React, t.ReactDOM)))
})(self, (t, e) =>
  (self.webpackChunkrdc = self.webpackChunkrdc || []).push([
    [191],
    {
      53817: (t, e, r) => {
        'use strict'
        r(14629), r(25047), r(92556)
      },
      92556: (t, e, r) => {
        r.p = window.rdcWidgetsPath || ''
      },
      59539: (t, e, r) => {
        'use strict'
        r.r(e),
          r.d(e, {
            LoadLiniusReplayByRace: () => ct,
            LoadLiniusReplayByUrl: () => it,
            LoadLiniusTopSelections: () => lt,
            PlayLiniusReplay: () => at,
            default: () => ot,
            trackLiniusReplayEvent: () => z,
          }),
          r(53817)
        var n = r(1024),
          o = r.n(n),
          a = r(71570),
          i = r(13980),
          c = r.n(i),
          l = r(24082),
          u = r(30186),
          s = r(13295),
          p = r(84953),
          f = r(85814),
          d = r(37309),
          y = r(92551),
          h = r(40163),
          v = r(69416),
          g = r(78667),
          m = r(2655),
          b = r(61173),
          w = (0, m.oM)({
            name: 'linius-replay',
            initialState: {
              playingLiniusReplay: null,
              loading: !1,
              error: null,
            },
            reducers: {
              loadLiniusReplayByRace: function (t) {
                ;(t.loading = !0), (t.error = null)
              },
              loadLiniusReplayByUrl: function (t) {
                ;(t.loading = !0), (t.error = null)
              },
              loadLiniusTopSelections: function (t) {
                ;(t.loading = !0), (t.error = null)
              },
              loadLiniusReplaySuccess: function (t) {
                ;(t.loading = !1), (t.error = null)
              },
              loadLiniusReplayFailed: function (t, e) {
                var r = e.payload.error
                ;(t.loading = !1), (t.error = r)
              },
              playLiniusReplay: function (t, e) {
                var r = e.payload,
                  n = r.data,
                  o = r.poster,
                  a = r.adTags
                ;(t.playingLiniusReplay = {
                  data: n,
                  adTags: a,
                  poster: (0, b.R)(o),
                }),
                  (t.loading = !1),
                  (t.error = null)
              },
              stopLiniusReplay: function (t) {
                ;(t.playingLiniusReplay = null),
                  (t.loading = !1),
                  (t.error = null)
              },
            },
          }),
          x = w.actions,
          L = x.loadLiniusReplayByRace,
          E = x.loadLiniusReplayByUrl,
          O = x.loadLiniusTopSelections,
          R = x.loadLiniusReplaySuccess,
          j = x.loadLiniusReplayFailed,
          T = x.playLiniusReplay,
          S = x.stopLiniusReplay,
          k = w.name,
          I = w.reducer
        const P = r.p + '62bb694d22281c387c9d.jpg',
          A = r.p + '0280f7ae1190e3821eb0.jpg'
        var C = (0, r(97698).zB)({
          loading: function (t) {
            var e
            return null === (e = t[k]) || void 0 === e ? void 0 : e.loading
          },
          error: function (t) {
            var e
            return null === (e = t[k]) || void 0 === e ? void 0 : e.error
          },
          liniusReplay: function (t) {
            var e
            return null === (e = t[k]) || void 0 === e
              ? void 0
              : e.playingLiniusReplay
          },
        })
        function _(t) {
          return (
            (function (t) {
              if (Array.isArray(t)) return F(t)
            })(t) ||
            (function (t) {
              if (
                ('undefined' != typeof Symbol && null != t[Symbol.iterator]) ||
                null != t['@@iterator']
              )
                return Array.from(t)
            })(t) ||
            (function (t, e) {
              if (t) {
                if ('string' == typeof t) return F(t, e)
                var r = Object.prototype.toString.call(t).slice(8, -1)
                return (
                  'Object' === r && t.constructor && (r = t.constructor.name),
                  'Map' === r || 'Set' === r
                    ? Array.from(t)
                    : 'Arguments' === r ||
                      /^(?:Ui|I)nt(?:8|16|32)(?:Clamped)?Array$/.test(r)
                    ? F(t, e)
                    : void 0
                )
              }
            })(t) ||
            (function () {
              throw new TypeError(
                'Invalid attempt to spread non-iterable instance.\nIn order to be iterable, non-array objects must have a [Symbol.iterator]() method.'
              )
            })()
          )
        }
        function F(t, e) {
          ;(null == e || e > t.length) && (e = t.length)
          for (var r = 0, n = new Array(e); r < e; r++) n[r] = t[r]
          return n
        }
        var z = (0, r(54951).fW)('Linius Replay')
        function M(t) {
          var e = t.match(/BANDWIDTH=(\d+)/)
          return e ? parseInt(e[1], 10) : null
        }
        var N = r(27422),
          B = r(1349)
        function G(t) {
          return (
            (G =
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
            G(t)
          )
        }
        function U() {
          U = function () {
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
            c = a.asyncIterator || '@@asyncIterator',
            l = a.toStringTag || '@@toStringTag'
          function u(t, e, r) {
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
            u({}, '')
          } catch (t) {
            u = function (t, e, r) {
              return (t[e] = r)
            }
          }
          function s(t, e, r, n) {
            var a = e && e.prototype instanceof g ? e : g,
              i = Object.create(a.prototype),
              c = new I(n || [])
            return o(i, '_invoke', { value: j(t, r, c) }), i
          }
          function p(t, e, r) {
            try {
              return { type: 'normal', arg: t.call(e, r) }
            } catch (t) {
              return { type: 'throw', arg: t }
            }
          }
          e.wrap = s
          var f = 'suspendedStart',
            d = 'suspendedYield',
            y = 'executing',
            h = 'completed',
            v = {}
          function g() {}
          function m() {}
          function b() {}
          var w = {}
          u(w, i, function () {
            return this
          })
          var x = Object.getPrototypeOf,
            L = x && x(x(P([])))
          L && L !== r && n.call(L, i) && (w = L)
          var E = (b.prototype = g.prototype = Object.create(w))
          function O(t) {
            ;['next', 'throw', 'return'].forEach(function (e) {
              u(t, e, function (t) {
                return this._invoke(e, t)
              })
            })
          }
          function R(t, e) {
            function r(o, a, i, c) {
              var l = p(t[o], t, a)
              if ('throw' !== l.type) {
                var u = l.arg,
                  s = u.value
                return s && 'object' == G(s) && n.call(s, '__await')
                  ? e.resolve(s.__await).then(
                      function (t) {
                        r('next', t, i, c)
                      },
                      function (t) {
                        r('throw', t, i, c)
                      }
                    )
                  : e.resolve(s).then(
                      function (t) {
                        ;(u.value = t), i(u)
                      },
                      function (t) {
                        return r('throw', t, i, c)
                      }
                    )
              }
              c(l.arg)
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
          function j(e, r, n) {
            var o = f
            return function (a, i) {
              if (o === y) throw new Error('Generator is already running')
              if (o === h) {
                if ('throw' === a) throw i
                return { value: t, done: !0 }
              }
              for (n.method = a, n.arg = i; ; ) {
                var c = n.delegate
                if (c) {
                  var l = T(c, n)
                  if (l) {
                    if (l === v) continue
                    return l
                  }
                }
                if ('next' === n.method) n.sent = n._sent = n.arg
                else if ('throw' === n.method) {
                  if (o === f) throw ((o = h), n.arg)
                  n.dispatchException(n.arg)
                } else 'return' === n.method && n.abrupt('return', n.arg)
                o = y
                var u = p(e, r, n)
                if ('normal' === u.type) {
                  if (((o = n.done ? h : d), u.arg === v)) continue
                  return { value: u.arg, done: n.done }
                }
                'throw' === u.type &&
                  ((o = h), (n.method = 'throw'), (n.arg = u.arg))
              }
            }
          }
          function T(e, r) {
            var n = r.method,
              o = e.iterator[n]
            if (o === t)
              return (
                (r.delegate = null),
                ('throw' === n &&
                  e.iterator.return &&
                  ((r.method = 'return'),
                  (r.arg = t),
                  T(e, r),
                  'throw' === r.method)) ||
                  ('return' !== n &&
                    ((r.method = 'throw'),
                    (r.arg = new TypeError(
                      "The iterator does not provide a '" + n + "' method"
                    )))),
                v
              )
            var a = p(o, e.iterator, r.arg)
            if ('throw' === a.type)
              return (
                (r.method = 'throw'), (r.arg = a.arg), (r.delegate = null), v
              )
            var i = a.arg
            return i
              ? i.done
                ? ((r[e.resultName] = i.value),
                  (r.next = e.nextLoc),
                  'return' !== r.method && ((r.method = 'next'), (r.arg = t)),
                  (r.delegate = null),
                  v)
                : i
              : ((r.method = 'throw'),
                (r.arg = new TypeError('iterator result is not an object')),
                (r.delegate = null),
                v)
          }
          function S(t) {
            var e = { tryLoc: t[0] }
            1 in t && (e.catchLoc = t[1]),
              2 in t && ((e.finallyLoc = t[2]), (e.afterLoc = t[3])),
              this.tryEntries.push(e)
          }
          function k(t) {
            var e = t.completion || {}
            ;(e.type = 'normal'), delete e.arg, (t.completion = e)
          }
          function I(t) {
            ;(this.tryEntries = [{ tryLoc: 'root' }]),
              t.forEach(S, this),
              this.reset(!0)
          }
          function P(e) {
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
            throw new TypeError(G(e) + ' is not iterable')
          }
          return (
            (m.prototype = b),
            o(E, 'constructor', { value: b, configurable: !0 }),
            o(b, 'constructor', { value: m, configurable: !0 }),
            (m.displayName = u(b, l, 'GeneratorFunction')),
            (e.isGeneratorFunction = function (t) {
              var e = 'function' == typeof t && t.constructor
              return (
                !!e &&
                (e === m || 'GeneratorFunction' === (e.displayName || e.name))
              )
            }),
            (e.mark = function (t) {
              return (
                Object.setPrototypeOf
                  ? Object.setPrototypeOf(t, b)
                  : ((t.__proto__ = b), u(t, l, 'GeneratorFunction')),
                (t.prototype = Object.create(E)),
                t
              )
            }),
            (e.awrap = function (t) {
              return { __await: t }
            }),
            O(R.prototype),
            u(R.prototype, c, function () {
              return this
            }),
            (e.AsyncIterator = R),
            (e.async = function (t, r, n, o, a) {
              void 0 === a && (a = Promise)
              var i = new R(s(t, r, n, o), a)
              return e.isGeneratorFunction(r)
                ? i
                : i.next().then(function (t) {
                    return t.done ? t.value : i.next()
                  })
            }),
            O(E),
            u(E, l, 'Generator'),
            u(E, i, function () {
              return this
            }),
            u(E, 'toString', function () {
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
            (e.values = P),
            (I.prototype = {
              constructor: I,
              reset: function (e) {
                if (
                  ((this.prev = 0),
                  (this.next = 0),
                  (this.sent = this._sent = t),
                  (this.done = !1),
                  (this.delegate = null),
                  (this.method = 'next'),
                  (this.arg = t),
                  this.tryEntries.forEach(k),
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
                for (var a = this.tryEntries.length - 1; a >= 0; --a) {
                  var i = this.tryEntries[a],
                    c = i.completion
                  if ('root' === i.tryLoc) return o('end')
                  if (i.tryLoc <= this.prev) {
                    var l = n.call(i, 'catchLoc'),
                      u = n.call(i, 'finallyLoc')
                    if (l && u) {
                      if (this.prev < i.catchLoc) return o(i.catchLoc, !0)
                      if (this.prev < i.finallyLoc) return o(i.finallyLoc)
                    } else if (l) {
                      if (this.prev < i.catchLoc) return o(i.catchLoc, !0)
                    } else {
                      if (!u)
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
                    ? ((this.method = 'next'), (this.next = a.finallyLoc), v)
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
                  v
                )
              },
              finish: function (t) {
                for (var e = this.tryEntries.length - 1; e >= 0; --e) {
                  var r = this.tryEntries[e]
                  if (r.finallyLoc === t)
                    return this.complete(r.completion, r.afterLoc), k(r), v
                }
              },
              catch: function (t) {
                for (var e = this.tryEntries.length - 1; e >= 0; --e) {
                  var r = this.tryEntries[e]
                  if (r.tryLoc === t) {
                    var n = r.completion
                    if ('throw' === n.type) {
                      var o = n.arg
                      k(r)
                    }
                    return o
                  }
                }
                throw new Error('illegal catch attempt')
              },
              delegateYield: function (e, r, n) {
                return (
                  (this.delegate = {
                    iterator: P(e),
                    resultName: r,
                    nextLoc: n,
                  }),
                  'next' === this.method && (this.arg = t),
                  v
                )
              },
            }),
            e
          )
        }
        var D = U().mark($),
          Z = U().mark(X),
          q = U().mark(Y),
          W = U().mark(H)
        function $(t) {
          var e, r, n, o, a, i, c, l, u
          return U().wrap(
            function (s) {
              for (;;)
                switch ((s.prev = s.next)) {
                  case 0:
                    return (
                      (e = t.payload),
                      (r = e.meetCode),
                      (n = e.raceCode),
                      (o = e.tipsterId),
                      (a = e.condition),
                      (i = e.adTags),
                      (s.prev = 1),
                      (s.next = 4),
                      (0, N.RE)(B.w$.get, '/playlist', {
                        params: {
                          condition: a.replace(/\s/g, ''),
                          meetcode: r,
                          racecode: n,
                          tipsterid: o,
                          lws_token: '',
                        },
                      })
                    )
                  case 4:
                    return (
                      (c = s.sent),
                      (l = c.data),
                      (u = c.headers),
                      (s.next = 9),
                      (0, N.gz)(
                        T({
                          data: l,
                          adTags: i,
                          poster:
                            null == u ? void 0 : u['x-play-initial-poster'],
                        })
                      )
                    )
                  case 9:
                    return (s.next = 11), (0, N.gz)(R())
                  case 11:
                    z('Play Race', ''.concat(r, '/').concat(n, '/').concat(o)),
                      (s.next = 20)
                    break
                  case 14:
                    return (
                      (s.prev = 14),
                      (s.t0 = s.catch(1)),
                      (s.next = 18),
                      (0, N.gz)(j({ error: s.t0 }))
                    )
                  case 18:
                    z(
                      'Play Race Failed',
                      ''.concat(r, '/').concat(n, '/').concat(o)
                    ),
                      console.error(s.t0)
                  case 20:
                  case 'end':
                    return s.stop()
                }
            },
            D,
            null,
            [[1, 14]]
          )
        }
        function X(t) {
          var e, r, n, o, a, i, c
          return U().wrap(
            function (l) {
              for (;;)
                switch ((l.prev = l.next)) {
                  case 0:
                    return (
                      (e = t.payload),
                      (r = e.url),
                      (n = e.poster),
                      (o = e.adTags),
                      (l.prev = 1),
                      (l.next = 4),
                      (0, N.RE)(B.w$.get, r)
                    )
                  case 4:
                    return (
                      (a = l.sent),
                      (i = a.data),
                      (c = a.headers),
                      (l.next = 9),
                      (0, N.gz)(
                        T({
                          data: i,
                          adTags: o,
                          poster:
                            (null == c ? void 0 : c['x-play-initial-poster']) ||
                            n,
                        })
                      )
                    )
                  case 9:
                    return (l.next = 11), (0, N.gz)(R())
                  case 11:
                    z('Play Url', r), (l.next = 20)
                    break
                  case 14:
                    return (
                      (l.prev = 14),
                      (l.t0 = l.catch(1)),
                      (l.next = 18),
                      (0, N.gz)(j({ error: l.t0 }))
                    )
                  case 18:
                    z('Play Url Failed', r), console.error(l.t0)
                  case 20:
                  case 'end':
                    return l.stop()
                }
            },
            Z,
            null,
            [[1, 14]]
          )
        }
        function Y(t) {
          var e, r, n, o, a, i, c
          return U().wrap(
            function (l) {
              for (;;)
                switch ((l.prev = l.next)) {
                  case 0:
                    return (
                      (e = t.payload),
                      (r = e.meetCode),
                      (n = e.tipsterId),
                      (o = e.adTags),
                      (l.prev = 1),
                      (l.next = 4),
                      (0, N.RE)(B.w$.get, '/playlist', {
                        params: {
                          condition: 'AnyCondition',
                          contentType: 'topSelections',
                          meetcode: r,
                          tipsterid: n,
                          racecode: '',
                          lws_token: '',
                        },
                      })
                    )
                  case 4:
                    return (
                      (a = l.sent),
                      (i = a.data),
                      (c = a.headers),
                      (l.next = 9),
                      (0, N.gz)(
                        T({
                          data: i,
                          adTags: o,
                          poster:
                            null == c ? void 0 : c['x-play-initial-poster'],
                        })
                      )
                    )
                  case 9:
                    return (l.next = 11), (0, N.gz)(R())
                  case 11:
                    z('Play Top Selections', ''.concat(r, '/').concat(n)),
                      (l.next = 20)
                    break
                  case 14:
                    return (
                      (l.prev = 14),
                      (l.t0 = l.catch(1)),
                      (l.next = 18),
                      (0, N.gz)(j({ error: l.t0 }))
                    )
                  case 18:
                    z(
                      'Play Top Selections Failed',
                      ''.concat(r, '/').concat(n)
                    ),
                      console.error(l.t0)
                  case 20:
                  case 'end':
                    return l.stop()
                }
            },
            q,
            null,
            [[1, 14]]
          )
        }
        function H() {
          return U().wrap(function (t) {
            for (;;)
              switch ((t.prev = t.next)) {
                case 0:
                  return (t.next = 2), (0, N.ib)(L.type, $)
                case 2:
                  return (t.next = 4), (0, N.ib)(E.type, X)
                case 4:
                  return (t.next = 6), (0, N.ib)(O.type, Y)
                case 6:
                case 'end':
                  return t.stop()
              }
          }, W)
        }
        var J = ['onExitFullscreen']
        function K() {
          return (
            (K = Object.assign
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
            K.apply(this, arguments)
          )
        }
        function Q(t, e) {
          ;(null == e || e > t.length) && (e = t.length)
          for (var r = 0, n = new Array(e); r < e; r++) n[r] = t[r]
          return n
        }
        var V = function (t) {
          var e = t.onExitFullscreen,
            r = (function (t, e) {
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
            })(t, J)
          ;(0, s.vp)({ key: k, reducer: I }), (0, s.hb)({ key: k, saga: H })
          var a,
            i,
            c = (0, l.v9)(C),
            m = c.loading,
            b = c.error,
            w = c.liniusReplay,
            x = (0, h.Ln)(),
            L = (0, l.I0)(),
            E = (0, g.n)('BrightCovePlayerIdForLinius'),
            O =
              ((a = E.split('_')),
              (i = 2),
              (function (t) {
                if (Array.isArray(t)) return t
              })(a) ||
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
                      c = [],
                      l = !0,
                      u = !1
                    try {
                      if (((a = (r = r.call(t)).next), 0 === e)) {
                        if (Object(r) !== r) return
                        l = !1
                      } else
                        for (
                          ;
                          !(l = (n = a.call(r)).done) &&
                          (c.push(n.value), c.length !== e);
                          l = !0
                        );
                    } catch (t) {
                      ;(u = !0), (o = t)
                    } finally {
                      try {
                        if (
                          !l &&
                          null != r.return &&
                          ((i = r.return()), Object(i) !== i)
                        )
                          return
                      } finally {
                        if (u) throw o
                      }
                    }
                    return c
                  }
                })(a, i) ||
                (function (t, e) {
                  if (t) {
                    if ('string' == typeof t) return Q(t, e)
                    var r = Object.prototype.toString.call(t).slice(8, -1)
                    return (
                      'Object' === r &&
                        t.constructor &&
                        (r = t.constructor.name),
                      'Map' === r || 'Set' === r
                        ? Array.from(t)
                        : 'Arguments' === r ||
                          /^(?:Ui|I)nt(?:8|16|32)(?:Clamped)?Array$/.test(r)
                        ? Q(t, e)
                        : void 0
                    )
                  }
                })(a, i) ||
                (function () {
                  throw new TypeError(
                    'Invalid attempt to destructure non-iterable instance.\nIn order to be iterable, non-array objects must have a [Symbol.iterator]() method.'
                  )
                })()),
            R = O[0],
            j =
              (O[1],
              (0, n.useMemo)(
                function () {
                  if (!w) return null
                  var t = w.data,
                    e = w.poster,
                    r = w.adTags,
                    n = 'application/vnd.apple.mpegurl',
                    o = (function (t) {
                      var e = ''.concat(
                          (0, g.n)('LiniusReplay'),
                          '/linius/v3/assembly/hls/v?lws_token=&'
                        ),
                        r = 0
                      return t
                        .split(/\n/)
                        .reduce(function (t, n) {
                          var o = n.replace(/hls\/v\?/g, e)
                          if (o.startsWith('#')) {
                            var a = M(o)
                            return (
                              null !== a && r < a && (r = a),
                              [].concat(_(t), [[o]])
                            )
                          }
                          var i = t.slice(0, -1),
                            c = t[t.length - 1]
                          return [].concat(_(i), [[].concat(_(c), [o])])
                        }, [])
                        .filter(function (t) {
                          if (t[0].startsWith('#EXT-X-STREAM-INF')) {
                            var e = M(t[0])
                            if (null !== e && e < r) return !1
                          }
                          return !0
                        })
                        .flatMap(function (t) {
                          return t
                        })
                        .join('\n')
                    })(t)
                  return {
                    type: n,
                    src: 'data:'.concat(n, ';base64,').concat(btoa(o)),
                    poster: e,
                    adTags: r,
                  }
                },
                [w]
              )),
            T = (0, n.useCallback)(
              function () {
                ;(0, d.lg)(R), L(S())
              },
              [L]
            )
          return o().createElement(
            p.Z,
            K(
              {
                isOpen: m || !!b || !!w,
                onAfterOpen: function () {
                  ;(0, v.f)()
                },
                onAfterClose: function () {
                  ;(0, v.L)()
                },
                onRequestClose: T,
              },
              r
            ),
            o().createElement(
              d.ZP,
              null,
              m &&
                o().createElement(
                  u.xu,
                  { sx: { position: 'relative', pb: '56.25%' } },
                  o().createElement(f.Z, { loading: !0 })
                ),
              b && o().createElement(u.Ee, { src: x ? A : P }),
              j &&
                o().createElement(y.Z, {
                  playerId: E,
                  linius: j,
                  trackEvent: z,
                  onExitFullscreen: e,
                }),
              !m && o().createElement(d.PZ, { onClick: T })
            )
          )
        }
        V.propTypes = { onExitFullscreen: c().func }
        const tt = V
        var et = r(96331),
          rt = r(79777)
        function nt() {
          return (
            (nt = Object.assign
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
            nt.apply(this, arguments)
          )
        }
        const ot = (0, a.w)(function (t) {
          var e = nt(
            {},
            ((function (t) {
              if (null == t) throw new TypeError('Cannot destructure ' + t)
            })(t),
            t)
          )
          return o().createElement(et.Z, null, o().createElement(tt, e))
        })
        var at = function (t) {
            var e = t.data,
              r = t.poster
            return rt.h.dispatch(T({ data: e, poster: r }))
          },
          it = function (t) {
            var e = t.url,
              r = t.poster,
              n = t.adTags
            return rt.h.dispatch(E({ url: e, poster: r, adTags: n }))
          },
          ct = function (t) {
            var e = t.meetCode,
              r = t.raceCode,
              n = t.tipsterId,
              o = t.condition,
              a = t.adTags
            return rt.h.dispatch(
              L({
                meetCode: e,
                raceCode: r,
                tipsterId: n,
                condition: o,
                adTags: a,
              })
            )
          },
          lt = function (t) {
            var e = t.meetCode,
              r = t.tipsterId,
              n = t.adTags
            return rt.h.dispatch(O({ meetCode: e, tipsterId: r, adTags: n }))
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
    (t) => (t.O(0, [736, 351], () => (59539, t((t.s = 59539)))), t.O()),
  ])
)

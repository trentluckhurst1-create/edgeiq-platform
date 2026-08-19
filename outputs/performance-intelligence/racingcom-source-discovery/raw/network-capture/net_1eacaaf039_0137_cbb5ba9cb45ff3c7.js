!(function (e, t) {
  'object' == typeof exports && 'object' == typeof module
    ? (module.exports = t(require('React'), require('ReactDOM')))
    : 'function' == typeof define && define.amd
    ? define(['React', 'ReactDOM'], t)
    : 'object' == typeof exports
    ? (exports.rdc = t(require('React'), require('ReactDOM')))
    : ((e.rdc = e.rdc || {}), (e.rdc.raceReplay = t(e.React, e.ReactDOM)))
})(self, (e, t) =>
  (self.webpackChunkrdc = self.webpackChunkrdc || []).push([
    [408],
    {
      98027: (e, t, r) => {
        'use strict'
        r.d(t, { Y: () => n })
        var n = (0, r(54951).fW)('Race Replay')
      },
      53817: (e, t, r) => {
        'use strict'
        r(14629), r(25047), r(92556)
      },
      92556: (e, t, r) => {
        r.p = window.rdcWidgetsPath || ''
      },
      63879: (e, t, r) => {
        'use strict'
        r.r(t),
          r.d(t, {
            PlayRaceReplay: () => M,
            default: () => q,
            trackRaceReplayEvent: () => S.Y,
          }),
          r(53817)
        var n = r(1024),
          a = r.n(n),
          l = r(71570),
          o = r(24082),
          i = r(13295),
          c = r(84953),
          u = r(92551),
          p = r(37309),
          s = r(13980),
          y = r.n(s),
          f = r(69416),
          d = r(78667),
          v = r(2738),
          R = (0, r(2655).oM)({
            name: 'race-replay',
            initialState: { playingRaceReplayId: null },
            reducers: {
              playRaceReplay: function (e, t) {
                var r = t.payload,
                  n = r.videoId,
                  a = r.time
                ;(e.playingRaceReplayId = n), (e.playingRaceReplayTime = a || 0)
              },
              stopRaceReplay: function (e) {
                ;(e.playingRaceReplayId = null), (e.playingRaceReplayTime = 0)
              },
            },
          }),
          b = R.actions,
          g = b.playRaceReplay,
          m = b.stopRaceReplay,
          O = R.name,
          h = R.reducer,
          j = function (e) {
            var t
            return null === (t = e[O]) || void 0 === t
              ? void 0
              : t.playingRaceReplayId
          },
          I = function (e) {
            var t
            return null === (t = e[O]) || void 0 === t
              ? void 0
              : t.playingRaceReplayTime
          },
          w = ['needsLogin']
        function C() {
          return (
            (C = Object.assign
              ? Object.assign.bind()
              : function (e) {
                  for (var t = 1; t < arguments.length; t++) {
                    var r = arguments[t]
                    for (var n in r)
                      Object.prototype.hasOwnProperty.call(r, n) &&
                        (e[n] = r[n])
                  }
                  return e
                }),
            C.apply(this, arguments)
          )
        }
        function E(e, t) {
          ;(null == t || t > e.length) && (t = e.length)
          for (var r = 0, n = new Array(t); r < t; r++) n[r] = e[r]
          return n
        }
        var P = function (e) {
          var t = e.needsLogin,
            r = void 0 !== t && t,
            l = (function (e, t) {
              if (null == e) return {}
              var r,
                n,
                a = (function (e, t) {
                  if (null == e) return {}
                  var r,
                    n,
                    a = {},
                    l = Object.keys(e)
                  for (n = 0; n < l.length; n++)
                    (r = l[n]), t.indexOf(r) >= 0 || (a[r] = e[r])
                  return a
                })(e, t)
              if (Object.getOwnPropertySymbols) {
                var l = Object.getOwnPropertySymbols(e)
                for (n = 0; n < l.length; n++)
                  (r = l[n]),
                    t.indexOf(r) >= 0 ||
                      (Object.prototype.propertyIsEnumerable.call(e, r) &&
                        (a[r] = e[r]))
              }
              return a
            })(e, w)
          ;(0, i.vp)({ key: O, reducer: h })
          var s,
            y,
            R = (0, o.v9)(j),
            b = (0, o.v9)(I),
            g = (0, v.Tq)().isLoggedIn,
            P = (0, o.I0)(),
            k =
              (null == l ? void 0 : l.brightCovePlayerIdForReplay) ||
              (0, d.n)('BrightCovePlayerIdForReplay'),
            x = ((s = null == k ? void 0 : k.split('_')),
            (y = 1),
            (function (e) {
              if (Array.isArray(e)) return e
            })(s) ||
              (function (e, t) {
                var r =
                  null == e
                    ? null
                    : ('undefined' != typeof Symbol && e[Symbol.iterator]) ||
                      e['@@iterator']
                if (null != r) {
                  var n,
                    a,
                    l,
                    o,
                    i = [],
                    c = !0,
                    u = !1
                  try {
                    if (((l = (r = r.call(e)).next), 0 === t)) {
                      if (Object(r) !== r) return
                      c = !1
                    } else
                      for (
                        ;
                        !(c = (n = l.call(r)).done) &&
                        (i.push(n.value), i.length !== t);
                        c = !0
                      );
                  } catch (e) {
                    ;(u = !0), (a = e)
                  } finally {
                    try {
                      if (
                        !c &&
                        null != r.return &&
                        ((o = r.return()), Object(o) !== o)
                      )
                        return
                    } finally {
                      if (u) throw a
                    }
                  }
                  return i
                }
              })(s, y) ||
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
              })(s, y) ||
              (function () {
                throw new TypeError(
                  'Invalid attempt to destructure non-iterable instance.\nIn order to be iterable, non-array objects must have a [Symbol.iterator]() method.'
                )
              })())[0],
            A = (0, n.useCallback)(
              function () {
                ;(0, p.lg)(x), P(m())
              },
              [P, x]
            )
          return a().createElement(
            c.Z,
            C(
              {
                isOpen: null !== R,
                onAfterOpen: f.f,
                onAfterClose: f.L,
                onRequestClose: A,
              },
              l
            ),
            a().createElement(
              p.ZP,
              null,
              R &&
                a().createElement(u.Z, {
                  playerId: k,
                  videoId: R,
                  videoTime: b,
                  autoplay: !r || g || !0,
                }),
              a().createElement(p.PZ, { onClick: A })
            )
          )
        }
        const k = P
        P.propTypes = { loginHandler: y().func, needsLogin: y().bool }
        var x = r(79777),
          A = r(96331),
          S = r(98027)
        function T() {
          return (
            (T = Object.assign
              ? Object.assign.bind()
              : function (e) {
                  for (var t = 1; t < arguments.length; t++) {
                    var r = arguments[t]
                    for (var n in r)
                      Object.prototype.hasOwnProperty.call(r, n) &&
                        (e[n] = r[n])
                  }
                  return e
                }),
            T.apply(this, arguments)
          )
        }
        const q = (0, l.w)(function (e) {
          var t = T(
            {},
            ((function (e) {
              if (null == e) throw new TypeError('Cannot destructure ' + e)
            })(e),
            e)
          )
          return a().createElement(A.Z, null, a().createElement(k, t))
        })
        var M = function (e) {
          var t = e.videoId,
            r = e.time
          return x.h.dispatch(g({ videoId: t, time: r }))
        }
      },
      1024: (t) => {
        'use strict'
        t.exports = e
      },
      30314: (e) => {
        'use strict'
        e.exports = t
      },
    },
    (e) => (e.O(0, [736, 351], () => (63879, e((e.s = 63879)))), e.O()),
  ])
)

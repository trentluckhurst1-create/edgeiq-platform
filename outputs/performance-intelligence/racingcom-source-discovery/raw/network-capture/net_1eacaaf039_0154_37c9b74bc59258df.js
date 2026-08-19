/*! For license information please see rdc.miniCalendar.js.LICENSE.txt */
!(function (e, t) {
  'object' == typeof exports && 'object' == typeof module
    ? (module.exports = t(require('React'), require('ReactDOM')))
    : 'function' == typeof define && define.amd
    ? define(['React', 'ReactDOM'], t)
    : 'object' == typeof exports
    ? (exports.rdc = t(require('React'), require('ReactDOM')))
    : ((e.rdc = e.rdc || {}), (e.rdc.miniCalendar = t(e.React, e.ReactDOM)))
})(self, (e, t) =>
  (self.webpackChunkrdc = self.webpackChunkrdc || []).push([
    [963],
    {
      53817: (e, t, r) => {
        'use strict'
        r(14629), r(25047), r(92556)
      },
      92556: (e, t, r) => {
        r.p = window.rdcWidgetsPath || ''
      },
      39720: (e, t, r) => {
        'use strict'
        r.r(t), r.d(t, { default: () => qt }), r(53817)
        var n = r(1024),
          o = r.n(n),
          a = r(71570),
          i = r(13980),
          l = r.n(i),
          c = r(30186),
          u = r(13295),
          s = r(24082),
          d = r(65016),
          f = r(63761),
          p = r(10405),
          m = r(40163),
          y = r(98662),
          v = r(71015),
          b = 0,
          g = 1,
          h = 5,
          x = 'HK',
          w = r(2655),
          O = r(70887),
          j = r(78667),
          E = function (e, t) {
            return e.sortOrderByFirstRaceTime === t.sortOrderByFirstRaceTime
              ? 0
              : e.sortOrderByFirstRaceTime < t.sortOrderByFirstRaceTime
              ? -1
              : 1
          },
          S = function (e) {
            switch (e) {
              case 'FinalFields':
              case 'Acceptances':
                return 'Accept'
              case 'Abandoned':
                return 'Abnd'
              case 'Nominations':
                return 'Noms'
              default:
                return e
            }
          },
          T = function (e) {
            return function (t) {
              return !(0, O.J)(t.meet.state, e)
            }
          },
          C = function (e, t, r) {
            var n = (0, j.n)('VenueTrackMapping'),
              o =
                null == n
                  ? void 0
                  : n.find(function (e) {
                      return e.venue_code === t
                    })
            if (!o || !e) return e
            var a = o.track.replace(/\s/g, '-').toLowerCase()
            return r
              ? (function (e, t) {
                  return e + t
                })(
                  e.replace(/([a-zA-Z0-9_-]+)$/, a),
                  (function (e) {
                    return null != e && e.isJumpOut
                      ? '-jumpout'
                      : null != e && e.isTrial
                      ? '-trial'
                      : ''
                  })(r)
                )
              : e.replace(/([a-zA-Z0-9_-]+)$/, a)
          },
          P = (0, w.oM)({
            name: 'mini-calendar',
            initialState: {
              dataLoaded: !1,
              todaysRaces: { nextToJump: [], latestResults: [] },
              extendedRaces: { nextToJump: [] },
              meetings: [],
            },
            reducers: {
              loadTodaysRaces: function (e) {
                e.dataLoaded = !1
              },
              storeTodaysRaces: function (e, t) {
                var r = t.payload,
                  n = r.nextToJump,
                  o = r.latestResults
                ;(e.todaysRaces = {
                  nextToJump: n.filter(T(x)),
                  latestResults: o.filter(T(x)),
                }),
                  (e.dataLoaded = !0)
              },
              loadMeetings: function (e) {},
              storeMeetings: function (e, t) {
                var r = t.payload.meetings
                e.meetings = r.filter(
                  (function (e) {
                    return function (t) {
                      return !(0, O.J)(t.state, e)
                    }
                  })(x)
                )
              },
              loadExtendedRaces: function (e) {
                e.dataLoaded = !1
              },
              storeExtendedRaces: function (e, t) {
                var r = t.payload.nextToJump
                ;(e.extendedRaces = { nextToJump: r.filter(T(x)) }),
                  (e.dataLoaded = !0)
              },
            },
          }),
          I = P.actions,
          N = I.loadMeetings,
          F = I.loadTodaysRaces,
          k = I.storeTodaysRaces,
          A = I.storeExtendedRaces,
          R = I.loadExtendedRaces,
          D = I.storeMeetings,
          J = P.name,
          q = P.reducer,
          L = r(58179),
          z = r(81657),
          X = r.n(z),
          G = r(54253),
          Z = r(46062),
          _ = r.n(Z),
          M = r(51247),
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
        _()(M.Z, Q)
        const B = M.Z.locals || {}
        var W = ['tabs', 'activeTab', 'onChange', 'bgColor']
        function H() {
          return (
            (H = Object.assign
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
            H.apply(this, arguments)
          )
        }
        function V(e, t) {
          ;(null == t || t > e.length) && (t = e.length)
          for (var r = 0, n = new Array(t); r < t; r++) n[r] = e[r]
          return n
        }
        var Y = function (e) {
          var t,
            r,
            a = e.tabs,
            i = e.activeTab,
            l = e.onChange,
            u = e.bgColor,
            s = void 0 === u ? '#FFFFFF' : u,
            d = (function (e, t) {
              if (null == e) return {}
              var r,
                n,
                o = (function (e, t) {
                  if (null == e) return {}
                  var r,
                    n,
                    o = {},
                    a = Object.keys(e)
                  for (n = 0; n < a.length; n++)
                    (r = a[n]), t.indexOf(r) >= 0 || (o[r] = e[r])
                  return o
                })(e, t)
              if (Object.getOwnPropertySymbols) {
                var a = Object.getOwnPropertySymbols(e)
                for (n = 0; n < a.length; n++)
                  (r = a[n]),
                    t.indexOf(r) >= 0 ||
                      (Object.prototype.propertyIsEnumerable.call(e, r) &&
                        (o[r] = e[r]))
              }
              return o
            })(e, W),
            f =
              ((t = (0, n.useState)(null)),
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
                      a,
                      i,
                      l = [],
                      c = !0,
                      u = !1
                    try {
                      if (((a = (r = r.call(e)).next), 0 === t)) {
                        if (Object(r) !== r) return
                        c = !1
                      } else
                        for (
                          ;
                          !(c = (n = a.call(r)).done) &&
                          (l.push(n.value), l.length !== t);
                          c = !0
                        );
                    } catch (e) {
                      ;(u = !0), (o = e)
                    } finally {
                      try {
                        if (
                          !c &&
                          null != r.return &&
                          ((i = r.return()), Object(i) !== i)
                        )
                          return
                      } finally {
                        if (u) throw o
                      }
                    }
                    return l
                  }
                })(t, r) ||
                (function (e, t) {
                  if (e) {
                    if ('string' == typeof e) return V(e, t)
                    var r = Object.prototype.toString.call(e).slice(8, -1)
                    return (
                      'Object' === r &&
                        e.constructor &&
                        (r = e.constructor.name),
                      'Map' === r || 'Set' === r
                        ? Array.from(e)
                        : 'Arguments' === r ||
                          /^(?:Ui|I)nt(?:8|16|32)(?:Clamped)?Array$/.test(r)
                        ? V(e, t)
                        : void 0
                    )
                  }
                })(t, r) ||
                (function () {
                  throw new TypeError(
                    'Invalid attempt to destructure non-iterable instance.\nIn order to be iterable, non-array objects must have a [Symbol.iterator]() method.'
                  )
                })()),
            p = f[0],
            m = f[1]
          return (
            (0, n.useEffect)(
              function () {
                return null == p ? void 0 : p.update()
              },
              [p]
            ),
            o().createElement(
              c.xu,
              H(
                {
                  className: 'rdc-mini-calendar__meeting-selector',
                  sx: {
                    position: 'relative',
                    '& .swiper-container': { height: '16px' },
                  },
                },
                d
              ),
              o().createElement(
                L.tq,
                {
                  onSwiper: m,
                  slidesPerView: 'auto',
                  spaceBetween: 20,
                  navigation: {
                    nextEl: '#meetingSelectorNext',
                    prevEl: '#meetingSelectorPrev',
                    disabledClass: B.meetingSelectorDisabled,
                  },
                },
                a.map(function (e) {
                  return o().createElement(
                    L.o5,
                    {
                      key: e.label,
                      style: { display: 'inline-block', width: 'auto' },
                    },
                    o().createElement(
                      G.Z,
                      {
                        active: e === i,
                        onClick: function () {
                          return l(e)
                        },
                      },
                      e.label
                    )
                  )
                }),
                o().createElement(
                  'span',
                  {
                    slot: 'container-end',
                    style: { position: 'static', backgroundColor: s },
                  },
                  o().createElement(c.xu, {
                    className: B.meetingSelectorNext,
                    id: 'meetingSelectorNext',
                    sx: {
                      '&::after': {
                        backgroundImage: 'linear-gradient(to left, '
                          .concat(X()(s, { format: 'css', alpha: 1 }), ', ')
                          .concat(X()(s, { format: 'css', alpha: 0 }), ')'),
                      },
                    },
                  }),
                  o().createElement(c.xu, {
                    className: B.meetingSelectorPrev,
                    id: 'meetingSelectorPrev',
                    sx: {
                      '&::after': {
                        backgroundImage: 'linear-gradient(to right, '
                          .concat(X()(s, { format: 'css', alpha: 1 }), ', ')
                          .concat(X()(s, { format: 'css', alpha: 0 }), ')'),
                      },
                    },
                  })
                )
              )
            )
          )
        }
        Y.propTypes = {
          tabs: l().arrayOf(l().object).isRequired,
          activeTab: l().object,
          onChange: l().func.isRequired,
          bgColor: l().string,
        }
        const $ = Y
        var U = r(35998),
          K = {
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
        _()(U.Z, K)
        const ee = U.Z.locals || {}
        var te = ['bgColor']
        function re() {
          return (
            (re = Object.assign
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
            re.apply(this, arguments)
          )
        }
        var ne = function (e) {
          e.bgColor
          var t = (function (e, t) {
            if (null == e) return {}
            var r,
              n,
              o = (function (e, t) {
                if (null == e) return {}
                var r,
                  n,
                  o = {},
                  a = Object.keys(e)
                for (n = 0; n < a.length; n++)
                  (r = a[n]), t.indexOf(r) >= 0 || (o[r] = e[r])
                return o
              })(e, t)
            if (Object.getOwnPropertySymbols) {
              var a = Object.getOwnPropertySymbols(e)
              for (n = 0; n < a.length; n++)
                (r = a[n]),
                  t.indexOf(r) >= 0 ||
                    (Object.prototype.propertyIsEnumerable.call(e, r) &&
                      (o[r] = e[r]))
            }
            return o
          })(e, te)
          return o().createElement(c.xu, re({ className: ee.shimmer }, t))
        }
        ne.propTypes = { bgColor: l().string }
        const oe = ne
        var ae = r(64864)
        const ie = (0, r(97698).zB)({
          nextToJump: function (e) {
            var t
            return null === (t = e[J]) || void 0 === t
              ? void 0
              : t.todaysRaces.nextToJump
          },
          extendedNextToJump: function (e) {
            var t
            return null === (t = e[J]) || void 0 === t
              ? void 0
              : t.extendedRaces.nextToJump
          },
          latestResults: function (e) {
            var t
            return null === (t = e[J]) || void 0 === t
              ? void 0
              : t.todaysRaces.latestResults
          },
          isDataLoaded: function (e) {
            var t
            return null === (t = e[J]) || void 0 === t ? void 0 : t.dataLoaded
          },
          meetings: function (e) {
            var t
            return null === (t = e[J]) || void 0 === t ? void 0 : t.meetings
          },
        })
        var le = r(27121),
          ce = r(28742)
        function ue(e) {
          return (
            (ue =
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
            ue(e)
          )
        }
        var se = ['active', 'qualityColor'],
          de = ['active'],
          fe = ['highlight', 'status']
        function pe() {
          return (
            (pe = Object.assign
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
            pe.apply(this, arguments)
          )
        }
        function me(e, t) {
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
        function ye(e) {
          for (var t = 1; t < arguments.length; t++) {
            var r = null != arguments[t] ? arguments[t] : {}
            t % 2
              ? me(Object(r), !0).forEach(function (t) {
                  var n, o, a, i
                  ;(n = e),
                    (o = t),
                    (a = r[t]),
                    (i = (function (e, t) {
                      if ('object' != ue(e) || !e) return e
                      var r = e[Symbol.toPrimitive]
                      if (void 0 !== r) {
                        var n = r.call(e, 'string')
                        if ('object' != ue(n)) return n
                        throw new TypeError(
                          '@@toPrimitive must return a primitive value.'
                        )
                      }
                      return String(e)
                    })(o)),
                    (o = 'symbol' == ue(i) ? i : String(i)) in n
                      ? Object.defineProperty(n, o, {
                          value: a,
                          enumerable: !0,
                          configurable: !0,
                          writable: !0,
                        })
                      : (n[o] = a)
                })
              : Object.getOwnPropertyDescriptors
              ? Object.defineProperties(e, Object.getOwnPropertyDescriptors(r))
              : me(Object(r)).forEach(function (t) {
                  Object.defineProperty(
                    e,
                    t,
                    Object.getOwnPropertyDescriptor(r, t)
                  )
                })
          }
          return e
        }
        function ve(e, t) {
          if (null == e) return {}
          var r,
            n,
            o = (function (e, t) {
              if (null == e) return {}
              var r,
                n,
                o = {},
                a = Object.keys(e)
              for (n = 0; n < a.length; n++)
                (r = a[n]), t.indexOf(r) >= 0 || (o[r] = e[r])
              return o
            })(e, t)
          if (Object.getOwnPropertySymbols) {
            var a = Object.getOwnPropertySymbols(e)
            for (n = 0; n < a.length; n++)
              (r = a[n]),
                t.indexOf(r) >= 0 ||
                  (Object.prototype.propertyIsEnumerable.call(e, r) &&
                    (o[r] = e[r]))
          }
          return o
        }
        var be = function (e) {
          var t = e.active,
            r = e.qualityColor,
            n = ve(e, se),
            a = (0, m.Ln)(),
            i = r
              ? { borderTopColor: a ? r : '', borderLeftColor: a ? '' : r }
              : {}
          return o().createElement(
            c.xu,
            pe(
              {
                className: 'rdc-meeting-list-item__wrap',
                sx: ye(
                  ye(
                    {
                      display: 'block',
                      textDecoration: 'none',
                      border: '1px solid',
                      borderColor: t ? 'grey-99' : 'grey-de',
                      width: ['124px', '', '', '180px'],
                      padding: '6px',
                      cursor: 'pointer',
                      color: '#000',
                      backgroundColor: 'white',
                      borderTopWidth: ['1px', '', '', '3px'],
                      borderLeftWidth: ['4px', '', '', '1px'],
                      transition: 'border-color 0.3s ease-in-out',
                      marginTop: n.trafficB ? ['', '', '', '17px'] : '',
                    },
                    i
                  ),
                  {},
                  {
                    '&:hover': ye(
                      ye({ borderColor: 'grey-99' }, i),
                      {},
                      { color: '#ED1C24' }
                    ),
                  }
                ),
              },
              n
            )
          )
        }
        be.propTypes = { qualityColor: l().string, active: l().bool }
        var ge = function (e) {
          e.active
          var t = ve(e, de)
          return o().createElement(
            c.xv,
            pe(
              {
                className: 'rdc-meeting-list-item__heading',
                sx: {
                  transition: 'color ease-out 0.2s',
                  fontSize: 'body',
                  fontWeight: 'bold',
                  lineHeight: '1.2',
                  whiteSpace: 'nowrap',
                  textOverflow: 'ellipsis',
                  overflow: 'hidden',
                },
              },
              t
            )
          )
        }
        ge.propTypes = { active: l().bool }
        var he = function (e) {
            return o().createElement(
              c.xv,
              pe(
                {
                  className: 'rdc-meeting-list-item__state',
                  sx: {
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    border: '1px solid',
                    borderColor: 'grey-de',
                    borderRadius: '2px',
                    padding: '1px',
                    backgroundColor: 'offWhite',
                    color: '#8C877F',
                    lineHeight: '1',
                    minWidth: '26px',
                    textAlign: 'center',
                    fontSize: 'sm',
                    fontWeight: 'bold',
                  },
                },
                e
              )
            )
          },
          xe = function (e) {
            return o().createElement(
              c.xv,
              pe({ sx: { fontSize: '12px', lineHeight: '1.5' } }, e)
            )
          },
          we = function (e) {
            var t = e.highlight,
              r = e.status,
              n = ve(e, fe),
              a = 'grey-99'
            return (
              'Abandoned' === r ? (a = 'src') : t && (a = 'primary'),
              o().createElement(
                c.xv,
                pe(
                  {
                    sx: {
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      borderRadius: '2px',
                      padding: '0 4px',
                      backgroundColor: a,
                      color: 'white',
                      lineHeight: '1',
                      minWidth: '50px',
                      textAlign: 'center',
                      fontSize: 'sm',
                      fontWeight: 'bold',
                    },
                  },
                  n
                )
              )
            )
          }
        function Oe(e) {
          return (
            (Oe =
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
            Oe(e)
          )
        }
        we.propTypes = { highlight: l().bool, status: l().string }
        var je = ['active', 'qualityColor', 'race']
        function Ee() {
          return (
            (Ee = Object.assign
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
            Ee.apply(this, arguments)
          )
        }
        function Se(e, t) {
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
        function Te(e) {
          for (var t = 1; t < arguments.length; t++) {
            var r = null != arguments[t] ? arguments[t] : {}
            t % 2
              ? Se(Object(r), !0).forEach(function (t) {
                  var n, o, a, i
                  ;(n = e),
                    (o = t),
                    (a = r[t]),
                    (i = (function (e, t) {
                      if ('object' != Oe(e) || !e) return e
                      var r = e[Symbol.toPrimitive]
                      if (void 0 !== r) {
                        var n = r.call(e, 'string')
                        if ('object' != Oe(n)) return n
                        throw new TypeError(
                          '@@toPrimitive must return a primitive value.'
                        )
                      }
                      return String(e)
                    })(o)),
                    (o = 'symbol' == Oe(i) ? i : String(i)) in n
                      ? Object.defineProperty(n, o, {
                          value: a,
                          enumerable: !0,
                          configurable: !0,
                          writable: !0,
                        })
                      : (n[o] = a)
                })
              : Object.getOwnPropertyDescriptors
              ? Object.defineProperties(e, Object.getOwnPropertyDescriptors(r))
              : Se(Object(r)).forEach(function (t) {
                  Object.defineProperty(
                    e,
                    t,
                    Object.getOwnPropertyDescriptor(r, t)
                  )
                })
          }
          return e
        }
        var Ce = function (e) {
          var t,
            r,
            n = e.active,
            a = e.qualityColor,
            i = e.race,
            l = (function (e, t) {
              if (null == e) return {}
              var r,
                n,
                o = (function (e, t) {
                  if (null == e) return {}
                  var r,
                    n,
                    o = {},
                    a = Object.keys(e)
                  for (n = 0; n < a.length; n++)
                    (r = a[n]), t.indexOf(r) >= 0 || (o[r] = e[r])
                  return o
                })(e, t)
              if (Object.getOwnPropertySymbols) {
                var a = Object.getOwnPropertySymbols(e)
                for (n = 0; n < a.length; n++)
                  (r = a[n]),
                    t.indexOf(r) >= 0 ||
                      (Object.prototype.propertyIsEnumerable.call(e, r) &&
                        (o[r] = e[r]))
              }
              return o
            })(e, je),
            u = (0, m.Ln)(),
            s = a
              ? { borderTopColor: u ? a : '', borderLeftColor: u ? '' : a }
              : {},
            d = function (e) {
              return e
                ? {
                    'data-race-code': null == e ? void 0 : e.raceCode,
                    'data-meet-code': null == e ? void 0 : e.meetCode,
                  }
                : {}
            }
          return o().createElement(
            o().Fragment,
            null,
            o().createElement(
              c.xu,
              Ee(
                {
                  sx: { position: 'relative', top: '-18px' },
                  'data-track-class': 'mini-racing-calendar',
                },
                d({
                  raceCode: null == i ? void 0 : i.id,
                  meetCode:
                    null == i || null === (t = i.meet) || void 0 === t
                      ? void 0
                      : t.id,
                })
              ),
              o().createElement(
                c.xu,
                {
                  sx: {
                    display: 'flex',
                    justifyContent: 'center',
                    alignItems: 'center',
                    backgroundColor: a,
                    height: '20px',
                    color: '#fff',
                    textAlign: 'center',
                    fontSize: '12px',
                    fontFamily:
                      'Circular,Helvetica Neue,Helvetica,Arial,sans-serif',
                    fontWeight: 700,
                    borderRadius: '3px 3px 0 0',
                  },
                },
                'Next Victorian Race'
              ),
              o().createElement(
                c.xu,
                Ee(
                  {
                    className: 'rdc-floating-list-item__wrap',
                    'data-track-class': 'mini-racing-calendar',
                  },
                  d({
                    raceCode: null == i ? void 0 : i.id,
                    meetCode:
                      null == i || null === (r = i.meet) || void 0 === r
                        ? void 0
                        : r.id,
                  }),
                  {
                    sx: Te(
                      Te(
                        {
                          display: 'block',
                          textDecoration: 'none',
                          border: '1px solid',
                          borderColor: n ? 'grey-99' : 'grey-de',
                          width: ['124px', '', '', '180px'],
                          padding: '6px',
                          color: '#000',
                          cursor: 'pointer',
                          backgroundColor: 'white',
                          borderLeftWidth: ['4px', '', '', '1px'],
                          transition: 'border-color 0.3s ease-in-out',
                        },
                        s
                      ),
                      {},
                      {
                        '&:hover': Te(
                          Te({ borderColor: 'grey-99' }, s),
                          {},
                          { color: '#ED1C24' }
                        ),
                      }
                    ),
                  },
                  l
                )
              )
            )
          )
        }
        Ce.propTypes = { qualityColor: l().string, active: l().bool }
        var Pe = ['active', 'qualityColor', 'race']
        function Ie() {
          return (
            (Ie = Object.assign
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
            Ie.apply(this, arguments)
          )
        }
        var Ne = function (e) {
          e.active, e.qualityColor
          var t,
            r,
            n = e.race,
            a = (function (e, t) {
              if (null == e) return {}
              var r,
                n,
                o = (function (e, t) {
                  if (null == e) return {}
                  var r,
                    n,
                    o = {},
                    a = Object.keys(e)
                  for (n = 0; n < a.length; n++)
                    (r = a[n]), t.indexOf(r) >= 0 || (o[r] = e[r])
                  return o
                })(e, t)
              if (Object.getOwnPropertySymbols) {
                var a = Object.getOwnPropertySymbols(e)
                for (n = 0; n < a.length; n++)
                  (r = a[n]),
                    t.indexOf(r) >= 0 ||
                      (Object.prototype.propertyIsEnumerable.call(e, r) &&
                        (o[r] = e[r]))
              }
              return o
            })(e, Pe)
          return o().createElement(
            'div',
            Ie(
              { 'data-track-class': 'mini-racing-calendar' },
              (r = {
                raceCode: null == n ? void 0 : n.id,
                meetCode:
                  null == n || null === (t = n.meet) || void 0 === t
                    ? void 0
                    : t.id,
              })
                ? {
                    'data-race-code': null == r ? void 0 : r.raceCode,
                    'data-meet-code': null == r ? void 0 : r.meetCode,
                  }
                : {}
            ),
            o().createElement(
              c.xu,
              {
                sx: {
                  display: 'block',
                  backgroundColor: 'grey-66',
                  padding: '5px',
                  color: '#fff',
                  textAlign: 'center',
                  fontSize: '12px',
                  fontFamily:
                    'Circular,Helvetica Neue,Helvetica,Arial,sans-serif',
                  fontWeight: 700,
                  borderRadius: '3px 3px 0 0',
                },
              },
              'Next Victorian Race'
            ),
            o().createElement(
              c.xu,
              Ie(
                {
                  className: 'rdc-floating-list-item__wrap',
                  sx: {
                    display: 'block',
                    textDecoration: 'none',
                    borderColor: 'grey-66',
                    width: ['124px', '', '', '180px'],
                    padding: '6px',
                    paddingTop: '15px',
                    cursor: 'pointer',
                    backgroundColor: 'white',
                    borderWidth: ['1px', '', '', '1px'],
                    color: '#000',
                    borderStyle: 'solid',
                    transition: 'border-color 0.3s ease-in-out',
                    '&:hover': { color: '#ED1C24' },
                  },
                },
                a
              )
            )
          )
        }
        Ne.propTypes = { qualityColor: l().string, active: l().bool }
        var Fe = ['race', 'customStatus']
        function ke() {
          return (
            (ke = Object.assign
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
            ke.apply(this, arguments)
          )
        }
        function Ae(e, t) {
          return (
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
                  a,
                  i,
                  l = [],
                  c = !0,
                  u = !1
                try {
                  if (((a = (r = r.call(e)).next), 0 === t)) {
                    if (Object(r) !== r) return
                    c = !1
                  } else
                    for (
                      ;
                      !(c = (n = a.call(r)).done) &&
                      (l.push(n.value), l.length !== t);
                      c = !0
                    );
                } catch (e) {
                  ;(u = !0), (o = e)
                } finally {
                  try {
                    if (
                      !c &&
                      null != r.return &&
                      ((i = r.return()), Object(i) !== i)
                    )
                      return
                  } finally {
                    if (u) throw o
                  }
                }
                return l
              }
            })(e, t) ||
            (function (e, t) {
              if (e) {
                if ('string' == typeof e) return Re(e, t)
                var r = Object.prototype.toString.call(e).slice(8, -1)
                return (
                  'Object' === r && e.constructor && (r = e.constructor.name),
                  'Map' === r || 'Set' === r
                    ? Array.from(e)
                    : 'Arguments' === r ||
                      /^(?:Ui|I)nt(?:8|16|32)(?:Clamped)?Array$/.test(r)
                    ? Re(e, t)
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
        function Re(e, t) {
          ;(null == t || t > e.length) && (t = e.length)
          for (var r = 0, n = new Array(t); r < t; r++) n[r] = e[r]
          return n
        }
        var De = function (e) {
          var t = e.race,
            r = e.customStatus,
            a = (function (e, t) {
              if (null == e) return {}
              var r,
                n,
                o = (function (e, t) {
                  if (null == e) return {}
                  var r,
                    n,
                    o = {},
                    a = Object.keys(e)
                  for (n = 0; n < a.length; n++)
                    (r = a[n]), t.indexOf(r) >= 0 || (o[r] = e[r])
                  return o
                })(e, t)
              if (Object.getOwnPropertySymbols) {
                var a = Object.getOwnPropertySymbols(e)
                for (n = 0; n < a.length; n++)
                  (r = a[n]),
                    t.indexOf(r) >= 0 ||
                      (Object.prototype.propertyIsEnumerable.call(e, r) &&
                        (o[r] = e[r]))
              }
              return o
            })(e, Fe),
            i = (0, m.Ln)(),
            l = Ae((0, n.useState)(''), 2),
            u = l[0],
            s = l[1],
            d = Ae((0, n.useState)(!1), 2),
            f = d[0],
            p = d[1],
            y = t.raceStatus,
            v = !(null == a || !a.nextVicRace),
            b = i && a.floatingNextToJump
          ;(0, n.useEffect)(
            function () {
              var e = function () {
                var e = new Date(),
                  n = new Date(t.time),
                  o = (0, le.Z)(n, e),
                  a = (0, ce.Z)({ start: e, end: n })
                if ((p(o < 300), 'Open' === t.raceStatus)) {
                  var i = o < 0 ? '-' : ''
                  a.hours
                    ? s(
                        ''
                          .concat(i)
                          .concat(a.hours, 'h ')
                          .concat(a.minutes, 'm')
                      )
                    : a.minutes > 5
                    ? s(''.concat(i).concat(a.minutes, 'm'))
                    : a.minutes
                    ? s(
                        ''
                          .concat(i)
                          .concat(a.minutes, 'm ')
                          .concat(a.seconds, 's')
                      )
                    : s(''.concat(i).concat(a.seconds, 's'))
                } else s(r || 'Running')
              }
              e()
              var n = setInterval(e, 1e3)
              return function () {
                clearInterval(n)
              }
            },
            [r, t]
          )
          var g = null == t ? void 0 : t.meet.meetQualityColor
          'Abandoned' === t.raceStatus && (g = 'src')
          var h = function (e) {
            return (0, e.wrapper)(e.children)
          }
          return o().createElement(
            h,
            {
              wrapper: function (e) {
                return v
                  ? o().createElement(
                      Ne,
                      ke({ qualityColor: g, race: t }, a),
                      e
                    )
                  : b
                  ? o().createElement(
                      Ce,
                      ke({ qualityColor: g, race: t }, a),
                      e
                    )
                  : o().createElement(
                      be,
                      ke({ qualityColor: g, race: t }, a),
                      e
                    )
              },
            },
            o().createElement(
              c.kC,
              {
                alignItems: 'center',
                justifyContent: 'space-between',
                mb: '4px',
              },
              o().createElement(
                ge,
                null,
                (null == t ? void 0 : t.meet.venue) || 'N/A'
              ),
              i &&
                o().createElement(
                  he,
                  null,
                  (null == t ? void 0 : t.meet.state) || 'N/A'
                )
            ),
            o().createElement(
              c.kC,
              { justifyContent: 'space-between' },
              o().createElement(
                xe,
                null,
                'Race ',
                null == t ? void 0 : t.raceNumber
              ),
              o().createElement(
                we,
                { highlight: f, status: y },
                t.raceStatus && 'Abandoned' === t.raceStatus
                  ? S(t.raceStatus)
                  : u
              )
            )
          )
        }
        De.propTypes = { customStatus: l().string, race: l().object.isRequired }
        const Je = De
        var qe = ['race']
        function Le() {
          return (
            (Le = Object.assign
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
            Le.apply(this, arguments)
          )
        }
        var ze = function (e) {
          var t = e.race,
            r = (function (e, t) {
              if (null == e) return {}
              var r,
                n,
                o = (function (e, t) {
                  if (null == e) return {}
                  var r,
                    n,
                    o = {},
                    a = Object.keys(e)
                  for (n = 0; n < a.length; n++)
                    (r = a[n]), t.indexOf(r) >= 0 || (o[r] = e[r])
                  return o
                })(e, t)
              if (Object.getOwnPropertySymbols) {
                var a = Object.getOwnPropertySymbols(e)
                for (n = 0; n < a.length; n++)
                  (r = a[n]),
                    t.indexOf(r) >= 0 ||
                      (Object.prototype.propertyIsEnumerable.call(e, r) &&
                        (o[r] = e[r]))
              }
              return o
            })(e, qe),
            n = (0, m.Ln)(),
            a = null == t ? void 0 : t.meet.meetQualityColor
          return (
            'Abandoned' === t.raceStatus && (a = 'src'),
            o().createElement(
              be,
              Le({ qualityColor: a }, r),
              o().createElement(
                c.kC,
                {
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  mb: '4px',
                },
                o().createElement(
                  ge,
                  null,
                  (null == t ? void 0 : t.meet.venue) || 'N/A'
                ),
                n &&
                  o().createElement(
                    he,
                    null,
                    (null == t ? void 0 : t.meet.state) || 'N/A'
                  )
              ),
              o().createElement(
                c.kC,
                { justifyContent: 'space-between' },
                o().createElement(
                  xe,
                  null,
                  'Race ',
                  null == t ? void 0 : t.raceNumber
                ),
                'Abandoned' !== t.raceStatus &&
                  o().createElement(xe, null, t.resultsString)
              )
            )
          )
        }
        ze.propTypes = { race: l().object.isRequired }
        const Xe = ze
        var Ge = ['meeting', 'showStatus']
        function Ze() {
          return (
            (Ze = Object.assign
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
            Ze.apply(this, arguments)
          )
        }
        var _e = function (e) {
          var t = e.meeting,
            r = e.showStatus,
            n = (function (e, t) {
              if (null == e) return {}
              var r,
                n,
                o = (function (e, t) {
                  if (null == e) return {}
                  var r,
                    n,
                    o = {},
                    a = Object.keys(e)
                  for (n = 0; n < a.length; n++)
                    (r = a[n]), t.indexOf(r) >= 0 || (o[r] = e[r])
                  return o
                })(e, t)
              if (Object.getOwnPropertySymbols) {
                var a = Object.getOwnPropertySymbols(e)
                for (n = 0; n < a.length; n++)
                  (r = a[n]),
                    t.indexOf(r) >= 0 ||
                      (Object.prototype.propertyIsEnumerable.call(e, r) &&
                        (o[r] = e[r]))
              }
              return o
            })(e, Ge),
            a = (0, m.Ln)(),
            i = null == t ? void 0 : t.meetQualityColor
          'Abandoned' === (null == t ? void 0 : t.status) && (i = 'src')
          var l = r
          return (
            l && t.isJumpOut && (l = 'Results' === t.status),
            o().createElement(
              be,
              Ze({ qualityColor: i }, n),
              o().createElement(
                c.kC,
                {
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  mb: '4px',
                },
                o().createElement(
                  ge,
                  null,
                  (null == t ? void 0 : t.venue) || 'N/A'
                ),
                a &&
                  o().createElement(
                    he,
                    null,
                    (null == t ? void 0 : t.state) || 'N/A'
                  )
              ),
              o().createElement(
                c.kC,
                { justifyContent: 'space-between' },
                o().createElement(
                  xe,
                  null,
                  null == t ? void 0 : t.racesCount,
                  ' ',
                  (function (e, t) {
                    return null != e && e.isTrial
                      ? 'Trials'
                      : null != e && e.isJumpOut
                      ? t
                        ? 'J/Outs'
                        : 'Jump Outs'
                      : 'Races'
                  })(t, !a)
                ),
                l && o().createElement(we, { status: t.status }, S(t.status))
              )
            )
          )
        }
        _e.propTypes = { meeting: l().object.isRequired, showStatus: l().bool }
        const Me = _e
        var Qe = ['label']
        function Be() {
          return (
            (Be = Object.assign
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
            Be.apply(this, arguments)
          )
        }
        var We = function (e) {
          var t = e.label,
            r = (function (e, t) {
              if (null == e) return {}
              var r,
                n,
                o = (function (e, t) {
                  if (null == e) return {}
                  var r,
                    n,
                    o = {},
                    a = Object.keys(e)
                  for (n = 0; n < a.length; n++)
                    (r = a[n]), t.indexOf(r) >= 0 || (o[r] = e[r])
                  return o
                })(e, t)
              if (Object.getOwnPropertySymbols) {
                var a = Object.getOwnPropertySymbols(e)
                for (n = 0; n < a.length; n++)
                  (r = a[n]),
                    t.indexOf(r) >= 0 ||
                      (Object.prototype.propertyIsEnumerable.call(e, r) &&
                        (o[r] = e[r]))
              }
              return o
            })(e, Qe)
          return o().createElement(
            c.kC,
            Be(
              {
                sx: {
                  height: ['50px', '', '', '52px'],
                  alignItems: 'center',
                  justifyContent: 'flex-start',
                },
              },
              r
            ),
            o().createElement(
              c.xv,
              {
                sx: {
                  fontFamily: 'circular',
                  fontWeight: 'bold',
                  fontSize: '16px',
                  color: 'grey-de',
                },
              },
              t || 'Data not available'
            )
          )
        }
        We.propTypes = { label: l().string }
        const He = We
        var Ve = r(99060),
          Ye = r(3204),
          $e = r(21604),
          Ue = r(54951)
        function Ke() {
          return (
            (Ke = Object.assign
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
            Ke.apply(this, arguments)
          )
        }
        function et(e) {
          return (
            (et =
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
            et(e)
          )
        }
        function tt(e, t, r) {
          var n
          return (
            (n = (function (e, t) {
              if ('object' != et(e) || !e) return e
              var r = e[Symbol.toPrimitive]
              if (void 0 !== r) {
                var n = r.call(e, 'string')
                if ('object' != et(n)) return n
                throw new TypeError(
                  '@@toPrimitive must return a primitive value.'
                )
              }
              return String(e)
            })(t)),
            (t = 'symbol' == et(n) ? n : String(n)) in e
              ? Object.defineProperty(e, t, {
                  value: r,
                  enumerable: !0,
                  configurable: !0,
                  writable: !0,
                })
              : (e[t] = r),
            e
          )
        }
        function rt(e, t) {
          ;(null == t || t > e.length) && (t = e.length)
          for (var r = 0, n = new Array(t); r < t; r++) n[r] = e[r]
          return n
        }
        function nt() {
          return (
            (nt = Object.assign
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
            nt.apply(this, arguments)
          )
        }
        var ot = function (e) {
          var t,
            r,
            a = e.activeTab,
            i = e.bgColor,
            l = void 0 === i ? '#FFFFFF' : i,
            u = e.isExtended,
            f = e.variant,
            p = void 0 === f ? 'none' : f,
            m = (0, s.v9)(ie),
            y = m.isDataLoaded,
            v = m.nextToJump,
            h = m.extendedNextToJump,
            x = m.latestResults,
            w = m.meetings,
            O = (0, n.useMemo)(
              function () {
                switch (null == a ? void 0 : a.value) {
                  case b:
                    return o().createElement(
                      o().Fragment,
                      null,
                      (function (e, t) {
                        var r =
                            arguments.length > 2 && void 0 !== arguments[2]
                              ? arguments[2]
                              : 'none',
                          n = e
                            .slice()
                            .sort(function (e, t) {
                              return new Date(e.time) - new Date(t.time)
                            })
                            .slice(0, 20)
                        if (0 === n.length)
                          return [
                            o().createElement(
                              L.o5,
                              { key: 'next-to-jump' },
                              o().createElement(He, {
                                label: 'No more races scheduled for today',
                              })
                            ),
                          ]
                        var a = n.find(function (e) {
                          return 'VIC' === e.meet.state && !t
                        })
                        return o().createElement(
                          o().Fragment,
                          null,
                          n.map(function (e) {
                            var n,
                              i,
                              l = (0, Ve.Z)(
                                e.meet.date,
                                'yyyy-MM-dd',
                                new Date()
                              ),
                              c = new Date(
                                new Date().getFullYear(),
                                new Date().getMonth(),
                                new Date().getDate()
                              ),
                              u = (0, Ye.Z)(l, c)
                            1 === u
                              ? (i = 'Tomorrow')
                              : u > 1 && (i = (0, d.Z)(l, 'd MMM yy'))
                            var s,
                              f = null == e ? void 0 : e.meet,
                              p =
                                'floating' === r &&
                                (null == e ? void 0 : e.id) ===
                                  (null == a ? void 0 : a.id) &&
                                'VIC' === (null == f ? void 0 : f.state) &&
                                !1 === (null == f ? void 0 : f.isJumpOut) &&
                                !1 === (null == f ? void 0 : f.isTrial) &&
                                !t
                            return o().createElement(
                              L.o5,
                              Ke(
                                {
                                  key: e.id,
                                  style: {
                                    display: 'inline-block',
                                    width: 'auto',
                                  },
                                  'data-track-class': 'mini-racing-calendar',
                                },
                                (s = {
                                  raceCode: null == e ? void 0 : e.id,
                                  meetCode:
                                    null == e ||
                                    null === (n = e.meet) ||
                                    void 0 === n
                                      ? void 0
                                      : n.id,
                                })
                                  ? {
                                      'data-race-code':
                                        null == s ? void 0 : s.raceCode,
                                      'data-meet-code':
                                        null == s ? void 0 : s.meetCode,
                                    }
                                  : {}
                              ),
                              o().createElement(Je, {
                                onClick: function () {
                                  return (function (e, n) {
                                    var o,
                                      a = 'NTJ'
                                    t || 'pinned' !== r
                                      ? t ||
                                        'floating' !== r ||
                                        (a = 'NTJFloating')
                                      : (a = 'NTJPinned'),
                                      (0, Ue.fW)(
                                        a,
                                        ''.concat(
                                          !t && n ? 'NTJFloating' : '',
                                          'RacecardTile'
                                        ),
                                        (null == e ||
                                        null === (o = e.meet) ||
                                        void 0 === o
                                          ? void 0
                                          : o.state) + 'race'
                                      )
                                  })(e, !!p)
                                },
                                as: 'a',
                                href: ''
                                  .concat(
                                    (0, $e.Rr)(
                                      C(e.meet.meetUrl, e.meet.venueCode, {
                                        isTrial: e.meet.isTrial || !1,
                                        isJumpOut: e.meet.isJumpOut || !1,
                                      })
                                    ),
                                    '/race/'
                                  )
                                  .concat(e.raceNumber),
                                race: e,
                                customStatus: i,
                                floatingNextToJump: p,
                              })
                            )
                          })
                        )
                      })(u ? h : v, u, p)
                    )
                  case g:
                    return 0 === x.length
                      ? [
                          o().createElement(
                            L.o5,
                            { key: 'latest-result' },
                            o().createElement(He, {
                              className: 'swiper-slide',
                              label: 'Currently no results available for today',
                            })
                          ),
                        ]
                      : x
                          .slice()
                          .sort(function (e, t) {
                            return new Date(t.time) - new Date(e.time)
                          })
                          .slice(0, 20)
                          .map(function (e) {
                            var t, r
                            return o().createElement(
                              L.o5,
                              nt(
                                {
                                  key: e.id,
                                  style: {
                                    display: 'inline-block',
                                    width: 'auto',
                                  },
                                  'data-track-class': 'mini-racing-calendar',
                                },
                                (r = {
                                  raceCode: null == e ? void 0 : e.id,
                                  meetCode:
                                    null == e ||
                                    null === (t = e.meet) ||
                                    void 0 === t
                                      ? void 0
                                      : t.id,
                                })
                                  ? {
                                      'data-race-code':
                                        null == r ? void 0 : r.raceCode,
                                      'data-meet-code':
                                        null == r ? void 0 : r.meetCode,
                                    }
                                  : {}
                              ),
                              o().createElement(Xe, {
                                as: 'a',
                                href: ''
                                  .concat(
                                    (0, $e.Rr)(
                                      C(e.meet.meetUrl, e.meet.venueCode, {
                                        isTrial: e.meet.isTrial || !1,
                                        isJumpOut: e.meet.isJumpOut || !1,
                                      })
                                    ),
                                    '/race/'
                                  )
                                  .concat(e.raceNumber, '/results'),
                                race: e,
                              })
                            )
                          })
                  default:
                    var e = null == a ? void 0 : a.value
                    if (e) {
                      var t = (0, d.Z)(new Date(), 'yyyy-MM-dd'),
                        r = (0, d.Z)(e, 'yyyy-MM-dd'),
                        n = w
                          .filter(function (e) {
                            return e.date === r
                          })
                          .sort(E)
                          .map(function (e) {
                            return o().createElement(
                              L.o5,
                              {
                                key: e.id,
                                style: {
                                  display: 'inline-block',
                                  width: 'auto',
                                },
                              },
                              o().createElement(Me, {
                                as: 'a',
                                href: (0, $e.Rr)(
                                  C(e.meetUrl, e.venueCode, {
                                    isTrial: e.isTrial || !1,
                                    isJumpOut: e.isJumpOut || !1,
                                  })
                                ),
                                meeting: e,
                                showStatus: t !== r,
                              })
                            )
                          })
                      return n.length
                        ? n
                        : [
                            o().createElement(
                              L.o5,
                              { key: 'no-meeting' },
                              o().createElement(He, {
                                label: 'No meeting scheduled',
                              })
                            ),
                          ]
                    }
                    return null
                }
              },
              [u, null == a ? void 0 : a.value, h, v, x, w]
            ),
            j =
              ((t = (0, n.useState)(null)),
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
                      a,
                      i,
                      l = [],
                      c = !0,
                      u = !1
                    try {
                      if (((a = (r = r.call(e)).next), 0 === t)) {
                        if (Object(r) !== r) return
                        c = !1
                      } else
                        for (
                          ;
                          !(c = (n = a.call(r)).done) &&
                          (l.push(n.value), l.length !== t);
                          c = !0
                        );
                    } catch (e) {
                      ;(u = !0), (o = e)
                    } finally {
                      try {
                        if (
                          !c &&
                          null != r.return &&
                          ((i = r.return()), Object(i) !== i)
                        )
                          return
                      } finally {
                        if (u) throw o
                      }
                    }
                    return l
                  }
                })(t, r) ||
                (function (e, t) {
                  if (e) {
                    if ('string' == typeof e) return rt(e, t)
                    var r = Object.prototype.toString.call(e).slice(8, -1)
                    return (
                      'Object' === r &&
                        e.constructor &&
                        (r = e.constructor.name),
                      'Map' === r || 'Set' === r
                        ? Array.from(e)
                        : 'Arguments' === r ||
                          /^(?:Ui|I)nt(?:8|16|32)(?:Clamped)?Array$/.test(r)
                        ? rt(e, t)
                        : void 0
                    )
                  }
                })(t, r) ||
                (function () {
                  throw new TypeError(
                    'Invalid attempt to destructure non-iterable instance.\nIn order to be iterable, non-array objects must have a [Symbol.iterator]() method.'
                  )
                })()),
            S = j[0],
            T = j[1]
          return (
            (0, n.useEffect)(
              function () {
                return null == S ? void 0 : S.update()
              },
              [S, O]
            ),
            y
              ? o().createElement(
                  c.xu,
                  { className: 'rdc-mini-calendar__meeting-list' },
                  o().createElement(
                    L.tq,
                    {
                      onSwiper: T,
                      slidesPerView: 'auto',
                      spaceBetween: 10,
                      slidesPerGroup: 1,
                      style:
                        'pinned' === p
                          ? { paddingBottom: '5px' }
                          : { paddingBottom: '5px', paddingTop: '20px' },
                      breakpoints: tt({}, ae.md, { slidesPerGroup: 3 }),
                      mousewheel: !0,
                      navigation: {
                        nextEl: '#meeting-list-next',
                        prevEl: '#meeting-list-prev',
                        disabledClass: ee.meetingListDisabled,
                      },
                    },
                    O,
                    o().createElement(
                      'span',
                      { slot: 'container-end', style: { position: 'static' } },
                      o().createElement(c.xu, {
                        id: 'meeting-list-next',
                        className: ee.meetingListNext,
                        sx: {
                          backgroundColor: l,
                          '&::after': {
                            backgroundImage: 'linear-gradient(to left, '
                              .concat(X()(l, { format: 'css', alpha: 1 }), ', ')
                              .concat(X()(l, { format: 'css', alpha: 0 }), ')'),
                          },
                        },
                      }),
                      o().createElement(c.xu, {
                        id: 'meeting-list-prev',
                        className: ee.meetingListPrev,
                        sx: {
                          backgroundColor: l,
                          '&::after': {
                            backgroundImage: 'linear-gradient(to right, '
                              .concat(X()(l, { format: 'css', alpha: 1 }), ', ')
                              .concat(X()(l, { format: 'css', alpha: 0 }), ')'),
                          },
                        },
                      })
                    )
                  )
                )
              : o().createElement(oe, null)
          )
        }
        ot.propTypes = {
          isExtended: l().bool,
          activeTab: l().object.isRequired,
          bgColor: l().string,
          variant: l().string,
        }
        const at = ot
        var it,
          lt,
          ct,
          ut,
          st = r(36007),
          dt = (r(36808), r(27422)),
          ft = r(38847),
          pt = r(69285),
          mt = r(67834)
        function yt(e, t) {
          return (
            t || (t = e.slice(0)),
            Object.freeze(
              Object.defineProperties(e, { raw: { value: Object.freeze(t) } })
            )
          )
        }
        var vt = (0, mt.Ps)(
            it ||
              (it = yt([
                '\n  fragment CDRace on Race {\n    id\n    time\n    group\n    raceStatus\n    raceNumber\n    resultsString\n    meet {\n      id\n      venue\n      venueCode\n      state\n      status\n      meetUrl\n      meetQualityColor\n      isTrial\n      isJumpOut\n      date\n    }\n  }\n',
              ]))
          ),
          bt = (0, mt.Ps)(
            lt ||
              (lt = yt([
                '\n  query CDGetTodaysRacesByState($states: String!) {\n    nextToJump: GetNextToJumpByState(states: $states) {\n      ...CDRace\n    }\n    latestResults: GetLatestResultsByState(states: $states) {\n      ...CDRace\n      raceEntries {\n        id\n        raceEntryNumber\n        position\n        finish\n        horseName\n      }\n    }\n  }\n  ',
                '\n',
              ])),
            vt
          ),
          gt = (0, mt.Ps)(
            ct ||
              (ct = yt([
                '\n  query CDGetTodaysRacesByState($states: String!) {\n    nextToJump: GetNextToJumpByState(states: $states) {\n      ...CDRace\n    }\n  }\n  ',
                '\n',
              ])),
            vt
          ),
          ht = (0, mt.Ps)(
            ut ||
              (ut = yt([
                '\n  query GetRaceMeetingsByState(\n    $daysBack: Int!\n    $daysForward: Int!\n    $states: String!\n  ) {\n    meetings: GetRaceMeetingsByState(\n      daysBack: $daysBack\n      daysForward: $daysForward\n      states: $states\n    ) {\n      id\n      venue\n      venueCode\n      country\n      trackName\n      state\n      status\n      date\n      racesCount\n      meetQualityColor\n      isTrial\n      isJumpOut\n      state\n      sortOrderByFirstRaceTime\n      meetUrl\n    }\n  }\n',
              ]))
          )
        function xt(e) {
          return (
            (xt =
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
            xt(e)
          )
        }
        function wt() {
          wt = function () {
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
            a = 'function' == typeof Symbol ? Symbol : {},
            i = a.iterator || '@@iterator',
            l = a.asyncIterator || '@@asyncIterator',
            c = a.toStringTag || '@@toStringTag'
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
            var a = t && t.prototype instanceof b ? t : b,
              i = Object.create(a.prototype),
              l = new N(n || [])
            return o(i, '_invoke', { value: T(e, r, l) }), i
          }
          function d(e, t, r) {
            try {
              return { type: 'normal', arg: e.call(t, r) }
            } catch (e) {
              return { type: 'throw', arg: e }
            }
          }
          t.wrap = s
          var f = 'suspendedStart',
            p = 'suspendedYield',
            m = 'executing',
            y = 'completed',
            v = {}
          function b() {}
          function g() {}
          function h() {}
          var x = {}
          u(x, i, function () {
            return this
          })
          var w = Object.getPrototypeOf,
            O = w && w(w(F([])))
          O && O !== r && n.call(O, i) && (x = O)
          var j = (h.prototype = b.prototype = Object.create(x))
          function E(e) {
            ;['next', 'throw', 'return'].forEach(function (t) {
              u(e, t, function (e) {
                return this._invoke(t, e)
              })
            })
          }
          function S(e, t) {
            function r(o, a, i, l) {
              var c = d(e[o], e, a)
              if ('throw' !== c.type) {
                var u = c.arg,
                  s = u.value
                return s && 'object' == xt(s) && n.call(s, '__await')
                  ? t.resolve(s.__await).then(
                      function (e) {
                        r('next', e, i, l)
                      },
                      function (e) {
                        r('throw', e, i, l)
                      }
                    )
                  : t.resolve(s).then(
                      function (e) {
                        ;(u.value = e), i(u)
                      },
                      function (e) {
                        return r('throw', e, i, l)
                      }
                    )
              }
              l(c.arg)
            }
            var a
            o(this, '_invoke', {
              value: function (e, n) {
                function o() {
                  return new t(function (t, o) {
                    r(e, n, t, o)
                  })
                }
                return (a = a ? a.then(o, o) : o())
              },
            })
          }
          function T(t, r, n) {
            var o = f
            return function (a, i) {
              if (o === m) throw new Error('Generator is already running')
              if (o === y) {
                if ('throw' === a) throw i
                return { value: e, done: !0 }
              }
              for (n.method = a, n.arg = i; ; ) {
                var l = n.delegate
                if (l) {
                  var c = C(l, n)
                  if (c) {
                    if (c === v) continue
                    return c
                  }
                }
                if ('next' === n.method) n.sent = n._sent = n.arg
                else if ('throw' === n.method) {
                  if (o === f) throw ((o = y), n.arg)
                  n.dispatchException(n.arg)
                } else 'return' === n.method && n.abrupt('return', n.arg)
                o = m
                var u = d(t, r, n)
                if ('normal' === u.type) {
                  if (((o = n.done ? y : p), u.arg === v)) continue
                  return { value: u.arg, done: n.done }
                }
                'throw' === u.type &&
                  ((o = y), (n.method = 'throw'), (n.arg = u.arg))
              }
            }
          }
          function C(t, r) {
            var n = r.method,
              o = t.iterator[n]
            if (o === e)
              return (
                (r.delegate = null),
                ('throw' === n &&
                  t.iterator.return &&
                  ((r.method = 'return'),
                  (r.arg = e),
                  C(t, r),
                  'throw' === r.method)) ||
                  ('return' !== n &&
                    ((r.method = 'throw'),
                    (r.arg = new TypeError(
                      "The iterator does not provide a '" + n + "' method"
                    )))),
                v
              )
            var a = d(o, t.iterator, r.arg)
            if ('throw' === a.type)
              return (
                (r.method = 'throw'), (r.arg = a.arg), (r.delegate = null), v
              )
            var i = a.arg
            return i
              ? i.done
                ? ((r[t.resultName] = i.value),
                  (r.next = t.nextLoc),
                  'return' !== r.method && ((r.method = 'next'), (r.arg = e)),
                  (r.delegate = null),
                  v)
                : i
              : ((r.method = 'throw'),
                (r.arg = new TypeError('iterator result is not an object')),
                (r.delegate = null),
                v)
          }
          function P(e) {
            var t = { tryLoc: e[0] }
            1 in e && (t.catchLoc = e[1]),
              2 in e && ((t.finallyLoc = e[2]), (t.afterLoc = e[3])),
              this.tryEntries.push(t)
          }
          function I(e) {
            var t = e.completion || {}
            ;(t.type = 'normal'), delete t.arg, (e.completion = t)
          }
          function N(e) {
            ;(this.tryEntries = [{ tryLoc: 'root' }]),
              e.forEach(P, this),
              this.reset(!0)
          }
          function F(t) {
            if (t || '' === t) {
              var r = t[i]
              if (r) return r.call(t)
              if ('function' == typeof t.next) return t
              if (!isNaN(t.length)) {
                var o = -1,
                  a = function r() {
                    for (; ++o < t.length; )
                      if (n.call(t, o))
                        return (r.value = t[o]), (r.done = !1), r
                    return (r.value = e), (r.done = !0), r
                  }
                return (a.next = a)
              }
            }
            throw new TypeError(xt(t) + ' is not iterable')
          }
          return (
            (g.prototype = h),
            o(j, 'constructor', { value: h, configurable: !0 }),
            o(h, 'constructor', { value: g, configurable: !0 }),
            (g.displayName = u(h, c, 'GeneratorFunction')),
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
                  ? Object.setPrototypeOf(e, h)
                  : ((e.__proto__ = h), u(e, c, 'GeneratorFunction')),
                (e.prototype = Object.create(j)),
                e
              )
            }),
            (t.awrap = function (e) {
              return { __await: e }
            }),
            E(S.prototype),
            u(S.prototype, l, function () {
              return this
            }),
            (t.AsyncIterator = S),
            (t.async = function (e, r, n, o, a) {
              void 0 === a && (a = Promise)
              var i = new S(s(e, r, n, o), a)
              return t.isGeneratorFunction(r)
                ? i
                : i.next().then(function (e) {
                    return e.done ? e.value : i.next()
                  })
            }),
            E(j),
            u(j, c, 'Generator'),
            u(j, i, function () {
              return this
            }),
            u(j, 'toString', function () {
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
            (t.values = F),
            (N.prototype = {
              constructor: N,
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
                    (l.type = 'throw'),
                    (l.arg = t),
                    (r.next = n),
                    o && ((r.method = 'next'), (r.arg = e)),
                    !!o
                  )
                }
                for (var a = this.tryEntries.length - 1; a >= 0; --a) {
                  var i = this.tryEntries[a],
                    l = i.completion
                  if ('root' === i.tryLoc) return o('end')
                  if (i.tryLoc <= this.prev) {
                    var c = n.call(i, 'catchLoc'),
                      u = n.call(i, 'finallyLoc')
                    if (c && u) {
                      if (this.prev < i.catchLoc) return o(i.catchLoc, !0)
                      if (this.prev < i.finallyLoc) return o(i.finallyLoc)
                    } else if (c) {
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
              abrupt: function (e, t) {
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
                  ('break' === e || 'continue' === e) &&
                  a.tryLoc <= t &&
                  t <= a.finallyLoc &&
                  (a = null)
                var i = a ? a.completion : {}
                return (
                  (i.type = e),
                  (i.arg = t),
                  a
                    ? ((this.method = 'next'), (this.next = a.finallyLoc), v)
                    : this.complete(i)
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
                  (this.delegate = {
                    iterator: F(t),
                    resultName: r,
                    nextLoc: n,
                  }),
                  'next' === this.method && (this.arg = e),
                  v
                )
              },
            }),
            t
          )
        }
        var Ot = wt().mark(Ct),
          jt = wt().mark(Pt),
          Et = wt().mark(It),
          St = wt().mark(Nt),
          Tt = function (e) {
            return e.replace(/[|]VIC|VIC[|]|VIC/i, '')
          }
        function Ct(e) {
          var t, r, n
          return wt().wrap(function (o) {
            for (;;)
              switch ((o.prev = o.next)) {
                case 0:
                  return (
                    (t = e && e.payload ? e.payload : ''),
                    (o.next = 3),
                    (0, dt.RE)(ft.I, {
                      query: ht,
                      variables: { daysBack: 1, daysForward: h, states: Tt(t) },
                      context: { useChampionData: !0 },
                    })
                  )
                case 3:
                  return (
                    (r = o.sent),
                    (n = r.data),
                    (o.next = 7),
                    (0, dt.gz)(D({ meetings: n.meetings }))
                  )
                case 7:
                case 'end':
                  return o.stop()
              }
          }, Ot)
        }
        function Pt(e) {
          var t, r, n, o, a
          return wt().wrap(function (i) {
            for (;;)
              switch ((i.prev = i.next)) {
                case 0:
                  return (
                    (t = e && e.payload ? e.payload : ''),
                    (i.next = 3),
                    (0, dt.RE)(ft.I, {
                      query: bt,
                      fetchPolicy: 'no-cache',
                      variables: { states: Tt(t) },
                      context: { useChampionData: !0 },
                    })
                  )
                case 3:
                  return (r = i.sent), (n = r.data), (i.next = 7), (0, pt.A)()
                case 7:
                  return (
                    (o = n.nextToJump),
                    (a = n.latestResults),
                    (i.next = 10),
                    (0, dt.gz)(k({ nextToJump: o, latestResults: a }))
                  )
                case 10:
                  return i.abrupt('return', n)
                case 11:
                case 'end':
                  return i.stop()
              }
          }, jt)
        }
        function It(e) {
          var t, r, n, o
          return wt().wrap(function (a) {
            for (;;)
              switch ((a.prev = a.next)) {
                case 0:
                  return (
                    (t = e && e.payload ? e.payload : ''),
                    (a.next = 3),
                    (0, dt.RE)(ft.I, {
                      query: gt,
                      fetchPolicy: 'no-cache',
                      variables: { states: Tt(t) },
                      context: { useChampionData: !0 },
                    })
                  )
                case 3:
                  return (r = a.sent), (n = r.data), (a.next = 7), (0, pt.A)()
                case 7:
                  return (
                    (o = n.nextToJump),
                    (a.next = 10),
                    (0, dt.gz)(A({ nextToJump: o }))
                  )
                case 10:
                  return a.abrupt('return', n)
                case 11:
                case 'end':
                  return a.stop()
              }
          }, Et)
        }
        function Nt() {
          return wt().wrap(function (e) {
            for (;;)
              switch ((e.prev = e.next)) {
                case 0:
                  return (e.next = 2), (0, y.W0)(N.type, Ct)
                case 2:
                  return (e.next = 4), (0, y.W0)(F.type, Pt)
                case 4:
                  return (e.next = 6), (0, y.W0)(R.type, It)
                case 6:
                case 'end':
                  return e.stop()
              }
          }, St)
        }
        var Ft = r(11594)
        function kt(e, t) {
          return (
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
                  a,
                  i,
                  l = [],
                  c = !0,
                  u = !1
                try {
                  if (((a = (r = r.call(e)).next), 0 === t)) {
                    if (Object(r) !== r) return
                    c = !1
                  } else
                    for (
                      ;
                      !(c = (n = a.call(r)).done) &&
                      (l.push(n.value), l.length !== t);
                      c = !0
                    );
                } catch (e) {
                  ;(u = !0), (o = e)
                } finally {
                  try {
                    if (
                      !c &&
                      null != r.return &&
                      ((i = r.return()), Object(i) !== i)
                    )
                      return
                  } finally {
                    if (u) throw o
                  }
                }
                return l
              }
            })(e, t) ||
            (function (e, t) {
              if (e) {
                if ('string' == typeof e) return At(e, t)
                var r = Object.prototype.toString.call(e).slice(8, -1)
                return (
                  'Object' === r && e.constructor && (r = e.constructor.name),
                  'Map' === r || 'Set' === r
                    ? Array.from(e)
                    : 'Arguments' === r ||
                      /^(?:Ui|I)nt(?:8|16|32)(?:Clamped)?Array$/.test(r)
                    ? At(e, t)
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
        function At(e, t) {
          ;(null == t || t > e.length) && (t = e.length)
          for (var r = 0, n = new Array(t); r < t; r++) n[r] = e[r]
          return n
        }
        r(81987)
        var Rt = function (e) {
          var t,
            r,
            a,
            i,
            l = e.bgColor,
            x = void 0 === l ? '#FFFFFF' : l,
            w = e.defaultTab,
            O = e.isHideOtherTabs,
            j = void 0 !== O && O,
            E = e.isHideViewCalendar,
            S = void 0 !== E && E,
            T = e.isExtended,
            P = void 0 !== T && T
          ;(0, u.vp)({ key: J, reducer: q }), (0, u.hb)({ key: J, saga: Nt })
          var I = (0, m.Ln)(),
            k = (0, y.fO)().dispatch,
            A = (0, s.v9)(ie),
            D = A.nextToJump,
            L = A.latestResults,
            z = A.isDataLoaded,
            X = A.extendedNextToJump,
            G = [
              { value: 'VIC', label: 'Victoria', forced: !0 },
              { value: 'SA', label: 'South Australia' },
              { value: 'QLD', label: 'Queensland' },
              { value: 'NSW', label: 'New South Wales' },
              { value: 'WA', label: 'Western Australia' },
              { value: 'ACT', label: 'Australian Capital Territory' },
              { value: 'NT', label: 'Northern Territory' },
              { value: 'TAS', label: 'Tasmania' },
            ],
            Z = kt((0, n.useState)([]), 2),
            _ = (Z[0], Z[1]),
            M = kt((0, n.useState)((0, Ft.c)()), 2),
            Q = M[0],
            B = M[1],
            W = kt(
              (0, n.useState)(
                G.filter(function (e) {
                  return Q.split('|').includes(e.value) || e.forced
                })
              ),
              2
            ),
            H = W[0],
            V = W[1],
            Y = Ft.Wp,
            U = kt((0, n.useState)(P ? 'none' : 'pinned'), 2),
            K = U[0],
            ee = U[1],
            te = kt((0, n.useState)(null), 2),
            re = te[0],
            ne = te[1]
          ;(0, n.useEffect)(function () {
            ;(0, st.J)(ee, P ? 'none' : 'pinned')
          }, []),
            (0, n.useEffect)(
              function () {
                ne(
                  P || 'pinned' !== K
                    ? P || 'floating' !== K
                      ? 'NTJ'
                      : 'NTJFloating'
                    : 'NTJPinned'
                )
              },
              [K]
            ),
            (0, n.useEffect)(
              function () {
                k(N(Q)), k(P ? R(Q) : F(Q))
              },
              [Q]
            )
          var oe = function (e) {
            return e.slice().sort(function (e, t) {
              return new Date(e.time) - new Date(t.time)
            })
          }
          ;(0, n.useEffect)(
            function () {
              var e,
                t = oe(D)[0]
              if (t) {
                var r = new Date(t.time) - new Date()
                e = setTimeout(function () {
                  k(F(Q))
                }, 6e4 + Math.max(0, r))
              }
              return function () {
                e && clearTimeout(e)
              }
            },
            [D, k]
          ),
            (0, n.useEffect)(
              function () {
                var e = oe(X).filter(function (e) {
                  var t = null == e ? void 0 : e.meet
                  return (
                    'VIC' === (null == t ? void 0 : t.state) &&
                    !1 === (null == t ? void 0 : t.isJumpOut) &&
                    !1 === (null == t ? void 0 : t.isTrial)
                  )
                })
                _(e)
              },
              [X, k]
            )
          var ae = (0, n.useMemo)(function () {
              for (
                var e = (0, p.Z)(new Date()),
                  t = (0, f.Z)(e, -1),
                  r = [
                    { label: 'Today', value: e },
                    { label: 'Tomorrow', value: (0, f.Z)(e, 1) },
                  ],
                  n = 2;
                n <= h;
                n += 1
              ) {
                var o = (0, f.Z)(e, n)
                r.push({ label: (0, d.Z)(o, 'EEEE'), value: o })
              }
              return [
                { label: 'Yesterday', value: t },
                { label: 'Latest Results', value: g },
                { label: 'Next To Jump', value: b },
              ].concat(r)
            }, []),
            le = kt((0, n.useState)(ae[2]), 2),
            ce = le[0],
            ue = le[1]
          function se(e) {
            return 'VIC' === e.meet.state
          }
          ;(0, n.useEffect)(
            function () {
              if (z) {
                if (w) return void ue(ae[w])
                0 === D.length && (L.length > 0 ? ue(ae[1]) : ue(ae[4]))
              }
            },
            [z, D, L, ae, w]
          )
          var de = D.find(se) ? D.find(se) : null
          return o().createElement(
            c.xu,
            { className: 'rdc-mini-calendar' },
            o().createElement(
              c.kC,
              { sx: { alignItems: 'center' } },
              I &&
                'pinned' === K &&
                D.length > 0 &&
                null != de &&
                o().createElement(
                  c.xu,
                  { sx: { minWidth: 'auto', mr: '10px' } },
                  o().createElement(Je, {
                    onClick: function () {
                      return (function (e, t) {
                        var r,
                          n = 'NTJ'
                        P || 'pinned' !== K
                          ? P || 'floating' !== K || (n = 'NTJFloating')
                          : (n = 'NTJPinned'),
                          (0, Ue.fW)(
                            n,
                            ''.concat(
                              !P && t ? 'NTJPinned' : '',
                              'RacecardTile'
                            ),
                            (null == e || null === (r = e.meet) || void 0 === r
                              ? void 0
                              : r.state) + 'race'
                          )
                      })(de, !!de)
                    },
                    as: 'a',
                    href: ''
                      .concat(
                        (0, $e.Rr)(
                          C(
                            null === (t = de.meet) || void 0 === t
                              ? void 0
                              : t.meetUrl,
                            null === (r = de.meet) || void 0 === r
                              ? void 0
                              : r.venueCode,
                            {
                              isTrial:
                                (null === (a = de.meet) || void 0 === a
                                  ? void 0
                                  : a.isTrial) || !1,
                              isJumpOut:
                                (null === (i = de.meet) || void 0 === i
                                  ? void 0
                                  : i.isJumpOut) || !1,
                            }
                          )
                        ),
                        '/race/'
                      )
                      .concat(null == de ? void 0 : de.raceNumber),
                    race: de,
                    nextVicRace: !0,
                  })
                ),
              o().createElement(
                c.xu,
                null,
                o().createElement(
                  c.kC,
                  { sx: { alignItems: 'center', mb: ['14px', '', '', '8px'] } },
                  !j &&
                    o().createElement(
                      o().Fragment,
                      null,
                      I &&
                        o().createElement(v.Z, {
                          callBack: function (e) {
                            if (!e) {
                              var t = (0, Ft.OY)(!1)
                              t &&
                                (V(
                                  G.filter(function (e) {
                                    return (
                                      t.split('|').includes(e.value) || e.forced
                                    )
                                  })
                                ),
                                B(t))
                            }
                          },
                          options: G,
                          optionsType: 'states',
                          defaultValues: ['Victoria'],
                          width: '208px',
                          height: '28px',
                          hideSelectedOptions: !1,
                          backspaceRemovesValue: !1,
                          closeMenuOnSelect: !1,
                          isClearable: !1,
                          isMulti: !0,
                          filterName: Y,
                          filterValues: H,
                          gaCategory: re,
                          gaCallback: function (e) {
                            e && (0, Ue.fW)(e.category, e.label, e.action)
                          },
                        }),
                      o().createElement($, {
                        tabs: ae,
                        activeTab: ce,
                        bgColor: x,
                        onChange: function (e) {
                          ue(e)
                        },
                        flex: '1 1 auto',
                      })
                    ),
                  !S &&
                    I &&
                    o().createElement(
                      c.xv,
                      {
                        as: 'a',
                        href: ''
                          .concat(location.protocol, '//')
                          .concat(location.host, '/calendar'),
                        sx: {
                          textDecoration: 'none',
                          fontSize: 'body',
                          fontFamily: 'link',
                          fontWeight: 'bold',
                          cursor: 'pointer',
                          color: 'tab.normal',
                          '&:hover': { color: 'tab.active' },
                        },
                      },
                      'View Calendar'
                    )
                ),
                o().createElement(at, {
                  activeTab: ce,
                  bgColor: x,
                  isExtended: P,
                  isLoading: !1,
                  variant: K,
                })
              )
            )
          )
        }
        Rt.propTypes = {
          bgColor: l().string,
          defaultTab: l().number || null,
          isHideOtherTabs: l().bool || null,
          isHideViewCalendar: l().bool || null,
          isExtended: l().bool || null,
        }
        const Dt = Rt
        r(39744)
        var Jt = r(96331)
        const qt = (0, a.w)(function (e) {
          return o().createElement(Jt.Z, null, o().createElement(Dt, e))
        })
      },
      35998: (e, t, r) => {
        'use strict'
        r.d(t, { Z: () => a })
        var n = r(82609),
          o = r.n(n)()(function (e) {
            return e[1]
          })
        o.push([
          e.id,
          '.QZXKTKvWw8uQwsE9pFWZdg\\=\\={height:52px;width:1260px;background-image:linear-gradient(#dedede,#dedede),linear-gradient(#dedede,#dedede);background-size:50% 1.8rem,100% 5.2rem;background-repeat:no-repeat}.izqPaIqHLJwjddnP9qI9FQ\\=\\=,.YttxNDD\\+fvJiTIXG7rwz3A\\=\\={position:absolute;top:0;bottom:0;width:0;z-index:1;opacity:1;transition:opacity .3s ease-out;}@media (min-width:1024px){.izqPaIqHLJwjddnP9qI9FQ\\=\\=,.YttxNDD\\+fvJiTIXG7rwz3A\\=\\={width:30px;display:flex;align-items:center;justify-content:center;cursor:pointer}}.izqPaIqHLJwjddnP9qI9FQ\\=\\=.UAkVb09yjtSdZpCgibMwTg\\=\\=,.YttxNDD\\+fvJiTIXG7rwz3A\\=\\=.UAkVb09yjtSdZpCgibMwTg\\=\\={opacity:0;pointer-events:none}.izqPaIqHLJwjddnP9qI9FQ\\=\\=:after,.izqPaIqHLJwjddnP9qI9FQ\\=\\=:before,.YttxNDD\\+fvJiTIXG7rwz3A\\=\\=:after,.YttxNDD\\+fvJiTIXG7rwz3A\\=\\=:before{transition:color .2s ease-in-out}.izqPaIqHLJwjddnP9qI9FQ\\=\\=:hover:after,.izqPaIqHLJwjddnP9qI9FQ\\=\\=:hover:before,.YttxNDD\\+fvJiTIXG7rwz3A\\=\\=:hover:after,.YttxNDD\\+fvJiTIXG7rwz3A\\=\\=:hover:before{color:#ed1c24;transition:color .3s ease-in-out}.izqPaIqHLJwjddnP9qI9FQ\\=\\=:before,.YttxNDD\\+fvJiTIXG7rwz3A\\=\\=:before{font-family:racing-icon-2;font-size:14px;color:#666}.izqPaIqHLJwjddnP9qI9FQ\\=\\=:after,.YttxNDD\\+fvJiTIXG7rwz3A\\=\\=:after{content:"";position:absolute;top:0;bottom:0;display:block;pointer-events:none;width:30px;}@media (min-width:1024px){.izqPaIqHLJwjddnP9qI9FQ\\=\\=:after,.YttxNDD\\+fvJiTIXG7rwz3A\\=\\=:after{width:100px}}.izqPaIqHLJwjddnP9qI9FQ\\=\\={right:0;}@media (min-width:1024px){.izqPaIqHLJwjddnP9qI9FQ\\=\\=:before{content:"\\39"}}.izqPaIqHLJwjddnP9qI9FQ\\=\\=:after{right:-1px;}@media (min-width:1024px){.izqPaIqHLJwjddnP9qI9FQ\\=\\=:after{right:30px}}.YttxNDD\\+fvJiTIXG7rwz3A\\=\\={left:0;}@media (min-width:1024px){.YttxNDD\\+fvJiTIXG7rwz3A\\=\\=:before{content:"\\4d"}}.YttxNDD\\+fvJiTIXG7rwz3A\\=\\=:after{left:-1px;}@media (min-width:1024px){.YttxNDD\\+fvJiTIXG7rwz3A\\=\\=:after{left:30px}}',
          '',
        ]),
          (o.locals = {
            shimmer: 'QZXKTKvWw8uQwsE9pFWZdg==',
            meetingListNext: 'izqPaIqHLJwjddnP9qI9FQ==',
            meetingListPrev: 'YttxNDD+fvJiTIXG7rwz3A==',
            meetingListDisabled: 'UAkVb09yjtSdZpCgibMwTg==',
          })
        const a = o
      },
      51247: (e, t, r) => {
        'use strict'
        r.d(t, { Z: () => a })
        var n = r(82609),
          o = r.n(n)()(function (e) {
            return e[1]
          })
        o.push([
          e.id,
          '.\\+5Z7TFzXAEeXmFjKPczFmw\\=\\=,.GvTh4XsQdX2nFPoR6ANo0w\\=\\={position:absolute;top:0;bottom:0;width:0;z-index:1;opacity:1;transition:opacity .3s ease-out;pointer-events:none;}.\\+5Z7TFzXAEeXmFjKPczFmw\\=\\=.c-b5F6CDvlRRn78am7xU5w\\=\\=,.GvTh4XsQdX2nFPoR6ANo0w\\=\\=.c-b5F6CDvlRRn78am7xU5w\\=\\={opacity:0}.\\+5Z7TFzXAEeXmFjKPczFmw\\=\\=:after,.GvTh4XsQdX2nFPoR6ANo0w\\=\\=:after{content:"";position:absolute;top:0;bottom:0;display:block;width:30px;}@media (min-width:1024px){.\\+5Z7TFzXAEeXmFjKPczFmw\\=\\=:after,.GvTh4XsQdX2nFPoR6ANo0w\\=\\=:after{width:100px}}.\\+5Z7TFzXAEeXmFjKPczFmw\\=\\={right:0;}.\\+5Z7TFzXAEeXmFjKPczFmw\\=\\=:after{content:"";right:-1px}.GvTh4XsQdX2nFPoR6ANo0w\\=\\={left:0;}.GvTh4XsQdX2nFPoR6ANo0w\\=\\=:after{content:"";left:-1px}',
          '',
        ]),
          (o.locals = {
            meetingSelectorNext: '+5Z7TFzXAEeXmFjKPczFmw==',
            meetingSelectorPrev: 'GvTh4XsQdX2nFPoR6ANo0w==',
            meetingSelectorDisabled: 'c-b5F6CDvlRRn78am7xU5w==',
          })
        const a = o
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
    (e) => (e.O(0, [736, 351], () => (39720, e((e.s = 39720)))), e.O()),
  ])
)

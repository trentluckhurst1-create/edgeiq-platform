/*! For license information please see rdc.formAnalystTips.js.LICENSE.txt */
!(function (e, t) {
  'object' == typeof exports && 'object' == typeof module
    ? (module.exports = t(require('React'), require('ReactDOM')))
    : 'function' == typeof define && define.amd
    ? define(['React', 'ReactDOM'], t)
    : 'object' == typeof exports
    ? (exports.rdc = t(require('React'), require('ReactDOM')))
    : ((e.rdc = e.rdc || {}), (e.rdc.formAnalystTips = t(e.React, e.ReactDOM)))
})(self, (e, t) =>
  (self.webpackChunkrdc = self.webpackChunkrdc || []).push([
    [67],
    {
      53817: (e, t, r) => {
        'use strict'
        r(14629), r(25047), r(92556)
      },
      92556: (e, t, r) => {
        r.p = window.rdcWidgetsPath || ''
      },
      10473: (e, t, r) => {
        'use strict'
        r.r(t), r.d(t, { default: () => dt }), r(53817)
        var n = r(1024),
          o = r.n(n),
          i = r(71570),
          a = r(62388),
          c = r(10687),
          s = r(30186),
          l = r(13980),
          u = r.n(l),
          f = r(13295),
          p = r(40163),
          d = r(24082),
          m = r(85814),
          h = r(98662),
          y = r(2738),
          v = r(2655),
          g = (0, v.oM)({
            name: 'form-analyst-tips',
            initialState: {
              tipster: null,
              tippings: { suggestedBets: null, quaddieLegs: null, races: [] },
              trackInformation: null,
              linius: { single: null, multiple: null },
            },
            reducers: {
              loadTippings: function () {},
              storeTipster: function (e, t) {
                var r = t.payload.tipster
                e.tipster = r
              },
              storeTippings: function (e, t) {
                var r = t.payload,
                  n = r.quaddieLegs,
                  o = r.suggestedBets,
                  i = r.tippingInformation
                e.tippings = { quaddieLegs: n, suggestedBets: o, races: i }
              },
              storeTrackInformation: function (e, t) {
                var r = t.payload.trackInformation
                e.trackInformation = r
              },
              loadTABData: function () {},
              storeTABData: function (e, t) {
                var r = t.payload,
                  n = r.raceNumber,
                  o = r.raceEntries,
                  i = e.tippings.races.find(function (e) {
                    return e.raceNumber === n
                  })
                i &&
                  i.selections.forEach(function (e) {
                    var t = o.find(function (t) {
                      return t.outcomeId === e.outcomeId
                    })
                    ;(e.winPriceBE = (null == t ? void 0 : t.winPriceBE) || {}),
                      (e.winPriceSB2 =
                        (null == t ? void 0 : t.winPriceSB2) || {})
                  })
              },
              loadLiniusReplays: function () {},
              storeLiniusReplays: function (e, t) {
                var r = t.payload,
                  n = r.single,
                  o = r.multiple
                ;(e.linius.single = n), (e.linius.multiple = o)
              },
            },
          }),
          b = g.actions,
          j = b.loadTippings,
          w = b.storeTipster,
          x = b.storeTippings,
          E = b.storeTrackInformation,
          k = b.loadTABData,
          O = b.storeTABData,
          S = b.loadLiniusReplays,
          I = b.storeLiniusReplays,
          L = g.name,
          N = g.reducer,
          C = function (e) {
            var t
            return null === (t = e[L]) || void 0 === t ? void 0 : t.tipster
          },
          P = function (e) {
            var t
            return null === (t = e[L]) || void 0 === t ? void 0 : t.linius
          },
          T = function (e) {
            var t
            return null === (t = e[L]) || void 0 === t
              ? void 0
              : t.trackInformation
          },
          A = function (e) {
            var t
            return null === (t = e[L]) ||
              void 0 === t ||
              null === (t = t.tippings) ||
              void 0 === t
              ? void 0
              : t.races
          },
          R = function (e) {
            var t
            return null === (t = e[L]) ||
              void 0 === t ||
              null === (t = t.tippings) ||
              void 0 === t
              ? void 0
              : t.suggestedBets
          },
          B = (0, r(54951).fW)('Form Analyst Tips'),
          z = (0, v.oM)({
            name: 'profile',
            initialState: { data: null, killSwitchActive: null },
            reducers: {
              updateProfile: function (e, t) {
                var r = t.payload,
                  n = r.firstName,
                  o = r.email
                e.data = { firstName: n, email: o }
              },
              checkKillSwitch: function () {},
              setKillSwitch: function (e, t) {
                var r = t.payload.active
                e.killSwitchActive = r
              },
            },
          }),
          _ = z.actions,
          F = _.updateProfile,
          U = _.checkKillSwitch,
          q = _.setKillSwitch,
          G = z.name,
          M = z.reducer,
          D = function (e) {
            var t, r
            return null !== (t = e[G]) && void 0 !== t && t.killSwitchActive
              ? { firstName: 'kill-switch' }
              : null === (r = e[G]) || void 0 === r
              ? void 0
              : r.data
          },
          $ = r(96921),
          W = r(61173),
          H = r(18838),
          V = ['linius', 'heading']
        function K() {
          return (
            (K = Object.assign
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
            K.apply(this, arguments)
          )
        }
        var Y = function (e) {
          var t = e.linius,
            r = e.heading,
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
            })(e, V),
            i = (0, d.v9)(D)
          return o().createElement(
            s.xu,
            K(
              {
                className: 'linius-single',
                sx: {
                  transition: 'all ease-out 0.3s',
                  cursor: 'pointer',
                  '&:hover': { boxShadow: '0px 0px 10px 0 rgba(0,0,0,0.1)' },
                },
              },
              n
            ),
            o().createElement(
              s.xu,
              {
                sx: {
                  position: 'relative',
                  backgroundColor: 'grey-de',
                  backgroundImage: 'url('.concat((0, W.R)(t.image), ')'),
                  backgroundPosition: 'center',
                  backgroundSize: 'cover',
                  '::before': {
                    content: '""',
                    display: 'block',
                    width: '100%',
                    paddingBottom: '56.14%',
                    '.container.no-pad &': { paddingBottom: '64%' },
                  },
                  '::after': {
                    content: '""',
                    display: 'block',
                    position: 'absolute',
                    top: 0,
                    right: 0,
                    bottom: 0,
                    left: 0,
                    backgroundColor: i ? '' : 'rgba(0,0,0,0.4)',
                  },
                },
              },
              o().createElement(
                s.xu,
                {
                  sx: {
                    position: 'absolute',
                    top: '50%',
                    left: '50%',
                    transform: 'translate(-50%, -50%)',
                    zIndex: 1,
                    color: 'white',
                  },
                },
                i
                  ? o().createElement(H.Vd.VideoPlaylist, {
                      width: '32px',
                      height: '32px',
                    })
                  : o().createElement(s.Ee, {
                      src: H.RU.racingPlus,
                      sx: { width: '25px', height: '25px' },
                    })
              ),
              o().createElement(
                s.xv,
                {
                  sx: {
                    position: 'absolute',
                    top: 0,
                    right: 0,
                    backgroundColor: 'grey-66',
                    width: '40px',
                    height: '16px',
                    fontSize: 'sm',
                    color: 'white',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    zIndex: 1,
                  },
                },
                (0, $.LU)(t.duration)
              )
            ),
            o().createElement(
              s.xu,
              {
                sx: {
                  p: '12px',
                  fontSize: '12px',
                  lineHeight: 16 / 12,
                  fontFamily: 'roboto',
                },
              },
              o().createElement(
                s.xv,
                {
                  as: 'h3',
                  sx: {
                    fontSize: '12px',
                    fontWeight: 'bold',
                    transition: 'color ease-out 0.3s',
                    '.linius-single:hover &': { color: 'primary' },
                    mb: '10px',
                  },
                },
                r
              ),
              o().createElement(
                s.xv,
                { sx: { fontSize: '12px' } },
                'Last Start Replays (Last 400m)'
              )
            )
          )
        }
        Y.propTypes = {
          linius: u().object.isRequired,
          heading: u().string.isRequired,
        }
        const J = Y
        function Z(e, t) {
          ;(null == t || t > e.length) && (t = e.length)
          for (var r = 0, n = new Array(t); r < t; r++) n[r] = e[r]
          return n
        }
        var Q = function (e) {
          var t,
            r,
            i = e.race,
            c = ((t = (0, n.useContext)(a.cp)),
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
                    s = !0,
                    l = !1
                  try {
                    if (((i = (r = r.call(e)).next), 0 === t)) {
                      if (Object(r) !== r) return
                      s = !1
                    } else
                      for (
                        ;
                        !(s = (n = i.call(r)).done) &&
                        (c.push(n.value), c.length !== t);
                        s = !0
                      );
                  } catch (e) {
                    ;(l = !0), (o = e)
                  } finally {
                    try {
                      if (
                        !s &&
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
              })(t, r) ||
              (function (e, t) {
                if (e) {
                  if ('string' == typeof e) return Z(e, t)
                  var r = Object.prototype.toString.call(e).slice(8, -1)
                  return (
                    'Object' === r && e.constructor && (r = e.constructor.name),
                    'Map' === r || 'Set' === r
                      ? Array.from(e)
                      : 'Arguments' === r ||
                        /^(?:Ui|I)nt(?:8|16|32)(?:Clamped)?Array$/.test(r)
                      ? Z(e, t)
                      : void 0
                  )
                }
              })(t, r) ||
              (function () {
                throw new TypeError(
                  'Invalid attempt to destructure non-iterable instance.\nIn order to be iterable, non-array objects must have a [Symbol.iterator]() method.'
                )
              })())[0],
            l = (0, d.v9)(C),
            u = (0, d.v9)(P),
            f = (0, h.fO)().dispatch
          return (
            (0, n.useEffect)(
              function () {
                !u.single &&
                  null != c &&
                  c.meetCode &&
                  null != l &&
                  l.tipsterId &&
                  i.condition &&
                  i.raceCode &&
                  f(
                    S({
                      meetCode: c.meetCode,
                      tipsterId: l.tipsterId,
                      raceCode: i.raceCode,
                      condition: i.condition,
                    })
                  )
              },
              [c, l, i, u, f]
            ),
            u.single && u.multiple
              ? o().createElement(
                  s.kC,
                  { sx: { justifyContent: 'space-between' } },
                  o().createElement(J, {
                    flex: '0 0 auto',
                    width: 'calc((100% - 20px) / 2)',
                    linius: u.single,
                    heading: 'Form Analyst Selections Playlist',
                    onClick: function () {
                      ;(0, y.Iq)().then(function () {
                        var e, t
                        B(
                          'Form Analyst Selections Playlist',
                          ''.concat(c.meetCode, '/').concat(i.raceNumber)
                        ),
                          null === (e = window.rdc) ||
                            void 0 === e ||
                            null === (e = e.liniusReplay) ||
                            void 0 === e ||
                            null === (t = e.PlayLiniusReplay) ||
                            void 0 === t ||
                            t.call(e, {
                              data: u.single.data,
                              poster: u.single.image,
                            })
                      })
                    },
                  }),
                  o().createElement(J, {
                    flex: '0 0 auto',
                    width: 'calc((100% - 20px) / 2)',
                    linius: u.multiple,
                    heading: 'Full Field Playlist',
                    onClick: function () {
                      ;(0, y.Iq)().then(function () {
                        var e, t
                        B('Full Field Playlist', c.meetCode),
                          null === (e = window.rdc) ||
                            void 0 === e ||
                            null === (e = e.liniusReplay) ||
                            void 0 === e ||
                            null === (t = e.PlayLiniusReplay) ||
                            void 0 === t ||
                            t.call(e, {
                              data: u.multiple.data,
                              poster: u.multiple.image,
                            })
                      })
                    },
                  })
                )
              : o().createElement(m.Z, { loading: !0 })
          )
        }
        Q.propTypes = { race: u().object.isRequired }
        const X = Q
        var ee = r(90570),
          te = r(55834),
          re = r(56877),
          ne = r(70887)
        function oe(e, t) {
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
                  i,
                  a,
                  c = [],
                  s = !0,
                  l = !1
                try {
                  if (((i = (r = r.call(e)).next), 0 === t)) {
                    if (Object(r) !== r) return
                    s = !1
                  } else
                    for (
                      ;
                      !(s = (n = i.call(r)).done) &&
                      (c.push(n.value), c.length !== t);
                      s = !0
                    );
                } catch (e) {
                  ;(l = !0), (o = e)
                } finally {
                  try {
                    if (
                      !s &&
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
            })(e, t) ||
            (function (e, t) {
              if (e) {
                if ('string' == typeof e) return ie(e, t)
                var r = Object.prototype.toString.call(e).slice(8, -1)
                return (
                  'Object' === r && e.constructor && (r = e.constructor.name),
                  'Map' === r || 'Set' === r
                    ? Array.from(e)
                    : 'Arguments' === r ||
                      /^(?:Ui|I)nt(?:8|16|32)(?:Clamped)?Array$/.test(r)
                    ? ie(e, t)
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
        function ie(e, t) {
          ;(null == t || t > e.length) && (t = e.length)
          for (var r = 0, n = new Array(t); r < t; r++) n[r] = e[r]
          return n
        }
        var ae = function (e) {
          var t = e.raceEntry,
            r = oe((0, n.useContext)(a.cp), 1)[0],
            i = oe((0, n.useContext)(a.Rl), 1)[0],
            c = (0, n.useContext)(a.$f).provider,
            s = (0, d.v9)(R)
          return (
            (0, n.useEffect)(function () {}, []),
            o().createElement(ee.ZP, {
              raceEntry: t,
              suggestedBets: s,
              betAction: function () {
                if (
                  t.isScratched ||
                  !(r && i && (0, ne.J)(i.raceStatus, 'not_started'))
                )
                  return null
                switch (c) {
                  case 'beteasy':
                    return t.winPriceBE
                      ? o().createElement(re.I, { winPrice: t.winPriceBE })
                      : null
                  case 'sportsbet':
                    return t.winPriceSB2
                      ? o().createElement(re.I, { winPrice: t.winPriceSB2 })
                      : null
                  default:
                    return null
                }
              },
            })
          )
        }
        ae.propTypes = { raceEntry: u().object.isRequired }
        const ce = ae
        var se = ['label', 'active'],
          le = ['race']
        function ue(e, t) {
          ;(null == t || t > e.length) && (t = e.length)
          for (var r = 0, n = new Array(t); r < t; r++) n[r] = e[r]
          return n
        }
        function fe() {
          return (
            (fe = Object.assign
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
            fe.apply(this, arguments)
          )
        }
        function pe(e, t) {
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
        var de = function (e) {
          var t = e.label,
            r = e.active,
            n = pe(e, se)
          return o().createElement(
            s.xu,
            fe(
              {
                sx: {
                  borderBottom: '2px solid',
                  borderBottomColor: r ? 'grey-33' : 'transparent',
                  transition: 'border-bottom-color ease-out 0.2s',
                  fontFamily: 'circular',
                  fontWeight: 'bold',
                  fontSize: '12px',
                  lineHeight: '20px',
                  ml: 'lg',
                  cursor: 'pointer',
                },
              },
              n
            ),
            t
          )
        }
        de.propTypes = { label: u().string.isRequired, active: u().bool }
        var me = function (e) {
          var t,
            r,
            i = e.race,
            c = pe(e, le),
            l = (0, d.v9)(C),
            u = (0, ee.YG)(i, { sort: !1 }),
            f = u.raceEntries,
            p = u.suggestedBets,
            m =
              ((t = (0, n.useState)('selections')),
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
                      s = !0,
                      l = !1
                    try {
                      if (((i = (r = r.call(e)).next), 0 === t)) {
                        if (Object(r) !== r) return
                        s = !1
                      } else
                        for (
                          ;
                          !(s = (n = i.call(r)).done) &&
                          (c.push(n.value), c.length !== t);
                          s = !0
                        );
                    } catch (e) {
                      ;(l = !0), (o = e)
                    } finally {
                      try {
                        if (
                          !s &&
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
                })(t, r) ||
                (function (e, t) {
                  if (e) {
                    if ('string' == typeof e) return ue(e, t)
                    var r = Object.prototype.toString.call(e).slice(8, -1)
                    return (
                      'Object' === r &&
                        e.constructor &&
                        (r = e.constructor.name),
                      'Map' === r || 'Set' === r
                        ? Array.from(e)
                        : 'Arguments' === r ||
                          /^(?:Ui|I)nt(?:8|16|32)(?:Clamped)?Array$/.test(r)
                        ? ue(e, t)
                        : void 0
                    )
                  }
                })(t, r) ||
                (function () {
                  throw new TypeError(
                    'Invalid attempt to destructure non-iterable instance.\nIn order to be iterable, non-array objects must have a [Symbol.iterator]() method.'
                  )
                })()),
            h = m[0],
            y = m[1]
          return o().createElement(
            a.Rl.Provider,
            { value: [i] },
            o().createElement(
              s.xu,
              fe(
                {
                  className: 'race-card  race-card--form-analyst-tips',
                  sx: { position: 'relative', '&:hover': { zIndex: 1 } },
                },
                c
              ),
              o().createElement(
                s.kC,
                {
                  className: 'race-card__banner',
                  sx: {
                    padding: '0 4px 8px',
                    alignItems: 'center',
                    justifyContent: 'flex-start',
                    borderBottom: '1px solid',
                    borderBottomColor: 'grey-de',
                  },
                },
                o().createElement(te.Z, {
                  src: null == l ? void 0 : l.profileImageUrl,
                  sx: {
                    flex: '0 0 auto',
                    borderRadius: '50%',
                    marginRight: 'md',
                    backgroundColor: 'grey-de',
                    border: 'none',
                    width: '30px',
                    height: '30px',
                  },
                }),
                o().createElement(
                  s.kC,
                  { sx: { flex: '1 1 auto', flexDirection: 'column' } },
                  o().createElement(
                    s.xv,
                    {
                      sx: {
                        fontSize: '12px',
                        lineHeight: '18px',
                        fontFamily: 'roboto',
                        fontWeight: 'bold',
                      },
                    },
                    l.tipsterName
                  ),
                  o().createElement(
                    s.xu,
                    { sx: { color: 'primary', mb: '2px' } },
                    o().createElement(H.Vd.FormAnalystColor, {
                      width: '59px',
                      height: '13px',
                    })
                  )
                ),
                (i.comment || p.length > 0) &&
                  o().createElement(
                    s.kC,
                    { sx: { flex: '0 0 auto', mr: '4px' } },
                    o().createElement(de, {
                      label: 'Selections',
                      active: 'selections' === h,
                      onClick: function () {
                        B('Change Tab', 'selections'), y('selections')
                      },
                    }),
                    o().createElement(de, {
                      label: 'Analysis',
                      active: 'analysis' === h,
                      onClick: function () {
                        B('Change Tab', 'analysis'), y('analysis')
                      },
                    })
                  )
              ),
              'selections' === h &&
                f.map(function (e) {
                  return o().createElement(
                    s.xu,
                    {
                      key: e.outcomeId,
                      sx: {
                        borderBottom: '1px solid',
                        borderBottomColor: 'grey-de',
                      },
                    },
                    o().createElement(ce, { raceEntry: e })
                  )
                }),
              'analysis' === h &&
                o().createElement(
                  s.xu,
                  { sx: { fontSize: 'body', p: '8px 12px' } },
                  i.comment &&
                    o().createElement(
                      s.xv,
                      null,
                      o().createElement('b', null, 'Overview:'),
                      ' ',
                      i.comment
                    ),
                  p.length > 0 &&
                    o().createElement(
                      s.xv,
                      null,
                      o().createElement('b', null, 'Suggested Bet:'),
                      ' ',
                      p
                        .map(function (e) {
                          return ''
                            .concat(e.horseName, ' (')
                            .concat((0, $.Tk)(e.tipBetType), ')')
                        })
                        .join(' & ')
                    )
                )
            )
          )
        }
        me.propTypes = { race: u().object.isRequired }
        const he = me
        var ye = r(84063),
          ve = r.n(ye),
          ge = r(7e4),
          be = r.n(ge),
          je = r(60918),
          we = r.n(je),
          xe = r(8816),
          Ee = r.n(xe),
          ke = r(40104),
          Oe = r.n(ke)
        function Se(e, t) {
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
                  i,
                  a,
                  c = [],
                  s = !0,
                  l = !1
                try {
                  if (((i = (r = r.call(e)).next), 0 === t)) {
                    if (Object(r) !== r) return
                    s = !1
                  } else
                    for (
                      ;
                      !(s = (n = i.call(r)).done) &&
                      (c.push(n.value), c.length !== t);
                      s = !0
                    );
                } catch (e) {
                  ;(l = !0), (o = e)
                } finally {
                  try {
                    if (
                      !s &&
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
            })(e, t) ||
            (function (e, t) {
              if (e) {
                if ('string' == typeof e) return Ie(e, t)
                var r = Object.prototype.toString.call(e).slice(8, -1)
                return (
                  'Object' === r && e.constructor && (r = e.constructor.name),
                  'Map' === r || 'Set' === r
                    ? Array.from(e)
                    : 'Arguments' === r ||
                      /^(?:Ui|I)nt(?:8|16|32)(?:Clamped)?Array$/.test(r)
                    ? Ie(e, t)
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
        function Ie(e, t) {
          ;(null == t || t > e.length) && (t = e.length)
          for (var r = 0, n = new Array(t); r < t; r++) n[r] = e[r]
          return n
        }
        var Le,
          Ne,
          Ce = r(27422),
          Pe = r(38847),
          Te = r(1349),
          Ae = r(67834)
        function Re(e, t) {
          return (
            t || (t = e.slice(0)),
            Object.freeze(
              Object.defineProperties(e, { raw: { value: Object.freeze(t) } })
            )
          )
        }
        var Be = (0, Ae.Ps)(
            Le ||
              (Le = Re([
                '\n  fragment bestRaceEntryItem on BestRaceEntryItem {\n    comment\n    raceEntryItem {\n      outcomeId: raceEntryNumber\n      raceNumber\n      horse {\n        name\n      }\n      horseCode\n      silkUrl\n    }\n  }\n',
              ]))
          ),
          ze = (0, Ae.Ps)(
            Ne ||
              (Ne = Re([
                '\n  query CDGetRaceForFormAnalyst($meetCode: ID!, $raceNumber: Int!) {\n    raceForm: getRaceForm(meetCode: $meetCode, raceNumber: $raceNumber) {\n      raceCode: id\n      raceNumber\n      raceName: name\n      raceStatus: status\n      condition: trackCondition\n      raceTips {\n        comment\n        condition\n        tipster {\n          tipsterId\n          tipsterName\n          profileImageUrl\n          isLead\n        }\n        tips {\n          raceEntryItem {\n            outcomeId: raceEntryNumber\n            barrierNumber\n            horseName\n            jockeyName\n            jockey {\n              initials\n              surname\n            }\n            trainerName\n            trainer {\n              initials\n              surname\n            }\n            position\n            isScratched: scratched\n            silkUrl\n            highlights: faisHighlight {\n              key\n              positive\n            }\n          }\n          tipBetType\n        }\n      }\n      meet {\n        meetUrl\n        meetTips {\n          tipComment\n          tipster {\n            tipsterId\n            tipsterName\n            profileImageUrl\n            isLead\n          }\n          bestBet {\n            ...bestRaceEntryItem\n          }\n          bestValue {\n            ...bestRaceEntryItem\n          }\n          bestRoughie {\n            ...bestRaceEntryItem\n          }\n        }\n      }\n    }\n  }\n  ',
                '\n',
              ])),
            Be
          )
        function _e(e) {
          return (
            (_e =
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
            _e(e)
          )
        }
        function Fe(e, t) {
          ;(null == t || t > e.length) && (t = e.length)
          for (var r = 0, n = new Array(t); r < t; r++) n[r] = e[r]
          return n
        }
        function Ue() {
          Ue = function () {
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
          function l(e, t, r) {
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
            l({}, '')
          } catch (e) {
            l = function (e, t, r) {
              return (e[t] = r)
            }
          }
          function u(e, t, r, n) {
            var i = t && t.prototype instanceof v ? t : v,
              a = Object.create(i.prototype),
              c = new C(n || [])
            return o(a, '_invoke', { value: S(e, r, c) }), a
          }
          function f(e, t, r) {
            try {
              return { type: 'normal', arg: e.call(t, r) }
            } catch (e) {
              return { type: 'throw', arg: e }
            }
          }
          t.wrap = u
          var p = 'suspendedStart',
            d = 'suspendedYield',
            m = 'executing',
            h = 'completed',
            y = {}
          function v() {}
          function g() {}
          function b() {}
          var j = {}
          l(j, a, function () {
            return this
          })
          var w = Object.getPrototypeOf,
            x = w && w(w(P([])))
          x && x !== r && n.call(x, a) && (j = x)
          var E = (b.prototype = v.prototype = Object.create(j))
          function k(e) {
            ;['next', 'throw', 'return'].forEach(function (t) {
              l(e, t, function (e) {
                return this._invoke(t, e)
              })
            })
          }
          function O(e, t) {
            function r(o, i, a, c) {
              var s = f(e[o], e, i)
              if ('throw' !== s.type) {
                var l = s.arg,
                  u = l.value
                return u && 'object' == _e(u) && n.call(u, '__await')
                  ? t.resolve(u.__await).then(
                      function (e) {
                        r('next', e, a, c)
                      },
                      function (e) {
                        r('throw', e, a, c)
                      }
                    )
                  : t.resolve(u).then(
                      function (e) {
                        ;(l.value = e), a(l)
                      },
                      function (e) {
                        return r('throw', e, a, c)
                      }
                    )
              }
              c(s.arg)
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
          function S(t, r, n) {
            var o = p
            return function (i, a) {
              if (o === m) throw new Error('Generator is already running')
              if (o === h) {
                if ('throw' === i) throw a
                return { value: e, done: !0 }
              }
              for (n.method = i, n.arg = a; ; ) {
                var c = n.delegate
                if (c) {
                  var s = I(c, n)
                  if (s) {
                    if (s === y) continue
                    return s
                  }
                }
                if ('next' === n.method) n.sent = n._sent = n.arg
                else if ('throw' === n.method) {
                  if (o === p) throw ((o = h), n.arg)
                  n.dispatchException(n.arg)
                } else 'return' === n.method && n.abrupt('return', n.arg)
                o = m
                var l = f(t, r, n)
                if ('normal' === l.type) {
                  if (((o = n.done ? h : d), l.arg === y)) continue
                  return { value: l.arg, done: n.done }
                }
                'throw' === l.type &&
                  ((o = h), (n.method = 'throw'), (n.arg = l.arg))
              }
            }
          }
          function I(t, r) {
            var n = r.method,
              o = t.iterator[n]
            if (o === e)
              return (
                (r.delegate = null),
                ('throw' === n &&
                  t.iterator.return &&
                  ((r.method = 'return'),
                  (r.arg = e),
                  I(t, r),
                  'throw' === r.method)) ||
                  ('return' !== n &&
                    ((r.method = 'throw'),
                    (r.arg = new TypeError(
                      "The iterator does not provide a '" + n + "' method"
                    )))),
                y
              )
            var i = f(o, t.iterator, r.arg)
            if ('throw' === i.type)
              return (
                (r.method = 'throw'), (r.arg = i.arg), (r.delegate = null), y
              )
            var a = i.arg
            return a
              ? a.done
                ? ((r[t.resultName] = a.value),
                  (r.next = t.nextLoc),
                  'return' !== r.method && ((r.method = 'next'), (r.arg = e)),
                  (r.delegate = null),
                  y)
                : a
              : ((r.method = 'throw'),
                (r.arg = new TypeError('iterator result is not an object')),
                (r.delegate = null),
                y)
          }
          function L(e) {
            var t = { tryLoc: e[0] }
            1 in e && (t.catchLoc = e[1]),
              2 in e && ((t.finallyLoc = e[2]), (t.afterLoc = e[3])),
              this.tryEntries.push(t)
          }
          function N(e) {
            var t = e.completion || {}
            ;(t.type = 'normal'), delete t.arg, (e.completion = t)
          }
          function C(e) {
            ;(this.tryEntries = [{ tryLoc: 'root' }]),
              e.forEach(L, this),
              this.reset(!0)
          }
          function P(t) {
            if (t || '' === t) {
              var r = t[a]
              if (r) return r.call(t)
              if ('function' == typeof t.next) return t
              if (!isNaN(t.length)) {
                var o = -1,
                  i = function r() {
                    for (; ++o < t.length; )
                      if (n.call(t, o))
                        return (r.value = t[o]), (r.done = !1), r
                    return (r.value = e), (r.done = !0), r
                  }
                return (i.next = i)
              }
            }
            throw new TypeError(_e(t) + ' is not iterable')
          }
          return (
            (g.prototype = b),
            o(E, 'constructor', { value: b, configurable: !0 }),
            o(b, 'constructor', { value: g, configurable: !0 }),
            (g.displayName = l(b, s, 'GeneratorFunction')),
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
                  ? Object.setPrototypeOf(e, b)
                  : ((e.__proto__ = b), l(e, s, 'GeneratorFunction')),
                (e.prototype = Object.create(E)),
                e
              )
            }),
            (t.awrap = function (e) {
              return { __await: e }
            }),
            k(O.prototype),
            l(O.prototype, c, function () {
              return this
            }),
            (t.AsyncIterator = O),
            (t.async = function (e, r, n, o, i) {
              void 0 === i && (i = Promise)
              var a = new O(u(e, r, n, o), i)
              return t.isGeneratorFunction(r)
                ? a
                : a.next().then(function (e) {
                    return e.done ? e.value : a.next()
                  })
            }),
            k(E),
            l(E, s, 'Generator'),
            l(E, a, function () {
              return this
            }),
            l(E, 'toString', function () {
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
            (t.values = P),
            (C.prototype = {
              constructor: C,
              reset: function (t) {
                if (
                  ((this.prev = 0),
                  (this.next = 0),
                  (this.sent = this._sent = e),
                  (this.done = !1),
                  (this.delegate = null),
                  (this.method = 'next'),
                  (this.arg = e),
                  this.tryEntries.forEach(N),
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
                    var s = n.call(a, 'catchLoc'),
                      l = n.call(a, 'finallyLoc')
                    if (s && l) {
                      if (this.prev < a.catchLoc) return o(a.catchLoc, !0)
                      if (this.prev < a.finallyLoc) return o(a.finallyLoc)
                    } else if (s) {
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
                    ? ((this.method = 'next'), (this.next = i.finallyLoc), y)
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
                  y
                )
              },
              finish: function (e) {
                for (var t = this.tryEntries.length - 1; t >= 0; --t) {
                  var r = this.tryEntries[t]
                  if (r.finallyLoc === e)
                    return this.complete(r.completion, r.afterLoc), N(r), y
                }
              },
              catch: function (e) {
                for (var t = this.tryEntries.length - 1; t >= 0; --t) {
                  var r = this.tryEntries[t]
                  if (r.tryLoc === e) {
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
              delegateYield: function (t, r, n) {
                return (
                  (this.delegate = {
                    iterator: P(t),
                    resultName: r,
                    nextLoc: n,
                  }),
                  'next' === this.method && (this.arg = e),
                  y
                )
              },
            }),
            t
          )
        }
        var qe = Ue().mark(He),
          Ge = Ue().mark(Ve),
          Me = Ue().mark(Ke),
          De = Ue().mark(Ye),
          $e = function (e) {
            return [
              'Interim',
              'Final Results',
              'Paying',
              'Abandoned',
              'Results',
            ].find(function (t) {
              return (0, ne.J)(t, e)
            })
              ? 'completed'
              : 'not_started'
          }
        function We(e, t) {
          var r
          if (!t || !t.raceEntryItem) return null
          var n = t.raceEntryItem
          return {
            type: e,
            raceNumber: n.raceNumber,
            comment: t.comment,
            horse: {
              name: null === (r = n.horse) || void 0 === r ? void 0 : r.name,
              outcomeId: n.outcomeId,
            },
          }
        }
        function He(e) {
          var t, r, n, o, i, a, c, s, l, u, f, p, d, m, h, y, v, g
          return Ue().wrap(function (b) {
            for (;;)
              switch ((b.prev = b.next)) {
                case 0:
                  return (
                    (t = e.payload),
                    (r = t.meetCode),
                    (n = t.raceNumber),
                    (b.next = 3),
                    (0, Ce.RE)(Pe.I, {
                      query: ze,
                      variables: { meetCode: r, raceNumber: n },
                      context: { useChampionData: !0 },
                    })
                  )
                case 3:
                  if (((o = b.sent), (i = o.data), !(a = i.raceForm))) {
                    b.next = 24
                    break
                  }
                  if (
                    ((l = a.raceTips),
                    (u = l.find(function (e) {
                      var t
                      return null === (t = e.tipster) || void 0 === t
                        ? void 0
                        : t.isLead
                    })),
                    (f = null == u ? void 0 : u.tipster))
                  ) {
                    b.next = 13
                    break
                  }
                  return console.warn('No lead tipster'), b.abrupt('return')
                case 13:
                  return (b.next = 15), (0, Ce.gz)(w({ tipster: f }))
                case 15:
                  return (
                    (p = a.condition),
                    (b.next = 18),
                    (0, Ce.gz)(E({ trackInformation: { condition: p } }))
                  )
                case 18:
                  return (
                    (d = []),
                    (m =
                      null === (c = a.meet) ||
                      void 0 === c ||
                      null === (c = c.meetTips) ||
                      void 0 === c
                        ? void 0
                        : c.find(function (e) {
                            var t
                            return null === (t = e.tipster) || void 0 === t
                              ? void 0
                              : t.isLead
                          })) &&
                      ((h = m.bestBet),
                      (y = m.bestValue),
                      (v = m.bestRoughie),
                      d.push(We('BEST_BET', h)),
                      d.push(We('BEST_VALUE', y)),
                      d.push(We('BEST_ROUGHIE', v))),
                    (g =
                      null === (s = a.raceTips) || void 0 === s
                        ? void 0
                        : s
                            .filter(function (e) {
                              var t
                              return null === (t = e.tipster) || void 0 === t
                                ? void 0
                                : t.isLead
                            })
                            .map(function (e) {
                              var t
                              return {
                                raceCode: a.raceCode,
                                raceNumber: a.raceNumber,
                                raceName: a.raceName,
                                raceStatus: $e(a.raceStatus),
                                condition: e.condition,
                                comment: e.comment,
                                selections:
                                  null == e ||
                                  null === (t = e.tips) ||
                                  void 0 === t
                                    ? void 0
                                    : t.map(function (e) {
                                        var t,
                                          r,
                                          n,
                                          o,
                                          i,
                                          a = e.tipBetType,
                                          c = e.raceEntryItem
                                        return {
                                          barrierNumber: c.barrierNumber,
                                          horseName: c.horseName,
                                          jockeyName: c.jockeyName,
                                          jockeyInitials:
                                            null === (t = c.jockey) ||
                                            void 0 === t
                                              ? void 0
                                              : t.initials,
                                          jockeySurname:
                                            null === (r = c.jockey) ||
                                            void 0 === r
                                              ? void 0
                                              : r.surname,
                                          trainerName: c.trainerName,
                                          trainerInitials:
                                            null === (n = c.trainer) ||
                                            void 0 === n
                                              ? void 0
                                              : n.initials,
                                          trainerSurname:
                                            null === (o = c.trainer) ||
                                            void 0 === o
                                              ? void 0
                                              : o.surname,
                                          position: c.position,
                                          isScratched: c.isScratched,
                                          highlights:
                                            null === (i = c.highlights) ||
                                            void 0 === i
                                              ? void 0
                                              : i.filter(function (e) {
                                                  return -1 !== e.key
                                                }),
                                          outcomeId: c.outcomeId,
                                          silkUrl: c.silkUrl,
                                          tipBetType: a,
                                        }
                                      }),
                              }
                            })),
                    (b.next = 24),
                    (0, Ce.gz)(
                      x({
                        tipsterId: f.tipsterId,
                        suggestedBets: d.filter(Boolean),
                        tippingInformation: g,
                      })
                    )
                  )
                case 24:
                case 'end':
                  return b.stop()
              }
          }, qe)
        }
        function Ve(e) {
          var t, r, n, o, i, a
          return Ue().wrap(function (c) {
            for (;;)
              switch ((c.prev = c.next)) {
                case 0:
                  return (
                    (t = e.payload),
                    (r = t.raceNumber),
                    (n = t.meetCode),
                    (c.next = 3),
                    (0, Ce.RE)(
                      Te.NA.get,
                      '/TAB/details/'.concat(n, '/').concat(r)
                    )
                  )
                case 3:
                  return (
                    (o = c.sent),
                    (i = o.data),
                    (a = i.TabRace.runners.map(function (e) {
                      var t,
                        r,
                        n =
                          null === (t = e.odds) || void 0 === t
                            ? void 0
                            : t.find(function (e) {
                                return 'BE' === e.provider
                              }),
                        o =
                          null === (r = e.odds) || void 0 === r
                            ? void 0
                            : r.find(function (e) {
                                return 'SB2' === e.provider
                              })
                      return {
                        outcomeId: e.runnerNumber,
                        winPriceBE: n && {
                          fixedMarketId: n.fixedMarketId,
                          price: n.returnWin,
                          url: n.winUrl,
                        },
                        winPriceSB2: o && { price: o.returnWin, url: o.winUrl },
                      }
                    })),
                    (c.next = 8),
                    (0, Ce.gz)(O({ raceNumber: r, raceEntries: a }))
                  )
                case 8:
                case 'end':
                  return c.stop()
              }
          }, Ge)
        }
        function Ke(e) {
          var t, r, n, o, i, a, c, s, l, u, f
          return Ue().wrap(function (p) {
            for (;;)
              switch ((p.prev = p.next)) {
                case 0:
                  return (
                    (t = e.payload),
                    (r = t.meetCode),
                    (n = t.tipsterId),
                    (o = t.raceCode),
                    (i = t.condition),
                    (p.next = 3),
                    (0, Ce.$6)([
                      (0, Ce.RE)(Te.w$.get, '/playlist', {
                        params: {
                          condition: i.replace(/\s/g, ''),
                          meetcode: r,
                          racecode: o,
                          tipsterid: n,
                          lws_token: '',
                        },
                      }),
                      (0, Ce.RE)(Te.w$.get, '/playlist', {
                        params: {
                          condition: 'AnyCondition',
                          tipsterid: 'racing',
                          meetcode: r,
                          racecode: o,
                          lws_token: '',
                        },
                      }),
                    ])
                  )
                case 3:
                  return (
                    (a = p.sent),
                    (m = 2),
                    (c =
                      (function (e) {
                        if (Array.isArray(e)) return e
                      })((d = a)) ||
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
                            s = !0,
                            l = !1
                          try {
                            if (((i = (r = r.call(e)).next), 0 === t)) {
                              if (Object(r) !== r) return
                              s = !1
                            } else
                              for (
                                ;
                                !(s = (n = i.call(r)).done) &&
                                (c.push(n.value), c.length !== t);
                                s = !0
                              );
                          } catch (e) {
                            ;(l = !0), (o = e)
                          } finally {
                            try {
                              if (
                                !s &&
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
                      })(d, m) ||
                      (function (e, t) {
                        if (e) {
                          if ('string' == typeof e) return Fe(e, t)
                          var r = Object.prototype.toString.call(e).slice(8, -1)
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
                              ? Fe(e, t)
                              : void 0
                          )
                        }
                      })(d, m) ||
                      (function () {
                        throw new TypeError(
                          'Invalid attempt to destructure non-iterable instance.\nIn order to be iterable, non-array objects must have a [Symbol.iterator]() method.'
                        )
                      })()),
                    (s = c[0]),
                    (l = c[1]),
                    (u = {
                      data: s.data,
                      image: s.headers['x-play-initial-poster'],
                      duration: s.headers['x-play-content-length'],
                    }),
                    (f = {
                      data: l.data,
                      image: l.headers['x-play-initial-poster'],
                      duration: l.headers['x-play-content-length'],
                    }),
                    (p.next = 11),
                    (0, Ce.gz)(I({ single: u, multiple: f }))
                  )
                case 11:
                case 'end':
                  return p.stop()
              }
            var d, m
          }, Me)
        }
        function Ye() {
          return Ue().wrap(function (e) {
            for (;;)
              switch ((e.prev = e.next)) {
                case 0:
                  return (e.next = 2), (0, h.W0)(j.type, He)
                case 2:
                  return (e.next = 4), (0, h.W0)(k.type, Ve)
                case 4:
                  return (e.next = 6), (0, h.W0)(S.type, Ke)
                case 6:
                case 'end':
                  return e.stop()
              }
          }, De)
        }
        var Je = function (e) {
          var t = e.raceNumber
          ;(0, f.vp)({ key: L, reducer: N }),
            (0, f.hb)({ key: L, saga: Ye }),
            (function (e) {
              var t = (0, h.fO)().dispatch,
                r = Se((0, n.useContext)(a.cp), 1)[0],
                o = (0, d.v9)(A)
              ;(0, n.useEffect)(
                function () {
                  var n,
                    i =
                      null == o
                        ? void 0
                        : o.find(function (t) {
                            return t.raceNumber === e
                          })
                  null != i &&
                    null !== (n = i.selections) &&
                    void 0 !== n &&
                    n.find(function (e) {
                      return !e.winPriceBE
                    }) &&
                    t(
                      k({
                        meetCode: null == r ? void 0 : r.meetCode,
                        raceNumber: e,
                      })
                    )
                },
                [t, r, e, o]
              )
            })(t),
            (function (e) {
              var t = Se((0, n.useContext)(a.cp), 1)[0],
                r = (0, h.fO)().dispatch
              ;(0, n.useEffect)(
                function () {
                  if (t && e) {
                    var n = t.meetCode
                    r(j({ meetCode: n, raceNumber: e })).catch(function (e) {
                      return console.warn(e)
                    })
                  }
                },
                [t, e, r]
              )
            })(t)
          var r = (function (e) {
            var t = (0, d.v9)(A),
              r = (0, d.v9)(T)
            return (0, n.useMemo)(
              function () {
                return Ee()([
                  we()('raceNumber', 'asc'),
                  Oe()(function (e) {
                    var t,
                      n =
                        null == r || null === (t = r.condition) || void 0 === t
                          ? void 0
                          : t.split(' ')[0]
                    return (
                      (0, ne.J)(e.condition, 'Any Condition') ||
                      (0, ne.J)(e.condition, n)
                    )
                  }),
                  be()('raceNumber'),
                  ve()(function (t) {
                    return t.raceNumber === e
                  }),
                ])(t)
              },
              [t, r, e]
            )
          })(t)
          return (0, p.Ln)() && r
            ? o().createElement(
                s.kC,
                {
                  sx: {
                    alignItems: 'stretch',
                    justifyContent: 'space-between',
                  },
                },
                o().createElement(
                  s.xu,
                  {
                    sx: {
                      flex: '0 0 auto',
                      width: 'calc((100% - 20px) / 2)',
                      minHeight: '218px',
                    },
                  },
                  o().createElement(he, { race: r })
                ),
                o().createElement(
                  s.xu,
                  {
                    sx: {
                      position: 'relative',
                      flex: '0 0 auto',
                      width: 'calc((100% - 20px) / 2)',
                    },
                  },
                  o().createElement(X, { race: r })
                )
              )
            : null
        }
        Je.propTypes = { raceNumber: u().number.isRequired }
        const Ze = Je
        function Qe(e) {
          return (
            (Qe =
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
            Qe(e)
          )
        }
        function Xe() {
          Xe = function () {
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
          function l(e, t, r) {
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
            l({}, '')
          } catch (e) {
            l = function (e, t, r) {
              return (e[t] = r)
            }
          }
          function u(e, t, r, n) {
            var i = t && t.prototype instanceof v ? t : v,
              a = Object.create(i.prototype),
              c = new C(n || [])
            return o(a, '_invoke', { value: S(e, r, c) }), a
          }
          function f(e, t, r) {
            try {
              return { type: 'normal', arg: e.call(t, r) }
            } catch (e) {
              return { type: 'throw', arg: e }
            }
          }
          t.wrap = u
          var p = 'suspendedStart',
            d = 'suspendedYield',
            m = 'executing',
            h = 'completed',
            y = {}
          function v() {}
          function g() {}
          function b() {}
          var j = {}
          l(j, a, function () {
            return this
          })
          var w = Object.getPrototypeOf,
            x = w && w(w(P([])))
          x && x !== r && n.call(x, a) && (j = x)
          var E = (b.prototype = v.prototype = Object.create(j))
          function k(e) {
            ;['next', 'throw', 'return'].forEach(function (t) {
              l(e, t, function (e) {
                return this._invoke(t, e)
              })
            })
          }
          function O(e, t) {
            function r(o, i, a, c) {
              var s = f(e[o], e, i)
              if ('throw' !== s.type) {
                var l = s.arg,
                  u = l.value
                return u && 'object' == Qe(u) && n.call(u, '__await')
                  ? t.resolve(u.__await).then(
                      function (e) {
                        r('next', e, a, c)
                      },
                      function (e) {
                        r('throw', e, a, c)
                      }
                    )
                  : t.resolve(u).then(
                      function (e) {
                        ;(l.value = e), a(l)
                      },
                      function (e) {
                        return r('throw', e, a, c)
                      }
                    )
              }
              c(s.arg)
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
          function S(t, r, n) {
            var o = p
            return function (i, a) {
              if (o === m) throw new Error('Generator is already running')
              if (o === h) {
                if ('throw' === i) throw a
                return { value: e, done: !0 }
              }
              for (n.method = i, n.arg = a; ; ) {
                var c = n.delegate
                if (c) {
                  var s = I(c, n)
                  if (s) {
                    if (s === y) continue
                    return s
                  }
                }
                if ('next' === n.method) n.sent = n._sent = n.arg
                else if ('throw' === n.method) {
                  if (o === p) throw ((o = h), n.arg)
                  n.dispatchException(n.arg)
                } else 'return' === n.method && n.abrupt('return', n.arg)
                o = m
                var l = f(t, r, n)
                if ('normal' === l.type) {
                  if (((o = n.done ? h : d), l.arg === y)) continue
                  return { value: l.arg, done: n.done }
                }
                'throw' === l.type &&
                  ((o = h), (n.method = 'throw'), (n.arg = l.arg))
              }
            }
          }
          function I(t, r) {
            var n = r.method,
              o = t.iterator[n]
            if (o === e)
              return (
                (r.delegate = null),
                ('throw' === n &&
                  t.iterator.return &&
                  ((r.method = 'return'),
                  (r.arg = e),
                  I(t, r),
                  'throw' === r.method)) ||
                  ('return' !== n &&
                    ((r.method = 'throw'),
                    (r.arg = new TypeError(
                      "The iterator does not provide a '" + n + "' method"
                    )))),
                y
              )
            var i = f(o, t.iterator, r.arg)
            if ('throw' === i.type)
              return (
                (r.method = 'throw'), (r.arg = i.arg), (r.delegate = null), y
              )
            var a = i.arg
            return a
              ? a.done
                ? ((r[t.resultName] = a.value),
                  (r.next = t.nextLoc),
                  'return' !== r.method && ((r.method = 'next'), (r.arg = e)),
                  (r.delegate = null),
                  y)
                : a
              : ((r.method = 'throw'),
                (r.arg = new TypeError('iterator result is not an object')),
                (r.delegate = null),
                y)
          }
          function L(e) {
            var t = { tryLoc: e[0] }
            1 in e && (t.catchLoc = e[1]),
              2 in e && ((t.finallyLoc = e[2]), (t.afterLoc = e[3])),
              this.tryEntries.push(t)
          }
          function N(e) {
            var t = e.completion || {}
            ;(t.type = 'normal'), delete t.arg, (e.completion = t)
          }
          function C(e) {
            ;(this.tryEntries = [{ tryLoc: 'root' }]),
              e.forEach(L, this),
              this.reset(!0)
          }
          function P(t) {
            if (t || '' === t) {
              var r = t[a]
              if (r) return r.call(t)
              if ('function' == typeof t.next) return t
              if (!isNaN(t.length)) {
                var o = -1,
                  i = function r() {
                    for (; ++o < t.length; )
                      if (n.call(t, o))
                        return (r.value = t[o]), (r.done = !1), r
                    return (r.value = e), (r.done = !0), r
                  }
                return (i.next = i)
              }
            }
            throw new TypeError(Qe(t) + ' is not iterable')
          }
          return (
            (g.prototype = b),
            o(E, 'constructor', { value: b, configurable: !0 }),
            o(b, 'constructor', { value: g, configurable: !0 }),
            (g.displayName = l(b, s, 'GeneratorFunction')),
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
                  ? Object.setPrototypeOf(e, b)
                  : ((e.__proto__ = b), l(e, s, 'GeneratorFunction')),
                (e.prototype = Object.create(E)),
                e
              )
            }),
            (t.awrap = function (e) {
              return { __await: e }
            }),
            k(O.prototype),
            l(O.prototype, c, function () {
              return this
            }),
            (t.AsyncIterator = O),
            (t.async = function (e, r, n, o, i) {
              void 0 === i && (i = Promise)
              var a = new O(u(e, r, n, o), i)
              return t.isGeneratorFunction(r)
                ? a
                : a.next().then(function (e) {
                    return e.done ? e.value : a.next()
                  })
            }),
            k(E),
            l(E, s, 'Generator'),
            l(E, a, function () {
              return this
            }),
            l(E, 'toString', function () {
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
            (t.values = P),
            (C.prototype = {
              constructor: C,
              reset: function (t) {
                if (
                  ((this.prev = 0),
                  (this.next = 0),
                  (this.sent = this._sent = e),
                  (this.done = !1),
                  (this.delegate = null),
                  (this.method = 'next'),
                  (this.arg = e),
                  this.tryEntries.forEach(N),
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
                    var s = n.call(a, 'catchLoc'),
                      l = n.call(a, 'finallyLoc')
                    if (s && l) {
                      if (this.prev < a.catchLoc) return o(a.catchLoc, !0)
                      if (this.prev < a.finallyLoc) return o(a.finallyLoc)
                    } else if (s) {
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
                    ? ((this.method = 'next'), (this.next = i.finallyLoc), y)
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
                  y
                )
              },
              finish: function (e) {
                for (var t = this.tryEntries.length - 1; t >= 0; --t) {
                  var r = this.tryEntries[t]
                  if (r.finallyLoc === e)
                    return this.complete(r.completion, r.afterLoc), N(r), y
                }
              },
              catch: function (e) {
                for (var t = this.tryEntries.length - 1; t >= 0; --t) {
                  var r = this.tryEntries[t]
                  if (r.tryLoc === e) {
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
              delegateYield: function (t, r, n) {
                return (
                  (this.delegate = {
                    iterator: P(t),
                    resultName: r,
                    nextLoc: n,
                  }),
                  'next' === this.method && (this.arg = e),
                  y
                )
              },
            }),
            t
          )
        }
        var et = Xe().mark(nt),
          tt = Xe().mark(ot),
          rt = Xe().mark(it)
        function nt() {
          var e
          return Xe().wrap(function (t) {
            for (;;)
              switch ((t.prev = t.next)) {
                case 0:
                  if (-1 === window.location.href.indexOf('/embed')) {
                    t.next = 5
                    break
                  }
                  return (t.next = 3), (0, Ce.gz)(F({ firstName: 'embed' }))
                case 3:
                  t.next = 9
                  break
                case 5:
                  if (!(e = (0, y.et)())) {
                    t.next = 9
                    break
                  }
                  return (t.next = 9), (0, Ce.gz)(F(e))
                case 9:
                case 'end':
                  return t.stop()
              }
          }, et)
        }
        function ot() {
          var e, t
          return Xe().wrap(function (r) {
            for (;;)
              switch ((r.prev = r.next)) {
                case 0:
                  return (r.next = 2), fetch(window.location.pathname)
                case 2:
                  return (
                    (e = r.sent),
                    (t = e.headers.get('AK_KILL_SWITCH_ACTIVE')),
                    (r.next = 6),
                    (0, Ce.gz)(q({ active: !!t }))
                  )
                case 6:
                case 'end':
                  return r.stop()
              }
          }, tt)
        }
        function it() {
          return Xe().wrap(function (e) {
            for (;;)
              switch ((e.prev = e.next)) {
                case 0:
                  return (e.next = 2), (0, Ce.rM)(nt)
                case 2:
                  return (e.next = 4), (0, Ce.ib)(U.type, ot)
                case 4:
                case 'end':
                  return e.stop()
              }
          }, rt)
        }
        var at = (0, n.createContext)()
        at.displayName = 'ProfileContext'
        const ct = at
        function st() {
          return (
            (st = Object.assign
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
            st.apply(this, arguments)
          )
        }
        const lt = function (e) {
          var t = st(
            {},
            ((function (e) {
              if (null == e) throw new TypeError('Cannot destructure ' + e)
            })(e),
            e)
          )
          ;(0, f.vp)({ key: G, reducer: M }), (0, f.hb)({ key: G, saga: it })
          var r = (0, d.v9)(D)
          return o().createElement(ct.Provider, st({ value: r }, t))
        }
        var ut = r(96331),
          ft = ['meetCode', 'raceNumber', 'betProvider']
        function pt() {
          return (
            (pt = Object.assign
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
            pt.apply(this, arguments)
          )
        }
        const dt = (0, i.w)(function (e) {
          var t = e.meetCode,
            r = e.raceNumber,
            i = e.betProvider,
            s = (function (e, t) {
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
            })(e, ft),
            l = (0, n.useState)({ meetCode: t }),
            u = (0, n.useMemo)(
              function () {
                return { provider: i }
              },
              [i]
            )
          return o().createElement(
            ut.Z,
            null,
            o().createElement(
              lt,
              null,
              o().createElement(
                a.$f.Provider,
                { value: u },
                o().createElement(
                  a.cp.Provider,
                  { value: l },
                  o().createElement(Ze, pt({ raceNumber: (0, c.SH)(r) }, s))
                )
              )
            )
          )
        })
      },
      96616: (e, t, r) => {
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
        function o(e) {
          var t = i(e)
          return r(t)
        }
        function i(e) {
          if (!r.o(n, e)) {
            var t = new Error("Cannot find module '" + e + "'")
            throw ((t.code = 'MODULE_NOT_FOUND'), t)
          }
          return n[e]
        }
        ;(o.keys = function () {
          return Object.keys(n)
        }),
          (o.resolve = i),
          (e.exports = o),
          (o.id = 96616)
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
    (e) => (e.O(0, [736, 351], () => (10473, e((e.s = 10473)))), e.O()),
  ])
)

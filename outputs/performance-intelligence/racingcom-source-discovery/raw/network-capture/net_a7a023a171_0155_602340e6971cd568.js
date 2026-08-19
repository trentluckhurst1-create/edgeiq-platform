!(function (e, t) {
  'object' == typeof exports && 'object' == typeof module
    ? (module.exports = t(require('React'), require('ReactDOM')))
    : 'function' == typeof define && define.amd
    ? define(['React', 'ReactDOM'], t)
    : 'object' == typeof exports
    ? (exports.rdc = t(require('React'), require('ReactDOM')))
    : ((e.rdc = e.rdc || {}), (e.rdc.replayHubTiles = t(e.React, e.ReactDOM)))
})(self, (e, t) =>
  (self.webpackChunkrdc = self.webpackChunkrdc || []).push([
    [143],
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
      24697: (e, t, r) => {
        'use strict'
        r.r(t), r.d(t, { default: () => V }), r(53817)
        var n = r(1024),
          a = r.n(n),
          o = r(71570),
          i = r(13980),
          l = r.n(i),
          s = r(15252),
          u = r(31218),
          c = r(81987),
          p = r(40163),
          f = r(62388),
          m = r(1349),
          y = r(30186),
          d = r(58179),
          h = r(31807),
          b = r(65016),
          v = r(30585),
          O = r(98027),
          x = (0, r(54951).fW)('Replay Hub Tiles'),
          g = ['post', 'featured', 'useTimeOnSameDay']
        function w() {
          return (
            (w = Object.assign
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
            w.apply(this, arguments)
          )
        }
        var T = function (e) {
          var t = e.post,
            r = e.featured,
            o = e.useTimeOnSameDay,
            i = (function (e, t) {
              if (null == e) return {}
              var r,
                n,
                a = (function (e, t) {
                  if (null == e) return {}
                  var r,
                    n,
                    a = {},
                    o = Object.keys(e)
                  for (n = 0; n < o.length; n++)
                    (r = o[n]), t.indexOf(r) >= 0 || (a[r] = e[r])
                  return a
                })(e, t)
              if (Object.getOwnPropertySymbols) {
                var o = Object.getOwnPropertySymbols(e)
                for (n = 0; n < o.length; n++)
                  (r = o[n]),
                    t.indexOf(r) >= 0 ||
                      (Object.prototype.propertyIsEnumerable.call(e, r) &&
                        (a[r] = e[r]))
              }
              return a
            })(e, g),
            l = (0, h.Z)(t.createdAt),
            s = (0, n.useContext)(f.ZF)
          return a().createElement(
            y.xu,
            w(
              {
                onClick: function () {
                  var e = {}
                  null != s && s.title && (e.playlist = s.title)
                  var r,
                    n,
                    a = (0, b.Z)(l, 'd MMMM, yyyy')
                  if (
                    (x('Click Post', ''.concat(t.title, ' (').concat(a, ')')),
                    t.brightcoveVideoId)
                  )
                    (0, O.Y)('Play Video', t.brightcoveVideoId),
                      null === (r = window.rdc) ||
                        void 0 === r ||
                        null === (r = r.raceReplay) ||
                        void 0 === r ||
                        null === (n = r.PlayRaceReplay) ||
                        void 0 === n ||
                        n.call(r, { videoId: t.brightcoveVideoId })
                  else if (t.videoUrl) {
                    var o, i
                    null === (o = window.rdc) ||
                      void 0 === o ||
                      null === (o = o.liniusReplay) ||
                      void 0 === o ||
                      null === (i = o.LoadLiniusReplayByUrl) ||
                      void 0 === i ||
                      i.call(o, {
                        url: t.videoUrl,
                        poster: t.thumbnailUrl,
                        adTags: e,
                      })
                  }
                },
              },
              i
            ),
            a().createElement(v.Z, {
              tx: { root: 'rdc-video-item' },
              post: t,
              cardSize: r ? 'featured' : 'normal',
              displayTime: o,
            })
          )
        }
        T.propTypes = {
          post: l().object.isRequired,
          featured: l().bool,
          useTimeOnSameDay: l().bool,
        }
        const S = T
        var j = ['posts', 'useTimeOnSameDay'],
          E = ['posts', 'useTimeOnSameDay'],
          D = ['posts', 'useTimeOnSameDay']
        function M() {
          return (
            (M = Object.assign
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
            M.apply(this, arguments)
          )
        }
        function R(e, t) {
          if (null == e) return {}
          var r,
            n,
            a = (function (e, t) {
              if (null == e) return {}
              var r,
                n,
                a = {},
                o = Object.keys(e)
              for (n = 0; n < o.length; n++)
                (r = o[n]), t.indexOf(r) >= 0 || (a[r] = e[r])
              return a
            })(e, t)
          if (Object.getOwnPropertySymbols) {
            var o = Object.getOwnPropertySymbols(e)
            for (n = 0; n < o.length; n++)
              (r = o[n]),
                t.indexOf(r) >= 0 ||
                  (Object.prototype.propertyIsEnumerable.call(e, r) &&
                    (a[r] = e[r]))
          }
          return a
        }
        var P = function (e) {
          var t = e.posts,
            r = e.useTimeOnSameDay,
            n = R(e, j),
            o = (0, p.Ln)()
          return a().createElement(
            y.xu,
            n,
            o
              ? a().createElement(C, { posts: t, useTimeOnSameDay: r })
              : a().createElement(I, { posts: t, useTimeOnSameDay: r })
          )
        }
        P.propTypes = {
          posts: l().array.isRequired,
          useTimeOnSameDay: l().bool,
        }
        const k = P
        function I(e) {
          var t = e.posts,
            r = e.useTimeOnSameDay,
            n = R(e, E)
          return a().createElement(
            y.xu,
            M({ sx: { '& .swiper-container': { overflow: 'visible' } } }, n),
            a().createElement(S, {
              featured: !0,
              post: t[0],
              useTimeOnSameDay: r,
              mb: '15px',
            }),
            a().createElement(
              d.tq,
              { slidesPerView: 'auto', spaceBetween: 20 },
              t.slice(1).map(function (e, t, n) {
                return a().createElement(
                  d.o5,
                  { style: { width: 'auto' }, key: e.id },
                  a().createElement(S, {
                    post: e,
                    useTimeOnSameDay: r,
                    width: '236px',
                    ml: 0 === t ? '12px' : '0',
                    mr: t === n.length - 1 ? '12px' : '0',
                  })
                )
              })
            )
          )
        }
        function C(e) {
          var t = e.posts,
            r = e.useTimeOnSameDay,
            n = R(e, D)
          return a().createElement(
            s.Z,
            { padding: !1 },
            a().createElement(
              y.kC,
              M(
                {
                  sx: {
                    alignItems: 'scratch',
                    justifyContent: 'space-between',
                  },
                },
                n
              ),
              a().createElement(
                y.xu,
                {
                  sx: {
                    flex: '0 0 auto',
                    width: 'calc((100% - 20px * 4) / 5 * 2 + 20px)',
                  },
                },
                a().createElement(S, {
                  featured: !0,
                  post: t[0],
                  useTimeOnSameDay: r,
                  height: '100%',
                })
              ),
              a().createElement(
                y.kC,
                {
                  sx: {
                    flexWrap: 'wrap',
                    justifyContent: 'space-between',
                    alignItems: 'scratch',
                    flex: '0 0 auto',
                    width: 'calc((100% - 20px * 4) / 5 * 3 + 20px * 2)',
                    mb: '-20px',
                  },
                },
                t.slice(1).map(function (e) {
                  return a().createElement(S, {
                    key: e.id,
                    post: e,
                    useTimeOnSameDay: r,
                    width: 'calc((100% - 20px * 2) / 3)',
                    mb: '20px',
                  })
                })
              )
            )
          )
        }
        ;(I.propTypes = P.propTypes), (C.propTypes = P.propTypes)
        var Z = ['url']
        function U() {
          return (
            (U = Object.assign
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
            U.apply(this, arguments)
          )
        }
        function q(e, t) {
          ;(null == t || t > e.length) && (t = e.length)
          for (var r = 0, n = new Array(t); r < t; r++) n[r] = e[r]
          return n
        }
        var A = function (e) {
          var t,
            r,
            o,
            i = e.url,
            l = (function (e, t) {
              if (null == e) return {}
              var r,
                n,
                a = (function (e, t) {
                  if (null == e) return {}
                  var r,
                    n,
                    a = {},
                    o = Object.keys(e)
                  for (n = 0; n < o.length; n++)
                    (r = o[n]), t.indexOf(r) >= 0 || (a[r] = e[r])
                  return a
                })(e, t)
              if (Object.getOwnPropertySymbols) {
                var o = Object.getOwnPropertySymbols(e)
                for (n = 0; n < o.length; n++)
                  (r = o[n]),
                    t.indexOf(r) >= 0 ||
                      (Object.prototype.propertyIsEnumerable.call(e, r) &&
                        (a[r] = e[r]))
              }
              return a
            })(e, Z),
            d =
              ((r = (0, n.useState)({
                posts: [],
                heading: null,
                showMore: null,
                showMoreText: 'Show More',
                useTimeOnSameDay: !0,
              })),
              (o = 2),
              (function (e) {
                if (Array.isArray(e)) return e
              })(r) ||
                (function (e, t) {
                  var r =
                    null == e
                      ? null
                      : ('undefined' != typeof Symbol && e[Symbol.iterator]) ||
                        e['@@iterator']
                  if (null != r) {
                    var n,
                      a,
                      o,
                      i,
                      l = [],
                      s = !0,
                      u = !1
                    try {
                      if (((o = (r = r.call(e)).next), 0 === t)) {
                        if (Object(r) !== r) return
                        s = !1
                      } else
                        for (
                          ;
                          !(s = (n = o.call(r)).done) &&
                          (l.push(n.value), l.length !== t);
                          s = !0
                        );
                    } catch (e) {
                      ;(u = !0), (a = e)
                    } finally {
                      try {
                        if (
                          !s &&
                          null != r.return &&
                          ((i = r.return()), Object(i) !== i)
                        )
                          return
                      } finally {
                        if (u) throw a
                      }
                    }
                    return l
                  }
                })(r, o) ||
                (function (e, t) {
                  if (e) {
                    if ('string' == typeof e) return q(e, t)
                    var r = Object.prototype.toString.call(e).slice(8, -1)
                    return (
                      'Object' === r &&
                        e.constructor &&
                        (r = e.constructor.name),
                      'Map' === r || 'Set' === r
                        ? Array.from(e)
                        : 'Arguments' === r ||
                          /^(?:Ui|I)nt(?:8|16|32)(?:Clamped)?Array$/.test(r)
                        ? q(e, t)
                        : void 0
                    )
                  }
                })(r, o) ||
                (function () {
                  throw new TypeError(
                    'Invalid attempt to destructure non-iterable instance.\nIn order to be iterable, non-array objects must have a [Symbol.iterator]() method.'
                  )
                })()),
            h = d[0],
            b = d[1],
            v = (0, p.Ln)()
          return (
            (0, n.useEffect)(
              function () {
                if (i) {
                  var e = i.startsWith('http') ? new URL(i) : { pathname: i }
                  m.YA.get(e.pathname, { baseURL: '' }).then(function (e) {
                    var t
                    b({
                      posts: e.data.videos || [],
                      heading: e.data.heading,
                      showMore: e.data.showMoreUrl,
                      showMoreText: e.data.showMoreText || 'Show More',
                      useTimeOnSameDay:
                        null === (t = e.data.useTimeOnSameDay) ||
                        void 0 === t ||
                        t,
                    })
                  })
                }
              },
              [i]
            ),
            !(null === (t = h.posts) || void 0 === t || !t.length) &&
              a().createElement(
                a().Fragment,
                null,
                h.heading &&
                  a().createElement(
                    y.xu,
                    { sx: { mb: ['', '', '', '15px'] } },
                    a().createElement(u.Z, {
                      title: h.heading,
                      moreUrl: h.showMore && h.showMoreText,
                    })
                  ),
                a().createElement(
                  f.ZF.Provider,
                  { value: { title: h.heading } },
                  a().createElement(k, U({ posts: h.posts }, l))
                ),
                v &&
                  h.showMore &&
                  a().createElement(
                    s.Z,
                    { style: { display: 'flex', justifyContent: 'center' } },
                    a().createElement(
                      c.Z,
                      {
                        variant: 'button.homepage',
                        as: 'a',
                        href: h.showMore,
                        sx: { mt: '34px', minWidth: '370px', height: '33px' },
                      },
                      h.showMoreText
                    )
                  )
              )
          )
        }
        A.propTypes = { url: l().string.isRequired }
        const L = A
        var W = r(96331)
        r(39744)
        const V = (0, o.w)(function (e) {
          return a().createElement(W.Z, null, a().createElement(L, e))
        })
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
    (e) => (e.O(0, [736, 351], () => (24697, e((e.s = 24697)))), e.O()),
  ])
)

!(function (e, t) {
  'object' == typeof exports && 'object' == typeof module
    ? (module.exports = t(require('React'), require('ReactDOM')))
    : 'function' == typeof define && define.amd
    ? define(['React', 'ReactDOM'], t)
    : 'object' == typeof exports
    ? (exports.rdc = t(require('React'), require('ReactDOM')))
    : ((e.rdc = e.rdc || {}),
      (e.rdc.multiselectDropdown = t(e.React, e.ReactDOM)))
})(self, (e, t) =>
  (self.webpackChunkrdc = self.webpackChunkrdc || []).push([
    [89],
    {
      53817: (e, t, r) => {
        'use strict'
        r(14629), r(25047), r(92556)
      },
      92556: (e, t, r) => {
        r.p = window.rdcWidgetsPath || ''
      },
      94116: (e, t, r) => {
        'use strict'
        r.r(t), r.d(t, { default: () => f }), r(53817)
        var c = r(1024),
          l = r.n(c),
          n = r(71570),
          a = r(71015),
          i = (r(39744), r(96331)),
          o = r(54951),
          s = ['options', 'callBack', 'filterName', 'filter', 'clearFilter']
        function u() {
          return (
            (u = Object.assign
              ? Object.assign.bind()
              : function (e) {
                  for (var t = 1; t < arguments.length; t++) {
                    var r = arguments[t]
                    for (var c in r)
                      Object.prototype.hasOwnProperty.call(r, c) &&
                        (e[c] = r[c])
                  }
                  return e
                }),
            u.apply(this, arguments)
          )
        }
        const f = (0, n.w)(function (e) {
          var t = e.options,
            r = e.callBack,
            c = e.filterName,
            n = e.filter,
            f = e.clearFilter,
            p = (function (e, t) {
              if (null == e) return {}
              var r,
                c,
                l = (function (e, t) {
                  if (null == e) return {}
                  var r,
                    c,
                    l = {},
                    n = Object.keys(e)
                  for (c = 0; c < n.length; c++)
                    (r = n[c]), t.indexOf(r) >= 0 || (l[r] = e[r])
                  return l
                })(e, t)
              if (Object.getOwnPropertySymbols) {
                var n = Object.getOwnPropertySymbols(e)
                for (c = 0; c < n.length; c++)
                  (r = n[c]),
                    t.indexOf(r) >= 0 ||
                      (Object.prototype.propertyIsEnumerable.call(e, r) &&
                        (l[r] = e[r]))
              }
              return l
            })(e, s)
          return l().createElement(
            i.Z,
            null,
            l().createElement(
              a.Z,
              u(
                {
                  callBack: r,
                  options: t,
                  optionsType: 'states',
                  defaultValues: ['Victoria'],
                  width: '208px',
                  height: '28px',
                  hideSelectedOptions: !1,
                  backspaceRemovesValue: !1,
                  closeMenuOnSelect: !1,
                  isClearable: !1,
                  selectOption: !0,
                  isMulti: !0,
                  filterName: c,
                  filterValues: n,
                  clearFilter: f,
                  gaCallback: function (e) {
                    e && (0, o.fW)(e.category, e.label, e.action)
                  },
                },
                p
              )
            )
          )
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
    (e) => (e.O(0, [736, 351], () => (94116, e((e.s = 94116)))), e.O()),
  ])
)

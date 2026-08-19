"use strict";(self.webpackChunkracing_widgets=self.webpackChunkracing_widgets||[]).push([[1962],{71962:(e,t,n)=>{n.r(t),n.d(t,{default:()=>d});var o=n(37900),r=n.n(o),a=n(58032),i=n(70070),c=n(76199),l=n(82292);function s(){return s=Object.assign?Object.assign.bind():function(e){for(var t=1;t<arguments.length;t++){var n=arguments[t];for(var o in n)Object.prototype.hasOwnProperty.call(n,o)&&(e[o]=n[o])}return e},s.apply(this,arguments)}var u=r().memo((function(e){var t=e.store,n=e.setParentIsLoading,a=e.isShowing,u=a,d=(0,i.kn)({variables:{routePath:"/",placeholder:"headless-header"}}),m=d.data,h=d.loading;if((0,o.useEffect)((function(){!h&&n&&n(!1)}),[h,n]),(0,o.useEffect)((function(){if("undefined"!=typeof window&&"www.racing.com"!==window.location.hostname){var e=function(){Array.from(document.querySelectorAll("a[href]")).forEach((function(e){var t=e.getAttribute("href");if(t)try{var n=new URL(t,window.location.origin);n.hostname.includes(".racing")&&n.hostname!==window.location.hostname&&(n.hostname=window.location.hostname,e.href=n.toString())}catch(e){}}))},t=setTimeout((function(){e()}),500),n=new MutationObserver((function(){e()}));return n.observe(document.body,{childList:!0,subtree:!0}),function(){clearTimeout(t),n.disconnect()}}}),[h,m,a]),h)return r().createElement(c.Z,null);if(h)return r().createElement(c.Z,null);var f=JSON.parse((null==m?void 0:m.layoutForRoute)||"{}").jsonLayout;return f&&f.rootPlaceholders&&u?r().createElement("header",null,r().createElement("div",{id:"header"},f.rootPlaceholders.map((function(e,n){return r().createElement(r().Fragment,{key:e.componentName+n},function(e,t){return r().createElement(l.default,s({store:e,componentName:t.componentName},t))}(t,e))})))):null}));const d=r().memo((function(e){var t=e.store,n=e.setParentIsLoading,o=e.isShowing;return r().createElement(a.I,null,r().createElement(u,{store:t,setParentIsLoading:n,isShowing:o}))}))},70070:(e,t,n)=>{n.d(t,{kn:()=>i});var o=n(33601);const r={context:{clientName:"dxp-externaldata"}},a=o.gql`
    query GetLayoutForRoute($routePath: String!, $placeholder: String) {
  layoutForRoute: getLayoutForRoute(
    routePath: $routePath
    placeholder: $placeholder
  )
}
    `;function i(e){const t={...r,...e};return o.useQuery(a,t)}o.gql`
    query GetNewsVideos($horseCode: Int, $jockeyCode: Int, $trainerCode: Int, $limit: Int) {
  getNewsVideos(
    horseCode: $horseCode
    jockeyCode: $jockeyCode
    trainerCode: $trainerCode
    limit: $limit
  ) {
    results {
      id
      title
      duration
      createdAt
      description
      videoId
      thumbnailUrl
      imageUrl
      contentType
      url
      badge {
        id
        label
      }
    }
    errorMessage
    success
  }
}
    `,o.gql`
    query GetSocialProfile($id: String, $type: String, $environment: String) {
  getSocialProfile(id: $id, type: $type, environment: $environment) {
    success
    responseCode
    result {
      id
      Facebook: facebook
      Instagram: instagram
      TwitterId: twitterId
      Website: website
      ImageUrl: imageUrl
    }
  }
}
    `}}]);
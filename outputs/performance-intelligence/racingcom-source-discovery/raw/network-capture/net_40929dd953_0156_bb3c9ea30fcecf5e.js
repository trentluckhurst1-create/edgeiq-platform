"use strict";(self.webpackChunkracing_widgets=self.webpackChunkracing_widgets||[]).push([[4241],{14241:(e,t,r)=>{r.r(t),r.d(t,{default:()=>d});var o=r(37900),n=r.n(o),a=r(58032),i=r(70070),l=r(76199),s=r(82292);function c(){return c=Object.assign?Object.assign.bind():function(e){for(var t=1;t<arguments.length;t++){var r=arguments[t];for(var o in r)Object.prototype.hasOwnProperty.call(r,o)&&(e[o]=r[o])}return e},c.apply(this,arguments)}var u=n().memo((function(e){var t=e.store,r=e.setParentIsLoading,a=e.isShowing,u=(0,i.kn)({variables:{routePath:"/",placeholder:"headless-footer"}}),d=u.data,g=u.loading;if((0,o.useEffect)((function(){!g&&r&&r(!1)}),[g,r]),g)return n().createElement(l.Z,null);var m=JSON.parse((null==d?void 0:d.layoutForRoute)||"{}").jsonLayout;return m&&m.rootPlaceholders&&a?n().createElement("footer",null,n().createElement("div",{id:"id-footer"},m.rootPlaceholders.map((function(e,r){return n().createElement(n().Fragment,{key:e.componentName+r},function(e,t){return n().createElement(s.default,c({store:e,componentName:t.componentName},t))}(t,e))})))):null}));const d=n().memo((function(e){var t=e.store,r=e.setParentIsLoading,o=e.isShowing;return n().createElement(a.I,null,n().createElement(u,{store:t,setParentIsLoading:r,isShowing:o}))}))},70070:(e,t,r)=>{r.d(t,{kn:()=>i});var o=r(33601);const n={context:{clientName:"dxp-externaldata"}},a=o.gql`
    query GetLayoutForRoute($routePath: String!, $placeholder: String) {
  layoutForRoute: getLayoutForRoute(
    routePath: $routePath
    placeholder: $placeholder
  )
}
    `;function i(e){const t={...n,...e};return o.useQuery(a,t)}o.gql`
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
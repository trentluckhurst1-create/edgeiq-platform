# EDGEiQ Racing Intelligence Platform

EDGEiQ is the Professional Racing Intelligence Operating System frontend.

## Production deployment

EDGEiQ is deployed exclusively through GitHub Pages from the `main` branch.

Production URL:

```text
https://trentluckhurst1-create.github.io/edgeiq-platform/
```

Deployment workflow:

```text
.github/workflows/edgeiq-github-pages.yml
```

A push to `main` that changes the frontend, public assets, package manifests, TypeScript configuration, Vite configuration, or the Pages workflow triggers a production build and GitHub Pages deployment.

The production build uses the repository path base:

```text
/edgeiq-platform/
```

Static runtime data intended for the frontend should live under `public/data/` so it is included in the GitHub Pages artifact and served from the same GitHub Pages deployment.

No Vercel, Render, Cloudflare Pages, or Cloudflare R2 deployment is part of the production hosting path.

## Local development

PowerShell:

```powershell
npm ci
npm run dev
```

Optional Clerk authentication can be configured with:

```text
VITE_CLERK_PUBLISHABLE_KEY=
```

Development auth bypass remains development-only:

```text
VITE_DISABLE_AUTH=false
```

## Production verification

The GitHub Pages workflow performs:

```text
npm ci
npm exec -- tsc -b
npm exec -- vite build -- --base=/edgeiq-platform/
```

The resulting `dist` directory is uploaded as the `github-pages` artifact and deployed with `actions/deploy-pages`.

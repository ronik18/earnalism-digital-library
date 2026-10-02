# Journal function packaging repair

Base: d89b85af806734eb79c66f082573abd74a4c9caa. Infrastructure-only; no catalogue, rights, pricing, entitlement, audio or UI changes.

The previous prebuilt deployment failed with ENOENT because `.vercelignore` excluded `frontend/build/journal-app-shell.html`, explicitly required by `frontend/vercel.json` and the generated function `filePathMap`. Replace only the build-directory rule with a child exclusion and one exact shell exception.

## Guard

`python3 -m unittest scripts.test_verify_vercel_packaging -v`

`vercel deploy --dry --format=json` supplies the actual source manifest. After `vercel build --prod`, use `vercel deploy --prebuilt --prod --dry --format=json`. The guard compares configured includeFiles, generated filePathMap assets and external file symlinks with selected files, rejects broken/missing traces and unrelated generated build files, and compares source/prebuilt required-asset SHA256s. Full manifests are not published; short asset-hash reports are durable CI artifacts.

PR CI builds and checks the actual source manifest; the production workflow checks both actual manifests before any deployment. Packaging changes now trigger the existing deployment job, even without frontend source changes. Existing regression and production-canary gates remain intact.

## Pre-merge proof

CLI62.1.0 actual negative control: old ignore rule omitted the shell. New rule includes the shell and no other frontend/build files. Nine focused tests pass. Production-config prebuilt build and deployment reached READY at dpl_Dma3V91YAWunCpmPY12zdRtKhcdZ; primary apex/www domains were not assigned. Direct journal function GET returned200 with authoritative title and canonical URL. Source Preview dpl_6H7mTzV4PjHGksDAx2z6aFAp1p3u also returned200; environment-specific bundle hashes are not treated as production equivalence.

Production-config source comparison and final merged automatic deployment are recorded in the PR closeout. No catalogue activation is included.

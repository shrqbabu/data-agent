# CI workflow templates

## `build-apk.yml` — hardened APK pipeline

The workflow that is currently active (`build-apk.yml` on `main`) has three problems:

1. it does not pass the publishable build configuration, so the APK it produces
   shows the *"This app is not configured yet."* screen;
2. it never installs/refreshes the Android SDK toolchain and it runs `./gradlew`
   without guaranteeing the wrapper is usable;
3. it only uploads a short-lived artifact, so there is no stable download link.

This template fixes all three: JDK 17 + Gradle 8.11.1 + Android SDK, the
publishable Supabase/API values injected from repository secrets, an APK
artifact **and** a rolling `apk-latest` release that always carries the newest
`analytics-agent-debug.apk` + `SHA256SUMS.txt`.

### Install it

```bash
cp ci/build-apk.yml .github/workflows/build-apk.yml
git add .github/workflows/build-apk.yml
git commit -m "ci: harden APK pipeline"
git push
```

> Why is the template here instead of already installed?
> Automation tokens (GitHub Apps) may only create or update files under
> `.github/workflows/` when they hold the `workflows` permission. This agent's
> installation does not have it, so a normal `git push` of that path is rejected
> with *"refusing to allow a GitHub App to create or update workflow"*.
> Everything outside `.github/workflows/` is unaffected.

### Required repository secrets

| Secret | Used for | Required |
| --- | --- | --- |
| `SUPABASE_URL` | `BuildConfig.SUPABASE_URL` | yes |
| `SUPABASE_KEY` | `BuildConfig.SUPABASE_PUBLISHABLE_KEY` (publishable/anon key only) | yes |
| `API_URL` | `BuildConfig.ANALYTICS_API_URL` (analytics backend base URL) | yes |

Set them in *Settings → Secrets and variables → Actions*. Publishable values
only: the service-role key, JWT secret and LLM keys must never be baked into an
APK.

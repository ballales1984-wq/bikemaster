# Frontend Architecture Contracts

## Layer boundaries

- `src/stores/`
  - Owns Pinia state for the current session (in-memory only, no localStorage persistence).
  - Exposes `ref`/`computed` and plain functions. No `getState()` pattern.
  - Each store owns one domain: `auth`, `trackingStore`, `athleteState`, `rides`, `settings`, etc.
  - Stores must not import Vue components or router directly.

- `src/components/`
  - Owns UI pieces; reads state via `storeToRefs(store)`.
  - Must not mutate another component’s local state.
  - Reusable logic goes in `src/composables/`.

- `src/views/`
  - Owns page orchestration: lifecycle hooks, watchers, route params.
  - Must clean timers/intervals in `onBeforeUnmount` or `onUnmounted`.
  - Must not contain business logic that belongs in a store or composable.

- `src/utils/`
  - Owns API helpers, backend config, constants, formats.
  - Must not import stores or components.

- `src/types/`
  - Owns TypeScript interfaces/types shared across layers.
  - Must not import Vue or runtime code.

## State management rules

- Auth token is in-memory only: `src/stores/auth.ts`.
- Logout resets all stores (see `resetStoreMap` in `auth.ts`).
- Computed values must be pure; side effects belong in `watch` or functions.
- Watchers must clean previous subscriptions/timers if they start new ones.

## API contract

- All HTTP calls use `src/utils/api.ts` (`apiGet`, `apiPost`, `apiUpload`).
- Base URL is resolved by `src/utils/backend-config.ts`.
- Errors surface as `ApiError` with `message` and `status`.
- No direct `fetch()` outside `utils/api.ts`.

## Routing and deep links

- Router lives in `src/router/`.
- Deep links use query params (e.g. `?rideId=123`).
- Views must handle missing/invalid query params gracefully.

## Testing

- Tests mirror the source tree under `frontend/src/`.
- Unit tests use `vitest` + `@vue/test-utils`.
- Do not mock stores globally; inject real stores with `setActivePinia(createPinia())`.

# Theme Tokens

## Source of truth

Design tokens are defined as CSS custom properties in `src/styles/tokens.css` (`:root` block).
This module (`src/theme/tokens.ts`) mirrors those values for use in TypeScript/Vue code
without magic strings.

## Adding a new token

1. Define the CSS custom property in `src/styles/tokens.css`.
2. Add the corresponding entry in `src/theme/tokens.ts` within the appropriate group.
3. Run `npx vitest run src/theme/tokens.test.ts` to confirm the token list stays in sync.

## Usage

```ts
import { tokens } from "@/theme/tokens";

const style = {
  background: tokens.color.accent,
  padding: tokens.space.lg,
  borderRadius: tokens.radius.default,
};
```

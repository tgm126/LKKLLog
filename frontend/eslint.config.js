import js from "@eslint/js";
import reactHooks from "eslint-plugin-react-hooks";
import globals from "globals";
import tseslint from "typescript-eslint";

export default tseslint.config(
  { ignores: ["dist", "test-results", "playwright-report"] },
  js.configs.recommended,
  tseslint.configs.recommended,
  reactHooks.configs.flat.recommended,
  {
    languageOptions: { globals: globals.browser },
    rules: {
      // Normalizace stylů: vzhled jen třídami z CSS, žádné vložené styly v komponentách.
      "no-restricted-syntax": [
        "error",
        {
          selector: "JSXAttribute[name.name='style']",
          message: "Vložený styl nepatří do komponenty – použijte třídu a tokeny (CLAUDE.md, bod 14).",
        },
      ],
    },
  },
);

// Normalizace stylů (CLAUDE.md, bod 14): pevné barvy a rozměry jen v souboru s tokeny.
// Výjimka jinde jen s důvodem:  /* stylelint-disable-next-line <pravidlo> -- VÝJIMKA: důvod */
const jenToken = [/^var\(--/, "inherit", "0"];

export default {
  extends: ["stylelint-config-standard"],
  reportDescriptionlessDisables: true,
  rules: {
    "color-no-hex": true,
    "color-named": "never",
    "function-disallowed-list": ["rgb", "rgba", "hsl", "hsla", "hwb", "lab", "lch", "oklab", "oklch", "color", "light-dark"],
    "unit-disallowed-list": ["px", "em", "rem", "pt", "ch", "ms", "s", "vh", "vw", "dvh", "svh"],
    "declaration-property-value-allowed-list": {
      "font-family": [/^var\(--/, "inherit"],
      "font-size": jenToken,
      "font-weight": jenToken,
      "line-height": jenToken,
      "letter-spacing": jenToken,
      "opacity": jenToken,
      "z-index": jenToken,
      "/^transition/": [/var\(--/, "none"],
    },
    // České názvy tříd a proměnných v kebab-case (bez diakritiky).
    "selector-class-pattern": "^[a-z][a-z0-9]*(-[a-z0-9]+)*$",
    "custom-property-pattern": "^[a-z][a-z0-9]*(-[a-z0-9]+)*$",
  },
  overrides: [
    {
      files: ["src/styly/tokeny.css"],
      rules: {
        "color-no-hex": null,
        "function-disallowed-list": null,
        "unit-disallowed-list": null,
        "declaration-property-value-allowed-list": null,
      },
    },
  ],
};

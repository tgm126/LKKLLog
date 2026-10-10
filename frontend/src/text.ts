// Pomocné funkce pro text.

/** Pro hledání: bez diakritiky a malými („cacky“ najde „Čacký“). */
export const proHledani = (text: string) =>
  text.normalize("NFD").replace(/\p{Diacritic}/gu, "").toLocaleLowerCase("cs-CZ");

/** „1 let“, „3 lety“, „44 letů“ */
export const pocetLetu = (n: number) => `${n} ${n === 1 ? "let" : n >= 2 && n <= 4 ? "lety" : "letů"}`;

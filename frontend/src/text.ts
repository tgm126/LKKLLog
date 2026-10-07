// Pomocné funkce pro text.

/** Pro hledání: bez diakritiky a malými („cacky“ najde „Čacký“). */
export const proHledani = (text: string) =>
  text.normalize("NFD").replace(/\p{Diacritic}/gu, "").toLocaleLowerCase("cs-CZ");

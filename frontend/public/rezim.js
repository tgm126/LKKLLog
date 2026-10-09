// Režim zobrazení (světlý / tmavý / podle zařízení) z úložiště prohlížeče dřív, než se načte
// aplikace – jinak by tmavý režim na okamžik bliknul světle (klíč jako v src/rezim.ts).
try {
  var rezim = localStorage.getItem("lkkl-rezim");
  if (rezim === "svetly" || rezim === "tmavy") document.documentElement.dataset.rezim = rezim;
} catch {
  // úložiště nemusí být dostupné – pak podle zařízení
}

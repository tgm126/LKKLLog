import type { ReactNode } from "react";

import "./Zaskrtavatko.css";

// Zaškrtávátko jako dlaždice pro palec (maketa docs/navrhy/osoby-mobil.html): popisek
// (a drobné vysvětlení) vlevo, políčko vpravo, zaškrtnuté modře a tučně. Ve skupině dvě
// vedle sebe s přepážkami jako pole údajů.

export function Zaskrtavatko({
  popisek,
  pod,
  zaskrtnuto,
  zmenit,
  zakazano = false,
}: {
  popisek: string;
  /** Drobné vysvětlení pod popiskem. */
  pod?: ReactNode;
  zaskrtnuto: boolean;
  zmenit: (zaskrtnuto: boolean) => void;
  zakazano?: boolean;
}) {
  return (
    <button
      type="button"
      role="checkbox"
      aria-checked={zaskrtnuto}
      className="zaskrtavatko"
      disabled={zakazano}
      onClick={() => zmenit(!zaskrtnuto)}
    >
      <span>
        {popisek}
        {pod && <span className="zaskrtavatko-pod">{pod}</span>}
      </span>
      <span className="zaskrtavatko-policko" aria-hidden>
        ✓
      </span>
    </button>
  );
}

/** Skupina zaškrtávátek (dvě vedle sebe). */
export function Zaskrtavatka({ children }: { children: ReactNode }) {
  return <div className="zaskrtavatka">{children}</div>;
}

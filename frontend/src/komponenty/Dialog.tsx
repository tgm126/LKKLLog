import { useEffect, useRef, type ReactNode } from "react";

import "./Dialog.css";

/** Dialog s otázkou zdola obrazovky (palcem dosažitelné akce); zástin nebo Esc zavře jako
 *  „zpět“. Fokus přejde na první tlačítko (klávesnice, čtečka). */
export function Dialog({
  nadpis,
  zavrit,
  children,
}: {
  nadpis: string;
  zavrit: () => void;
  children: ReactNode;
}) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    ref.current?.querySelector<HTMLElement>("button")?.focus();
  }, []);
  return (
    <>
      <div className="dialog-zastin" onClick={zavrit} />
      <div
        ref={ref}
        className="dialog"
        role="dialog"
        aria-modal="true"
        aria-label={nadpis}
        onKeyDown={(e) => {
          if (e.key !== "Escape") return;
          e.stopPropagation(); // Esc patří dialogu, ne panelu desky pod ním
          zavrit();
        }}
      >
        <h2 className="velke tucne">{nadpis}</h2>
        {children}
      </div>
    </>
  );
}

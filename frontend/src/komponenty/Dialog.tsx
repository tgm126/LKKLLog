import type { ReactNode } from "react";

import "./Dialog.css";

/** Dialog s otázkou zdola obrazovky (palcem dosažitelné akce); zástin zavře jako „zpět“. */
export function Dialog({
  nadpis,
  zavrit,
  children,
}: {
  nadpis: string;
  zavrit: () => void;
  children: ReactNode;
}) {
  return (
    <>
      <div className="dialog-zastin" onClick={zavrit} />
      <div className="dialog" role="dialog" aria-modal="true" aria-label={nadpis}>
        <h2 className="velke tucne">{nadpis}</h2>
        {children}
      </div>
    </>
  );
}

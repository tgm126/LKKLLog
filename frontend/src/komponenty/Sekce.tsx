import { useState, type ReactNode } from "react";

import "./Sekce.css";

export function Sekce({
  nadpis,
  vpravo,
  sbalena = false,
  children,
}: {
  nadpis: string;
  vpravo?: ReactNode;
  sbalena?: boolean;
  children: ReactNode;
}) {
  const [otevrena, setOtevrena] = useState(!sbalena);
  return (
    <>
      <button className="sekce" aria-expanded={otevrena} onClick={() => setOtevrena(!otevrena)}>
        <span className="sekce-sipka" aria-hidden>
          ▾
        </span>
        <h2 className="nadpisek">{nadpis}</h2>
        {vpravo && <span className="sekce-vpravo male seda cisla">{vpravo}</span>}
      </button>
      {otevrena && <div>{children}</div>}
    </>
  );
}

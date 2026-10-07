import { Children, cloneElement, isValidElement, type ReactElement, type ReactNode } from "react";

import "./Udaje.css";

// Údaje v bloku (detail letu, průvodce): pole „popisek nad hodnotou“ ve dvou sloupcích jako
// přihrádky; upravitelné pole je tlačítko se „›“ a úprava se otevře pod ním přes celou šířku.

type UdajProps = {
  popisek: string;
  hodnota: ReactNode;
  upravit?: () => void;
  otevreno?: boolean;
  /** Přes celou šířku (dlouhá hodnota: úloha, poznámka, plátce). */
  cely?: boolean;
  /** Odkaz na jiný let (modře). */
  odkaz?: boolean;
  /** Hodnota tučně (časy, doba). */
  zvyraznit?: boolean;
  children?: ReactNode;
};

export function Udaj(props: UdajProps) {
  const { popisek, hodnota, upravit, otevreno, cely, odkaz, zvyraznit, children } = props;
  const trida = ["udaj", cely && "cely", upravit && "upravit", odkaz && "odkaz", zvyraznit && "zvyraznit"];
  const obsah = (
    <>
      <span className="udaj-popisek">{popisek}</span>
      <span className="udaj-hodnota">{hodnota ?? <span className="seda">—</span>}</span>
    </>
  );
  return (
    <>
      {upravit ? (
        <button
          type="button"
          className={trida.filter(Boolean).join(" ")}
          aria-expanded={otevreno}
          onClick={upravit}
        >
          {obsah}
        </button>
      ) : (
        <div className={trida.filter(Boolean).join(" ")}>{obsah}</div>
      )}
      {otevreno && <div className="uprava">{children}</div>}
    </>
  );
}

/** Index posledního polovičního pole, které by zůstalo v řádku samo (jinak null). */
function samotnaPulka(cela: boolean[]): number | null {
  let vlevo: number | null = null; // poloviční pole čekající na souseda vpravo
  cela.forEach((cely, i) => {
    if (!cely) vlevo = vlevo === null ? i : null;
  });
  return vlevo;
}

/** Mřížka údajů; poslední pole, které by zůstalo v řádku samo, se roztáhne přes celou šířku. */
export function Udaje({ children }: { children: ReactNode }) {
  const pole = Children.toArray(children).filter(isValidElement) as ReactElement<UdajProps>[];
  const posledniPulka = samotnaPulka(pole.map((u) => !!u.props.cely));
  return (
    <div className="udaje-bloku">
      {pole.map((u, i) => (i === posledniPulka ? cloneElement(u, { cely: true }) : u))}
    </div>
  );
}

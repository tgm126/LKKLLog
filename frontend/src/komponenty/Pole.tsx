import { useId, useState, type InputHTMLAttributes, type ReactNode, type Ref } from "react";

import { Tlacitko } from "./Tlacitko";
import "./Pole.css";

type Props = InputHTMLAttributes<HTMLInputElement> & {
  popisek: string;
  napoveda?: ReactNode;
  /** Heslo s tlačítkem Ukázat / Skrýt. */
  ukazat?: boolean;
  ref?: Ref<HTMLInputElement>;
};

export function Pole({ popisek, napoveda, ukazat, type, ...vstup }: Props) {
  const id = useId();
  const [videt, setVidet] = useState(false);
  return (
    <div className="pole">
      <label className="pole-popisek" htmlFor={id}>
        {popisek}
      </label>
      <div className="pole-ram">
        <input
          id={id}
          type={ukazat && videt ? "text" : type}
          aria-describedby={napoveda ? `${id}-napoveda` : undefined}
          {...vstup}
        />
        {ukazat && (
          <Tlacitko varianta={["bez-ramu", "svetle"]} onClick={() => setVidet(!videt)}>
            {videt ? "Skrýt" : "Ukázat"}
          </Tlacitko>
        )}
      </div>
      {napoveda && (
        <span className="pole-napoveda" id={`${id}-napoveda`} aria-live="polite">
          {napoveda}
        </span>
      )}
    </div>
  );
}

import type { ReactNode } from "react";

import "./Hlaska.css";

export function Hlaska({ children }: { children: ReactNode }) {
  if (!children) return null;
  return (
    <p className="hlaska" role="alert">
      {children}
    </p>
  );
}

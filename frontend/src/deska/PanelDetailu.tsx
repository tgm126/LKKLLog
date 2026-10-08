import { useNavigate, useParams } from "react-router";

import { Hlaska } from "../komponenty/Hlaska";
import { Panel } from "../komponenty/Panel";
import { useDetail, useNabidky } from "../lety/api";
import { AkceDetailu, DetailBloky } from "../lety/Detail";
import { useMujProvoz } from "../provoz/api";
import { useJenCteni } from "../uzivatel";
import { PasekDeska } from "./PasekDeska";

// Detail letu v panelu zprava (docs/modul-desktop.md 3.8): nahoře pásek a vedle něj
// zavírací křížek (rejstřík se neopakuje v liště nad páskem), pod ním stejné bloky
// a úpravy jako na mobilu, akce v patičce. Deska pod panelem zůstává ovladatelná.

export function PanelDetailu() {
  const letId = Number(useParams().id);
  const { data: l, error } = useDetail(letId);
  const nabidky = useNabidky().data;
  const mojeKod = useMujProvoz().data?.letiste?.kod;
  const navigate = useNavigate();
  const jenCteni = useJenCteni();
  const zavrit = () => navigate("/");
  if (!l || !nabidky) {
    return (
      <Panel nadpis="Detail letu" hlava={<h2 className="velke tucne">Let</h2>} zavrit={zavrit}>
        {error && <Hlaska>{error.message}</Hlaska>}
      </Panel>
    );
  }
  return (
    <Panel
      key={l.id}
      nadpis="Detail letu"
      zavrit={zavrit}
      hlava={
        <PasekDeska
          // moje letiště v trase šedě (jako v přehledu – server ho u pásků vynechá)
          let={{
            ...l,
            misto_vzletu: l.misto_vzletu === mojeKod ? null : l.misto_vzletu,
            misto_pristani: l.misto_pristani === mojeKod ? null : l.misto_pristani,
          }}
          mojeKod={mojeKod}
          vPanelu
        />
      }
      pata={jenCteni ? undefined : <AkceDetailu let_={l} nabidky={nabidky} />}
    >
      <DetailBloky let_={l} nabidky={nabidky} />
    </Panel>
  );
}

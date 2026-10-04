import { Center, Loader } from '@mantine/core'
import { useQuery } from '@tanstack/react-query'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router'

import { nactiHealth } from './api/health'
import { Navigace } from './komponenty/Navigace'
import { Pruhy } from './komponenty/Pruhy'
import { Paticka, Zahlavi } from './komponenty/Zahlavi'
import { NastavitHeslo } from './stranky/NastavitHeslo'
import { Ciselniky } from './stranky/Ciselniky'
import { Displej } from './stranky/Displej'
import { KartaOsoby } from './stranky/KartaOsoby'
import { Letadla } from './stranky/Letadla'
import { MujNalet } from './stranky/MujNalet'
import { Prihlaseni } from './stranky/Prihlaseni'
import { Osoby } from './stranky/Osoby'
import { PrehledDne } from './stranky/PrehledDne'
import { Uzaverky } from './stranky/Uzaverky'
import { Vypis } from './stranky/Vypis'
import { ZapomenuteHeslo } from './stranky/ZapomenuteHeslo'
import { useJa } from './useJa'

function Obsah() {
  const { data: ja, isPending } = useJa()
  if (isPending) {
    return (
      <Center py="xl">
        <Loader />
      </Center>
    )
  }
  return (
    <>
    {ja?.prihlasen && <Navigace />}
    <Routes>
      <Route path="/nastavit-heslo/:uid/:token" element={<NastavitHeslo />} />
      <Route
        path="/zapomenute-heslo"
        element={ja?.prihlasen ? <Navigate to="/" replace /> : <ZapomenuteHeslo />}
      />
      <Route path="/vypis" element={ja?.prihlasen ? <Vypis /> : <Prihlaseni />} />
      <Route path="/uzaverky" element={ja?.prihlasen ? <Uzaverky /> : <Prihlaseni />} />
      <Route path="/nalet" element={ja?.prihlasen ? <MujNalet /> : <Prihlaseni />} />
      <Route path="/osoby" element={ja?.prihlasen ? <Osoby /> : <Prihlaseni />} />
      <Route path="/osoby/:id" element={ja?.prihlasen ? <KartaOsoby /> : <Prihlaseni />} />
      <Route path="/letadla" element={ja?.prihlasen ? <Letadla /> : <Prihlaseni />} />
      <Route path="/sprava" element={<Navigate to="/letadla" replace />} />
      <Route path="/ciselniky" element={ja?.prihlasen ? <Ciselniky /> : <Prihlaseni />} />
      <Route path="*" element={ja?.prihlasen ? <PrehledDne /> : <Prihlaseni />} />
    </Routes>
    </>
  )
}

/** Běžná aplikace: pruhy, záhlaví, navigace a patička kolem obsahu. */
function Aplikace() {
  const { data: health } = useQuery({ queryKey: ['health'], queryFn: nactiHealth })
  return (
    <>
      <Pruhy />
      <Zahlavi />
      <Obsah />
      <Paticka verze={health?.verze} />
    </>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Velký displej běží bez přihlášení a bez záhlaví aplikace. */}
        <Route path="/displej/:klic" element={<Displej />} />
        <Route path="*" element={<Aplikace />} />
      </Routes>
    </BrowserRouter>
  )
}

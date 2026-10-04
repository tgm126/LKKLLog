import { Center, Loader } from '@mantine/core'
import { useQuery } from '@tanstack/react-query'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router'

import { nactiHealth } from './api/health'
import { Navigace } from './komponenty/Navigace'
import { Pruhy } from './komponenty/Pruhy'
import { Paticka, Zahlavi } from './komponenty/Zahlavi'
import { NastavitHeslo } from './stranky/NastavitHeslo'
import { Prihlaseni } from './stranky/Prihlaseni'
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
      <Route path="*" element={ja?.prihlasen ? <PrehledDne /> : <Prihlaseni />} />
    </Routes>
    </>
  )
}

export default function App() {
  const { data: health } = useQuery({ queryKey: ['health'], queryFn: nactiHealth })
  return (
    <BrowserRouter>
      <Pruhy />
      <Zahlavi />
      <Obsah />
      <Paticka verze={health?.verze} />
    </BrowserRouter>
  )
}

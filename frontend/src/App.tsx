import { Center, Loader } from '@mantine/core'
import { useQuery } from '@tanstack/react-query'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router'

import { nactiHealth } from './api/health'
import { Pruhy } from './komponenty/Pruhy'
import { Paticka, Zahlavi } from './komponenty/Zahlavi'
import { NastavitHeslo } from './stranky/NastavitHeslo'
import { Prihlaseni } from './stranky/Prihlaseni'
import { Uvod } from './stranky/Uvod'
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
    <Routes>
      <Route path="/nastavit-heslo/:uid/:token" element={<NastavitHeslo />} />
      <Route
        path="/zapomenute-heslo"
        element={ja?.prihlasen ? <Navigate to="/" replace /> : <ZapomenuteHeslo />}
      />
      <Route path="*" element={ja?.prihlasen ? <Uvod /> : <Prihlaseni />} />
    </Routes>
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

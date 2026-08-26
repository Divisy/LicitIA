import { useCallback, useEffect, useState } from 'react'
import axios from 'axios'
import { getTender, Tender } from '../api/client'
import {
  addFavoriteTender,
  FAVORITES_CHANGED_EVENT,
  FavoriteTenderRef,
  isFavoriteTender,
  loadFavoriteRefs,
  removeFavoriteTender,
  toggleFavoriteTender,
} from '../utils/favoriteTendersStorage'

export interface UnavailableFavorite {
  ref: FavoriteTenderRef
}

export function useFavoriteTenders() {
  const [refs, setRefs] = useState<FavoriteTenderRef[]>(() => loadFavoriteRefs())
  const [favoriteTenders, setFavoriteTenders] = useState<Tender[]>([])
  const [unavailableFavorites, setUnavailableFavorites] = useState<UnavailableFavorite[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const syncRefs = useCallback(() => {
    setRefs(loadFavoriteRefs())
  }, [])

  const refreshFavoriteTenders = useCallback(async () => {
    const currentRefs = loadFavoriteRefs()
    setRefs(currentRefs)

    if (currentRefs.length === 0) {
      setFavoriteTenders([])
      setUnavailableFavorites([])
      setError(null)
      return
    }

    setLoading(true)
    setError(null)

    const available: Tender[] = []
    const unavailable: UnavailableFavorite[] = []

    await Promise.all(
      currentRefs.map(async (ref) => {
        try {
          const tender = await getTender(ref.tender_id)
          available.push(tender)
        } catch (err) {
          if (axios.isAxiosError(err) && err.response?.status === 404) {
            unavailable.push({ ref })
            return
          }
          console.error('Failed to load favorite tender', ref.tender_id, err)
        }
      })
    )

    const order = new Map(currentRefs.map((ref, index) => [ref.tender_id, index]))
    available.sort(
      (a, b) => (order.get(a.id) ?? 0) - (order.get(b.id) ?? 0)
    )

    setFavoriteTenders(available)
    setUnavailableFavorites(unavailable)
    setLoading(false)
  }, [])

  useEffect(() => {
    const handleChange = () => syncRefs()
    window.addEventListener(FAVORITES_CHANGED_EVENT, handleChange)
    return () => window.removeEventListener(FAVORITES_CHANGED_EVENT, handleChange)
  }, [syncRefs])

  const isFavorite = useCallback(
    (tenderId: string) => isFavoriteTender(tenderId),
    [refs]
  )

  const addFavorite = useCallback((tender: Tender) => {
    const next = addFavoriteTender(tender)
    setRefs(next)
    return true
  }, [])

  const removeFavorite = useCallback((tenderId: string) => {
    const next = removeFavoriteTender(tenderId)
    setRefs(next)
    setFavoriteTenders((current) => current.filter((tender) => tender.id !== tenderId))
    setUnavailableFavorites((current) =>
      current.filter((item) => item.ref.tender_id !== tenderId)
    )
  }, [])

  const toggleFavorite = useCallback((tender: Tender) => {
    const added = toggleFavoriteTender(tender)
    setRefs(loadFavoriteRefs())
    return added
  }, [])

  return {
    refs,
    favoriteTenders,
    unavailableFavorites,
    loading,
    error,
    setError,
    isFavorite,
    addFavorite,
    removeFavorite,
    toggleFavorite,
    refreshFavoriteTenders,
    syncRefs,
  }
}

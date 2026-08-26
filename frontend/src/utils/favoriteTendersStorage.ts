import type { Tender } from '../api/client'

export const FAVORITES_CHANGED_EVENT = 'licitia:favorites-changed'

export interface FavoriteTenderRef {
  tender_id: string
  external_id: string
  reference?: string | null
  marked_at: string
}

export function getUserEmail(): string {
  return (localStorage.getItem('licitia_user_email') || '').trim().toLowerCase()
}

export function getFavoriteStorageKey(email?: string): string {
  const resolved = (email || getUserEmail()).trim().toLowerCase()
  return `licitia_favorite_tenders:${resolved || 'anonymous'}`
}

export function loadFavoriteRefs(email?: string): FavoriteTenderRef[] {
  const raw = localStorage.getItem(getFavoriteStorageKey(email))
  if (!raw) {
    return []
  }
  try {
    const parsed = JSON.parse(raw) as FavoriteTenderRef[]
    if (!Array.isArray(parsed)) {
      return []
    }
    return parsed.filter((item) => Boolean(item?.tender_id))
  } catch {
    return []
  }
}

export function saveFavoriteRefs(refs: FavoriteTenderRef[], email?: string): void {
  localStorage.setItem(getFavoriteStorageKey(email), JSON.stringify(refs))
  window.dispatchEvent(new CustomEvent(FAVORITES_CHANGED_EVENT))
}

export function isFavoriteTender(tenderId: string, email?: string): boolean {
  return loadFavoriteRefs(email).some((ref) => ref.tender_id === tenderId)
}

export function addFavoriteTender(tender: Tender, email?: string): FavoriteTenderRef[] {
  const refs = loadFavoriteRefs(email)
  if (refs.some((ref) => ref.tender_id === tender.id)) {
    return refs
  }
  const next: FavoriteTenderRef[] = [
    {
      tender_id: tender.id,
      external_id: tender.external_id,
      reference: tender.reference,
      marked_at: new Date().toISOString(),
    },
    ...refs,
  ]
  saveFavoriteRefs(next, email)
  return next
}

export function removeFavoriteTender(tenderId: string, email?: string): FavoriteTenderRef[] {
  const next = loadFavoriteRefs(email).filter((ref) => ref.tender_id !== tenderId)
  saveFavoriteRefs(next, email)
  return next
}

export function toggleFavoriteTender(tender: Tender, email?: string): boolean {
  if (isFavoriteTender(tender.id, email)) {
    removeFavoriteTender(tender.id, email)
    return false
  }
  addFavoriteTender(tender, email)
  return true
}

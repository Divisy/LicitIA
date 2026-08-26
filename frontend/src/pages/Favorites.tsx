import React, { useEffect, useState } from 'react'
import {
  Grid,
  Column,
  InlineNotification,
  Loading,
  Tile,
  Tag,
  Button,
} from '@carbon/react'
import TenderTable from '../components/TenderTable'
import TenderDetailPanel from '../components/TenderDetailPanel'
import EmptyState from '../components/empty-states/EmptyState'
import Logo from '../components/Logo'
import { Tender } from '../api/client'
import { useFavoriteTenders } from '../hooks/useFavoriteTenders'
import { FAVORITES_CHANGED_EVENT } from '../utils/favoriteTendersStorage'
import './Favorites.scss'

const Favorites: React.FC = () => {
  const {
    refs,
    favoriteTenders,
    unavailableFavorites,
    loading,
    error,
    setError,
    isFavorite,
    toggleFavorite,
    removeFavorite,
    refreshFavoriteTenders,
  } = useFavoriteTenders()

  const [selectedTender, setSelectedTender] = useState<Tender | null>(null)

  useEffect(() => {
    refreshFavoriteTenders().catch((err: unknown) => {
      const message =
        err instanceof Error ? err.message : 'No se pudieron cargar las favoritas'
      setError(message)
    })
  }, [refreshFavoriteTenders, setError])

  useEffect(() => {
    const handleChange = () => {
      refreshFavoriteTenders().catch((err: unknown) => {
        const message =
          err instanceof Error ? err.message : 'No se pudieron cargar las favoritas'
        setError(message)
      })
    }
    window.addEventListener(FAVORITES_CHANGED_EVENT, handleChange)
    return () => window.removeEventListener(FAVORITES_CHANGED_EVENT, handleChange)
  }, [refreshFavoriteTenders, setError])

  const totalFavorites = refs.length

  return (
    <div className="favorites-page">
      <Grid className="favorites-page__grid">
        <Column lg={16} md={8} sm={4}>
          <div className="favorites-page__header">
            <div className="favorites-page__header-logo">
              <Logo size="md" showText={true} />
            </div>
            <div>
              <h1 className="favorites-page__title">
                Favoritas{totalFavorites > 0 ? ` (${totalFavorites})` : ''}
              </h1>
              <p className="favorites-page__subtitle">
                Licitaciones que marcaste para estudiar y decidir si ofertas.
              </p>
            </div>
          </div>
        </Column>
      </Grid>

      {error && (
        <Grid className="favorites-page__grid">
          <Column lg={16} md={8} sm={4}>
            <InlineNotification
              kind="error"
              title="Error"
              subtitle={error}
              lowContrast={false}
            />
          </Column>
        </Grid>
      )}

      {loading && (
        <Grid className="favorites-page__grid">
          <Column lg={16} md={8} sm={4}>
            <Tile className="favorites-page__loading">
              <Loading description="Cargando favoritas..." withOverlay={false} />
            </Tile>
          </Column>
        </Grid>
      )}

      {!loading && totalFavorites === 0 && (
        <Grid className="favorites-page__grid">
          <Column lg={16} md={8} sm={4}>
            <EmptyState
              type="no-tenders"
              title="Aún no tienes favoritas"
              description="Explora el dashboard, abre el detalle de una licitación y márcala con la estrella para guardarla aquí."
            />
          </Column>
        </Grid>
      )}

      {!loading && unavailableFavorites.length > 0 && (
        <Grid className="favorites-page__grid">
          <Column lg={16} md={8} sm={4}>
            <section className="favorites-page__unavailable">
              <h2 className="favorites-page__section-title">Ya no disponibles</h2>
              {unavailableFavorites.map(({ ref }) => (
                <Tile key={ref.tender_id} className="favorites-page__unavailable-item">
                  <div>
                    <p className="favorites-page__unavailable-title">
                      {ref.reference || ref.external_id}
                    </p>
                    <Tag type="red" size="sm">
                      Ya no disponible
                    </Tag>
                  </div>
                  <Button
                    kind="ghost"
                    size="sm"
                    onClick={() => removeFavorite(ref.tender_id)}
                  >
                    Quitar de favoritas
                  </Button>
                </Tile>
              ))}
            </section>
          </Column>
        </Grid>
      )}

      {!loading && favoriteTenders.length > 0 && (
        <Grid className="favorites-page__grid">
          <Column lg={16} md={8} sm={4}>
            <TenderTable
              tenders={favoriteTenders}
              onSelectTender={setSelectedTender}
              showFavoriteColumn
              isFavorite={isFavorite}
              onToggleFavorite={toggleFavorite}
            />
          </Column>
        </Grid>
      )}

      <TenderDetailPanel
        tender={selectedTender}
        open={selectedTender !== null}
        onClose={() => setSelectedTender(null)}
      />
    </div>
  )
}

export default Favorites

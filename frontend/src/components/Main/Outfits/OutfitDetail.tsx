import { useEffect, useState, useMemo } from 'react'
import { useParams } from 'react-router-dom'
import api from '../../../api/client'
import { Button } from '../../ui/button'
import { Heart } from 'lucide-react'
import { type OutfitCommentOut } from '../../../api/schemas'
import {
  toggleFavoriteOutfit,
  listOutfitComments,
  addOutfitComment,
  likeOutfitComment,
  deleteOutfitComment,
} from '../../../api/outfits'
import RatingStars from '../../common/RatingStars'
import { useAuth } from '../../../context/AuthContext'
import { categoryConfig } from './OutfitBuilder'

interface Item {
  id: number
  name: string
  image_url?: string | null
}

interface Outfit {
  id: number
  name: string
  style: string
  description?: string | null
  total_price?: number | null
  tops: Item[]
  bottoms: Item[]
  footwear: Item[]
  accessories: Item[]
  fragrances: Item[]
}

const OutfitDetail = () => {
  const { id } = useParams<{ id: string }>()
  const { user, isAdmin } = useAuth()
  const [outfit, setOutfit] = useState<Outfit | null>(null)
  const [loading, setLoading] = useState(true)
  const [comments, setComments] = useState<OutfitCommentOut[]>([])
  const [newComment, setNewComment] = useState('')
  const [rating, setRating] = useState<number | undefined>()
  const [favorited, setFavorited] = useState<boolean | null>(null)

  useEffect(() => {
    const fetchOutfit = async () => {
      try {
        const resp = await api.get<Outfit>(`/api/outfits/${id}`)
        setOutfit(resp.data)
        const commentsData = await listOutfitComments(Number(id))
        setComments(commentsData)
      } catch (err) {
        console.error(err)
      } finally {
        setLoading(false)
      }
    }
    if (id) fetchOutfit()
  }, [id])

  // Need to fetch favorited state separately
  useEffect(() => {
    const fetchFavoriteStatus = async () => {
      if (!id || !user) return
      try {
        // We can check if this outfit is in the list of user's favorite outfits
        const favs = await api.get<Outfit[]>('/api/outfits/favorites')
        setFavorited(favs.data.some((o) => o.id === Number(id)))
      } catch (err) {
        // ignore, e.g. 401
      }
    }
    fetchFavoriteStatus()
  }, [id, user])

  const handleToggleFavorite = async () => {
    if (!id || user === null) return
    // Optimistic update
    setFavorited((prev) => !prev)
    try {
      await toggleFavoriteOutfit(Number(id))
    } catch (err) {
      // Revert on error
      setFavorited((prev) => !prev)
      console.error(err)
    }
  }

  const handleAddComment = async () => {
    if (!id || !newComment.trim()) return
    try {
      const newComm = await addOutfitComment(Number(id), { content: newComment, rating })
      setComments([newComm, ...comments])
      setNewComment('')
      setRating(undefined)
    } catch (err) {
      console.error(err)
    }
  }

  const previewLayers = useMemo(() => {
    if (!outfit) {
      // Return placeholders to keep indexes in sync
      return categoryConfig.map(() => null)
    }
    // Return array of image urls by same ordering as categoryConfig
    return categoryConfig.map((c) => {
      const key = c.key as keyof Outfit
      const items = outfit[key] as Item[] | undefined
      const first = items && items.length ? items[0] : undefined
      return first?.image_url || null
    })
  }, [outfit])

  if (loading) return <div className="text-center py-8">Загрузка...</div>
  if (!outfit) return <div className="text-center py-8">Образ не найден</div>

  const categories = [
    { label: 'Верх', items: outfit.tops },
    { label: 'Низ', items: outfit.bottoms },
    { label: 'Обувь', items: outfit.footwear },
    { label: 'Аксессуары', items: outfit.accessories },
    { label: 'Ароматы', items: outfit.fragrances },
  ]

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Header */}
      <div className="mb-8 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="mb-1 text-3xl font-bold tracking-tight text-foreground">{outfit.name}</h1>
          <p className="text-sm text-muted-foreground">Стиль: {outfit.style}</p>
        </div>
        <Button
          onClick={handleToggleFavorite}
          variant={favorited ? 'default' : 'outline'}
          className="gap-2"
        >
          <Heart className={`h-5 w-5 ${favorited ? 'fill-primary text-primary' : ''}`} />
          {favorited ? 'В избранном' : 'В избранное'}
        </Button>
      </div>

      {/* Top section: mannequin preview + description */}
      <div className="mb-12 grid gap-8 md:grid-cols-2 md:items-start">
        {/* Preview */}
        <div className="relative mx-auto h-[540px] w-[320px] shrink-0 rounded-xl border bg-card shadow-lg">
          <img
            src="/maneken.jpg"
            alt="Манекен"
            className="absolute inset-0 h-full w-full object-contain"
          />
          {previewLayers.map((url, idx) => {
            if (!url) return null
            return (
              <img
                key={idx}
                src={url}
                alt="layer"
                className="absolute inset-0 h-full w-full object-contain"
                style={{ zIndex: idx + 1 }}
              />
            )
          })}
        </div>

        {/* Info */}
        <div className="space-y-6">
          {outfit.description && <p className="leading-relaxed">{outfit.description}</p>}
          {outfit.total_price && (
            <p className="text-xl font-semibold">
              Стоимость:{' '}
              {outfit.total_price.toLocaleString('ru-RU')} ₽
            </p>
          )}
        </div>
      </div>

      {/* Items by category */}
      <div className="space-y-10">
        {categories.map((cat) => (
          cat.items.length > 0 && (
            <div key={cat.label}>
              <h2 className="mb-4 text-2xl font-semibold tracking-tight text-foreground">
                {cat.label}
              </h2>
              <div className="flex flex-wrap gap-6">
                {cat.items.map((i) => (
                  <div key={i.id} className="w-32 text-center">
                    {i.image_url ? (
                      <img
                        src={i.image_url}
                        alt={i.name}
                        className="h-32 w-32 rounded object-cover shadow-sm"
                      />
                    ) : (
                      <div className="h-32 w-32 rounded bg-muted" />
                    )}
                    <p className="mt-2 truncate text-sm font-medium">{i.name}</p>
                  </div>
                ))}
              </div>
            </div>
          )
        ))}
      </div>

      {/* Comments */}
      <div className="mt-16 max-w-2xl">
        <h2 className="mb-4 text-xl font-medium">Комментарии</h2>
        <div className="mb-6 space-y-2">
          <textarea
            className="w-full rounded border px-3 py-2 text-sm"
            placeholder="Ваш отзыв..."
            value={newComment}
            onChange={(e) => setNewComment(e.target.value)}
            rows={3}
          />
          <div className="flex items-center justify-between">
            <RatingStars value={rating} onChange={setRating} />
            <Button onClick={handleAddComment}>Отправить</Button>
          </div>
        </div>
        {comments.length === 0 && <p className="text-muted-foreground">Нет комментариев</p>}
        <ul className="space-y-4">
          {comments.map((c) => (
            <li key={c.id} className="rounded border p-3">
              <p className="mb-1 text-sm whitespace-pre-line">{c.content}</p>
              {c.rating !== undefined && c.rating !== null && (
                <RatingStars value={c.rating} className="mb-1" />
              )}
              <div className="flex items-center gap-4 text-xs text-muted-foreground">
                <span>{new Date(c.created_at).toLocaleString()}</span>
                <button
                  className="flex items-center gap-1 hover:text-primary"
                  onClick={async () => {
                    if (!id || !user) return;
                    try {
                      await likeOutfitComment(Number(id), c.id);
                      // Refetch comments to get updated like count
                      const updatedComments = await listOutfitComments(Number(id));
                      setComments(updatedComments);
                    } catch (err) {
                      console.error(err);
                    }
                  }}
                >
                  <Heart className="h-3 w-3" /> {c.likes}
                </button>
                {(user?.id === c.user_id || isAdmin) && (
                  <button
                    className="text-xs text-red-500 hover:underline"
                    onClick={async () => {
                      if (!id) return
                      if (!confirm('Удалить комментарий?')) return
                      try {
                        await deleteOutfitComment(Number(id), c.id)
                        setComments((prev) => prev.filter((x) => x.id !== c.id))
                      } catch (err) {
                        console.error(err)
                      }
                    }}
                  >
                    Удалить
                  </button>
                )}
              </div>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}

export default OutfitDetail 
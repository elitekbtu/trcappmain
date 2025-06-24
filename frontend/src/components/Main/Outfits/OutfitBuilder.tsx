import { useEffect, useState } from 'react'
import { ArrowLeft, ArrowRight, X } from 'lucide-react'
import { listItems } from '../../../api/items'
import { type ItemOut } from '../../../api/schemas'
import { Button } from '../../ui/button'
import { useTranslation } from 'react-i18next'

// Mapping for UI labels and API clothing types
export const categoryConfig = [
  { key: 'tops', apiType: 'top', label: 'Верх' },
  { key: 'accessories', apiType: 'accessories', label: 'Аксессуары' },
  { key: 'bottoms', apiType: 'bottom', label: 'Низ' },
  { key: 'footwear', apiType: 'footwear', label: 'Обувь' },
  { key: 'fragrances', apiType: 'fragrances', label: 'Ароматы' },
] as const

type CategoryKey = (typeof categoryConfig)[number]['key']

interface IndexState {
  [k: string]: number
}

const OutfitBuilder = () => {
  const [itemsByCat, setItemsByCat] = useState<Record<string, ItemOut[]>>({})
  const [indexByCat, setIndexByCat] = useState<IndexState>({})
  const [selectedByCat, setSelectedByCat] = useState<Record<string, ItemOut[]>>({})
  const [loading, setLoading] = useState(true)
  const { t } = useTranslation()

  useEffect(() => {
    const fetchAll = async () => {
      try {
        const promises = categoryConfig.map((c) =>
          listItems({ category: c.apiType, limit: 50 })
        )
        const results = await Promise.all(promises)
        const grouped: Record<string, ItemOut[]> = {}
        const idx: IndexState = {}
        const sel: Record<string, ItemOut[]> = {}
        categoryConfig.forEach((c, i) => {
          grouped[c.key] = results[i]
          idx[c.key] = 0
          sel[c.key] = []
        })
        setItemsByCat(grouped)
        setIndexByCat(idx)
        setSelectedByCat(sel)
      } catch (err) {
        // eslint-disable-next-line no-console
        console.error(err)
      } finally {
        setLoading(false)
      }
    }
    fetchAll()
  }, [])

  const cycle = (key: CategoryKey, dir: 'prev' | 'next') => {
    setIndexByCat((prev) => {
      const list = itemsByCat[key] || []
      if (list.length === 0) return prev
      const current = prev[key] ?? 0
      const nextIndex = dir === 'next' ? (current + 1) % list.length : (current - 1 + list.length) % list.length
      return { ...prev, [key]: nextIndex }
    })
  }

  const toggleSelect = (key: CategoryKey) => {
    setSelectedByCat((prev) => {
      const list = itemsByCat[key] || []
      const currIdx = indexByCat[key] ?? 0
      const item = list[currIdx]
      if (!item) return prev
      const already = prev[key]?.some((it) => it.id === item.id) ?? false
      const updated = already ? prev[key].filter((it) => it.id !== item.id) : [...(prev[key] || []), item]
      return { ...prev, [key]: updated }
    })
  }

  const mannequinUrl = '/maneken.jpg'

  if (loading) {
    return <div className="flex h-64 items-center justify-center">{t('common.loading')}</div>
  }

  return (
    <div className="container mx-auto flex flex-col gap-8 px-4 py-8 md:flex-row md:items-start">
      {/* Mannequin Preview */}
      <div className="relative mx-auto h-[520px] w-[300px] shrink-0 shadow-lg">
        <img
          src={mannequinUrl}
          alt="Mannequin"
          className="absolute inset-0 h-full w-full object-contain"
        />
        {categoryConfig.flatMap((c, i) => {
          const selectedList = selectedByCat[c.key] || []
          return selectedList.map((sel, j) => (
            sel.image_url ? (
              <img
                key={`${c.key}-${sel.id}`}
                src={sel.image_url}
                alt={sel.name}
                className="absolute inset-0 h-full w-full object-contain"
                style={{ zIndex: i + j + 1 }}
              />
            ) : null
          ))
        })}
      </div>

      {/* Controls */}
      <div className="flex-1 space-y-6">
        {categoryConfig.map((c) => {
          const list = itemsByCat[c.key] || []
          const idx = indexByCat[c.key]
          const current = list[idx]
          const selectedList = selectedByCat[c.key] || []
          return (
            <div key={c.key} className="flex items-center gap-4">
              <Button
                variant="ghost"
                size="icon"
                onClick={() => cycle(c.key, 'prev')}
                disabled={list.length === 0}
                className="hover:bg-accent/50"
              >
                <ArrowLeft className="h-5 w-5" />
              </Button>

              <div className="flex flex-1 items-center gap-4 overflow-hidden">
                <span className="w-28 shrink-0 text-sm font-medium">{c.label}</span>
                {current ? (
                  <div className="flex items-center gap-2 overflow-hidden">
                    {current.image_url ? (
                      <img
                        src={current.image_url}
                        alt={current.name}
                        className="h-20 w-20 rounded object-cover"
                      />
                    ) : (
                      <div className="h-20 w-20 rounded bg-muted" />
                    )}
                    <span className="truncate text-sm">{current.name}</span>
                  </div>
                ) : (
                  <span className="text-sm text-muted-foreground">{t('outfitBuilder.noOptions')}</span>
                )}
              </div>

              <Button
                variant="ghost"
                size="icon"
                onClick={() => cycle(c.key, 'next')}
                disabled={list.length === 0}
                className="hover:bg-accent/50"
              >
                <ArrowRight className="h-5 w-5" />
              </Button>

              <Button
                variant="secondary"
                size="sm"
                disabled={!current}
                onClick={() => toggleSelect(c.key)}
              >
                {current && selectedList.some((it) => it.id === current.id) ? 'Убрать' : 'Добавить'}
              </Button>

              {selectedList.length > 0 && (
                <div className="flex gap-1 overflow-x-auto">
                  {selectedList.map((it) => (
                    <div key={it.id} className="relative h-12 w-12 shrink-0 rounded">
                      {it.image_url ? (
                        <img src={it.image_url} alt={it.name} className="h-full w-full rounded object-cover" />
                      ) : (
                        <div className="h-full w-full rounded bg-muted" />
                      )}
                      <button
                        type="button"
                        onClick={() => setSelectedByCat((prev) => ({
                          ...prev,
                          [c.key]: prev[c.key].filter((x) => x.id !== it.id),
                        }))}
                        className="absolute -right-1 -top-1 rounded-full bg-red-500 p-0.5 text-white hover:bg-red-600"
                      >
                        <X className="h-3 w-3" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default OutfitBuilder 
import { useEffect, useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { Loader2, Save, X } from 'lucide-react'
import { Button } from '../../ui/button'
import { Input } from '../../ui/input'
import { Textarea } from '../../ui/textarea'
import { Label } from '../../ui/label'
import { useToast } from '../../ui/use-toast'
import { listItems } from '../../../api/items'
import { type ItemOut } from '../../../api/schemas'
import { createOutfit } from '../../../api/outfits'
import { categoryConfig } from './OutfitBuilder'

interface IndexState {
  [key: string]: number
}

// Map category key to payload field
const idFieldMap: Record<string, string> = {
  tops: 'top_ids',
  bottoms: 'bottom_ids',
  footwear: 'footwear_ids',
  accessories: 'accessories_ids',
  fragrances: 'fragrances_ids',
}

// At least one category must be selected for a valid outfit (рест не обязательно)
// Backend всё равно проверит, что минимум одна категория есть

const CreateOutfit = () => {
  const navigate = useNavigate()
  const { toast } = useToast()
  const [itemsByCat, setItemsByCat] = useState<Record<string, ItemOut[]>>({})
  const [indexByCat, setIndexByCat] = useState<IndexState>({})
  const [selectedByCat, setSelectedByCat] = useState<Record<string, ItemOut[]>>({})
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)

  // Form fields
  const [name, setName] = useState('')
  const [style, setStyle] = useState('')
  const [description, setDescription] = useState('')

  // Compute total price of currently selected items
  const totalPrice = useMemo(() => {
    let total = 0
    categoryConfig.forEach((c) => {
      const selList = selectedByCat[c.key] || []
      selList.forEach((it) => {
        if (typeof it.price === 'number') total += it.price
      })
    })
    return total
  }, [selectedByCat])

  useEffect(() => {
    const fetchAll = async () => {
      try {
        const promises = categoryConfig.map((c) => listItems({ category: c.apiType, limit: 50 }))
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
        console.error(err)
        toast({ variant: 'destructive', title: 'Ошибка', description: 'Не удалось загрузить список вещей' })
      } finally {
        setLoading(false)
      }
    }
    fetchAll()
  }, [toast])

  const cycle = (key: string, dir: 'prev' | 'next') => {
    setIndexByCat((prev) => {
      const list = itemsByCat[key] || []
      if (list.length === 0) return prev
      const current = prev[key] ?? 0
      const next = dir === 'next' ? (current + 1) % list.length : (current - 1 + list.length) % list.length
      return { ...prev, [key]: next }
    })
  }

  const toggleSelect = (key: string) => {
    setSelectedByCat((prev) => {
      const list = itemsByCat[key] || []
      const currIdx = indexByCat[key] ?? 0
      const item = list[currIdx]
      if (!item) return prev
      const exists = prev[key]?.some((it) => it.id === item.id) ?? false
      const updated = exists ? prev[key].filter((x) => x.id !== item.id) : [...(prev[key] || []), item]
      return { ...prev, [key]: updated }
    })
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim() || !style.trim()) {
      toast({ variant: 'destructive', title: 'Заполните обязательные поля' })
      return
    }

    // Validate at least one selected item
    const hasAnySelected = categoryConfig.some((c) => (selectedByCat[c.key] || []).length > 0)
    if (!hasAnySelected) {
      toast({
        variant: 'destructive',
        title: 'Пустой образ',
        description: 'Добавьте хотя бы один предмет, чтобы создать образ.',
      })
      return
    }

    setSubmitting(true)
    try {
      // Prepare payload
      const payload: Record<string, any> = {
        name,
        style,
        description,
      }
      categoryConfig.forEach((c) => {
        const selList = selectedByCat[c.key] || []
        if (selList.length > 0) {
          (payload as any)[idFieldMap[c.key]] = selList.map((it) => it.id)
        }
      })
      const newOutfit = await createOutfit(payload as any)
      toast({ title: 'Образ создан', description: 'Вы перенаправлены на страницу образа' })
      navigate(`/outfits/${newOutfit.id}`)
    } catch (err: any) {
      console.error(err)
      const message = err?.response?.data?.detail || 'Не удалось создать образ'
      toast({ variant: 'destructive', title: 'Ошибка', description: message })
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-primary" />
      </div>
    )
  }

  return (
    <form onSubmit={handleSubmit} className="container mx-auto flex flex-col gap-8 px-4 py-8 md:flex-row md:items-start">
      {/* Builder preview */}
      <div className="flex-1">
        {/* Reuse preview from builder */}
        {/* We'll render similarly */}
        <div className="relative mx-auto h-[520px] w-[300px] shadow-lg">
          <img src="/maneken.jpg" alt="Манекен" className="absolute inset-0 h-full w-full object-contain" />
          {categoryConfig.flatMap((c, i) => {
            const selList = selectedByCat[c.key] || []
            return selList.map((sel, j) => (
              sel.image_url ? (
                <img key={`${c.key}-${sel.id}`} src={sel.image_url} alt={sel.name} className="absolute inset-0 h-full w-full object-contain" style={{ zIndex: i + j + 1 }} />
              ) : null
            ))
          })}
        </div>
        {/* Total price */}
        <div className="mt-4 text-center text-sm font-medium">
          Примерная стоимость:{' '}
          {totalPrice > 0 ? `${totalPrice.toLocaleString('ru-RU')} ₽` : '—'}
        </div>

        {/* Category controls */}
        <div className="mt-6 space-y-6">
          {categoryConfig.map((c) => {
            const list = itemsByCat[c.key] || []
            const idx = indexByCat[c.key]
            const current = list[idx]
            const selectedList = selectedByCat[c.key] || []
            return (
              <div key={c.key} className="flex items-center gap-4">
                <Button variant="ghost" size="icon" onClick={() => cycle(c.key, 'prev')} disabled={list.length === 0} className="hover:bg-accent/50">
                  ‹
                </Button>
                <div className="flex flex-1 items-center gap-4 overflow-hidden">
                  <span className="w-28 shrink-0 text-sm font-medium">{c.label}</span>
                  {current ? (
                    <div className="flex items-center gap-2 overflow-hidden">
                      {current.image_url ? (
                        <img src={current.image_url} alt={current.name} className="h-20 w-20 rounded object-cover" />
                      ) : (
                        <div className="h-20 w-20 rounded bg-muted" />
                      )}
                      <span className="truncate text-sm">{current.name}</span>
                    </div>
                  ) : (
                    <span className="text-sm text-muted-foreground">Нет вариантов</span>
                  )}
                </div>
                <Button variant="ghost" size="icon" onClick={() => cycle(c.key, 'next')} disabled={list.length === 0} className="hover:bg-accent/50">
                  ›
                </Button>
                <Button variant="secondary" size="sm" disabled={!current} onClick={() => toggleSelect(c.key)}>
                  {current && selectedList.some((it) => it.id === current.id) ? 'Убрать' : 'Добавить'}
                </Button>
                {selectedList.length > 0 && (
                  <div className="flex gap-1 overflow-x-auto">
                    {selectedList.map((it) => (
                      <div key={it.id} className="relative h-10 w-10 shrink-0 rounded">
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

      {/* Form fields */}
      <div className="w-full max-w-md space-y-6">
        <div className="space-y-3">
          <Label htmlFor="name">Название образа*</Label>
          <Input id="name" value={name} onChange={(e) => setName(e.target.value)} placeholder="Название" required />
        </div>
        <div className="space-y-3">
          <Label htmlFor="style">Стиль*</Label>
          <Input id="style" value={style} onChange={(e) => setStyle(e.target.value)} placeholder="Кэжуал, streetwear..." required />
        </div>
        <div className="space-y-3">
          <Label htmlFor="description">Описание</Label>
          <Textarea id="description" value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Краткое описание" rows={4} />
        </div>

        <div className="flex justify-end">
          <Button type="submit" disabled={submitting} className="gap-2 bg-primary hover:bg-primary/90">
            {submitting && <Loader2 className="h-4 w-4 animate-spin" />}
            {!submitting && <Save className="h-4 w-4" />}
            {submitting ? 'Сохранение...' : 'Создать образ'}
          </Button>
        </div>
      </div>
    </form>
  )
}

export default CreateOutfit 
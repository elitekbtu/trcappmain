import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Loader2, ArrowLeft, Save } from 'lucide-react'
import {
  getItem,
  createItem,
  updateItem,
  listVariants,
  createVariant as apiCreateVariant,
  deleteVariant as apiDeleteVariant,
  listItemImages,
  deleteItemImage as apiDeleteItemImage,
} from '../../api/items'
import { type ItemUpdate, type VariantCreate } from '../../api/schemas'
import type { ItemImageOut } from '../../api/items'
import { Button } from '../../components/ui/button'
import { Input } from '../../components/ui/input'
import { Textarea } from '../../components/ui/textarea'
import { Label } from '../../components/ui/label'
import { useToast } from '../../components/ui/use-toast'
import { cn } from '../../lib/utils'
import type { Body_create_item_api_items__post as ItemCreate } from '../../api/schemas'

const emptyItem: ItemCreate = {
  name: '',
  brand: '',
  color: '',
  clothing_type: 'top',
  image_url: '',
  description: '',
  price: undefined,
  category: 'top',
  article: '',
  size: '',
  style: '',
  collection: '',
}

const ItemForm = () => {
  const navigate = useNavigate()
  const { id } = useParams<{ id: string }>()
  const { toast } = useToast()
  const isEdit = !!id

  const [form, setForm] = useState<ItemCreate>(emptyItem)
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [files, setFiles] = useState<File[]>([])
  const [variants, setVariants] = useState<VariantCreate[]>([])
  const [existingImages, setExistingImages] = useState<ItemImageOut[]>([])

  useEffect(() => {
    const fetchItem = async () => {
      try {
        if (isEdit) {
          const data = await getItem(Number(id))
          setForm({ ...(data as ItemCreate), clothing_type: (data as any).category as any })
          try {
            const imgs = await listItemImages(Number(id))
            setExistingImages(imgs)
          } catch (_) {/* ignore */}
        }
      } catch (error) {
        toast({
          variant: 'destructive',
          title: 'Ошибка',
          description: 'Не удалось загрузить данные о товаре',
        })
      } finally {
        setLoading(false)
      }
    }

    fetchItem()
  }, [id, isEdit, toast])

  useEffect(() => {
    const fetchVariants = async () => {
      if (!isEdit) return
      try {
        const data = await listVariants(Number(id))
        setVariants(data.map((v) => ({ size: v.size, color: v.color, sku: v.sku, stock: v.stock, price: v.price })))
      } catch (_) {
        /* ignore */
      }
    }
    fetchVariants()
  }, [id, isEdit])

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value } = e.target
    if (name === 'clothing_type') {
      setForm((prev) => ({ ...prev, clothing_type: value as any, category: value }))
    } else if (name === 'category') {
      setForm((prev) => ({ ...prev, category: value, clothing_type: value as any }))
    } else {
      setForm((prev: ItemCreate) => ({ ...prev, [name]: value }))
    }
  }

  const handleNumberChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target
    setForm((prev: ItemCreate) => ({ ...prev, [name]: value === '' ? undefined : Number(value) }))
  }

  const handleFilesChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files) return
    const selected = Array.from(e.target.files)
    setFiles(selected)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    // Client-side validation
    if (!form.name.trim()) {
      toast({ variant: 'destructive', title: 'Ошибка', description: 'Название товара обязательно' })
      return
    }
    if (form.price !== undefined && form.price <= 0) {
      toast({ variant: 'destructive', title: 'Ошибка', description: 'Цена должна быть положительным числом' })
      return
    }

    setSubmitting(true)

    try {
      let itemId: number | null = null

      if (isEdit) {
        const payload: ItemUpdate = { ...form }
        await updateItem(Number(id), payload)
        itemId = Number(id)
        toast({
          title: 'Успешно',
          description: 'Товар успешно обновлен',
        })
      } else {
        const formData = new FormData()
        Object.entries(form).forEach(([key, value]) => {
          if (value !== undefined && value !== '') {
            formData.append(key, String(value))
          }
        })
        files.forEach((file) => {
          formData.append('images', file)
        })
        const created = await createItem(formData)
        itemId = created.id
        toast({
          title: 'Успешно',
          description: 'Товар успешно создан',
        })
      }

      // Synchronize variants if any exist
      if (itemId && variants.length > 0) {
        // For simplicity: delete all existing variants then recreate
        if (isEdit) {
          const existing = await listVariants(itemId)
          await Promise.all(existing.map((v) => apiDeleteVariant(itemId!, v.id)))
        }
        for (const v of variants) {
          await apiCreateVariant(itemId, v)
        }
      }

      navigate('/admin/items')
    } catch (error) {
      toast({
        variant: 'destructive',
        title: 'Ошибка',
        description: 'Произошла ошибка при сохранении',
      })
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    )
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="container mx-auto max-w-4xl px-4 py-8"
    >
      <div className="mb-8 flex items-center gap-4">
        <Button
          variant="ghost"
          size="icon"
          onClick={() => navigate('/admin/items')}
          className="shrink-0 hover:bg-accent/50"
        >
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <h1 className="text-3xl font-bold tracking-tight text-foreground">
          {isEdit ? 'Редактирование товара' : 'Создание нового товара'}
        </h1>
      </div>

      <form onSubmit={handleSubmit} className="space-y-8">
        <div className="rounded-xl border bg-card p-6 shadow-sm">
          <h2 className="mb-6 text-xl font-semibold text-foreground">
            Основная информация
          </h2>
          
          <div className="grid gap-6 md:grid-cols-2">
            <div className="space-y-3">
              <Label htmlFor="name" className="text-sm font-medium text-muted-foreground">
                Название*
              </Label>
              <Input
                id="name"
                name="name"
                value={form.name}
                onChange={handleChange}
                required
                placeholder="Название товара"
                className="focus:border-primary focus:ring-1 focus:ring-primary"
              />
            </div>

            <div className="space-y-3">
              <Label htmlFor="brand" className="text-sm font-medium text-muted-foreground">
                Бренд
              </Label>
              <Input
                id="brand"
                name="brand"
                value={form.brand || ''}
                onChange={handleChange}
                placeholder="Бренд"
                className="focus:border-primary focus:ring-1 focus:ring-primary"
              />
            </div>

            <div className="space-y-3">
              <Label htmlFor="category" className="text-sm font-medium text-muted-foreground">
                Категория товара
              </Label>
              <select
                id="category"
                name="category"
                value={form.category}
                onChange={handleChange}
                required
                className="block w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:border-primary focus:ring-1 focus:ring-primary"
              >
                <option value="top">Верх (top)</option>
                <option value="bottom">Низ (bottom)</option>
                <option value="accessories">Аксессуары (accessories)</option>
                <option value="footwear">Обувь (footwear)</option>
                <option value="fragrances">Ароматы (fragrances)</option>
              </select>
            </div>

            <div className="space-y-3">
              <Label htmlFor="price" className="text-sm font-medium text-muted-foreground">
                Цена
              </Label>
              <Input
                id="price"
                name="price"
                type="number"
                value={form.price ?? ''}
                onChange={handleNumberChange}
                placeholder="Цена"
                className="focus:border-primary focus:ring-1 focus:ring-primary"
              />
            </div>

            <div className="space-y-3">
              <Label htmlFor="size" className="text-sm font-medium text-muted-foreground">
                Размер
              </Label>
              <Input
                id="size"
                name="size"
                value={form.size || ''}
                onChange={handleChange}
                placeholder="Размер"
                className="focus:border-primary focus:ring-1 focus:ring-primary"
              />
            </div>

            <div className="space-y-3">
              <Label htmlFor="color" className="text-sm font-medium text-muted-foreground">
                Цвет
              </Label>
              <Input
                id="color"
                name="color"
                value={form.color || ''}
                onChange={handleChange}
                placeholder="Цвет"
                className="focus:border-primary focus:ring-1 focus:ring-primary"
              />
            </div>

            <div className="space-y-3">
              <Label htmlFor="article" className="text-sm font-medium text-muted-foreground">
                Артикул / SKU
              </Label>
              <Input
                id="article"
                name="article"
                value={form.article || ''}
                onChange={handleChange}
                placeholder="Уникальный артикул товара"
                className="focus:border-primary focus:ring-1 focus:ring-primary"
              />
            </div>

            <div className="space-y-3">
              <Label htmlFor="style" className="text-sm font-medium text-muted-foreground">
                Стиль
              </Label>
              <Input
                id="style"
                name="style"
                value={form.style || ''}
                onChange={handleChange}
                placeholder="Классический, спорт-шик, casual..."
                className="focus:border-primary focus:ring-1 focus:ring-primary"
              />
            </div>

            <div className="space-y-3">
              <Label htmlFor="collection" className="text-sm font-medium text-muted-foreground">
                Коллекция
              </Label>
              <Input
                id="collection"
                name="collection"
                value={form.collection || ''}
                onChange={handleChange}
                placeholder="Напр. Summer 2024"
                className="focus:border-primary focus:ring-1 focus:ring-primary"
              />
            </div>
          </div>
        </div>

        <div className="rounded-xl border bg-card p-6 shadow-sm">
          <h2 className="mb-6 text-xl font-semibold text-foreground">
            Изображение и описание
          </h2>
          
          <div className="space-y-6">
            <div className="space-y-3">
              <Label htmlFor="image_url" className="text-sm font-medium text-muted-foreground">
                URL изображения
              </Label>
              <Input
                id="image_url"
                name="image_url"
                type="url"
                value={form.image_url || ''}
                onChange={handleChange}
                placeholder="https://example.com/image.jpg"
                className="focus:border-primary focus:ring-1 focus:ring-primary"
              />
            </div>

            {/* File Upload */}
            <div className="space-y-3">
              <Label htmlFor="image_files" className="text-sm font-medium text-muted-foreground">
                Загрузить изображения
              </Label>
              <Input
                id="image_files"
                name="image_files"
                type="file"
                accept="image/*"
                multiple
                onChange={handleFilesChange}
                className="focus:border-primary focus:ring-1 focus:ring-primary"
              />
            </div>

            {/* Existing images (edit mode) */}
            {existingImages.length > 0 && (
              <div className="grid grid-cols-3 gap-4">
                {existingImages.map((img) => (
                  <div key={img.id} className="relative group h-32 w-full overflow-hidden rounded-lg border">
                    <img src={img.image_url} alt="img" className="h-full w-full object-cover" />
                    {/* delete overlay */}
                    <button
                      type="button"
                      onClick={async () => {
                        if (!confirm('Удалить изображение?')) return
                        try {
                          await apiDeleteItemImage(Number(id), img.id)
                          setExistingImages((prev) => prev.filter((x) => x.id !== img.id))
                        } catch (err) {
                          toast({ variant: 'destructive', title: 'Ошибка', description: 'Не удалось удалить изображение' })
                        }
                      }}
                      className="absolute inset-0 flex items-center justify-center bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity text-white text-xl"
                    >
                      ×
                    </button>
                  </div>
                ))}
              </div>
            )}

            {/* Previews for selected files */}
            {files.length > 0 && (
              <div className="grid grid-cols-3 gap-4">
                {files.map((file, idx) => (
                  <div key={idx} className="relative h-32 w-full overflow-hidden rounded-lg border">
                    <img
                      src={URL.createObjectURL(file)}
                      alt={`preview-${idx}`}
                      className="h-full w-full object-cover"
                    />
                  </div>
                ))}
              </div>
            )}

            {/* Preview for image URL */}
            {form.image_url && (
              <div className="flex justify-center">
                <div className="relative h-48 w-48 overflow-hidden rounded-lg border-2 border-dashed border-muted-foreground/20">
                  <img
                    src={form.image_url}
                    alt="Предпросмотр"
                    className="h-full w-full object-contain"
                    onError={(e) => {
                      e.currentTarget.style.display = 'none'
                    }}
                  />
                </div>
              </div>
            )}

            <div className="space-y-3">
              <Label htmlFor="description" className="text-sm font-medium text-muted-foreground">
                Описание
              </Label>
              <Textarea
                id="description"
                name="description"
                value={form.description || ''}
                onChange={handleChange}
                placeholder="Подробное описание товара"
                rows={5}
                className="min-h-[120px] focus:border-primary focus:ring-1 focus:ring-primary"
              />
            </div>
          </div>
        </div>

        <div className="rounded-xl border bg-card p-6 shadow-sm">
          <h2 className="mb-6 text-xl font-semibold text-foreground">Вариации и остатки</h2>

          {variants.length === 0 && (
            <p className="mb-4 text-sm text-muted-foreground">Вариации ещё не добавлены.</p>
          )}

          {variants.map((variant, idx) => (
            <div key={idx} className="mb-6 grid gap-4 md:grid-cols-5">
              {([
                { prop: 'size', placeholder: 'Размер' },
                { prop: 'color', placeholder: 'Цвет' },
                { prop: 'sku', placeholder: 'SKU' },
                { prop: 'stock', placeholder: 'Остаток', type: 'number' as const },
                { prop: 'price', placeholder: 'Цена', type: 'number' as const },
              ] as const).map((field) => {
                const inputType = (field as any).type ?? 'text'
                const isNumberField = (field as any).type === 'number'
                return (
                  <Input
                    key={field.prop}
                    type={inputType}
                    placeholder={field.placeholder}
                    value={(variant as any)[field.prop] ?? ''}
                    onChange={(e) => {
                      const value = isNumberField ? Number(e.target.value) : e.target.value
                      setVariants((prev) => {
                        const copy = [...prev]
                        ;(copy[idx] as any)[field.prop] = value === '' ? undefined : value
                        return copy
                      })
                    }}
                    className="focus:border-primary focus:ring-1 focus:ring-primary"
                  />
                )
              })}
              {/* Remove btn */}
              <Button
                type="button"
                variant="destructive"
                size="icon"
                onClick={() => setVariants((prev) => prev.filter((_, i) => i !== idx))}
              >
                ×
              </Button>
            </div>
          ))}

          <Button type="button" onClick={() => setVariants((prev) => [...prev, { stock: 0 }] as VariantCreate[])}>
            + Добавить вариацию
          </Button>
        </div>

        <div className="flex justify-end gap-3">
          <Button
            type="button"
            variant="outline"
            onClick={() => navigate('/admin/items')}
            className="border-muted-foreground/30 hover:bg-muted/50"
          >
            Отмена
          </Button>
          <Button 
            type="submit" 
            disabled={submitting}
            className="bg-primary hover:bg-primary/90"
          >
            {submitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            <Save className={cn('h-4 w-4', !submitting && 'mr-2')} />
            {submitting ? 'Сохранение...' : 'Сохранить'}
          </Button>
        </div>
      </form>
    </motion.div>
  )
}

export default ItemForm
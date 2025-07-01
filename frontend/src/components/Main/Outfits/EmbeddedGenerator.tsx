import React, { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../ui/card'
import { Button } from '../../ui/button'
import { Input } from '../../ui/input'
import { Label } from '../../ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../ui/select'
import { Badge } from '../../ui/badge'
import { LoadingSpinner } from '../../ui/LoadingSpinner'
import { useToast } from '../../ui/use-toast'
import { 
  generateOutfitFromItems,
  generateRandomOutfit,
  type OutfitGenerationFromItemsRequest,
  type RandomOutfitGenerationRequest
} from '../../../api/outfits'
import { listItems } from '../../../api/items'
import { Wand2, Shuffle, CheckSquare, Search, X } from 'lucide-react'

interface EmbeddedGeneratorProps {
  onOutfitGenerated?: (outfitId: number) => void
}

interface GenerationFormData {
  style: string
  occasion: string
  budget: string
  collection: string
  additional_categories: string
}

const STYLE_OPTIONS = [
  'casual', 'formal', 'business', 'sporty', 'elegant', 'trendy', 
  'vintage', 'minimalist', 'bohemian', 'streetwear'
]

const OCCASION_OPTIONS = [
  'work', 'party', 'date', 'casual', 'formal event', 'business meeting',
  'weekend', 'vacation', 'gym', 'shopping', 'dinner'
]

export const EmbeddedGenerator: React.FC<EmbeddedGeneratorProps> = ({ onOutfitGenerated }) => {
  const [isGenerating, setIsGenerating] = useState(false)
  const [generatedOutfit, setGeneratedOutfit] = useState<any>(null)
  const [selectedItems, setSelectedItems] = useState<any[]>([])
  const [searchItems, setSearchItems] = useState('')
  const [availableItems, setAvailableItems] = useState<any[]>([])
  const [showItemSelector, setShowItemSelector] = useState(false)
  
  const { toast } = useToast()
  
  const { register, handleSubmit, setValue } = useForm<GenerationFormData>({
    defaultValues: {
      style: 'casual',
      occasion: 'casual',
      budget: '',
      collection: '',
      additional_categories: ''
    }
  })



  const handleGenerateFromItems = async (data: GenerationFormData) => {
    if (selectedItems.length === 0) {
      toast({
        title: "Выберите товары",
        description: "Для этого типа генерации нужно выбрать хотя бы одну вещь",
        variant: "destructive",
      })
      return
    }

    setIsGenerating(true)
    
    try {
      const request: OutfitGenerationFromItemsRequest = {
        selected_item_ids: selectedItems.map(item => item.id),
        style: data.style,
        occasion: data.occasion,
        additional_categories: data.additional_categories ? data.additional_categories.split(',').map(c => c.trim()) : undefined
      }
      
      const result = await generateOutfitFromItems(request)
      
      // Синхронная обработка результата
      if (result.status === 'completed' && result.result) {
        setGeneratedOutfit(result.result)
        if (result.result.outfit_id && onOutfitGenerated) {
          onOutfitGenerated(result.result.outfit_id)
        }
        toast({
          title: "Готово!",
          description: "Образ создан успешно",
          variant: "default",
        })
      } else {
        throw new Error(result.message || 'Неизвестная ошибка')
      }
    } catch (error: any) {
      toast({
        title: "Ошибка",
        description: error.message || "Не удалось создать образ",
        variant: "destructive",
      })
    } finally {
      setIsGenerating(false)
    }
  }

  const handleGenerateRandom = async (data: GenerationFormData) => {
    setIsGenerating(true)
    
    try {
      const request: RandomOutfitGenerationRequest = {
        style: data.style,
        occasion: data.occasion,
        budget: data.budget ? parseFloat(data.budget) : undefined,
        collection: data.collection || undefined
      }
      
      const result = await generateRandomOutfit(request)
      
      // Синхронная обработка результата
      if (result.status === 'completed' && result.result) {
        setGeneratedOutfit(result.result)
        if (result.result.outfit_id && onOutfitGenerated) {
          onOutfitGenerated(result.result.outfit_id)
        }
        toast({
          title: "Готово!",
          description: "Случайный образ создан успешно",
          variant: "default",
        })
      } else {
        throw new Error(result.message || 'Неизвестная ошибка')
      }
    } catch (error: any) {
      toast({
        title: "Ошибка",
        description: error.message || "Не удалось создать образ",
        variant: "destructive",
      })
    } finally {
      setIsGenerating(false)
    }
  }

  const searchForItems = async () => {
    try {
      const items = await listItems({ q: searchItems, limit: 20 })
      setAvailableItems(items)
    } catch (error) {
      toast({
        title: "Ошибка",
        description: "Не удалось найти товары",
        variant: "destructive",
      })
    }
  }

  const toggleItemSelection = (item: any) => {
    if (selectedItems.find(selected => selected.id === item.id)) {
      setSelectedItems(selectedItems.filter(selected => selected.id !== item.id))
    } else {
      setSelectedItems([...selectedItems, item])
    }
  }

  const removeSelectedItem = (itemId: number) => {
    setSelectedItems(selectedItems.filter(item => item.id !== itemId))
  }

  return (
    <Card className="mb-8">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Wand2 className="w-5 h-5 text-purple-600" />
          AI Генератор Образов
        </CardTitle>
        <CardDescription>
          Создавайте стильные образы из выбранных вещей или позвольте AI удивить вас случайным сочетанием
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Common Form Fields */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label htmlFor="style">Стиль</Label>
            <Select onValueChange={(value) => setValue('style', value)}>
              <SelectTrigger>
                <SelectValue placeholder="Выберите стиль" />
              </SelectTrigger>
              <SelectContent>
                {STYLE_OPTIONS.map((style) => (
                  <SelectItem key={style} value={style}>
                    {style}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="occasion">Повод</Label>
            <Select onValueChange={(value) => setValue('occasion', value)}>
              <SelectTrigger>
                <SelectValue placeholder="Выберите повод" />
              </SelectTrigger>
              <SelectContent>
                {OCCASION_OPTIONS.map((occasion) => (
                  <SelectItem key={occasion} value={occasion}>
                    {occasion}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label htmlFor="budget">Бюджет (для случайной генерации)</Label>
            <Input
              {...register('budget')}
              type="number"
              placeholder="Максимальная сумма"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="collection">Коллекция</Label>
            <Input
              {...register('collection')}
              placeholder="Название коллекции"
            />
          </div>
        </div>

        {/* Item Selection Section */}
        <div className="border-t pt-6">
          <div className="flex items-center justify-between mb-4">
            <h4 className="font-medium">Выбранные вещи ({selectedItems.length})</h4>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowItemSelector(!showItemSelector)}
              className="flex items-center gap-2"
            >
              <CheckSquare className="w-4 h-4" />
              {showItemSelector ? 'Скрыть' : 'Выбрать товары'}
            </Button>
          </div>

          {/* Selected Items Display */}
          {selectedItems.length > 0 && (
            <div className="flex flex-wrap gap-2 mb-4">
              {selectedItems.map((item) => (
                <Badge
                  key={item.id}
                  variant="default"
                  className="flex items-center gap-2 py-1 px-3"
                >
                  {item.name}
                  <button
                    onClick={() => removeSelectedItem(item.id)}
                    className="ml-1 hover:text-red-500"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </Badge>
              ))}
            </div>
          )}

          {/* Item Selector */}
          {showItemSelector && (
            <div className="border rounded-lg p-4 space-y-4">
              <div className="flex gap-2">
                <Input
                  placeholder="Поиск товаров..."
                  value={searchItems}
                  onChange={(e) => setSearchItems(e.target.value)}
                  className="flex-1"
                />
                <Button onClick={searchForItems} size="icon">
                  <Search className="w-4 h-4" />
                </Button>
              </div>

              {availableItems.length > 0 && (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 max-h-64 overflow-y-auto">
                  {availableItems.map((item) => {
                    const isSelected = selectedItems.find(selected => selected.id === item.id)
                    return (
                      <div
                        key={item.id}
                        onClick={() => toggleItemSelection(item)}
                        className={`border rounded-lg p-3 cursor-pointer transition-all ${
                          isSelected 
                            ? 'border-purple-500 bg-purple-50' 
                            : 'border-gray-200 hover:border-gray-300'
                        }`}
                      >
                        <div className="flex items-center gap-3">
                          {item.image_url && (
                            <img 
                              src={item.image_url} 
                              alt={item.name}
                              className="w-12 h-12 object-cover rounded"
                            />
                          )}
                          <div className="flex-1 min-w-0">
                            <h5 className="font-medium text-sm truncate">{item.name}</h5>
                            <p className="text-xs text-gray-500">{item.category}</p>
                            {item.price && (
                              <p className="text-xs font-medium">{item.price} ₽</p>
                            )}
                          </div>
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          )}
        </div>

        <div className="space-y-2">
          <Label htmlFor="additional_categories">Дополнительные категории (для генерации из выбранных вещей)</Label>
          <Input
            {...register('additional_categories')}
            placeholder="footwear, accessories"
          />
        </div>

        {/* Generation Buttons */}
        <div className="flex flex-col sm:flex-row gap-3 pt-4 border-t">
          <Button 
            onClick={handleSubmit(handleGenerateFromItems)}
            disabled={isGenerating}
            className="flex-1 flex items-center gap-2 bg-purple-600 hover:bg-purple-700"
          >
            {isGenerating ? (
              <LoadingSpinner className="w-4 h-4" />
            ) : (
              <CheckSquare className="w-4 h-4" />
            )}
            Создать из выбранных ({selectedItems.length})
          </Button>
          
          <Button 
            onClick={handleSubmit(handleGenerateRandom)}
            disabled={isGenerating}
            variant="outline"
            className="flex-1 flex items-center gap-2 border-orange-200 text-orange-700 hover:bg-orange-50"
          >
            {isGenerating ? (
              <LoadingSpinner className="w-4 h-4" />
            ) : (
              <Shuffle className="w-4 h-4" />
            )}
            Случайный образ
          </Button>
        </div>

        {/* Result Display */}
        {generatedOutfit && (
          <div className="border-t pt-6">
            <div className="bg-green-50 p-4 rounded-lg border border-green-200">
              <h4 className="font-medium text-green-900 mb-2">
                ✨ {generatedOutfit.outfit_name || 'Новый образ'}
              </h4>
              <p className="text-sm text-green-800 mb-2">
                {generatedOutfit.description}
              </p>
              {generatedOutfit.total_price && (
                <Badge className="bg-green-100 text-green-800 mb-2">
                  {generatedOutfit.total_price} ₽
                </Badge>
              )}
              {generatedOutfit.style_notes && (
                <div className="mt-3 p-3 bg-blue-50 rounded border border-blue-200">
                  <p className="text-sm text-blue-800">
                    <strong>💡 Совет стилиста:</strong> {generatedOutfit.style_notes}
                  </p>
                </div>
              )}
              {generatedOutfit.surprise_factor && (
                <div className="mt-3 p-3 bg-orange-50 rounded border border-orange-200">
                  <p className="text-sm text-orange-800">
                    <strong>🎭 Изюминка:</strong> {generatedOutfit.surprise_factor}
                  </p>
                </div>
              )}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
} 
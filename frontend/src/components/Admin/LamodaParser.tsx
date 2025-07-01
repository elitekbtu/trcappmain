import { useState } from 'react'
import { motion } from 'framer-motion'
import { Loader2, Globe, Package, AlertCircle, CheckCircle, Plus, Search, Link, List, Zap } from 'lucide-react'
import api from '../../api/client'
import { Button } from '../../components/ui/button'
import { Input } from '../../components/ui/input'
import { Label } from '../../components/ui/label'
import { useToast } from '../../components/ui/use-toast'
import { Checkbox } from '../../components/ui'
import { Textarea } from '../../components/ui/textarea'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../../components/ui/tabs'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../components/ui/card'
import { Badge } from '../../components/ui/badge'

interface ParsedProduct {
  sku: string
  name: string
  brand: string
  price: number
  old_price?: number | null
  url: string
  image_url: string
  image_urls: string[]
  type?: string
  description?: string
}

interface ParseResponse {
  success: boolean
  message: string
  product?: ParsedProduct
  item_id?: number
}

interface BatchParseResult {
  url: string
  success: boolean
  message: string
  product?: ParsedProduct
  item_id?: number
  error?: string
}

interface BatchParseResponse {
  total_requested: number
  successful: number
  failed: number
  results: BatchParseResult[]
  summary: string
}

interface BatchSearchResponse {
  query: string
  total_found: number
  requested_limit: number
  successful: number
  failed: number
  products: ParsedProduct[]
  summary: string
}

const LamodaParser = () => {
  const [url, setUrl] = useState('')
  const [urls, setUrls] = useState('')
  const [searchQuery, setSearchQuery] = useState('')
  const [quickSearchQuery, setQuickSearchQuery] = useState('')
  const [searchLimit, setSearchLimit] = useState(10)
  const [domain, setDomain] = useState('kz')
  const [saveToDb, setSaveToDb] = useState(true)
  const [loading, setLoading] = useState(false)
  const [results, setResults] = useState<ParsedProduct[]>([])
  const [batchResults, setBatchResults] = useState<BatchParseResult[]>([])
  const [activeTab, setActiveTab] = useState('quick')
  const { toast } = useToast()

  const handleQuickSearch = async () => {
    if (!quickSearchQuery.trim()) {
      toast({
        title: "Ошибка",
        description: "Введите название товара для поиска",
        variant: "destructive",
      })
      return
    }

    setLoading(true)
    setResults([])
    
    try {
      // Автоматически используем разумные настройки для быстрого поиска
      const response = await api.post('/api/lamoda/batch-search', {
        query: quickSearchQuery.trim(),
        limit: 20,  // Больше товаров для лучшего выбора
        domain: domain,
        save_to_db: true  // Всегда сохраняем при быстром поиске
      })

      const data: BatchSearchResponse = response.data
      setResults(data.products)

      if (data.successful > 0) {
        toast({
          title: "✅ Готово!",
          description: `Найдено и добавлено ${data.successful} товаров по запросу "${quickSearchQuery}"`,
        })
      } else {
        toast({
          title: "🔍 Ничего не найдено",
          description: `По запросу "${quickSearchQuery}" товары не найдены`,
          variant: "destructive",
        })
      }
    } catch (error: any) {
      console.error('Quick search error:', error)
      toast({
        title: "Ошибка",
        description: error.response?.data?.detail || "Произошла ошибка при поиске товаров",
        variant: "destructive",
      })
    } finally {
      setLoading(false)
    }
  }

  const handleSingleParse = async () => {
    if (!url.trim()) {
      toast({
        title: "Ошибка",
        description: "Введите URL товара",
        variant: "destructive",
      })
      return
    }

    setLoading(true)
    try {
      const response = await api.post('/api/lamoda/parse-url', {
        url: url.trim(),
        save_to_db: saveToDb
      })

      const data: ParseResponse = response.data

      if (data.success && data.product) {
        setResults([data.product])
        toast({
          title: "Успех",
          description: data.message,
        })
      } else {
        toast({
          title: "Ошибка",
          description: data.message,
          variant: "destructive",
        })
      }
    } catch (error: any) {
      console.error('Parse error:', error)
      toast({
        title: "Ошибка",
        description: error.response?.data?.detail || "Произошла ошибка при парсинге",
        variant: "destructive",
      })
    } finally {
      setLoading(false)
    }
  }

  const handleBatchParse = async () => {
    const urlList = urls.trim().split('\n').filter(u => u.trim())
    
    if (urlList.length === 0) {
      toast({
        title: "Ошибка",
        description: "Введите хотя бы один URL товара (по одному на строку)",
        variant: "destructive",
      })
      return
    }

    if (urlList.length > 10) {
      toast({
        title: "Ошибка",
        description: "Максимум 10 URL за один раз",
        variant: "destructive",
      })
      return
    }

    setLoading(true)
    setBatchResults([])
    
    try {
      const response = await api.post('/api/lamoda/parse-urls', {
        urls: urlList,
        save_to_db: saveToDb
      })

      const data: BatchParseResponse = response.data
      setBatchResults(data.results)
      
      // Собираем успешно распарсенные товары
      const successfulProducts = data.results
        .filter(r => r.success && r.product)
        .map(r => r.product!)
      
      setResults(successfulProducts)

      toast({
        title: data.successful > 0 ? "Завершено" : "Ошибка",
        description: data.summary,
        variant: data.successful > 0 ? "default" : "destructive",
      })
    } catch (error: any) {
      console.error('Batch parse error:', error)
      toast({
        title: "Ошибка",
        description: error.response?.data?.detail || "Произошла ошибка при массовом парсинге",
        variant: "destructive",
      })
    } finally {
      setLoading(false)
    }
  }

  const handleBatchSearch = async () => {
    if (!searchQuery.trim()) {
      toast({
        title: "Ошибка",
        description: "Введите поисковый запрос",
        variant: "destructive",
      })
      return
    }

    setLoading(true)
    setResults([])
    
    try {
      const response = await api.post('/api/lamoda/batch-search', {
        query: searchQuery.trim(),
        limit: searchLimit,
        domain: domain,
        save_to_db: saveToDb
      })

      const data: BatchSearchResponse = response.data
      setResults(data.products)

      toast({
        title: data.successful > 0 ? "Завершено" : "Информация",
        description: data.summary,
      })
    } catch (error: any) {
      console.error('Batch search error:', error)
      toast({
        title: "Ошибка",
        description: error.response?.data?.detail || "Произошла ошибка при поиске товаров",
        variant: "destructive",
      })
    } finally {
      setLoading(false)
    }
  }

  const formatPrice = (price: number) => {
    return new Intl.NumberFormat('ru-RU').format(price)
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !loading) {
      if (activeTab === 'quick') {
        handleQuickSearch()
      }
    }
  }

  return (
    <div className="space-y-6">
      <div className="mb-6">
        <h1 className="flex items-center gap-2 text-3xl font-bold tracking-tight">
          <Globe className="w-6 h-6" />
          Парсер Lamoda
        </h1>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="quick" className="flex items-center gap-2">
            <Zap className="w-4 h-4" />
            Быстрый поиск
          </TabsTrigger>
          <TabsTrigger value="single" className="flex items-center gap-2">
            <Link className="w-4 h-4" />
            Один товар
          </TabsTrigger>
          <TabsTrigger value="batch" className="flex items-center gap-2">
            <List className="w-4 h-4" />
            Несколько URL
          </TabsTrigger>
          <TabsTrigger value="search" className="flex items-center gap-2">
            <Search className="w-4 h-4" />
            Расширенный поиск
          </TabsTrigger>
        </TabsList>

        {/* Общие настройки */}
        <div className="mb-4 p-4 bg-gray-50 rounded-lg">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <Label htmlFor="domain">Домен:</Label>
              <select
                id="domain"
                value={domain}
                onChange={(e) => setDomain(e.target.value)}
                className="px-3 py-1 border rounded"
              >
                <option value="kz">Казахстан (kz)</option>
                <option value="ru">Россия (ru)</option>
                <option value="by">Беларусь (by)</option>
              </select>
            </div>
            
            {activeTab !== 'quick' && (
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="save-to-db"
                  checked={saveToDb}
                  onCheckedChange={(checked: boolean) => setSaveToDb(checked)}
                />
                <Label htmlFor="save-to-db">Сохранить в базу данных</Label>
              </div>
            )}
          </div>
        </div>

        <TabsContent value="quick" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Zap className="w-5 h-5" />
                Быстрый поиск товаров
              </CardTitle>
              <CardDescription>
                Просто введите название товара и мы найдем и добавим все подходящие товары автоматически
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label htmlFor="quick-search" className="text-base font-medium">
                  Что ищем?
                </Label>
                <Input
                  id="quick-search"
                  placeholder="пальто, кроссовки nike, джинсы..."
                  value={quickSearchQuery}
                  onChange={(e) => setQuickSearchQuery(e.target.value)}
                  onKeyPress={handleKeyPress}
                  disabled={loading}
                  className="text-lg py-3 mt-2"
                />
                <p className="text-sm text-gray-500 mt-1">
                  Нажмите Enter или кнопку ниже для поиска
                </p>
              </div>

              <Button 
                onClick={handleQuickSearch} 
                disabled={loading}
                className="w-full py-3 text-lg"
                size="lg"
              >
                {loading ? (
                  <>
                    <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                    Ищем товары...
                  </>
                ) : (
                  <>
                    <Zap className="mr-2 h-5 w-5" />
                    Найти и добавить товары
                  </>
                )}
              </Button>

              <div className="grid grid-cols-2 gap-4 pt-2">
                <div className="text-center p-3 bg-white rounded-lg border">
                  <div className="text-2xl font-bold text-green-600">~20</div>
                  <div className="text-sm text-gray-600">товаров за поиск</div>
                </div>
                <div className="text-center p-3 bg-white rounded-lg border">
                  <div className="text-2xl font-bold text-blue-600">AUTO</div>
                  <div className="text-sm text-gray-600">сохранение в БД</div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="single" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Парсинг одного товара</CardTitle>
              <CardDescription>
                Введите URL товара с Lamoda для парсинга
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label htmlFor="product-url">URL товара</Label>
                <Input
                  id="product-url"
                  placeholder="https://www.lamoda.kz/p/..."
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  disabled={loading}
                />
              </div>

              <Button 
                onClick={handleSingleParse} 
                disabled={loading}
                className="w-full"
              >
                {loading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Парсинг...
                  </>
                ) : (
                  <>
                    <Package className="mr-2 h-4 w-4" />
                    Распарсить товар
                  </>
                )}
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="batch" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Массовый парсинг товаров</CardTitle>
              <CardDescription>
                Введите список URL товаров (по одному на строку, максимум 10)
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label htmlFor="product-urls">URL товаров (по одному на строку)</Label>
                <Textarea
                  id="product-urls"
                  placeholder={`https://www.lamoda.kz/p/rtlaek537801/
https://www.lamoda.kz/p/another-product/
https://www.lamoda.kz/p/third-product/`}
                  value={urls}
                  onChange={(e) => setUrls(e.target.value)}
                  disabled={loading}
                  rows={6}
                />
              </div>

              <Button 
                onClick={handleBatchParse} 
                disabled={loading}
                className="w-full"
              >
                {loading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Парсинг...
                  </>
                ) : (
                  <>
                    <Plus className="mr-2 h-4 w-4" />
                    Распарсить все товары
                  </>
                )}
              </Button>

              {/* Результаты массового парсинга */}
              {batchResults.length > 0 && (
                <div className="mt-6">
                  <h3 className="text-lg font-semibold mb-4">Результаты парсинга</h3>
                  <div className="space-y-2 max-h-60 overflow-y-auto">
                    {batchResults.map((result, index) => (
                      <div
                        key={index}
                        className={`p-3 rounded-lg border ${result.success 
                          ? 'bg-green-50 border-green-200' 
                          : 'bg-red-50 border-red-200'
                        }`}
                      >
                        <div className="flex items-center gap-2 mb-1">
                          {result.success ? (
                            <CheckCircle className="w-4 h-4 text-green-600" />
                          ) : (
                            <AlertCircle className="w-4 h-4 text-red-600" />
                          )}
                          <span className="font-medium text-sm">
                            {result.success ? 'Успех' : 'Ошибка'}
                          </span>
                        </div>
                        <p className="text-sm text-gray-600 break-all mb-1">{result.url}</p>
                        <p className="text-sm">{result.message}</p>
                        {result.product && (
                          <p className="text-xs text-gray-500 mt-1">
                            {result.product.brand} - {result.product.name}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="search" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Расширенный поиск товаров</CardTitle>
              <CardDescription>
                Найти товары по запросу с настройками количества и сохранения
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label htmlFor="search-query">Поисковый запрос</Label>
                <Input
                  id="search-query"
                  placeholder="nike кроссовки"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  disabled={loading}
                />
              </div>

              <div>
                <Label htmlFor="search-limit">Максимум товаров</Label>
                <Input
                  id="search-limit"
                  type="number"
                  min="1"
                  max="50"
                  value={searchLimit}
                  onChange={(e) => setSearchLimit(Math.max(1, Math.min(50, Number(e.target.value))))}
                  disabled={loading}
                />
              </div>

              <Button 
                onClick={handleBatchSearch} 
                disabled={loading}
                className="w-full"
              >
                {loading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Поиск и добавление...
                  </>
                ) : (
                  <>
                    <Search className="mr-2 h-4 w-4" />
                    Найти и добавить товары
                  </>
                )}
              </Button>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Результаты */}
      {results.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="space-y-4"
        >
          <h3 className="text-xl font-semibold flex items-center gap-2">
            <Package className="w-5 h-5" />
            Добавленные товары ({results.length})
          </h3>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {results.map((product, index) => (
              <motion.div
                key={`${product.sku}-${index}`}
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: index * 0.1 }}
                className="bg-white rounded-lg shadow-md overflow-hidden hover:shadow-lg transition-shadow"
              >
                <div className="aspect-square relative">
                  <img
                    src={product.image_url}
                    alt={product.name}
                    className="w-full h-full object-cover"
                    onError={(e) => {
                      (e.target as HTMLImageElement).src = '/placeholder-image.jpg'
                    }}
                  />
                  {product.old_price && (
                    <Badge className="absolute top-2 right-2 bg-red-500">
                      Скидка
                    </Badge>
                  )}
                </div>
                <div className="p-4">
                  <div className="flex items-center justify-between mb-2">
                    <Badge variant="outline">{product.brand}</Badge>
                    <Badge variant="secondary" className="text-xs">
                      {product.sku}
                    </Badge>
                  </div>
                  <h4 className="font-medium text-sm mb-2 line-clamp-2">
                    {product.name}
                  </h4>
                  {product.description && (
                    <p className="text-xs text-gray-500 line-clamp-2 mb-2">
                      {product.description}
                    </p>
                  )}
                  <div className="flex items-center gap-2 mb-2">
                    <span className="font-bold text-lg text-green-600">
                      {formatPrice(product.price)} ₸
                    </span>
                    {product.old_price && (
                      <span className="text-sm text-gray-500 line-through">
                        {formatPrice(product.old_price)} ₸
                      </span>
                    )}
                  </div>
                  {product.type && (
                    <Badge variant="outline" className="text-xs">
                      {product.type}
                    </Badge>
                  )}
                  <div className="mt-2">
                    <a
                      href={product.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-600 hover:text-blue-800 text-xs"
                    >
                      Посмотреть на Lamoda →
                    </a>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        </motion.div>
      )}
    </div>
  )
}

export default LamodaParser 
import api from './client'
import {
  type OutfitCommentCreate,
  type OutfitCommentOut,
  type OutfitCreate,
  type OutfitOut,
  type OutfitUpdate,
} from './schemas'

export interface ListOutfitsParams {
  skip?: number
  limit?: number
  q?: string
  style?: string
  collection?: string
  min_price?: number
  max_price?: number
  sort_by?: string
}

export const listOutfits = async (params: ListOutfitsParams = {}) => {
  const resp = await api.get<OutfitOut[]>('/api/outfits/', { params })
  return resp.data
}

export const getOutfit = async (id: number) => {
  const resp = await api.get<OutfitOut>(`/api/outfits/${id}`)
  return resp.data
}

export const createOutfit = async (data: OutfitCreate) => {
  const resp = await api.post<OutfitOut>('/api/outfits/', data)
  return resp.data
}

export const updateOutfit = async (id: number, data: OutfitUpdate) => {
  const resp = await api.put<OutfitOut>(`/api/outfits/${id}`, data)
  return resp.data
}

export const deleteOutfit = async (id: number) => {
  await api.delete(`/api/outfits/${id}`)
}

// ---------- Trending ----------

export const trendingOutfits = async (limit?: number) => {
  const resp = await api.get<OutfitOut[]>('/api/outfits/trending', { params: { limit } })
  return resp.data
}

// ---------- Favorites ----------

export const toggleFavoriteOutfit = async (id: number) => {
  await api.post(`/api/outfits/${id}/favorite`)
}

export const listFavoriteOutfits = async () => {
  const resp = await api.get<OutfitOut[]>('/api/outfits/favorites')
  return resp.data
}

// ---------- View History ----------

export const viewedOutfits = async (limit = 50) => {
  const resp = await api.get<OutfitOut[]>('/api/outfits/history', { params: { limit } })
  return resp.data
}

export const clearOutfitViewHistory = async () => {
  await api.delete('/api/outfits/history')
}

// ---------- Comments ----------

export const listOutfitComments = async (outfitId: number) => {
  const resp = await api.get<OutfitCommentOut[]>(`/api/outfits/${outfitId}/comments`)
  return resp.data
}

export const addOutfitComment = async (outfitId: number, data: OutfitCommentCreate) => {
  const resp = await api.post<OutfitCommentOut>(`/api/outfits/${outfitId}/comments`, data)
  return resp.data
}

export const likeOutfitComment = async (outfitId: number, commentId: number) => {
  await api.post(`/api/outfits/${outfitId}/comments/${commentId}/like`)
}

// ---------- Delete Comment ----------

export const deleteOutfitComment = async (outfitId: number, commentId: number) => {
  await api.delete(`/api/outfits/${outfitId}/comments/${commentId}`)
}

// ---------- Простой генератор образов ----------

export interface OutfitGenerationFromItemsRequest {
  selected_item_ids: number[]
  style: string
  occasion: string
  additional_categories?: string[]
}

export interface RandomOutfitGenerationRequest {
  style: string
  occasion: string
  budget?: number
  collection?: string
}

export interface GenerationResult {
  status: 'completed' | 'failed'
  result?: {
    outfit_id: number
    outfit_name: string
    description: string
    total_price: number
    style_notes: string
    selected_items: number[]
    user_items_included?: number[]
    suggested_additions?: number[]
    surprise_factor?: string
  }
  message?: string
  error?: string
}

// Генерация из выбранных товаров
export const generateOutfitFromItems = async (data: OutfitGenerationFromItemsRequest): Promise<GenerationResult> => {
  const resp = await api.post<GenerationResult>('/api/outfits/generate-from-items', data)
  return resp.data
}

// Случайная генерация
export const generateRandomOutfit = async (data: RandomOutfitGenerationRequest): Promise<GenerationResult> => {
  const resp = await api.post<GenerationResult>('/api/outfits/generate-random', data)
  return resp.data
} 
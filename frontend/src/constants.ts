export const CLOTHING_TYPES = ['top', 'bottom', 'accessories', 'footwear', 'fragrances'] as const;
export type ClothingType = (typeof CLOTHING_TYPES)[number]; 
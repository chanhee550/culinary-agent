export interface Ingredient {
  id: number | string | null;
  name: string;
  category: string;
  quantity: string | null;
  expiry_date?: string | null;
  source: string;
}

export interface ConfirmedItem {
  name: string;
  category: string;
  quantity?: string;
}

export interface UnknownItem {
  id: number;
  description: string;
  guess?: string;
  location?: string;
  image_index?: number;
}

export interface ScanResult {
  confirmed: ConfirmedItem[];
  unknowns: UnknownItem[];
  errors?: string[];
}

export interface Recipe {
  name: string;
  description: string;
  ingredients: string[];
  missing: string[];
  instructions: string[];
  difficulty: "쉬움" | "보통" | "어려움";
  time: string;
  substitutions?: Record<string, string>;
}

export const CATEGORIES = [
  "채소", "과일", "육류", "해산물", "유제품",
  "양념/소스", "곡류/면", "음료", "냉동식품", "기타",
] as const;

export type Category = (typeof CATEGORIES)[number];

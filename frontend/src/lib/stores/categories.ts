import { writable } from 'svelte/store';
import { api } from '$lib/api';

export interface Category {
  id: number;
  name: string;
  type: string;
  is_active: boolean;
}

export interface SubCategory {
  id: number;
  category_id: number;
  name: string;
  is_active: boolean;
}

export const categories = writable<Category[]>([]);
export const subCategories = writable<SubCategory[]>([]);

export async function loadCategories() {
  try {
    const cats = await api<Category[]>('/budget/categories');
    categories.set(cats || []);
    const subs = await api<SubCategory[]>('/budget/subcategories');
    subCategories.set(subs || []);
  } catch {
    // ignore
  }
}

import { writable } from 'svelte/store';
import { browser } from '$app/environment';
import type { SiteReport } from '../types';

const STORAGE_KEY_HISTORY = 'webdna_history';
const STORAGE_KEY_FAVORITES = 'webdna_favorites';

function createPersistedStore<T>(key: string, startValue: T) {
  const initialValue = browser ? JSON.parse(localStorage.getItem(key) || JSON.stringify(startValue)) : startValue;
  const { subscribe, set, update } = writable<T>(initialValue);

  return {
    subscribe,
    set: (value: T) => {
      if (browser) localStorage.setItem(key, JSON.stringify(value));
      set(value);
    },
    update: (fn: (v: T) => T) => {
      update((v) => {
        const newValue = fn(v);
        if (browser) localStorage.setItem(key, JSON.stringify(newValue));
        return newValue;
      });
    }
  };
}

export const history = createPersistedStore<SiteReport[]>(STORAGE_KEY_HISTORY, []);
export const favorites = createPersistedStore<SiteReport[]>(STORAGE_KEY_FAVORITES, []);

export function addToHistory(report: SiteReport) {
  history.update(h => {
    // Map all existing items to lightweight versions to fix any old giant objects causing QuotaExceededError
    const lightweightH = h.map(item => ({
      domain: item.domain,
      name: item.name,
      favicon: item.favicon,
      ogImage: item.ogImage,
      description: item.description,
      updatedAt: item.updatedAt
    } as SiteReport));
    
    const filtered = lightweightH.filter(item => item.domain !== report.domain);
    const lightweightReport = {
      domain: report.domain,
      name: report.name,
      favicon: report.favicon,
      ogImage: report.ogImage,
      description: report.description,
      updatedAt: report.updatedAt
    } as SiteReport;
    return [lightweightReport, ...filtered].slice(0, 20);
  });
}

export function toggleFavorite(report: SiteReport) {
  favorites.update(f => {
    // Map all existing items to lightweight versions to fix any old giant objects
    const lightweightF = f.map(item => ({
      domain: item.domain,
      name: item.name,
      favicon: item.favicon,
      ogImage: item.ogImage,
      description: item.description,
      updatedAt: item.updatedAt
    } as SiteReport));
    
    const exists = lightweightF.find(item => item.domain === report.domain);
    if (exists) {
      return lightweightF.filter(item => item.domain !== report.domain);
    } else {
      const lightweightReport = {
        domain: report.domain,
        name: report.name,
        favicon: report.favicon,
        ogImage: report.ogImage,
        description: report.description,
        updatedAt: report.updatedAt
      } as SiteReport;
      return [lightweightReport, ...lightweightF];
    }
  });
}

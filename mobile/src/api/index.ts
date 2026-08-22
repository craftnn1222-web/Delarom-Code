// Typed API surface for the Delarom mobile app. These mirror the shared
// FastAPI contract consumed by the web frontend.

import { api } from "./client";

// ---------------- Types ----------------
export interface User {
  id: string;
  username: string;
  email: string;
  currency: number;
  role: string;
  status: string;
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface Character {
  id: string;
  user_id: string;
  name: string;
  race: string;
  character_class: string;
  backstory: string;
  powers: string;
  appearance: string;
  nation: string;
  level: number;
  xp: number;
  xp_to_next_level: number;
  strength: number;
  magic: number;
  agility: number;
  endurance: number;
  charisma: number;
  luck: number;
  portrait_url?: string | null;
  created_at: string;
}

export interface CharacterCreate {
  name: string;
  race: string;
  character_class: string;
  backstory: string;
  powers: string;
  appearance: string;
  nation: string;
  strength: number;
  magic: number;
  agility: number;
  endurance: number;
  charisma: number;
  luck: number;
}

export interface Nation {
  slug: string;
  name: string;
  image_url?: string | null;
}

export interface City {
  id: string;
  nation: string;
  slug: string;
  name: string;
  region?: string | null;
  description: string;
  lore?: string | null;
  faction?: string | null;
  has_image: boolean;
}

export interface LocationItem {
  id: string;
  nation: string;
  city?: string | null;
  slug: string;
  name: string;
  location_type?: string | null;
  description: string;
  is_active: boolean;
  is_rp_enabled: boolean;
  has_image: boolean;
  controlling_faction_name?: string | null;
  siege_state?: Record<string, unknown> | null;
}

export interface RpPost {
  id: string;
  nation: string;
  location: string;
  character_name: string;
  action_text: string;
  ai_response?: string | null;
  created_at: string;
}

export interface WorldClock {
  time_of_day?: { phase?: string; icon?: string; vibe?: string };
  calendar?: {
    year_label?: string;
    month_name?: string;
    day?: number;
    formatted?: string;
    compact?: string;
  };
}

// ---------------- Endpoints ----------------
export const AuthApi = {
  login: (email: string, password: string) =>
    api.post<AuthResponse>("/auth/login", { email, password }),
  register: (payload: {
    username: string;
    email: string;
    password: string;
    application_text: string;
  }) => api.post<AuthResponse>("/auth/register", payload),
  me: () => api.get<User>("/auth/me"),
};

export const CharacterApi = {
  list: () => api.get<Character[]>("/characters"),
  get: (id: string) => api.get<Character>(`/characters/${id}`),
  create: (payload: CharacterCreate) => api.post<Character>("/characters", payload),
  uploadImage: (id: string, form: FormData) =>
    api.postForm<{ portrait_url: string }>(`/characters/${id}/upload-image`, form),
};

export const WorldApi = {
  nations: () => api.get<Nation[]>("/nations/images"),
  cities: (nation: string) => api.get<City[]>(`/cities/${nation}`),
  locationsByCity: (nation: string, city: string) =>
    api.get<LocationItem[]>(`/locations/${nation}/${city}/locations`),
  locationsByNation: (nation: string) =>
    api.get<LocationItem[]>(`/locations/${nation}`),
  clock: () => api.get<WorldClock>("/world-clock"),
};

export const RpApi = {
  history: (nation: string, location: string, limit = 50) =>
    api.get<RpPost[]>(`/locations/${nation}/${location}/roleplay?limit=${limit}`),
  submit: (nation: string, location: string, action_text: string) =>
    api.post<{ rp_id: string; ai_response: string; auto_arrest?: unknown }>(
      `/locations/${nation}/${location}/roleplay`,
      { action_text },
    ),
};

// The 4 nations the character-creation endpoint accepts (matches the backend
// Nation enum). Display names are exact enum values.
export const CREATE_NATIONS = ["Ammeonon", "Selindori", "Dhor-Kuldor", "Aigraels"];

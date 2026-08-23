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

export interface ActiveCharacterResponse {
  character: Character | null;
  active_character_id: string | null;
}

export const CharacterApi = {
  list: () => api.get<Character[]>("/characters"),
  get: (id: string) => api.get<Character>(`/characters/${id}`),
  active: () => api.get<ActiveCharacterResponse>("/characters/active"),
  setActive: (id: string) =>
    api.put<{ character: Character; active_character_id: string }>("/characters/active", {
      character_id: id,
    }),
  create: (payload: CharacterCreate) => api.post<Character>("/characters", payload),
  uploadImage: (id: string, form: FormData) =>
    api.postForm<{ portrait_url: string }>(`/characters/${id}/upload-image`, form),
};

export interface ContinueLastScene {
  nation: string;
  location: string;
  location_name: string;
  city: string;
  character_name: string;
  at: string;
}

export interface ContinueActiveParty {
  id: string;
  name: string;
  status: string;
  location: string;
  member_count: number;
}

export interface ContinueState {
  last_scene: ContinueLastScene | null;
  active_party: ContinueActiveParty | null;
}

export const MeApi = {
  continueState: () => api.get<ContinueState>("/me/continue"),
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

// ---------------- Quests ----------------
export interface QuestReward {
  name: string;
  description?: string;
  item_type?: string;
  equipment_slot?: string | null;
  stat_bonuses?: Record<string, number>;
}

export interface Quest {
  id: string;
  creator_id: string;
  creator_username: string;
  title: string;
  description: string;
  difficulty: string;
  reward_currency: number;
  reward_xp: number;
  reward_items: QuestReward[];
  nation: string;
  category?: string | null;
  max_acceptors: number;
  current_acceptors: number;
  status: string;
  image_url?: string | null;
  created_at: string;
}

export interface AcceptedQuest {
  quest: Quest;
  acceptance: {
    id: string;
    status: string;
    accepted_at: string;
    completed_at?: string | null;
    character_id: string;
  };
  character?: { id: string; name: string } | null;
}

export interface QuestAction {
  id: string;
  quest_id: string;
  character_name: string;
  action_text: string;
  ai_response?: string | null;
  turn_number: number;
  created_at: string;
}export const QuestApi = {
  list: (status = "open") => api.get<Quest[]>(`/quests?status=${status}`),
  get: (id: string) => api.get<Quest>(`/quests/${id}`),
  accept: (id: string, character_id: string) =>
    api.post<{ message: string; acceptance_id: string }>(`/quests/${id}/accept`, {
      character_id,
    }),
  myAccepted: () => api.get<AcceptedQuest[]>("/quests/my-quests/accepted"),
  actions: (id: string) => api.get<QuestAction[]>(`/quests/${id}/actions`),
  submitAction: (id: string, action_text: string) =>
    api.post<{ action_id: string; ai_response: string; turn_number: number }>(
      `/quests/${id}/actions`,
      { action_text },
    ),
};

// ---------------- Shops / Marketplace ----------------
export interface Shop {
  id: string;
  owner_id: string;
  owner_username: string;
  name: string;
  description: string;
  nation: string;
  city_slug?: string | null;
  created_at: string;
}

export interface Item {
  id: string;
  shop_id: string;
  name: string;
  description: string;
  price: number;
  stock: number;
  category?: string | null;
  item_type: string;
  equipment_slot?: string | null;
  stat_bonuses?: Record<string, number>;
  is_auto_priced: boolean;
  created_at: string;
}

export interface PurchaseResult {
  message: string;
  item: string;
  list_price: number;
  price_paid: number;
  price_modifier_pct: number;
  new_balance: number;
}

export const ShopApi = {
  list: () => api.get<Shop[]>("/shops"),
  get: (id: string) => api.get<Shop>(`/shops/${id}`),
  items: (id: string) => api.get<Item[]>(`/shops/${id}/items`),
  purchase: (itemId: string, character_id: string) =>
    api.post<PurchaseResult>(`/items/${itemId}/purchase`, { character_id }),
};

// ---------------- Factions ----------------
export interface Faction {
  id: string;
  slug: string;
  name: string;
  nation_home: string;
  motto: string;
  description: string;
  color_hex: string;
  icon: string;
  is_active: boolean;
  is_secret: boolean;
  leader_character_id?: string | null;
  founded_at: string;
  member_count: number;
}

export interface FactionMember {
  id: string;
  character_id: string;
  character_name: string;
  user_id: string;
  faction_id: string;
  faction_slug: string;
  faction_name: string;
  rank: string;
  rank_index: number;
  joined_at: string;
  status: string;
}

export const FactionApi = {
  list: () => api.get<Faction[]>("/factions"),
  get: (slug: string) => api.get<Faction>(`/factions/${slug}`),
  members: (slug: string) => api.get<FactionMember[]>(`/factions/${slug}/members`),
  myMembership: () => api.get<FactionMember[]>("/factions/my/membership"),
  join: (slug: string, character_id: string, pitch?: string) =>
    api.post<FactionMember>(`/factions/${slug}/join`, { character_id, pitch }),
  leave: (slug: string, character_id: string) =>
    api.post<{ ok: boolean; left: string }>(`/factions/${slug}/leave`, { character_id }),
};

// ---------------- Parties ----------------
export interface PartyMember {
  user_id: string;
  username: string;
  character_id: string;
  character_name: string;
  character_race: string;
  character_class: string;
  role: string;
  joined_at: string;
}

export interface Party {
  id: string;
  name: string;
  scene_description: string;
  location: string;
  host_user_id: string;
  host_character_id: string;
  max_members: number;
  members: PartyMember[];
  turn_order: string[];
  current_turn_index: number;
  status: string; // recruiting | active | finished
  created_at: string;
  started_at?: string | null;
  finished_at?: string | null;
}

export interface PartyAction {
  id: string;
  party_id: string;
  turn_number: number;
  actor_user_id: string;
  actor_character_id: string;
  actor_character_name: string;
  action_text: string;
  ai_response?: string | null;
  created_at: string;
}

export const PartyApi = {
  list: (status?: string) => api.get<Party[]>(`/parties${status ? `?status=${status}` : ""}`),
  mine: () => api.get<Party[]>("/parties/mine"),
  get: (id: string) => api.get<Party>(`/parties/${id}`),
  create: (payload: {
    name: string;
    scene_description: string;
    location: string;
    host_character_id: string;
    max_members: number;
  }) => api.post<Party>("/parties", payload),
  join: (id: string, character_id: string) =>
    api.post<Party>(`/parties/${id}/join`, { character_id }),
  leave: (id: string) => api.post<Party>(`/parties/${id}/leave`),
  start: (id: string) => api.post<Party>(`/parties/${id}/start`),
  finish: (id: string) => api.post<Party>(`/parties/${id}/finish`),
  action: (id: string, action_text: string) =>
    api.post<unknown>(`/parties/${id}/action`, { action_text }),
  actions: (id: string) => api.get<PartyAction[]>(`/parties/${id}/actions`),
};

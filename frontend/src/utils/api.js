import axios from 'axios';

/**
 * Auth transport strategy
 * ------------------------------------------------------------------
 * The backend accepts EITHER an httpOnly `access_token` cookie OR an
 * `Authorization: Bearer <token>` header.
 *
 * Production puts a reverse proxy/CDN in front of the API that rewrites
 * `Access-Control-Allow-Origin` to `*`. Per CORS spec, the browser
 * REFUSES to combine `*` with `credentials: include`, so cross-origin
 * cookies are unusable. We use the Bearer header exclusively, with
 * `withCredentials: false` so the browser never enters credentials mode.
 */

const TOKEN_KEY = 'access_token';

export const setAuthToken = (token) => {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
};
export const getAuthToken = () => localStorage.getItem(TOKEN_KEY);

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API_BASE = `${BACKEND_URL}/api`;

const api = axios.create({
  baseURL: API_BASE,
  // IMPORTANT: must be false. When true, the browser enters "credentials
  // include" mode and refuses any response with `Access-Control-Allow-Origin: *`
  // (which the production proxy unfortunately sets). Auth rides on the
  // Authorization header instead — see request interceptor below.
  withCredentials: false,
});

// Inject Bearer header on every outgoing request when a token is present.
api.interceptors.request.use((config) => {
  const token = getAuthToken();
  if (token) {
    config.headers = config.headers || {};
    if (!config.headers.Authorization) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

// Same for raw `axios.*` callers outside the `api` instance.
axios.defaults.withCredentials = false;
axios.interceptors.request.use((config) => {
  const token = getAuthToken();
  if (token && config.url && config.url.includes('/api/')) {
    config.headers = config.headers || {};
    if (!config.headers.Authorization) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

// Auth
export const register = (data) => api.post('/auth/register', data);
export const login = (data) => api.post('/auth/login', data);
export const logout = () => api.post('/auth/logout');
export const getMe = () => api.get('/auth/me');
export const changePassword = (data) => api.post('/auth/change-password', data);

// Phase 2: Letters
export const sendLetter = (data) => api.post('/letters', data);
export const getActiveCharacter = () => api.get('/characters/active');
export const setActiveCharacterApi = (characterId) => api.put('/characters/active', { character_id: characterId });

export const fetchInbox = (characterId) => api.get(`/characters/${characterId}/letters/inbox`);
export const fetchSentLetters = (characterId) => api.get(`/characters/${characterId}/letters/sent`);
export const markLetterRead = (letterId) => api.post(`/letters/${letterId}/read`);

// Phase 2: Tavern Bulletin Board
export const postNotice = (nation, location, data) => api.post(`/locations/${nation}/${location}/notices`, data);
export const fetchNotices = (nation, location) => api.get(`/locations/${nation}/${location}/notices`);
export const deleteNotice = (noticeId) => api.delete(`/notices/${noticeId}`);

// Phase 2: Sworn Bonds
export const fetchBondTypes = () => api.get('/bonds/types');
export const proposeBond = (characterId, data) => api.post(`/characters/${characterId}/bonds/propose`, data);
export const fetchMyBonds = () => api.get('/users/me/bonds');
export const acceptBond = (bondId) => api.post(`/bonds/${bondId}/accept`);
export const declineBond = (bondId) => api.post(`/bonds/${bondId}/decline`);
export const breakBond = (bondId, reason) => api.post(`/bonds/${bondId}/break`, { reason });

// Phase 3: Ballads
export const fetchBallads = (params = {}) => api.get('/ballads', { params });
export const fetchBallad = (id) => api.get(`/ballads/${id}`);
export const commissionBallad = (data) => api.post('/ballads/commission', data);

// Phase 3: Family
export const fetchRelationshipTypes = () => api.get('/family/relationship-types');
export const fetchFamily = (characterId) => api.get(`/characters/${characterId}/family`);
export const addRelative = (characterId, data) => api.post(`/characters/${characterId}/family`, data);
export const updateRelative = (characterId, relativeId, data) => api.patch(`/characters/${characterId}/family/${relativeId}`, data);
export const deleteRelative = (characterId, relativeId) => api.delete(`/characters/${characterId}/family/${relativeId}`);

// Phase 3: Memorial Hall
export const fetchMemorial = (params = {}) => api.get('/memorial', { params });
export const fetchMemorialCharacter = (characterId) => api.get(`/memorial/${characterId}`);
export const retireCharacter = (characterId, cause) => api.post(`/characters/${characterId}/retire`, { cause });

// Phase 4: Dreams
export const fetchDreams = (characterId) => api.get(`/characters/${characterId}/dreams`);
export const sleepAndDream = (characterId) => api.post(`/characters/${characterId}/dream`);

// Phase 4: Prophecy
export const fetchProphecy = (characterId) => api.get(`/characters/${characterId}/prophecy`);
export const receiveProphecy = (characterId, context) => api.post(`/characters/${characterId}/prophecy`, { context });

// Phase 4: Persona / Disguise
export const fetchPersona = (characterId) => api.get(`/characters/${characterId}/persona`);
export const upsertPersona = (characterId, data) => api.put(`/characters/${characterId}/persona`, data);
export const togglePersona = (characterId, active) => api.post(`/characters/${characterId}/persona/toggle`, { active });
export const dropPersona = (characterId) => api.delete(`/characters/${characterId}/persona`);

// Phase 5: Wanted Posters
export const commissionPoster = (bountyId) => api.post(`/bounties/${bountyId}/poster`);
export const getPoster = (bountyId) => api.get(`/bounties/${bountyId}/poster`);

// Phase 5: Whispered Rumors
export const plantRumor = (data) => api.post('/rumors', data);
export const fetchRumors = (params = {}) => api.get('/rumors', { params });
export const fetchMyRumors = (characterId) => api.get(`/characters/${characterId}/rumors/mine`);

// Phase 5: Apprenticeships
export const fetchCrafts = () => api.get('/apprenticeships/crafts');
export const fetchFeaturedMaster = () => api.get('/apprenticeships/featured-master');
export const searchMentors = (params = {}) => api.get('/apprenticeships/mentors', { params });
export const fetchApprenticeships = (characterId) => api.get(`/characters/${characterId}/apprenticeships`);
export const startApprenticeship = (data) => api.post('/apprenticeships', data);
export const recordMilestone = (appId, text) => api.post(`/apprenticeships/${appId}/milestone`, { text });
export const promoteApprentice = (appId, rank) => api.post(`/apprenticeships/${appId}/promote`, { rank });
export const graduateApprentice = (appId) => api.post(`/apprenticeships/${appId}/graduate`);
export const abandonApprenticeship = (appId) => api.post(`/apprenticeships/${appId}/abandon`);

// Characters
export const createCharacter = (data) => api.post('/characters', data);
export const getMyCharacters = () => api.get('/characters');
export const getCharacter = (id) => api.get(`/characters/${id}`);
export const updateCharacter = (id, data) => api.put(`/characters/${id}`, data);
export const deleteCharacter = (id) => api.delete(`/characters/${id}`);

// Quests
export const createQuest = (data) => api.post('/quests', data);
export const getQuests = (params) => api.get('/quests', { params });
export const getQuest = (id) => api.get(`/quests/${id}`);
export const deleteQuest = (id) => api.delete(`/quests/${id}`);
export const acceptQuest = (id, character_id) => api.post(`/quests/${id}/accept`, { character_id });
// Participant completion is now handled exclusively by quest creators via
// /quests/{quest_id}/participants/{acceptance_id}/complete. Kept for potential
// backwards compatibility but not used in the UI.
export const completeQuest = (id) => api.post(`/quests/${id}/complete`);
export const getMyQuests = () => api.get('/quests/my-quests/accepted');
export const getMyCreatedQuests = () => api.get('/quests/my-quests/created');
export const getQuestParticipants = (questId) => api.get(`/quests/${questId}/participants`);
export const creatorCompleteParticipant = (questId, acceptanceId) =>
  api.post(`/quests/${questId}/participants/${acceptanceId}/complete`);

// Wallet
export const getWallet = () => api.get('/wallet');
export const getTransactions = () => api.get('/wallet/transactions');

// Shops
export const createShop = (data) => api.post('/shops', data);
export const getShops = (params) => api.get('/shops', { params });
export const getShop = (id) => api.get(`/shops/${id}`);
export const getMyShop = () => api.get('/shops/my-shop');
export const addItem = (shopId, data) => api.post(`/shops/${shopId}/items`, data);
export const getShopItems = (shopId) => api.get(`/shops/${shopId}/items`);
export const purchaseItem = (itemId, characterId) => api.post(`/items/${itemId}/purchase`, { character_id: characterId });
export const deleteShopItem = (itemId) => api.delete(`/items/${itemId}`);
export const updateShopItem = (itemId, data) => api.put(`/items/${itemId}`, data);

// Forums
export const createForumPost = (data) => api.post('/forums/posts', data);
export const getForumPosts = (params) => api.get('/forums/posts', { params });
export const getForumPost = (id) => api.get(`/forums/posts/${id}`);
export const createReply = (postId, data) => api.post(`/forums/posts/${postId}/replies`, data);
export const getPostReplies = (postId) => api.get(`/forums/posts/${postId}/replies`);

// Image Generation
export const generateQuestImage = (questId) => api.post(`/quests/${questId}/generate-image`);
export const generateCharacterPortrait = (characterId) => api.post(`/characters/${characterId}/generate-portrait`);

// Equipment/Inventory
export const equipItem = (characterId, inventoryItemId) => api.post(`/characters/${characterId}/equip-item`, { inventory_item_id: inventoryItemId });
export const unequipItem = (characterId, equipmentSlot) => api.post(`/characters/${characterId}/unequip-item`, { equipment_slot: equipmentSlot });
export const getCharacterStats = (characterId) => api.get(`/characters/${characterId}/stats`);

// Character Images
export const uploadCharacterImage = (characterId, formData) => api.post(`/characters/${characterId}/upload-image`, formData, {
  headers: { 'Content-Type': 'multipart/form-data' }
});

// Member Directory
export const getMemberDirectory = () => api.get('/public/members-directory');

// Cities
export const getCities = (nation) => api.get('/cities', { params: { nation } });
export const getCitiesByNation = (nation) => api.get(`/cities/${nation}`);
export const getCity = (nation, citySlug) => api.get(`/cities/${nation}/${citySlug}`);
export const getCityImage = (nation, citySlug) => api.get(`/city-image/${nation}/${citySlug}`);
export const createCity = (data) => api.post('/admin/cities', data);
export const updateCity = (cityId, data) => api.put(`/admin/cities/${cityId}`, data);

// Locations
export const getLocationsByCity = (nation, citySlug) => api.get(`/locations/${nation}/${citySlug}/locations`);
export const getLocationsByNation = (nation) => api.get(`/locations/${nation}`);
export const getLocationImage = (nation, locationSlug) => api.get(`/location-image/${nation}/${locationSlug}`);
export const createLocation = (data) => api.post('/admin/locations', data);
export const updateLocation = (locationId, data) => api.put(`/admin/locations/${locationId}`, data);

// Factions (Round 1 — foundation)
export const listFactions = (params = {}) => api.get('/factions', { params });
export const getFaction = (slug) => api.get(`/factions/${slug}`);
export const listFactionMembers = (slug) => api.get(`/factions/${slug}/members`);
export const getMyFactionMemberships = () => api.get('/factions/my/membership');
export const joinFaction = (slug, characterId, pitch = '') =>
  api.post(`/factions/${slug}/join`, { character_id: characterId, pitch });
export const leaveFaction = (slug, characterId) =>
  api.post(`/factions/${slug}/leave`, { character_id: characterId });
export const promoteFactionMember = (slug, targetCharId, actorCharId) =>
  api.post(`/factions/${slug}/promote/${targetCharId}`, { actor_character_id: actorCharId });
export const demoteFactionMember = (slug, targetCharId, actorCharId) =>
  api.post(`/factions/${slug}/demote/${targetCharId}`, { actor_character_id: actorCharId });
export const expelFactionMember = (slug, targetCharId, actorCharId) =>
  api.post(`/factions/${slug}/expel/${targetCharId}`, { actor_character_id: actorCharId });

// Factions Round 3 — quests, treasury, rivalry
export const getFactionTreasury = (slug) => api.get(`/factions/${slug}/treasury`);
export const donateToFactionTreasury = (slug, characterId, amount) =>
  api.post(`/factions/${slug}/treasury/donate`, { character_id: characterId, amount });

export const listFactionQuests = (slug, { include_closed = false } = {}) =>
  api.get(`/factions/${slug}/quests`, { params: { include_closed } });
export const createFactionQuest = (slug, payload) =>
  api.post(`/factions/${slug}/quests`, payload);
export const aiGenerateFactionQuest = (slug, payload) =>
  api.post(`/factions/${slug}/quests/ai-generate`, payload);
export const completeFactionQuest = (slug, questId, characterId, proof = '') =>
  api.post(`/factions/${slug}/quests/${questId}/complete`, { character_id: characterId, proof });
export const closeFactionQuest = (slug, questId, actorCharId) =>
  api.post(`/factions/${slug}/quests/${questId}/close`, { actor_character_id: actorCharId });

export const listFactionRivalries = (slug) => api.get(`/factions/${slug}/rivalries`);
export const declareFactionRivalry = (slug, actorCharId, targetSlug, reason = '') =>
  api.post(`/factions/${slug}/rivalries/declare`, {
    actor_character_id: actorCharId, target_slug: targetSlug, reason,
  });
export const escalateFactionRivalry = (slug, rivalryId, actorCharId, delta = 10, reason = '') =>
  api.post(`/factions/${slug}/rivalries/${rivalryId}/escalate`, {
    actor_character_id: actorCharId, delta, reason,
  });
export const sueForPeace = (slug, rivalryId, actorCharId) =>
  api.post(`/factions/${slug}/rivalries/${rivalryId}/sue-for-peace`, { actor_character_id: actorCharId });

// Player-founded factions (charter system)
export const fileFactionCharter = (payload) =>
  api.post('/factions/charter', payload);
export const getMyCharters = () => api.get('/factions/charter/mine');
export const adminListCharters = (status = 'pending') =>
  api.get('/admin/factions/charters', { params: { status } });
export const adminApproveCharter = (charterId, note = '') =>
  api.post(`/admin/factions/charters/${charterId}/approve`, { note });
export const adminRejectCharter = (charterId, note = '') =>
  api.post(`/admin/factions/charters/${charterId}/reject`, { note });

// NPC roster
export const listFactionNpcs = (slug) => api.get(`/factions/${slug}/npcs`);
export const factionTick = (slug) => api.post(`/factions/${slug}/tick`);
export const adminForceFactionTick = (slug) =>
  api.post(`/admin/factions/${slug}/tick`);

// Admin — one-shot seeder for the 6 starter factions (idempotent)
export const adminSeedStarterFactions = () =>
  api.post('/factions/admin/seed-starter');
export const adminSeedMasterNpcs = () =>
  api.post('/apprenticeships/admin/seed-masters');
export const adminSeedRoyalsAndNobles = () =>
  api.post('/admin/seed-royals-and-nobles');
export const adminPopulateCitiesAi = (maxCities = 5) =>
  api.post('/admin/populate-cities-ai', null, { params: { max_cities: maxCities } });
export const adminCleanupGeoData = () =>
  api.post('/admin/cleanup-geo-data');

// Image batcher — gpt-image-1 background job
export const adminImageBatchSurvey = () =>
  api.get('/admin/image-batch/survey');
export const adminImageBatchStatus = () =>
  api.get('/admin/image-batch/status');
export const adminImageBatchGenerate = ({ autoContinue = false } = {}) =>
  api.post(`/admin/image-batch/generate${autoContinue ? '?auto_continue=true' : ''}`);
export const adminImageBatchStop = () =>
  api.post('/admin/image-batch/stop');
export const adminSeedTitanSacredSites = () =>
  api.post('/admin/seed-titan-sacred-sites');
export const adminSeedDhorKuldorCanon = () =>
  api.post('/admin/seed-dhor-kuldor-canon');
export const adminSeedAllRealmsCanon = () =>
  api.post('/admin/seed-all-realms-canon');
export const adminRepairWorldLocations = () =>
  api.post('/admin/repair-world-locations');
export const adminShrinkImageStorage = (limit = 100) =>
  api.post(`/admin/shrink-image-storage?limit=${limit}`);

// Visibility — fetch faction info for a single character or a batch
export const getCharacterFaction = (characterId) =>
  api.get(`/characters/${characterId}/faction`);
export const getFactionsForCharactersBatch = (characterIds) =>
  api.post('/characters/factions/batch', { character_ids: characterIds });

export default api;

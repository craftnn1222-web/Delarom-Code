# Cross-Platform Port Blueprint

## Detection
- **Source Platform:** Web (React, Tailwind CSS, `shadcn/ui` in `/app/frontend`).
- **Target Platform:** Mobile (Expo, React Native in `/app/mobile`).
- **Evidence:** `/app/frontend` contains a rich `src/` directory with complex routing (`App.js`), components, and `package.json` with React/Tailwind/Radix UI dependencies. `/app/mobile/app` contains only scaffolding for a new Expo app (`index.tsx`, `_layout.tsx`) and uses React Native.

## Existing App Map (Web)
**Screens & Routes**
The web app manages a vast, feature-rich text/RP-based MMORPG.
- **Auth:** LandingPage (`/`), Login (`/login`), Register (`/register`).
- **Core Hub:** Dashboard (`/dashboard`), Settings (`/settings`).
- **Characters:** Characters (`/characters`), CharacterEquipment (`/characters/:id/equipment`).
- **World Exploration:** InteractiveMap (`/nations`), Nations & Cities (`/nations/:nation`, `/nations/:nation/cities`), LocationRP (`/roleplay/:nation/:locationSlug`).
- **Quests & Economy:** QuestBoard (`/quests`), MyQuests (`/my-quests`), Marketplace (`/marketplace`), MyShop (`/my-shop`), Markets (`/markets`), TradeCompanies (`/trade-companies`).
- **Social & Lore:** Forums (`/forums`), QuillAndCoffer (combines Rumors, Bounties, Ballads, Letters), MemberDirectory (`/members`).
- **Factions & Groups:** Factions (`/factions`), Parties (`/parties`).
- **Mechanics:** Prayers, TongueOfYros, ContestedCities, Sieges, Cults, Wanted.
- **Admin:** AdminDashboard (`/admin`).

**Components & State**
- **UI Library:** Custom components heavily relying on `shadcn/ui` (Radix UI + Tailwind + `lucide-react`).
- **State Management:** React Context (`AuthContext` for JWT sessions, `MusicContext` for global audio state).
- **Data Fetching:** Axios with Bearer token injection.
- **Key UI Patterns:** Sticky navbars, expansive data grids for economy, modal dialogs for game actions (purchasing, equipping, accepting quests), and rich form-based layouts (`react-hook-form` + `zod`).

**Primary User Flows**
1. **Authentication Loop:** Login -> Receive JWT -> Store in `localStorage` -> Redirect to Dashboard.
2. **Character Loop:** Create characters -> equip items -> access stats.
3. **Gameplay Loop:** Explore map/cities -> enter LocationRP -> pick up quests -> buy/sell items on the Marketplace.
4. **Social Loop:** Join Factions/Parties -> communicate on Forums/Letters -> trigger mechanics (Prayers, Cults, Sieges).

## Shared Backend API Surface
The backend (`/app/backend`) is a massive FastAPI + Motor MongoDB application. The new mobile app will consume these identical endpoints via `EXPO_PUBLIC_BACKEND_URL`:
- **Auth:** `POST /api/auth/login`, `POST /api/auth/register`, `GET /api/auth/me`.
- **Characters:** `GET /api/characters`, `POST /api/characters`, `POST /api/characters/{id}/upload-image`.
- **World:** `GET /api/cities/{nation}`, `GET /api/locations/{nation}`, `GET /api/world/calendar`.
- **Economy:** `GET /api/shops`, `POST /api/items/{item_id}/purchase`, `GET /api/economy/goods`.
- **Quests:** `GET /api/quests`, `POST /api/quests/{id}/accept`, `POST /api/quests/{id}/complete`.
- **Factions/Parties:** `GET /api/factions`, `GET /api/parties`, `POST /api/parties/{id}/join`.
- **Roleplay:** `GET /api/locations/{nation}/{location}/roleplay`.

## Data Models & Integrations
- **Database:** MongoDB (via Motor AsyncIO). Models are unstructured dicts directly injected into DB or Pydantic models living inside routers.
- **Auth Integration:** JWT Bearer tokens.
- **LLM Integrations:** OpenAI (`gpt-4o`, `gpt-4o-mini`) via an internal `Emergent LLM key`. Used heavily by `QuestMasterAI` and `faction_ai` to generate quests and NPC interactions.
- **Image Generation:** OpenAI DALL-E integration (`image_generator.py`) generates base64 images for characters, locations, and quest scenes.
- **Audio/Music:** Serves static music files and tracks themes (`GET /api/music/list`).

## Port Requirements (Mobile Target)
The main agent will build the mobile application within `/app/mobile` using Expo Router.

**General Technical Translation:**
- **Routing:** Replace `react-router-dom` with Expo Router (file-based routing in `mobile/app/`).
- **UI & Styling:** Replace HTML (`div`, `span`, `img`) with React Native (`View`, `Text`, `Image`). Replace `shadcn/ui` with custom React Native components. Use `StyleSheet.create` or `NativeWind` for styling.
- **State & Auth:** Replace `localStorage` inside `AuthContext.js` with `@react-native-async-storage/async-storage` or `expo-secure-store`.
- **API Fetching:** Map `REACT_APP_BACKEND_URL` to `EXPO_PUBLIC_BACKEND_URL`.

**Screen-by-Screen Porting (Recommended MVP Phase 1 Scope):**
1. **Auth (`app/(auth)/login.tsx`, `register.tsx`)**:
   - Use `TextInput` for forms and wrap the view in `KeyboardAvoidingView`.
2. **Dashboard (`app/(tabs)/dashboard.tsx`)**:
   - The primary landing hub post-auth. Display active character stats.
3. **Characters (`app/(tabs)/characters/index.tsx`, `[id].tsx`)**:
   - List characters using `FlatList`.
   - Character image upload must utilize `expo-image-picker` rather than web file inputs.
4. **World / Map (`app/(tabs)/world/index.tsx`)**:
   - Stack navigation to browse Nations -> Cities -> `LocationRP`.
5. **Quests (`app/(tabs)/quests/index.tsx`)**:
   - Port QuestBoard and MyQuests using card layouts in `ScrollView` or `FlatList`.
6. **Marketplace (`app/(tabs)/market/index.tsx`)**:
   - Use modal overlays for purchase confirmation.

**Mobile-Specific Considerations:**
- **Navigation:** Implement a bottom Tab Bar (`app/(tabs)/_layout.tsx`) for core loops and Stack navigators for drill-downs.
- **Safe Area:** Wrap all top-level layouts in `SafeAreaView` (via `react-native-safe-area-context`) to avoid overlap with device notches and home indicators.
- **Audio Playback:** The web app uses HTML5 `<audio>` within `MusicPlayer.js`. The mobile app MUST implement this using `expo-av` if music playback is required.
- **Images:** Base64 image payloads and backend static URLs must use the React Native `<Image>` or `expo-image` component.

## Open Questions / Risks
- **Scope Size:** The web app has ~50 highly specific pages (Cults, Sieges, Admin panels, Tongue of Yros, Courtroom). The mobile MVP should likely focus strictly on the core loop (Auth, Characters, Quests, World, Market) initially. The main agent should clarify if ALL mechanics are required for this iteration.
- **Interactive Map:** The web app contains an `InteractiveMap.js`. If it relies heavily on SVG or Canvas interactions, porting it to mobile may require `react-native-svg` or a `react-native-webview` fallback.
- **Background Audio:** The web app features continuous background music. If the mobile app is expected to keep music playing while the app is backgrounded, specific iOS/Android capabilities and permissions will be required.

// Test IDs for the core Delarom app surfaces (dashboard, characters, world,
// roleplay). React Native uses the `testID` prop. Values are kebab-case.

export const NAV = {
  dashboardTab: "nav-dashboard-tab",
  charactersTab: "nav-characters-tab",
  worldTab: "nav-world-tab",
  questsTab: "nav-quests-tab",
  realmTab: "nav-realm-tab",
};

export const DASHBOARD = {
  screen: "dashboard-screen",
  logoutButton: "dashboard-logout-button",
  worldClock: "dashboard-world-clock",
  activeCharacterCard: "dashboard-active-character-card",
  charactersLink: "dashboard-characters-link",
  worldLink: "dashboard-world-link",
  createCharacterLink: "dashboard-create-character-link",
  switchHeroButton: "dashboard-switch-hero-button",
  heroSwitcher: "dashboard-hero-switcher",
  heroOption: (id) => `dashboard-hero-option-${id}`,
  continueCard: "dashboard-continue-card",
  continueRp: "dashboard-continue-rp",
  continueParty: "dashboard-continue-party",
};

export const CHARACTERS = {
  screen: "characters-screen",
  newButton: "characters-new-button",
  card: "character-card",
  detailScreen: "character-detail-screen",
  createScreen: "character-create-screen",
  createSubmit: "character-create-submit",
  nameInput: "character-name-input",
  raceInput: "character-race-input",
  classInput: "character-class-input",
  appearanceInput: "character-appearance-input",
  powersInput: "character-powers-input",
  backstoryInput: "character-backstory-input",
  nationOption: "character-nation-option",
  statIncrement: "character-stat-increment",
  statDecrement: "character-stat-decrement",
  changePortraitButton: "character-change-portrait-button",
};

export const WORLD = {
  screen: "world-screen",
  nationCard: "nation-card",
  cityCard: "city-card",
  locationCard: "location-card",
  nationLocationsButton: "world-nation-locations-button",
};

export const RP = {
  screen: "rp-screen",
  input: "rp-action-input",
  sendButton: "rp-send-button",
  logEntry: "rp-log-entry",
};

export const QUESTS = {
  screen: "quests-screen",
  boardToggle: "quests-board-toggle",
  mineToggle: "quests-mine-toggle",
  card: "quest-card",
  detailScreen: "quest-detail-screen",
  acceptButton: "quest-accept-button",
  playButton: "quest-play-button",
  playScreen: "quest-play-screen",
  playInput: "quest-play-input",
  playSendButton: "quest-play-send-button",
  playLogEntry: "quest-play-log-entry",
};

export const MARKET = {
  screen: "marketplace-screen",
  shopCard: "shop-card",
  shopScreen: "shop-detail-screen",
  itemCard: "shop-item-card",
  buyButton: "item-buy-button",
};

export const FACTIONS = {
  screen: "factions-screen",
  card: "faction-card",
  detailScreen: "faction-detail-screen",
  joinButton: "faction-join-button",
  leaveButton: "faction-leave-button",
};

export const PARTIES = {
  screen: "parties-screen",
  newButton: "parties-new-button",
  card: "party-card",
  detailScreen: "party-detail-screen",
  createScreen: "party-create-screen",
  createSubmit: "party-create-submit",
  nameInput: "party-name-input",
  locationInput: "party-location-input",
  sceneInput: "party-scene-input",
  joinButton: "party-join-button",
  leaveButton: "party-leave-button",
  startButton: "party-start-button",
  finishButton: "party-finish-button",
  actionInput: "party-action-input",
  sendButton: "party-send-button",
};

export const REALM = {
  screen: "realm-screen",
  marketplaceLink: "realm-marketplace-link",
  factionsLink: "realm-factions-link",
  partiesLink: "realm-parties-link",
};

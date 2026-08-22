import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'sonner';
import { AuthProvider } from './contexts/AuthContext';
import { MusicProvider } from './contexts/MusicContext';
import MusicPlayer from './components/MusicPlayer';
import LandingPage from './pages/LandingPage';
import Register from './pages/Register';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Characters from './pages/Characters';
import CharacterEquipment from './pages/CharacterEquipment';
import QuestBoard from './pages/QuestBoard';
import MyQuests from './pages/MyQuests';
import Marketplace from './pages/Marketplace';
import MyShop from './pages/MyShop';
import Forums from './pages/Forums';
import ForumPost from './pages/ForumPost';
import Nations from './pages/Nations';
import InteractiveMap from './pages/InteractiveMap';
import NationDetail from './pages/NationDetail';
import Cities from './pages/Cities';
import CityDetail from './pages/CityDetail';
import LocationRP from './pages/LocationRP';
import AdminDashboard from './pages/AdminDashboard';
import MemberDirectory from './pages/MemberDirectory';
import T1Tutorial from './pages/T1Tutorial';
import QuillAndCoffer from './pages/QuillAndCoffer';
import Factions from './pages/Factions';
import FactionDetail from './pages/FactionDetail';
import Markets from './pages/Markets';
import Prayers from './pages/Prayers';
import TongueOfYros from './pages/TongueOfYros';
import Parties from './pages/Parties';
import PartyDetail from './pages/PartyDetail';
import TradeCompanies from './pages/TradeCompanies';
import TradeCompanyDetail from './pages/TradeCompanyDetail';
import GoodDetail from './pages/GoodDetail';
import Wanted from './pages/Wanted';
import ContestedCities from './pages/ContestedCities';
import Settings from './pages/Settings';
import ProtectedRoute from './components/ProtectedRoute';
import './App.css';

function App() {
  return (
    <AuthProvider>
      <MusicProvider>
        <BrowserRouter>
          <Toaster position="top-right" richColors offset={80} />
          <MusicPlayer />
          <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/register" element={<Register />} />
          <Route path="/login" element={<Login />} />
          <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
          <Route path="/characters" element={<ProtectedRoute><Characters /></ProtectedRoute>} />
          <Route path="/characters/:characterId/equipment" element={<ProtectedRoute><CharacterEquipment /></ProtectedRoute>} />
          <Route path="/quests" element={<ProtectedRoute><QuestBoard /></ProtectedRoute>} />
          <Route path="/my-quests" element={<ProtectedRoute><MyQuests /></ProtectedRoute>} />
          <Route path="/marketplace" element={<ProtectedRoute><Marketplace /></ProtectedRoute>} />
          <Route path="/my-shop" element={<ProtectedRoute><MyShop /></ProtectedRoute>} />
          <Route path="/forums" element={<ProtectedRoute><Forums /></ProtectedRoute>} />
          <Route path="/forums/:postId" element={<ProtectedRoute><ForumPost /></ProtectedRoute>} />
          <Route path="/nations" element={<ProtectedRoute><InteractiveMap /></ProtectedRoute>} />
          <Route path="/nations-list" element={<ProtectedRoute><Nations /></ProtectedRoute>} />
          <Route path="/nations/:nation/cities" element={<ProtectedRoute><Cities /></ProtectedRoute>} />
          <Route path="/nations/:nation/:citySlug" element={<ProtectedRoute><CityDetail /></ProtectedRoute>} />
          <Route path="/roleplay/:nation/:locationSlug" element={<ProtectedRoute><LocationRP /></ProtectedRoute>} />
          <Route path="/nations/:nationName" element={<ProtectedRoute><NationDetail /></ProtectedRoute>} />
          <Route path="/nations/:nationName/:locationName" element={<ProtectedRoute><LocationRP /></ProtectedRoute>} />
          <Route path="/members" element={<ProtectedRoute><MemberDirectory /></ProtectedRoute>} />
          <Route path="/t1-tutorial" element={<ProtectedRoute><T1Tutorial /></ProtectedRoute>} />
          <Route path="/quill-and-coffer" element={<ProtectedRoute><QuillAndCoffer /></ProtectedRoute>} />
          <Route path="/factions" element={<ProtectedRoute><Factions /></ProtectedRoute>} />
          <Route path="/factions/:slug" element={<ProtectedRoute><FactionDetail /></ProtectedRoute>} />
          <Route path="/markets" element={<ProtectedRoute><Markets /></ProtectedRoute>} />
          <Route path="/prayers" element={<ProtectedRoute><Prayers /></ProtectedRoute>} />
          <Route path="/tongue-of-yros" element={<ProtectedRoute><TongueOfYros /></ProtectedRoute>} />
          <Route path="/parties" element={<ProtectedRoute><Parties /></ProtectedRoute>} />
          <Route path="/parties/:partyId" element={<ProtectedRoute><PartyDetail /></ProtectedRoute>} />
          <Route path="/trade-companies" element={<ProtectedRoute><TradeCompanies /></ProtectedRoute>} />
          <Route path="/trade-companies/:companyId" element={<ProtectedRoute><TradeCompanyDetail /></ProtectedRoute>} />
          <Route path="/markets/:goodSlug" element={<ProtectedRoute><GoodDetail /></ProtectedRoute>} />
          <Route path="/wanted" element={<ProtectedRoute><Wanted /></ProtectedRoute>} />
          <Route path="/contested" element={<ProtectedRoute><ContestedCities /></ProtectedRoute>} />
          {/* Legacy redirects — pages folded into Quill & Coffer */}
          <Route path="/chronicle" element={<Navigate to="/quill-and-coffer" replace />} />
          <Route path="/rumors" element={<Navigate to="/quill-and-coffer" replace />} />
          <Route path="/bounties" element={<Navigate to="/quill-and-coffer" replace />} />
          <Route path="/memorial" element={<Navigate to="/quill-and-coffer" replace />} />
          <Route path="/memorial/:characterId" element={<Navigate to="/quill-and-coffer" replace />} />
          <Route path="/ballads" element={<Navigate to="/quill-and-coffer" replace />} />
          <Route path="/letters" element={<Navigate to="/quill-and-coffer" replace />} />
          <Route path="/bonds" element={<Navigate to="/quill-and-coffer" replace />} />
          <Route path="/settings" element={<ProtectedRoute><Settings /></ProtectedRoute>} />
          <Route path="/admin" element={<ProtectedRoute><AdminDashboard /></ProtectedRoute>} />
        </Routes>
        </BrowserRouter>
      </MusicProvider>
    </AuthProvider>
  );
}

export default App;

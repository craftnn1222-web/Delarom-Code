import { Ionicons } from "@expo/vector-icons";
import { Redirect, Tabs } from "expo-router";

import { NAV } from "@/constants/testIds";
import { useAuth } from "@/src/context/AuthContext";
import { colors } from "@/src/theme/theme";

export default function TabsLayout() {
  const { user, loading } = useAuth();

  // Guard the whole authed area. On logout `user` becomes null and this
  // redirects back to the auth stack instead of leaving a half-cleared shell.
  if (loading) return null;
  if (!user) return <Redirect href="/(auth)/login" />;

  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: colors.gold,
        tabBarInactiveTintColor: colors.textMuted,
        tabBarStyle: {
          backgroundColor: colors.bgElevated,
          borderTopColor: colors.border,
          borderTopWidth: 1,
          height: 88,
          paddingTop: 8,
          paddingBottom: 30,
        },
        tabBarLabelStyle: { fontSize: 11, fontWeight: "600" },
      }}
    >
      <Tabs.Screen
        name="dashboard"
        options={{
          title: "Hearth",
          tabBarButtonTestID: NAV.dashboardTab,
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="home" size={size} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="characters"
        options={{
          title: "Heroes",
          tabBarButtonTestID: NAV.charactersTab,
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="people" size={size} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="world"
        options={{
          title: "World",
          tabBarButtonTestID: NAV.worldTab,
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="map" size={size} color={color} />
          ),
        }}
      />
    </Tabs>
  );
}

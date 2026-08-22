import { Stack } from "expo-router";

import { colors } from "@/src/theme/theme";

export default function RealmLayout() {
  return (
    <Stack
      screenOptions={{
        headerShown: false,
        contentStyle: { backgroundColor: colors.bg },
      }}
    />
  );
}

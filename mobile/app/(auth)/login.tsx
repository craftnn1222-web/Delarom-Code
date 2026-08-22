import { Ionicons } from "@expo/vector-icons";
import { Link, router } from "expo-router";
import { useState } from "react";
import {
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { LOGIN } from "@/constants/testIds";
import { AuthApi } from "@/src/api";
import { Button } from "@/src/components/Button";
import { TextField } from "@/src/components/TextField";
import { useAuth } from "@/src/context/AuthContext";
import { colors, radius, spacing, typography } from "@/src/theme/theme";

export default function LoginScreen() {
  const { signIn } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const submit = async () => {
    if (!email.trim() || !password) {
      setError("Enter your email and password.");
      return;
    }
    setError(null);
    setLoading(true);
    try {
      const res = await AuthApi.login(email.trim(), password);
      await signIn(res.access_token, res.user);
      router.replace("/(tabs)/dashboard");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Login failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.safe}>
      <KeyboardAvoidingView
        style={styles.flex}
        behavior={Platform.OS === "ios" ? "padding" : undefined}
      >
        <ScrollView
          contentContainerStyle={styles.content}
          keyboardShouldPersistTaps="handled"
          showsVerticalScrollIndicator={false}
        >
          <View style={styles.brand}>
            <View style={styles.sigil}>
              <Ionicons name="planet-outline" size={30} color={colors.gold} />
            </View>
            <Text style={styles.title}>Continents of Delarom</Text>
            <Text style={styles.subtitle}>· 217 A.E. ·</Text>
          </View>

          <View style={styles.card}>
            <Text style={styles.cardTitle}>Return to the Realm</Text>

            <TextField
              label="Email"
              value={email}
              onChangeText={setEmail}
              placeholder="you@realm.com"
              autoCapitalize="none"
              keyboardType="email-address"
              testID={LOGIN.emailInput}
            />
            <TextField
              label="Password"
              value={password}
              onChangeText={setPassword}
              placeholder="Your secret word"
              secureTextEntry
              autoCapitalize="none"
              testID={LOGIN.passwordInput}
              error={error}
            />

            <Button
              title="Enter"
              onPress={submit}
              loading={loading}
              testID={LOGIN.submitButton}
              style={styles.submit}
            />

            <View style={styles.footer}>
              <Text style={styles.footerText}>New to Delarom? </Text>
              <Link href="/(auth)/register" testID={LOGIN.registerLink}>
                <Text style={styles.link}>Begin your journey</Text>
              </Link>
            </View>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.bg },
  flex: { flex: 1 },
  content: {
    flexGrow: 1,
    justifyContent: "center",
    padding: spacing.lg,
  },
  brand: { alignItems: "center", marginBottom: spacing.xl },
  sigil: {
    width: 72,
    height: 72,
    borderRadius: 36,
    borderWidth: 1,
    borderColor: colors.goldBorder,
    backgroundColor: colors.goldDim,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: spacing.md,
  },
  title: { ...typography.display, color: colors.textPrimary, textAlign: "center" },
  subtitle: {
    ...typography.tiny,
    color: colors.gold,
    marginTop: spacing.xs,
    letterSpacing: 2,
  },
  card: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.xl,
    padding: spacing.lg,
  },
  cardTitle: {
    ...typography.h2,
    color: colors.textPrimary,
    marginBottom: spacing.lg,
  },
  submit: { marginTop: spacing.sm },
  footer: {
    flexDirection: "row",
    justifyContent: "center",
    marginTop: spacing.lg,
    flexWrap: "wrap",
  },
  footerText: { ...typography.small, color: colors.textSecondary },
  link: { ...typography.small, color: colors.gold, fontWeight: "700" },
});

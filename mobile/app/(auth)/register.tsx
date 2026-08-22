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

import { REGISTER } from "@/constants/testIds";
import { AuthApi } from "@/src/api";
import { Button } from "@/src/components/Button";
import { TextField } from "@/src/components/TextField";
import { colors, radius, spacing, typography } from "@/src/theme/theme";

export default function RegisterScreen() {
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [application, setApplication] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const submit = async () => {
    if (!username.trim() || !email.trim() || !password || !application.trim()) {
      setError("Fill in every field to send your application.");
      return;
    }
    if (password.length < 6) {
      setError("Password must be at least 6 characters.");
      return;
    }
    setError(null);
    setLoading(true);
    try {
      await AuthApi.register({
        username: username.trim(),
        email: email.trim(),
        password,
        application_text: application.trim(),
      });
      setSubmitted(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Registration failed.");
    } finally {
      setLoading(false);
    }
  };

  if (submitted) {
    return (
      <SafeAreaView style={styles.safe} testID="register-success">
        <View style={styles.successWrap}>
          <View style={styles.successIcon}>
            <Ionicons name="mail-open-outline" size={34} color={colors.gold} />
          </View>
          <Text style={styles.title}>Application sent</Text>
          <Text style={styles.successBody}>
            A steward will review your petition. Once you&apos;re approved, return here to log in.
          </Text>
          <Button
            title="To the gates"
            onPress={() => router.replace("/(auth)/login")}
            style={styles.successBtn}
            testID={REGISTER.loginLink}
          />
        </View>
      </SafeAreaView>
    );
  }

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
              <Ionicons name="sparkles-outline" size={26} color={colors.gold} />
            </View>
            <Text style={styles.title}>Begin Your Journey</Text>
            <Text style={styles.subtitle}>Petition to join the realm</Text>
          </View>

          <View style={styles.card}>
            <TextField
              label="Username"
              value={username}
              onChangeText={setUsername}
              placeholder="Your traveler name"
              autoCapitalize="words"
              testID={REGISTER.nameInput}
            />
            <TextField
              label="Email"
              value={email}
              onChangeText={setEmail}
              placeholder="you@realm.com"
              autoCapitalize="none"
              keyboardType="email-address"
              testID={REGISTER.emailInput}
            />
            <TextField
              label="Password"
              value={password}
              onChangeText={setPassword}
              placeholder="At least 6 characters"
              secureTextEntry
              autoCapitalize="none"
              testID={REGISTER.passwordInput}
            />
            <TextField
              label="Why do you seek to join?"
              value={application}
              onChangeText={setApplication}
              placeholder="Tell the stewards about yourself…"
              multiline
              numberOfLines={4}
              testID={REGISTER.passwordConfirmInput}
              error={error}
            />

            <Button
              title="Send application"
              onPress={submit}
              loading={loading}
              testID={REGISTER.submitButton}
              style={styles.submit}
            />

            <View style={styles.footer}>
              <Text style={styles.footerText}>Already sworn in? </Text>
              <Link href="/(auth)/login" testID={REGISTER.loginLink}>
                <Text style={styles.link}>Return to the Realm</Text>
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
  content: { flexGrow: 1, justifyContent: "center", padding: spacing.lg },
  brand: { alignItems: "center", marginBottom: spacing.lg },
  sigil: {
    width: 64,
    height: 64,
    borderRadius: 32,
    borderWidth: 1,
    borderColor: colors.goldBorder,
    backgroundColor: colors.goldDim,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: spacing.md,
  },
  title: { ...typography.h1, color: colors.textPrimary, textAlign: "center" },
  subtitle: { ...typography.small, color: colors.textSecondary, marginTop: spacing.xs },
  card: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.xl,
    padding: spacing.lg,
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
  successWrap: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    padding: spacing.xl,
  },
  successIcon: {
    width: 84,
    height: 84,
    borderRadius: 42,
    borderWidth: 1,
    borderColor: colors.goldBorder,
    backgroundColor: colors.goldDim,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: spacing.lg,
  },
  successBody: {
    ...typography.body,
    color: colors.textSecondary,
    textAlign: "center",
    marginTop: spacing.sm,
    lineHeight: 22,
  },
  successBtn: { alignSelf: "stretch", marginTop: spacing.xl },
});

// Cross-platform toast. `Alert.alert` is a no-op on React Native Web, so we
// render our own lightweight animated toast that works on web AND native.
// Usage: const toast = useToast(); toast.show("Saved", "success").

import { Ionicons } from "@expo/vector-icons";
import React, {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
} from "react";
import { Animated, StyleSheet, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { colors, radius, spacing, typography } from "@/src/theme/theme";

type ToastType = "success" | "error" | "info";

interface ToastContextValue {
  show: (message: string, type?: ToastType) => void;
}

const ToastContext = createContext<ToastContextValue>({ show: () => {} });

export const useToast = () => useContext(ToastContext);

const CONFIG: Record<ToastType, { color: string; icon: keyof typeof Ionicons.glyphMap }> = {
  success: { color: colors.green, icon: "checkmark-circle" },
  error: { color: colors.rose, icon: "alert-circle" },
  info: { color: colors.gold, icon: "information-circle" },
};

export const ToastProvider = ({ children }: { children: React.ReactNode }) => {
  const insets = useSafeAreaInsets();
  const [message, setMessage] = useState<string | null>(null);
  const [type, setType] = useState<ToastType>("info");
  const opacity = useRef(new Animated.Value(0)).current;
  const translateY = useRef(new Animated.Value(24)).current;
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const hide = useCallback(() => {
    Animated.parallel([
      Animated.timing(opacity, { toValue: 0, duration: 200, useNativeDriver: true }),
      Animated.timing(translateY, { toValue: 24, duration: 200, useNativeDriver: true }),
    ]).start(() => setMessage(null));
  }, [opacity, translateY]);

  const show = useCallback(
    (msg: string, t: ToastType = "info") => {
      setMessage(msg);
      setType(t);
      opacity.setValue(0);
      translateY.setValue(24);
      Animated.parallel([
        Animated.timing(opacity, { toValue: 1, duration: 220, useNativeDriver: true }),
        Animated.spring(translateY, { toValue: 0, useNativeDriver: true }),
      ]).start();
      if (timer.current) clearTimeout(timer.current);
      timer.current = setTimeout(hide, 3000);
    },
    [opacity, translateY, hide],
  );

  const value = useMemo(() => ({ show }), [show]);
  const cfg = CONFIG[type];

  return (
    <ToastContext.Provider value={value}>
      {children}
      {message !== null ? (
        <Animated.View
          pointerEvents="box-none"
          style={[
            styles.wrap,
            { bottom: insets.bottom + 96, opacity, transform: [{ translateY }] },
          ]}
        >
          <View style={[styles.toast, { borderColor: cfg.color }]} testID="app-toast">
            <Ionicons name={cfg.icon} size={18} color={cfg.color} />
            <Text style={styles.text}>{message}</Text>
          </View>
        </Animated.View>
      ) : null}
    </ToastContext.Provider>
  );
};

const styles = StyleSheet.create({
  wrap: {
    position: "absolute",
    left: spacing.md,
    right: spacing.md,
    alignItems: "center",
  },
  toast: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
    maxWidth: 520,
    backgroundColor: colors.bgElevated,
    borderWidth: 1,
    borderRadius: radius.md,
    paddingHorizontal: spacing.md,
    paddingVertical: 12,
    boxShadow: "0px 6px 12px rgba(0, 0, 0, 0.4)",
    elevation: 8,
  },
  text: { ...typography.small, color: colors.textPrimary, flexShrink: 1 },
});

import { Ionicons } from "@expo/vector-icons";
import React, { useState } from "react";
import {
  FlatList,
  Modal,
  Pressable,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";

import { colors, radius, spacing, typography } from "@/src/theme/theme";

export interface PickerOption {
  label: string;
  value: string;
}

interface Props {
  label?: string;
  placeholder?: string;
  value?: string | null;
  options: PickerOption[];
  onSelect: (value: string) => void;
  testID?: string;
  disabled?: boolean;
}

/** A tap-to-open modal list picker — the RN stand-in for a web <select>. */
export const PickerField = ({
  label,
  placeholder = "Select…",
  value,
  options,
  onSelect,
  testID,
  disabled,
}: Props) => {
  const [open, setOpen] = useState(false);
  const selected = options.find((o) => o.value === value);

  return (
    <View style={styles.wrap}>
      {label ? <Text style={styles.label}>{label}</Text> : null}
      <TouchableOpacity
        testID={testID}
        activeOpacity={0.8}
        disabled={disabled}
        style={[styles.field, disabled && styles.fieldDisabled]}
        onPress={() => setOpen(true)}
      >
        <Text style={[styles.value, !selected && styles.placeholder]} numberOfLines={1}>
          {selected ? selected.label : placeholder}
        </Text>
        <Ionicons name="chevron-down" size={18} color={colors.textMuted} />
      </TouchableOpacity>

      <Modal visible={open} transparent animationType="fade" onRequestClose={() => setOpen(false)}>
        <Pressable style={styles.backdrop} onPress={() => setOpen(false)}>
          <Pressable style={styles.sheet} onPress={() => {}}>
            <Text style={styles.sheetTitle}>{label ?? "Select"}</Text>
            <FlatList
              data={options}
              keyExtractor={(o) => o.value}
              style={styles.list}
              keyboardShouldPersistTaps="handled"
              renderItem={({ item }) => {
                const active = item.value === value;
                return (
                  <TouchableOpacity
                    testID={testID ? `${testID}-option-${item.value}` : undefined}
                    style={[styles.option, active && styles.optionActive]}
                    onPress={() => {
                      onSelect(item.value);
                      setOpen(false);
                    }}
                  >
                    <Text style={[styles.optionText, active && styles.optionTextActive]}>
                      {item.label}
                    </Text>
                    {active ? <Ionicons name="checkmark" size={18} color={colors.gold} /> : null}
                  </TouchableOpacity>
                );
              }}
              ListEmptyComponent={<Text style={styles.empty}>No options available.</Text>}
            />
          </Pressable>
        </Pressable>
      </Modal>
    </View>
  );
};

const styles = StyleSheet.create({
  wrap: { marginBottom: spacing.md },
  label: {
    ...typography.small,
    color: colors.textSecondary,
    marginBottom: spacing.xs,
    fontWeight: "600",
  },
  field: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.md,
    paddingHorizontal: spacing.md,
    paddingVertical: 13,
  },
  fieldDisabled: { opacity: 0.5 },
  value: { ...typography.body, color: colors.textPrimary, flex: 1, marginRight: spacing.sm },
  placeholder: { color: colors.textMuted },
  backdrop: {
    flex: 1,
    backgroundColor: colors.overlay,
    justifyContent: "flex-end",
  },
  sheet: {
    backgroundColor: colors.bgElevated,
    borderTopLeftRadius: radius.xl,
    borderTopRightRadius: radius.xl,
    borderWidth: 1,
    borderColor: colors.border,
    paddingTop: spacing.md,
    paddingBottom: spacing.xl,
    maxHeight: "70%",
  },
  sheetTitle: {
    ...typography.h3,
    color: colors.textPrimary,
    paddingHorizontal: spacing.lg,
    marginBottom: spacing.sm,
  },
  list: { paddingHorizontal: spacing.md },
  option: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingVertical: 14,
    paddingHorizontal: spacing.md,
    borderRadius: radius.md,
  },
  optionActive: { backgroundColor: colors.goldDim },
  optionText: { ...typography.body, color: colors.textSecondary },
  optionTextActive: { color: colors.goldSoft, fontWeight: "700" },
  empty: { ...typography.small, color: colors.textMuted, padding: spacing.lg, textAlign: "center" },
});

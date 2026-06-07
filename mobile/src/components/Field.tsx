import { Text, TextInput, View } from 'react-native';
import { colors, styles } from '../theme';

type FieldProps = {
  label: string;
  value: string;
  onChangeText: (value: string) => void;
  keyboardType?: 'default' | 'number-pad';
  placeholder?: string;
  autoCapitalize?: 'none' | 'sentences';
};

export function Field({
  label,
  value,
  onChangeText,
  keyboardType = 'default',
  placeholder,
  autoCapitalize = 'sentences',
}: FieldProps) {
  return (
    <View style={styles.fieldWrap}>
      <Text style={styles.inputLabel}>{label}</Text>
      <TextInput
        style={styles.input}
        value={value}
        onChangeText={onChangeText}
        keyboardType={keyboardType}
        autoCapitalize={autoCapitalize}
        autoCorrect={false}
        placeholder={placeholder}
        placeholderTextColor={colors.muted}
      />
    </View>
  );
}

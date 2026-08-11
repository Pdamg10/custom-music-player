import React from 'react';
import { StyleSheet, View, Text, TouchableOpacity } from 'react-native';
import { useNeonTheme } from '@/context/ThemeContext';
import { getAlphaColor } from '@/utils/colorUtils';

interface EmptyScanStateCardProps {
  onPickFolder: () => void;
  onRescan: () => void;
}

export const EmptyScanStateCard: React.FC<EmptyScanStateCardProps> = ({
  onPickFolder,
  onRescan,
}) => {
  const { accentColor, textColor, subtextColor, cardColor } = useNeonTheme();

  return (
    <View style={[styles.container, { backgroundColor: cardColor, borderColor: getAlphaColor(accentColor, '33') }]}>
      <Text style={styles.icon}>📻</Text>
      <Text style={[styles.title, { color: textColor }]}>No se encontraron canciones</Text>
      <Text style={[styles.subtitle, { color: subtextColor }]}>
        No detectamos archivos de audio en el almacenamiento principal de tu teléfono. Puedes elegir una carpeta manualmente o volver a escanear.
      </Text>

      <View style={styles.ctaRow}>
        <TouchableOpacity
          style={[styles.ctaBtn, { backgroundColor: accentColor }]}
          onPress={onPickFolder}
        >
          <Text style={styles.ctaBtnTextPrimary}>📂 ELEGIR CARPETA</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.ctaBtn, { borderColor: accentColor, borderWidth: 1.5 }]}
          onPress={onRescan}
        >
          <Text style={[styles.ctaBtnTextSecondary, { color: accentColor }]}>🔄 RE-ESCANEAR</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    width: '100%',
    padding: 20,
    borderRadius: 18,
    alignItems: 'center',
    borderWidth: 1,
    marginVertical: 10,
  },
  icon: {
    fontSize: 36,
    marginBottom: 8,
  },
  title: {
    fontSize: 14,
    fontWeight: 'bold',
    marginBottom: 4,
  },
  subtitle: {
    fontSize: 11,
    textAlign: 'center',
    lineHeight: 16,
    marginBottom: 16,
    paddingHorizontal: 8,
  },
  ctaRow: {
    flexDirection: 'row',
    gap: 10,
    width: '100%',
  },
  ctaBtn: {
    flex: 1,
    paddingVertical: 11,
    borderRadius: 14,
    alignItems: 'center',
    justifyContent: 'center',
  },
  ctaBtnTextPrimary: {
    color: '#000000',
    fontSize: 11,
    fontWeight: '900',
    letterSpacing: 0.5,
  },
  ctaBtnTextSecondary: {
    fontSize: 11,
    fontWeight: '900',
    letterSpacing: 0.5,
  },
});

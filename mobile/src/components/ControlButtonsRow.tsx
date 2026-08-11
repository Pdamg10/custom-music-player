import React from 'react';
import { StyleSheet, View, Text, TouchableOpacity } from 'react-native';
import { useNeonTheme } from '@/context/ThemeContext';

interface ControlButtonsRowProps {
  isPlaying: boolean;
  isFavorite: boolean;
  isLoop: boolean;
  onTogglePlayPause: () => void;
  onToggleFavorite: () => void;
  onToggleLoop: () => void;
  onPrev: () => void;
  onNext: () => void;
}

export const ControlButtonsRow: React.FC<ControlButtonsRowProps> = ({
  isPlaying,
  isFavorite,
  isLoop,
  onTogglePlayPause,
  onToggleFavorite,
  onToggleLoop,
  onPrev,
  onNext,
}) => {
  const { accentColor, textColor, surfaceColor } = useNeonTheme();

  return (
    <View style={styles.container}>
      {/* 1. FAVORITO (♥️) */}
      <TouchableOpacity
        style={[
          styles.sideBtnCircle,
          { backgroundColor: surfaceColor },
          isFavorite && { borderColor: accentColor, borderWidth: 1.5 },
        ]}
        onPress={onToggleFavorite}
      >
        <Text style={[styles.sideIconText, { color: isFavorite ? accentColor : '#666688' }]}>
          {isFavorite ? '♥️' : '🤍'}
        </Text>
      </TouchableOpacity>

      {/* 2. ANTERIOR (⏮️) */}
      <TouchableOpacity
        style={[styles.sideBtnCircle, { backgroundColor: surfaceColor }]}
        onPress={onPrev}
      >
        <Text style={[styles.sideIconText, { color: textColor }]}>⏮️</Text>
      </TouchableOpacity>

      {/* 3. BOTÓN CENTRAL DE PLAY / PAUSA (MAYOR PESO VISUAL + GLOW NEÓN) */}
      <TouchableOpacity
        style={[
          styles.mainPlayCircle,
          {
            backgroundColor: accentColor,
            shadowColor: accentColor,
            shadowOpacity: isPlaying ? 0.9 : 0.4,
            shadowRadius: isPlaying ? 16 : 8,
            elevation: isPlaying ? 12 : 6,
          },
        ]}
        onPress={onTogglePlayPause}
      >
        <Text style={styles.mainPlayIcon}>
          {isPlaying ? '⏸' : '▶'}
        </Text>
      </TouchableOpacity>

      {/* 4. SIGUIENTE (⏭️) */}
      <TouchableOpacity
        style={[styles.sideBtnCircle, { backgroundColor: surfaceColor }]}
        onPress={onNext}
      >
        <Text style={[styles.sideIconText, { color: textColor }]}>⏭️</Text>
      </TouchableOpacity>

      {/* 5. REPETIR (↻) */}
      <TouchableOpacity
        style={[
          styles.sideBtnCircle,
          { backgroundColor: surfaceColor },
          isLoop && { borderColor: accentColor, borderWidth: 1.5 },
        ]}
        onPress={onToggleLoop}
      >
        <Text style={[styles.sideIconText, { color: isLoop ? accentColor : '#666688' }]}>
          ↻
        </Text>
      </TouchableOpacity>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    width: '100%',
    marginVertical: 14,
    paddingHorizontal: 8,
  },
  sideBtnCircle: {
    width: 44,
    height: 44,
    borderRadius: 22,
    justifyContent: 'center',
    alignItems: 'center',
  },
  sideIconText: {
    fontSize: 18,
    fontWeight: 'bold',
  },
  mainPlayCircle: {
    width: 68,
    height: 68,
    borderRadius: 34,
    justifyContent: 'center',
    alignItems: 'center',
    shadowOffset: { width: 0, height: 6 },
  },
  mainPlayIcon: {
    color: '#000000',
    fontSize: 28,
    marginLeft: 3,
    fontWeight: '900',
  },
});

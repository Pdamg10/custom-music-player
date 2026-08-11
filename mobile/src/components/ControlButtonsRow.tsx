import React from 'react';
import { StyleSheet, View, Text, TouchableOpacity } from 'react-native';
import { useNeonTheme } from '@/context/ThemeContext';
import { getAlphaColor } from '@/utils/colorUtils';

interface ControlButtonsRowProps {
  isPlaying: boolean;
  isFavorite: boolean;
  isLoop: boolean;
  isShuffle?: boolean;
  onTogglePlayPause: () => void;
  onToggleFavorite: () => void;
  onToggleLoop: () => void;
  onToggleShuffle?: () => void;
  onPrev: () => void;
  onNext: () => void;
  onOpenLibrary?: () => void;
}

export const ControlButtonsRow: React.FC<ControlButtonsRowProps> = ({
  isPlaying,
  isFavorite,
  isLoop,
  isShuffle,
  onTogglePlayPause,
  onToggleFavorite,
  onToggleLoop,
  onToggleShuffle,
  onPrev,
  onNext,
  onOpenLibrary,
}) => {
  const { accentColor, textColor, surfaceColor } = useNeonTheme();

  return (
    <View style={styles.container}>
      {/* 1. FAVORITO / CORAZÓN EN CÍRCULO */}
      <TouchableOpacity
        style={[
          styles.circleBtn,
          {
            borderColor: isFavorite ? accentColor : getAlphaColor(textColor, '44'),
            backgroundColor: isFavorite ? getAlphaColor(accentColor, '22') : 'rgba(0,0,0,0.3)',
          },
        ]}
        onPress={onToggleFavorite}
      >
        <Text style={[styles.iconSymbol, { color: isFavorite ? accentColor : getAlphaColor(textColor, '88') }]}>
          {isFavorite ? '♥' : '♡'}
        </Text>
      </TouchableOpacity>

      {/* 2. PISTA ANTERIOR (⏮) */}
      <TouchableOpacity
        style={[
          styles.circleBtn,
          {
            borderColor: accentColor,
            backgroundColor: getAlphaColor(accentColor, '15'),
          },
        ]}
        onPress={onPrev}
      >
        <Text style={[styles.iconSymbol, { color: accentColor }]}>⏮</Text>
      </TouchableOpacity>

      {/* 3. REPRODUCIR / PAUSAR EN CÍRCULO PRINCIPAL RESALTADO CON ANILLO NEÓN */}
      <TouchableOpacity
        style={[
          styles.mainPlayCircle,
          {
            borderColor: accentColor,
            backgroundColor: accentColor,
            shadowColor: accentColor,
            shadowOpacity: isPlaying ? 0.9 : 0.4,
            shadowRadius: isPlaying ? 16 : 8,
            elevation: isPlaying ? 12 : 6,
          },
        ]}
        onPress={onTogglePlayPause}
      >
        <Text style={styles.mainPlayIconSymbol}>
          {isPlaying ? '❚❚' : '▶'}
        </Text>
      </TouchableOpacity>

      {/* 4. PISTA SIGUIENTE (⏭) */}
      <TouchableOpacity
        style={[
          styles.circleBtn,
          {
            borderColor: accentColor,
            backgroundColor: getAlphaColor(accentColor, '15'),
          },
        ]}
        onPress={onNext}
      >
        <Text style={[styles.iconSymbol, { color: accentColor }]}>⏭</Text>
      </TouchableOpacity>

      {/* 5. MODO REPETIR EN CÍRCULO */}
      <TouchableOpacity
        style={[
          styles.circleBtn,
          {
            borderColor: isLoop ? accentColor : getAlphaColor(textColor, '44'),
            backgroundColor: isLoop ? getAlphaColor(accentColor, '22') : 'rgba(0,0,0,0.3)',
          },
        ]}
        onPress={onToggleLoop}
      >
        <Text style={[styles.iconSymbol, { color: isLoop ? accentColor : getAlphaColor(textColor, '88') }]}>
          🔁
        </Text>
      </TouchableOpacity>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-evenly',
    width: '100%',
    marginVertical: 14,
    paddingHorizontal: 4,
  },
  // ESTILO DE BOTÓN EN CÍRCULO INSPIRADO EXACTAMENTE EN LA REFERENCIA (file:///home/phame/Descargas/….jpeg)
  circleBtn: {
    width: 46,
    height: 46,
    borderRadius: 23,
    borderWidth: 2,
    justifyContent: 'center',
    alignItems: 'center',
  },
  iconSymbol: {
    fontSize: 20,
    fontWeight: '900',
    textAlign: 'center',
  },
  mainPlayCircle: {
    width: 66,
    height: 66,
    borderRadius: 33,
    borderWidth: 2.5,
    justifyContent: 'center',
    alignItems: 'center',
    shadowOffset: { width: 0, height: 4 },
  },
  mainPlayIconSymbol: {
    color: '#000000',
    fontSize: 24,
    fontWeight: '900',
    textAlign: 'center',
  },
});

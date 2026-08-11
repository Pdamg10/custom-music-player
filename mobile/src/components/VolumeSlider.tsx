import React, { useState } from 'react';
import { StyleSheet, View, Text, TouchableOpacity, PanResponder } from 'react-native';
import { useNeonTheme } from '@/context/ThemeContext';
import { getAlphaColor } from '@/utils/colorUtils';

interface VolumeSliderProps {
  volume: number; // 0 to 100
  onVolumeChange: (vol: number) => void;
}

export const VolumeSlider: React.FC<VolumeSliderProps> = ({ volume, onVolumeChange }) => {
  const { accentColor, textColor, surfaceColor } = useNeonTheme();
  const [trackWidth, setTrackWidth] = useState(180);

  const updateVolumeFromX = (locationX: number) => {
    if (trackWidth <= 0) return;
    const ratio = Math.max(0, Math.min(1, locationX / trackWidth));
    const newVol = Math.round(ratio * 100);
    onVolumeChange(newVol);
  };

  const panResponder = PanResponder.create({
    onStartShouldSetPanResponder: () => true,
    onMoveShouldSetPanResponder: () => true,
    onPanResponderGrant: (evt) => {
      updateVolumeFromX(evt.nativeEvent.locationX);
    },
    onPanResponderMove: (evt) => {
      updateVolumeFromX(evt.nativeEvent.locationX);
    },
    onPanResponderRelease: (evt) => {
      updateVolumeFromX(evt.nativeEvent.locationX);
    },
  });

  return (
    <View style={styles.container}>
      {/* Botón Silenciar / Volumen Bajo */}
      <TouchableOpacity style={styles.speakerBtn} onPress={() => onVolumeChange(0)}>
        <Text style={[styles.speakerIcon, { color: accentColor }]}>🔈</Text>
      </TouchableOpacity>

      {/* Barra de Volumen Deslizable e Interactiva */}
      <View
        style={styles.trackContainer}
        onLayout={(e) => setTrackWidth(e.nativeEvent.layout.width)}
        {...panResponder.panHandlers}
      >
        <View style={[styles.trackBg, { backgroundColor: getAlphaColor(surfaceColor || '#222', 'FF') }]} />
        <View
          style={[
            styles.trackFill,
            {
              width: `${Math.max(0, Math.min(100, volume))}%`,
              backgroundColor: accentColor,
              shadowColor: accentColor,
            },
          ]}
        />
        <View
          style={[
            styles.thumb,
            {
              left: `${Math.max(0, Math.min(92, volume - 4))}%`,
              backgroundColor: '#FFFFFF',
              borderColor: accentColor,
              shadowColor: accentColor,
            },
          ]}
        />
      </View>

      {/* Botón Volumen Máximo */}
      <TouchableOpacity style={styles.speakerBtn} onPress={() => onVolumeChange(100)}>
        <Text style={[styles.speakerIcon, { color: accentColor }]}>🔊</Text>
      </TouchableOpacity>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    width: '100%',
    paddingHorizontal: 10,
    marginTop: 10,
    gap: 10,
  },
  speakerBtn: {
    padding: 4,
  },
  speakerIcon: {
    fontSize: 16,
  },
  trackContainer: {
    flex: 1,
    maxWidth: 220,
    height: 30,
    justifyContent: 'center',
  },
  trackBg: {
    width: '100%',
    height: 6,
    borderRadius: 3,
  },
  trackFill: {
    position: 'absolute',
    height: 6,
    borderRadius: 3,
    shadowOffset: { width: 0, height: 0 },
    shadowRadius: 6,
    shadowOpacity: 0.9,
    elevation: 4,
  },
  thumb: {
    position: 'absolute',
    width: 16,
    height: 16,
    borderRadius: 8,
    borderWidth: 2,
    shadowOffset: { width: 0, height: 0 },
    shadowRadius: 6,
    shadowOpacity: 0.9,
    elevation: 5,
  },
});

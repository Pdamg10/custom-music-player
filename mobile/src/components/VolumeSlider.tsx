import React from 'react';
import { StyleSheet, View, Text, TouchableOpacity } from 'react-native';
import Svg, { Path, Rect, Circle } from 'react-native-svg';
import { useNeonTheme } from '@/context/ThemeContext';

interface VolumeSliderProps {
  volume: number; // 0 to 100
  onVolumeChange: (vol: number) => void;
}

export const VolumeSlider: React.FC<VolumeSliderProps> = ({ volume, onVolumeChange }) => {
  const { accentColor, cardColor, surfaceColor } = useNeonTheme();

  const handleTrackPress = (evt: any) => {
    const { locationX } = evt.nativeEvent;
    const barWidth = 180; // approximate width of track
    const newVol = Math.min(100, Math.max(0, Math.round((locationX / barWidth) * 100)));
    onVolumeChange(newVol);
  };

  return (
    <View style={styles.container}>
      {/* Low Volume Icon */}
      <TouchableOpacity onPress={() => onVolumeChange(0)}>
        <Text style={[styles.speakerIcon, { color: accentColor }]}>🔈</Text>
      </TouchableOpacity>

      {/* Interactive Volume Bar */}
      <TouchableOpacity
        activeOpacity={0.9}
        onPress={handleTrackPress}
        style={styles.trackContainer}
      >
        <View style={[styles.trackBg, { backgroundColor: surfaceColor || '#222' }]} />
        <View
          style={[
            styles.trackFill,
            {
              width: `${volume}%`,
              backgroundColor: accentColor,
              shadowColor: accentColor,
            },
          ]}
        />
        <View
          style={[
            styles.thumb,
            {
              left: `${Math.min(94, Math.max(0, volume - 4))}%`,
              backgroundColor: '#FFF',
              borderColor: accentColor,
              shadowColor: accentColor,
            },
          ]}
        />
      </TouchableOpacity>

      {/* High Volume Icon */}
      <TouchableOpacity onPress={() => onVolumeChange(100)}>
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
    paddingHorizontal: 16,
    marginTop: 10,
    gap: 12,
  },
  speakerIcon: {
    fontSize: 16,
  },
  trackContainer: {
    width: 180,
    height: 24,
    justifyContent: 'center',
  },
  trackBg: {
    width: '100%',
    height: 5,
    borderRadius: 3,
  },
  trackFill: {
    position: 'absolute',
    height: 5,
    borderRadius: 3,
    shadowOffset: { width: 0, height: 0 },
    shadowRadius: 6,
    shadowOpacity: 0.8,
    elevation: 4,
  },
  thumb: {
    position: 'absolute',
    width: 14,
    height: 14,
    borderRadius: 7,
    borderWidth: 2,
    shadowOffset: { width: 0, height: 0 },
    shadowRadius: 6,
    shadowOpacity: 0.9,
    elevation: 5,
  },
});

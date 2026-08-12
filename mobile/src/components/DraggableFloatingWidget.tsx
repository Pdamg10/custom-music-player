import React, { useRef, useState } from 'react';
import { StyleSheet, View, Text, TouchableOpacity, PanResponder, Dimensions, Image } from 'react-native';
import TrackPlayer, { State, usePlaybackState } from 'react-native-track-player';
import { useNeonTheme } from '../context/ThemeContext';
import { getAlphaColor } from '../utils/colorUtils';
import { router } from 'expo-router';

const { width: SCREEN_WIDTH, height: SCREEN_HEIGHT } = Dimensions.get('window');
const DEFAULT_FALLBACK_COVER = require('../../assets/images/record_player.jpeg');

export const DraggableFloatingWidget: React.FC = () => {
  const { accentColor, cardColor } = useNeonTheme();
  const playbackState = usePlaybackState();
  const isPlaying = playbackState.state === State.Playing;

  const [position, setPosition] = useState({ x: SCREEN_WIDTH - 70, y: SCREEN_HEIGHT - 160 });
  const panOffset = useRef({ x: 0, y: 0 });

  const panResponder = useRef(
    PanResponder.create({
      onStartShouldSetPanResponder: () => true,
      onMoveShouldSetPanResponder: () => true,
      onPanResponderGrant: () => {
        panOffset.current = { ...position };
      },
      onPanResponderMove: (_, gestureState) => {
        const newX = Math.max(10, Math.min(SCREEN_WIDTH - 70, panOffset.current.x + gestureState.dx));
        const newY = Math.max(40, Math.min(SCREEN_HEIGHT - 140, panOffset.current.y + gestureState.dy));
        setPosition({ x: newX, y: newY });
      },
      onPanResponderRelease: () => {},
    })
  ).current;

  const togglePlay = async () => {
    if (isPlaying) {
      await TrackPlayer.pause();
    } else {
      await TrackPlayer.play();
    }
  };

  return (
    <View
      style={[
        styles.widgetContainer,
        {
          left: position.x,
          top: position.y,
          backgroundColor: getAlphaColor(cardColor, 'EE'),
          borderColor: accentColor,
        },
      ]}
      {...panResponder.panHandlers}
    >
      <TouchableOpacity
        style={styles.innerTouchable}
        onPress={() => router.push('/' as any)}
        onLongPress={togglePlay}
        activeOpacity={0.8}
      >
        <Image source={DEFAULT_FALLBACK_COVER} style={styles.miniCover} />
        <View style={styles.glowIndicator}>
          <Text style={[styles.widgetIcon, { color: accentColor }]}>{isPlaying ? '🎵' : '⏸️'}</Text>
        </View>
      </TouchableOpacity>
    </View>
  );
};

const styles = StyleSheet.create({
  widgetContainer: {
    position: 'absolute',
    width: 54,
    height: 54,
    borderRadius: 27,
    borderWidth: 2,
    justifyContent: 'center',
    alignItems: 'center',
    zIndex: 9999,
    elevation: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.6,
    shadowRadius: 8,
  },
  innerTouchable: {
    width: '100%',
    height: '100%',
    borderRadius: 27,
    justifyContent: 'center',
    alignItems: 'center',
    overflow: 'hidden',
  },
  miniCover: {
    width: '100%',
    height: '100%',
    resizeMode: 'cover',
  },
  glowIndicator: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(0, 0, 0, 0.45)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  widgetIcon: {
    fontSize: 18,
  },
});

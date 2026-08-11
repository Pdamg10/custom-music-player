import React from 'react';
import { StyleSheet, View, Text, TouchableOpacity, Image, Dimensions } from 'react-native';
import { PanGestureHandler, PanGestureHandlerGestureEvent } from 'react-native-gesture-handler';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withSpring,
} from 'react-native-reanimated';
import { useNeonTheme } from '@/context/ThemeContext';

const { width: SCREEN_WIDTH, height: SCREEN_HEIGHT } = Dimensions.get('window');

interface DraggableFloatingWidgetProps {
  trackTitle?: string;
  trackArtist?: string;
  coverSource: any;
  isPlaying: boolean;
  onTogglePlayPause: () => void;
  onNext: () => void;
  onExpand: () => void;
}

export const DraggableFloatingWidget: React.FC<DraggableFloatingWidgetProps> = ({
  trackTitle = 'Sin Canción',
  trackArtist = 'Desconocido',
  coverSource,
  isPlaying,
  onTogglePlayPause,
  onNext,
  onExpand,
}) => {
  const { accentColor, textColor, cardColor } = useNeonTheme();

  // Posiciones de arrastre con Reanimated a 60fps
  const translateX = useSharedValue(16);
  const translateY = useSharedValue(SCREEN_HEIGHT - 160);
  const startX = useSharedValue(0);
  const startY = useSharedValue(0);

  const onGestureEvent = (event: PanGestureHandlerGestureEvent) => {
    'worklet';
    translateX.value = startX.value + event.nativeEvent.translationX;
    translateY.value = startY.value + event.nativeEvent.translationY;
  };

  const onHandlerStateChange = (event: any) => {
    'worklet';
    if (event.nativeEvent.state === 5) { // END state
      startX.value = translateX.value;
      startY.value = translateY.value;

      // Limitar dentro de los bordes de la pantalla
      const maxX = SCREEN_WIDTH - 320;
      const maxY = SCREEN_HEIGHT - 120;
      
      if (translateX.value < 10) translateX.value = withSpring(10);
      if (translateX.value > maxX) translateX.value = withSpring(maxX);
      if (translateY.value < 40) translateY.value = withSpring(40);
      if (translateY.value > maxY) translateY.value = withSpring(maxY);
    }
  };

  const animatedStyle = useAnimatedStyle(() => ({
    transform: [
      { translateX: translateX.value },
      { translateY: translateY.value },
    ],
  }));

  return (
    <PanGestureHandler
      onGestureEvent={onGestureEvent}
      onHandlerStateChange={onHandlerStateChange}
    >
      <Animated.View
        style={[
          styles.widgetContainer,
          {
            backgroundColor: '#0A0A0A',
            borderColor: accentColor,
            shadowColor: accentColor,
          },
          animatedStyle,
        ]}
      >
        {/* CARÁTULA CIRCULAR DE LA CANCIÓN */}
        <Image source={coverSource} style={styles.coverThumb} />

        {/* METADATOS COMPACTOS */}
        <View style={styles.textContainer}>
          <Text numberOfLines={1} style={[styles.titleText, { color: textColor }]}>
            {trackTitle}
          </Text>
          <Text numberOfLines={1} style={[styles.artistText, { color: accentColor }]}>
            {trackArtist}
          </Text>
        </View>

        {/* CONTROLES: PLAY/PAUSA + SIGUIENTE + EXPANDIR */}
        <View style={styles.controlsRow}>
          <TouchableOpacity
            style={[styles.playBtn, { backgroundColor: accentColor }]}
            onPress={onTogglePlayPause}
          >
            <Text style={styles.playIcon}>{isPlaying ? '⏸' : '▶'}</Text>
          </TouchableOpacity>

          <TouchableOpacity style={styles.actionBtn} onPress={onNext}>
            <Text style={[styles.actionIcon, { color: textColor }]}>⏭</Text>
          </TouchableOpacity>

          <TouchableOpacity style={styles.actionBtn} onPress={onExpand}>
            <Text style={[styles.expandIcon, { color: accentColor }]}>⤢</Text>
          </TouchableOpacity>
        </View>
      </Animated.View>
    </PanGestureHandler>
  );
};

const styles = StyleSheet.create({
  widgetContainer: {
    position: 'absolute',
    top: 0,
    left: 0,
    width: 310,
    height: 62,
    borderRadius: 31,
    borderWidth: 1.5,
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 8,
    shadowOffset: { width: 0, height: 6 },
    shadowOpacity: 0.5,
    shadowRadius: 12,
    elevation: 14,
    zIndex: 9999,
  },
  coverThumb: {
    width: 44,
    height: 44,
    borderRadius: 22,
  },
  textContainer: {
    flex: 1,
    marginLeft: 10,
    marginRight: 6,
  },
  titleText: {
    fontSize: 12,
    fontWeight: 'bold',
  },
  artistText: {
    fontSize: 10,
    fontWeight: '600',
    marginTop: 2,
  },
  controlsRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  playBtn: {
    width: 36,
    height: 36,
    borderRadius: 18,
    justifyContent: 'center',
    alignItems: 'center',
  },
  playIcon: {
    color: '#000000',
    fontSize: 15,
    fontWeight: 'bold',
    marginLeft: 1,
  },
  actionBtn: {
    width: 32,
    height: 32,
    justifyContent: 'center',
    alignItems: 'center',
  },
  actionIcon: {
    fontSize: 16,
  },
  expandIcon: {
    fontSize: 18,
    fontWeight: 'bold',
  },
});

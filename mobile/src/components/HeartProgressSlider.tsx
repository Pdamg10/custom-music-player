import React, { useState } from 'react';
import { StyleSheet, View, Text, GestureResponderEvent, LayoutChangeEvent } from 'react-native';
import Svg, { Path } from 'react-native-svg';
import { useNeonTheme } from '@/context/ThemeContext';

interface HeartProgressSliderProps {
  positionSec: number;
  durationSec: number;
  onSeek: (seconds: number) => void;
}

export const HeartProgressSlider: React.FC<HeartProgressSliderProps> = ({
  positionSec,
  durationSec,
  onSeek,
}) => {
  const { accentColor, textColor, subtextColor, surfaceColor } = useNeonTheme();
  const [trackWidth, setTrackWidth] = useState(300);

  const handleLayout = (e: LayoutChangeEvent) => {
    const { width } = e.nativeEvent.layout;
    if (width > 0) setTrackWidth(width);
  };

  const handleTouch = (evt: GestureResponderEvent) => {
    const touchX = evt.nativeEvent.locationX;
    const clampedX = Math.max(0, Math.min(trackWidth, touchX));
    const percent = clampedX / trackWidth;
    const targetSeconds = Math.floor(percent * (durationSec || 1));
    onSeek(targetSeconds);
  };

  const progressPercent = Math.min(100, Math.max(0, (positionSec / (durationSec || 1)) * 100));
  const thumbLeft = Math.max(0, Math.min(trackWidth - 18, (progressPercent / 100) * trackWidth - 9));

  const formatElapsed = (secs: number) => {
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return `${m}:${s < 10 ? '0' : ''}${s}`;
  };

  // Formato estricto de Tiempo Restante con Signo Negativo (ej: -1:45)
  const formatRemaining = (pos: number, dur: number) => {
    const remain = Math.max(0, dur - pos);
    const m = Math.floor(remain / 60);
    const s = remain % 60;
    return `-${m}:${s < 10 ? '0' : ''}${s}`;
  };

  return (
    <View style={styles.container}>
      {/* BARRA DE PROGRESO CON TOUCH Y THUMB DE CORAZÓN SVG */}
      <View
        style={styles.touchArea}
        onLayout={handleLayout}
        onStartShouldSetResponder={() => true}
        onResponderGrant={handleTouch}
        onResponderMove={handleTouch}
      >
        <View style={styles.trackBackground}>
          <View
            style={[
              styles.trackFill,
              { width: `${progressPercent}%`, backgroundColor: accentColor },
            ]}
          />
        </View>

        {/* THUMB EN FORMA DE CORAZÓN (SVG) */}
        <View
          style={[
            styles.heartThumbWrapper,
            {
              left: thumbLeft,
              shadowColor: accentColor,
            },
          ]}
          pointerEvents="none"
        >
          <Svg width={20} height={20} viewBox="0 0 24 24">
            <Path
              d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"
              fill={accentColor}
              stroke="#FFFFFF"
              strokeWidth={0.8}
            />
          </Svg>
        </View>
      </View>

      {/* TIEMPOS: TRANSCURRIDO vs TIEMPO RESTANTE CON SIGNO NEGATIVO (-1:45) */}
      <View style={styles.timeLabelsRow}>
        <View style={[styles.timeBadge, { backgroundColor: surfaceColor }]}>
          <Text style={[styles.timeText, { color: textColor }]}>{formatElapsed(positionSec)}</Text>
        </View>
        <View style={[styles.timeBadge, { backgroundColor: surfaceColor }]}>
          <Text style={[styles.timeText, { color: subtextColor }]}>
            {formatRemaining(positionSec, durationSec)}
          </Text>
        </View>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    width: '100%',
    marginVertical: 4,
  },
  touchArea: {
    height: 24,
    justifyContent: 'center',
    width: '100%',
    position: 'relative',
  },
  trackBackground: {
    height: 5,
    backgroundColor: 'rgba(255, 255, 255, 0.15)',
    borderRadius: 2.5,
    width: '100%',
    overflow: 'hidden',
  },
  trackFill: {
    height: '100%',
    borderRadius: 2.5,
  },
  heartThumbWrapper: {
    position: 'absolute',
    top: 2,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.8,
    shadowRadius: 6,
    elevation: 6,
  },
  timeLabelsRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: 4,
  },
  timeBadge: {
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 8,
  },
  timeText: {
    fontSize: 10,
    fontWeight: 'bold',
  },
});

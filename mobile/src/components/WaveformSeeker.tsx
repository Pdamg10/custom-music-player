import React, { useState, useMemo } from 'react';
import {
  StyleSheet,
  View,
  Text,
  Dimensions,
} from 'react-native';
import Svg, { Rect } from 'react-native-svg';
import { getAlphaColor } from '../utils/colorUtils';

const { width: SCREEN_WIDTH } = Dimensions.get('window');
export const DEFAULT_WAVEFORM_BAR_COUNT = 44;

/**
 * Generador pseudo-aleatorio determinista para las alturas del waveform por pista.
 * Garantiza barras idénticas y estables entre re-renders para el mismo ID de canción.
 */
export const generateStableWaveform = (
  seedStr: string = 'custom_music_player_seed',
  barCount: number = DEFAULT_WAVEFORM_BAR_COUNT
): number[] => {
  let hash = 0;
  const str = seedStr || 'custom_music_player_seed';
  for (let i = 0; i < str.length; i++) {
    hash = (hash << 5) - hash + str.charCodeAt(i);
    hash |= 0;
  }

  let seed = Math.abs(hash) || 88219;
  const nextRandom = () => {
    seed = (seed * 1664525 + 1013904223) % 4294967296;
    return seed / 4294967296;
  };

  const bars: number[] = [];
  for (let i = 0; i < barCount; i++) {
    const curve = Math.sin((i / barCount) * Math.PI) * 0.45 + 0.25;
    const variation = nextRandom() * 0.42;
    const barHeight = Math.max(0.18, Math.min(1.0, curve + variation));
    bars.push(barHeight);
  }
  return bars;
};

export const formatWaveformTime = (totalSeconds: number = 0): string => {
  const safeSec = Math.max(0, Math.floor(totalSeconds));
  const mins = Math.floor(safeSec / 60);
  const secs = safeSec % 60;
  return `${mins}:${secs < 10 ? '0' : ''}${secs}`;
};

export interface WaveformSeekerProps {
  trackId?: string;
  position: number;
  duration: number;
  onSeek?: (seconds: number) => void;
  accentColor?: string;
  textColor?: string;
  subtextColor?: string;
  barCount?: number;
  height?: number;
  containerWidth?: number;
  showTimeLabels?: boolean;
}

export const WaveformSeeker: React.FC<WaveformSeekerProps> = ({
  trackId = 'default_track',
  position = 0,
  duration = 0,
  onSeek,
  accentColor = '#FF2A6D',
  textColor = '#FFFFFF',
  subtextColor = '#A0A0A0',
  barCount = DEFAULT_WAVEFORM_BAR_COUNT,
  height = 48,
  containerWidth,
  showTimeLabels = true,
}) => {
  const [dragRatio, setDragRatio] = useState<number | null>(null);

  const effectiveWidth = containerWidth || SCREEN_WIDTH - 64;

  const waveformBars = useMemo(
    () => generateStableWaveform(trackId, barCount),
    [trackId, barCount]
  );

  const effectivePosition = dragRatio !== null ? dragRatio * duration : position;
  const progressRatio = duration > 0 ? Math.min(1.0, Math.max(0, effectivePosition / duration)) : 0;
  const activeBarIndex = Math.floor(progressRatio * barCount);

  return (
    <View style={styles.container}>
      <View
        style={[styles.touchableArea, { height }]}
        onStartShouldSetResponder={() => true}
        onMoveShouldSetResponder={() => true}
        onResponderGrant={(evt) => {
          const touchX = evt.nativeEvent.locationX;
          const ratio = Math.max(0, Math.min(1.0, touchX / effectiveWidth));
          setDragRatio(ratio);
        }}
        onResponderMove={(evt) => {
          const touchX = evt.nativeEvent.locationX;
          const ratio = Math.max(0, Math.min(1.0, touchX / effectiveWidth));
          setDragRatio(ratio);
        }}
        onResponderRelease={(evt) => {
          const touchX = evt.nativeEvent.locationX;
          const ratio = Math.max(0, Math.min(1.0, touchX / effectiveWidth));
          if (duration > 0 && onSeek) {
            onSeek(ratio * duration);
          }
          setDragRatio(null);
        }}
        onResponderTerminate={() => {
          setDragRatio(null);
        }}
      >
        <Svg width={effectiveWidth} height={height}>
          {waveformBars.map((barHeightRatio, index) => {
            const barWidth = 3;
            const gap = (effectiveWidth - barWidth * barCount) / (barCount - 1);
            const x = index * (barWidth + gap);
            const maxBarH = height - 4;
            const barH = Math.max(6, barHeightRatio * maxBarH);
            const y = (height - barH) / 2;

            const isPassed = index <= activeBarIndex;
            const barFill = isPassed ? accentColor : getAlphaColor(textColor, '33');

            return (
              <Rect
                key={index}
                x={x}
                y={y}
                width={barWidth}
                height={barH}
                rx={1.5}
                ry={1.5}
                fill={barFill}
              />
            );
          })}
        </Svg>
      </View>

      {showTimeLabels && (
        <View style={styles.timeLabelsRow}>
          <Text style={[styles.timeText, { color: subtextColor }]}>
            {formatWaveformTime(effectivePosition)}
          </Text>
          <Text style={[styles.timeText, { color: subtextColor }]}>
            {formatWaveformTime(duration)}
          </Text>
        </View>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    width: '100%',
    alignItems: 'center',
  },
  touchableArea: {
    width: '100%',
    justifyContent: 'center',
    alignItems: 'center',
  },
  timeLabelsRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    width: '100%',
    marginTop: 6,
    paddingHorizontal: 2,
  },
  timeText: {
    fontSize: 12,
    fontWeight: '600',
    fontVariant: ['tabular-nums'],
  },
});

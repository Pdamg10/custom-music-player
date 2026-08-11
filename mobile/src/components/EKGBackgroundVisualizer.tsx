import React, { useEffect } from 'react';
import { StyleSheet, View, Dimensions } from 'react-native';
import Svg, { Rect, Defs, LinearGradient as SvgGradient, Stop } from 'react-native-svg';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withRepeat,
  withSequence,
  withTiming,
  withDelay,
  Easing,
} from 'react-native-reanimated';
import { useNeonTheme } from '@/context/ThemeContext';

const { width: SCREEN_WIDTH } = Dimensions.get('window');

interface EKGBackgroundVisualizerProps {
  isPlaying: boolean;
  barCount?: number;
}

// Single SVG Bar component driven by Reanimated at 60fps on UI thread
const AnimatedEKGBar: React.FC<{
  index: number;
  totalBars: number;
  isPlaying: boolean;
  accentColor: string;
}> = ({ index, totalBars, isPlaying, accentColor }) => {
  const heightProgress = useSharedValue(0.1);
  const opacityProgress = useSharedValue(0.3);

  // Distancia del centro para crear curva de pulso cardíaco / EKG
  const centerOffset = Math.abs(index - totalBars / 2) / (totalBars / 2);
  const maxBarHeight = 160 * (1 - centerOffset * 0.45); // Barras centrales más altas

  useEffect(() => {
    if (isPlaying) {
      // Fase y duración única por barra para simular armónicos de audio
      const baseDuration = 350 + (index % 5) * 80;
      const delay = (index % 7) * 60;

      heightProgress.value = withDelay(
        delay,
        withRepeat(
          withSequence(
            withTiming(0.85 + (index % 3) * 0.05, {
              duration: baseDuration,
              easing: Easing.bezier(0.25, 0.1, 0.25, 1),
            }),
            withTiming(0.15 + (index % 4) * 0.05, {
              duration: baseDuration * 1.2,
              easing: Easing.sin,
            }),
            withTiming(0.6, {
              duration: baseDuration * 0.8,
              easing: Easing.ease,
            })
          ),
          -1,
          true
        )
      );

      opacityProgress.value = withDelay(
        delay,
        withRepeat(
          withSequence(
            withTiming(0.85, { duration: baseDuration }),
            withTiming(0.35, { duration: baseDuration * 1.2 })
          ),
          -1,
          true
        )
      );
    } else {
      // Decaimiento suave cuando está en pausa
      heightProgress.value = withTiming(0.08, { duration: 400, easing: Easing.out(Easing.quad) });
      opacityProgress.value = withTiming(0.2, { duration: 400 });
    }
  }, [isPlaying, index]);

  const animatedStyle = useAnimatedStyle(() => ({
    height: heightProgress.value * maxBarHeight,
    opacity: opacityProgress.value,
  }));

  const barWidth = Math.floor((SCREEN_WIDTH - 40) / totalBars) - 3;

  return (
    <View style={styles.barWrapper}>
      <Animated.View
        style={[
          styles.svgBarContainer,
          { width: Math.max(3, barWidth) },
          animatedStyle,
        ]}
      >
        <Svg height="100%" width="100%">
          <Defs>
            <SvgGradient id={`grad-${index}`} x1="0%" y1="100%" x2="0%" y2="0%">
              <Stop offset="0%" stopColor={accentColor} stopOpacity="0.15" />
              <Stop offset="70%" stopColor={accentColor} stopOpacity="0.85" />
              <Stop offset="100%" stopColor="#FFFFFF" stopOpacity="1" />
            </SvgGradient>
          </Defs>
          <Rect
            x="0"
            y="0"
            width="100%"
            height="100%"
            rx={Math.max(2, barWidth / 2)}
            fill={`url(#grad-${index})`}
          />
        </Svg>
      </Animated.View>
    </View>
  );
};

export const EKGBackgroundVisualizer: React.FC<EKGBackgroundVisualizerProps> = ({
  isPlaying,
  barCount = 20,
}) => {
  const { accentColor } = useNeonTheme();

  return (
    <View style={styles.container} pointerEvents="none">
      <View style={styles.barsRow}>
        {Array.from({ length: barCount }).map((_, i) => (
          <AnimatedEKGBar
            key={i}
            index={i}
            totalBars={barCount}
            isPlaying={isPlaying}
            accentColor={accentColor}
          />
        ))}
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    position: 'absolute',
    top: 60,
    left: 0,
    right: 0,
    height: 180,
    justifyContent: 'flex-end',
    alignItems: 'center',
    zIndex: 0,
  },
  barsRow: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    justifyContent: 'center',
    width: '100%',
    paddingHorizontal: 16,
    gap: 3,
  },
  barWrapper: {
    alignItems: 'center',
    justifyContent: 'flex-end',
    height: 170,
  },
  svgBarContainer: {
    borderRadius: 4,
    overflow: 'hidden',
  },
});

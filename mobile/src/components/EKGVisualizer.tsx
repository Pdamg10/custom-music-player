import React, { useEffect } from 'react';
import { View, StyleSheet } from 'react-native';
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
import { getAlphaColor } from '@/utils/colorUtils';

interface EKGVisualizerProps {
  isPlaying: boolean;
  barCount?: number;
  color?: string;
}

const SingleVerticalBar: React.FC<{
  index: number;
  total: number;
  isPlaying: boolean;
  accentColor: string;
}> = ({ index, total, isPlaying, accentColor }) => {
  const heightProgress = useSharedValue(0.2);

  useEffect(() => {
    if (isPlaying) {
      const baseDuration = 200 + (index % 6) * 60;
      const delay = (index % 7) * 40;

      heightProgress.value = withDelay(
        delay,
        withRepeat(
          withSequence(
            withTiming(0.95 - (index % 4) * 0.1, {
              duration: baseDuration,
              easing: Easing.bezier(0.25, 0.1, 0.25, 1),
            }),
            withTiming(0.18 + (index % 3) * 0.05, {
              duration: baseDuration * 1.15,
              easing: Easing.sin,
            }),
            withTiming(0.65, {
              duration: baseDuration * 0.85,
              easing: Easing.ease,
            })
          ),
          -1,
          true
        )
      );
    } else {
      heightProgress.value = withTiming(0.12, { duration: 350, easing: Easing.ease });
    }
  }, [isPlaying, index]);

  const animatedStyle = useAnimatedStyle(() => ({
    height: heightProgress.value * 42,
  }));

  return (
    <View style={styles.barItemContainer}>
      <Animated.View style={[styles.barAnimatedView, animatedStyle]}>
        <Svg height="100%" width="100%">
          <Defs>
            <SvgGradient id={`bar-grad-${index}`} x1="0%" y1="100%" x2="0%" y2="0%">
              <Stop offset="0%" stopColor={accentColor} stopOpacity="0.25" />
              <Stop offset="75%" stopColor={accentColor} stopOpacity="0.9" />
              <Stop offset="100%" stopColor="#FFFFFF" stopOpacity="1" />
            </SvgGradient>
          </Defs>
          <Rect x="0" y="0" width="100%" height="100%" rx={2.5} fill={`url(#bar-grad-${index})`} />
        </Svg>
      </Animated.View>
    </View>
  );
};

export const EKGVisualizer: React.FC<EKGVisualizerProps> = ({
  isPlaying,
  barCount = 24,
  color,
}) => {
  const { accentColor: themeAccent } = useNeonTheme();
  const activeColor = color || themeAccent;

  return (
    <View style={styles.container}>
      {Array.from({ length: barCount }).map((_, i) => (
        <SingleVerticalBar key={i} index={i} total={barCount} isPlaying={isPlaying} accentColor={activeColor} />
      ))}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    justifyContent: 'center',
    height: 46,
    width: '100%',
    paddingHorizontal: 12,
    gap: 3.5,
  },
  barItemContainer: {
    height: 44,
    justifyContent: 'flex-end',
    alignItems: 'center',
    flex: 1,
    maxWidth: 8,
  },
  barAnimatedView: {
    width: '100%',
    borderRadius: 2.5,
    overflow: 'hidden',
  },
});

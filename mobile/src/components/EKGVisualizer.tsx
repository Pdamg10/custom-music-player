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

interface EKGVisualizerProps {
  isPlaying: boolean;
  barCount?: number;
  color?: string;
}

const SingleSVGBar: React.FC<{
  index: number;
  total: number;
  isPlaying: boolean;
  color: string;
}> = ({ index, total, isPlaying, color }) => {
  const heightProgress = useSharedValue(0.15);

  useEffect(() => {
    if (isPlaying) {
      const baseDuration = 220 + (index % 4) * 70;
      const delay = (index % 5) * 45;

      heightProgress.value = withDelay(
        delay,
        withRepeat(
          withSequence(
            withTiming(0.9 - (index % 3) * 0.1, {
              duration: baseDuration,
              easing: Easing.bezier(0.4, 0.0, 0.2, 1),
            }),
            withTiming(0.2, {
              duration: baseDuration * 1.1,
              easing: Easing.sin,
            })
          ),
          -1,
          true
        )
      );
    } else {
      heightProgress.value = withTiming(0.12, { duration: 300, easing: Easing.ease });
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
            <SvgGradient id={`inline-grad-${index}`} x1="0%" y1="100%" x2="0%" y2="0%">
              <Stop offset="0%" stopColor={color} stopOpacity="0.4" />
              <Stop offset="100%" stopColor={color} stopOpacity="1" />
            </SvgGradient>
          </Defs>
          <Rect x="0" y="0" width="100%" height="100%" rx={2.5} fill={`url(#inline-grad-${index})`} />
        </Svg>
      </Animated.View>
    </View>
  );
};

export const EKGVisualizer: React.FC<EKGVisualizerProps> = ({
  isPlaying,
  barCount = 16,
  color = '#FF073A',
}) => {
  return (
    <View style={styles.container}>
      {Array.from({ length: barCount }).map((_, i) => (
        <SingleSVGBar key={i} index={i} total={barCount} isPlaying={isPlaying} color={color} />
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
    paddingHorizontal: 8,
    gap: 4,
  },
  barItemContainer: {
    height: 44,
    justifyContent: 'flex-end',
    alignItems: 'center',
    width: 5,
  },
  barAnimatedView: {
    width: '100%',
    borderRadius: 2.5,
    overflow: 'hidden',
  },
});

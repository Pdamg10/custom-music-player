import React, { useEffect } from 'react';
import { StyleSheet, View, Text } from 'react-native';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withRepeat,
  withTiming,
  withSequence,
  Easing,
} from 'react-native-reanimated';
import { useNeonTheme } from '@/context/ThemeContext';

interface NeonScannerLoaderProps {
  message?: string;
}

export const NeonScannerLoader: React.FC<NeonScannerLoaderProps> = ({
  message = 'ESCANEANDO MÚSICA...',
}) => {
  const { accentColor, textColor, cardColor } = useNeonTheme();

  const scale = useSharedValue(1);
  const opacity = useSharedValue(0.4);

  useEffect(() => {
    scale.value = withRepeat(
      withSequence(
        withTiming(1.25, { duration: 750, easing: Easing.bezier(0.25, 0.1, 0.25, 1) }),
        withTiming(1, { duration: 750, easing: Easing.ease })
      ),
      -1,
      true
    );

    opacity.value = withRepeat(
      withSequence(
        withTiming(0.9, { duration: 750 }),
        withTiming(0.3, { duration: 750 })
      ),
      -1,
      true
    );
  }, []);

  const animatedRingStyle = useAnimatedStyle(() => ({
    transform: [{ scale: scale.value }],
    opacity: opacity.value,
  }));

  return (
    <View style={[styles.container, { backgroundColor: cardColor }]}>
      <View style={styles.loaderWrapper}>
        <Animated.View
          style={[
            styles.pulseRing,
            {
              borderColor: accentColor,
              shadowColor: accentColor,
            },
            animatedRingStyle,
          ]}
        />
        <Text style={styles.centerIcon}>🎧</Text>
      </View>
      <Text style={[styles.loaderMessageText, { color: accentColor }]}>{message}</Text>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    width: '100%',
    paddingVertical: 20,
    paddingHorizontal: 16,
    borderRadius: 18,
    alignItems: 'center',
    justifyContent: 'center',
    marginVertical: 10,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.08)',
  },
  loaderWrapper: {
    width: 60,
    height: 60,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 10,
  },
  pulseRing: {
    position: 'absolute',
    width: 56,
    height: 56,
    borderRadius: 28,
    borderWidth: 2.5,
    shadowOffset: { width: 0, height: 0 },
    shadowRadius: 10,
    elevation: 8,
  },
  centerIcon: {
    fontSize: 24,
  },
  loaderMessageText: {
    fontSize: 11,
    fontWeight: '900',
    letterSpacing: 1.2,
  },
});

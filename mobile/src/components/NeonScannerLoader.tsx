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
  count?: number;
}

export const NeonScannerLoader: React.FC<NeonScannerLoaderProps> = ({
  message = 'ANALIZANDO ALMACENAMIENTO DE MÚSICA...',
  count = 0,
}) => {
  const { accentColor, textColor, cardColor, surfaceColor } = useNeonTheme();

  const scale = useSharedValue(1);
  const opacity = useSharedValue(0.4);

  useEffect(() => {
    scale.value = withRepeat(
      withSequence(
        withTiming(1.3, { duration: 600, easing: Easing.bezier(0.25, 0.1, 0.25, 1) }),
        withTiming(1, { duration: 600, easing: Easing.ease })
      ),
      -1,
      true
    );

    opacity.value = withRepeat(
      withSequence(
        withTiming(0.95, { duration: 600 }),
        withTiming(0.25, { duration: 600 })
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
    <View style={[styles.container, { backgroundColor: cardColor, borderColor: accentColor + '44' }]}>
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
        <Text style={styles.centerIcon}>📡</Text>
      </View>
      <Text style={[styles.loaderMessageText, { color: accentColor }]}>{message}</Text>

      <View style={[styles.countBadge, { backgroundColor: surfaceColor, borderColor: accentColor + '66' }]}>
        <Text style={[styles.countBadgeText, { color: textColor }]}>
          🎵 CANCIONES DETECTADAS: <Text style={{ color: accentColor, fontWeight: '900' }}>{count.toLocaleString()}</Text>
        </Text>
      </View>
      <Text style={[styles.subStatusText, { color: textColor + '88' }]}>
        Leyendo archivos de audio (.mp3, .flac, .wav, .m4a)...
      </Text>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    width: '100%',
    paddingVertical: 24,
    paddingHorizontal: 16,
    borderRadius: 20,
    alignItems: 'center',
    justifyContent: 'center',
    marginVertical: 12,
    borderWidth: 1.5,
  },
  loaderWrapper: {
    width: 64,
    height: 64,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 12,
  },
  pulseRing: {
    position: 'absolute',
    width: 60,
    height: 60,
    borderRadius: 30,
    borderWidth: 3,
    shadowOffset: { width: 0, height: 0 },
    shadowRadius: 12,
    elevation: 8,
  },
  centerIcon: {
    fontSize: 26,
  },
  loaderMessageText: {
    fontSize: 12,
    fontWeight: '900',
    letterSpacing: 1.2,
    textAlign: 'center',
    marginBottom: 10,
  },
  countBadge: {
    paddingVertical: 6,
    paddingHorizontal: 16,
    borderRadius: 20,
    borderWidth: 1,
    marginTop: 4,
  },
  countBadgeText: {
    fontSize: 12,
    fontWeight: '600',
  },
  subStatusText: {
    fontSize: 10,
    marginTop: 8,
    textAlign: 'center',
  },
});

import React, { useEffect, useRef } from 'react';
import { View, StyleSheet, Animated } from 'react-native';

interface EKGVisualizerProps {
  isPlaying: boolean;
  barCount?: number;
  color?: string;
}

export const EKGVisualizer: React.FC<EKGVisualizerProps> = ({
  isPlaying,
  barCount = 14,
  color = '#FF1744',
}) => {
  const animValues = useRef<Animated.Value[]>(
    Array.from({ length: barCount }, () => new Animated.Value(12))
  ).current;

  useEffect(() => {
    let timer: NodeJS.Timeout;
    if (isPlaying) {
      const animateBars = () => {
        const animations = animValues.map((anim) => {
          const targetHeight = Math.floor(Math.random() * 45) + 10;
          return Animated.timing(anim, {
            toValue: targetHeight,
            duration: 80 + Math.random() * 60,
            useNativeDriver: false,
          });
        });

        Animated.parallel(animations).start(() => {
          if (isPlaying) {
            timer = setTimeout(animateBars, 40);
          }
        });
      };

      animateBars();
    } else {
      animValues.forEach((anim) => {
        Animated.timing(anim, {
          toValue: 8,
          duration: 200,
          useNativeDriver: false,
        }).start();
      });
    }

    return () => clearTimeout(timer);
  }, [isPlaying]);

  return (
    <View style={styles.container}>
      {animValues.map((anim, index) => (
        <Animated.View
          key={index}
          style={[
            styles.bar,
            {
              height: anim,
              backgroundColor: color,
            },
          ]}
        />
      ))}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    justifyContent: 'center',
    height: 60,
    width: '100%',
    paddingHorizontal: 8,
    gap: 4,
  },
  bar: {
    width: 5,
    borderRadius: 3,
  },
});

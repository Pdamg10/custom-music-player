import React from 'react';
import { StyleSheet, TouchableOpacity, View } from 'react-native';
import Svg, { Circle, Rect } from 'react-native-svg';

interface CircleMenuIconProps {
  color: string;
  backgroundColor?: string;
  size?: number;
  onPress: () => void;
}

export const CircleMenuIcon: React.FC<CircleMenuIconProps> = ({
  color,
  backgroundColor = 'rgba(15, 15, 18, 0.85)',
  size = 40,
  onPress,
}) => {
  return (
    <TouchableOpacity
      activeOpacity={0.7}
      style={[
        styles.btn,
        {
          width: size,
          height: size,
          borderRadius: size / 2,
          borderColor: color + '55',
        },
      ]}
      onPress={onPress}
    >
      <Svg width={size} height={size} viewBox="0 0 100 100">
        {/* Circle background */}
        <Circle cx="50" cy="50" r="48" fill={backgroundColor} stroke={color + '44'} strokeWidth="3" />
        {/* 3 horizontal rounded pill bars matching user reference icon */}
        <Rect x="26" y="32" width="48" height="8" rx="4" fill={color} />
        <Rect x="26" y="46" width="48" height="8" rx="4" fill={color} />
        <Rect x="26" y="60" width="48" height="8" rx="4" fill={color} />
      </Svg>
    </TouchableOpacity>
  );
};

const styles = StyleSheet.create({
  btn: {
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 1,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 5,
    elevation: 6,
  },
});

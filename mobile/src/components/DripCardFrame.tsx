import React from 'react';
import { StyleSheet, View } from 'react-native';
import Svg, { Path } from 'react-native-svg';

interface DripCardFrameProps {
  color: string;
  borderColor: string;
  width?: number;
}

export const DripCardFrame: React.FC<DripCardFrameProps> = ({
  color,
  borderColor,
  width = 340,
}) => {
  const height = 50;

  return (
    <View style={styles.container}>
      <Svg width={width} height={height} viewBox="0 0 340 50">
        {/* Liquid Drip Silhouette Path matching user reference mockup */}
        <Path
          d="M 0 0 
             Q 15 2, 25 18 
             Q 32 34, 40 38 
             Q 48 38, 52 22 
             Q 56 6, 75 4 
             Q 95 2, 105 28 
             Q 112 48, 122 48 
             Q 132 48, 138 28 
             Q 145 8, 165 6 
             Q 185 4, 195 38 
             Q 202 50, 212 50 
             Q 222 50, 228 32 
             Q 235 14, 255 10 
             Q 275 6, 285 24 
             Q 292 40, 300 40 
             Q 308 40, 314 20 
             Q 322 2, 340 0 
             Z"
          fill={color}
          stroke={borderColor}
          strokeWidth="2.5"
        />
      </Svg>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    width: '100%',
    alignItems: 'center',
    marginTop: -2, // Seamlessly connect to card bottom
  },
});

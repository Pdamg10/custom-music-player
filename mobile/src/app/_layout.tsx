import React, { useEffect } from 'react';
import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { ThemeProvider } from '@/context/ThemeContext';
import { DraggableFloatingWidget } from '@/components/DraggableFloatingWidget';
import { View, StyleSheet } from 'react-native';
import { setupTrackPlayer } from '@/utils/trackPlayerManager';

export default function RootLayout() {
  useEffect(() => {
    setupTrackPlayer();
  }, []);

  return (
    <ThemeProvider>
      <View style={styles.rootContainer}>
        <StatusBar style="light" />
        <Stack
          screenOptions={{
            headerShown: false,
            contentStyle: { backgroundColor: '#0A0A0A' },
          }}
        />
        {/* WIDGET FLOTANTE FLUIDO EN LA RAÍZ SOBRE CUALQUIER PESTAÑA */}
        <DraggableFloatingWidget />
      </View>
    </ThemeProvider>
  );
}

const styles = StyleSheet.create({
  rootContainer: {
    flex: 1,
    backgroundColor: '#0A0A0A',
    position: 'relative',
  },
});

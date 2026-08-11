import React from 'react';
import { Tabs } from 'expo-router';
import { useNeonTheme } from '@/context/ThemeContext';
import { getAlphaColor } from '@/utils/colorUtils';
import { Text, View, StyleSheet } from 'react-native';

export default function TabsLayout() {
  const { accentColor, cardColor, textColor, subtextColor } = useNeonTheme();

  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: accentColor,
        tabBarInactiveTintColor: subtextColor,
        tabBarStyle: {
          backgroundColor: getAlphaColor(cardColor, 'FA'),
          borderTopColor: getAlphaColor(accentColor, '44'),
          borderTopWidth: 1.5,
          height: 60,
          paddingBottom: 8,
          paddingTop: 6,
        },
        tabBarLabelStyle: {
          fontSize: 10,
          fontWeight: 'bold',
        },
        sceneStyle: {
          backgroundColor: '#0A0A0A',
        },
      }}
    >
      <Tabs.Screen
        name="index"
        options={{
          title: 'Reproductor',
          tabBarIcon: ({ color, focused }) => (
            <Text style={[styles.tabIcon, focused && { transform: [{ scale: 1.15 }] }]}>🎵</Text>
          ),
        }}
      />
      <Tabs.Screen
        name="library"
        options={{
          title: 'Biblioteca',
          tabBarIcon: ({ color, focused }) => (
            <Text style={[styles.tabIcon, focused && { transform: [{ scale: 1.15 }] }]}>📚</Text>
          ),
        }}
      />
      <Tabs.Screen
        name="search"
        options={{
          title: 'Búsqueda',
          tabBarIcon: ({ color, focused }) => (
            <Text style={[styles.tabIcon, focused && { transform: [{ scale: 1.15 }] }]}>🔍</Text>
          ),
        }}
      />
      <Tabs.Screen
        name="settings"
        options={{
          title: 'Ajustes',
          tabBarIcon: ({ color, focused }) => (
            <Text style={[styles.tabIcon, focused && { transform: [{ scale: 1.15 }] }]}>⚙️</Text>
          ),
        }}
      />
    </Tabs>
  );
}

const styles = StyleSheet.create({
  tabIcon: {
    fontSize: 18,
  },
});

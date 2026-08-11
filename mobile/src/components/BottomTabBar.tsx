import React from 'react';
import { StyleSheet, View, Text, TouchableOpacity } from 'react-native';
import { useNeonTheme } from '../context/ThemeContext';
import { getAlphaColor } from '../utils/colorUtils';

export type MainTabType = 'player' | 'library' | 'search' | 'lyrics' | 'settings';

interface BottomTabBarProps {
  activeTab: MainTabType;
  onTabPress: (tab: MainTabType) => void;
}

export const BottomTabBar: React.FC<BottomTabBarProps> = ({ activeTab, onTabPress }) => {
  const { accentColor, textColor, subtextColor, cardColor } = useNeonTheme();

  const tabs: { id: MainTabType; label: string; icon: string }[] = [
    { id: 'player', label: 'Reproductor', icon: '🎵' },
    { id: 'library', label: 'Biblioteca', icon: '📚' },
    { id: 'search', label: 'Búsqueda', icon: '🔍' },
    { id: 'lyrics', label: 'Letras', icon: '📝' },
    { id: 'settings', label: 'Ajustes', icon: '⚙️' },
  ];

  return (
    <View style={[styles.container, { backgroundColor: getAlphaColor(cardColor, 'FA'), borderColor: getAlphaColor(accentColor, '44') }]}>
      {tabs.map((tab) => {
        const isActive = activeTab === tab.id;
        return (
          <TouchableOpacity
            key={tab.id}
            style={[
              styles.tabItem,
              isActive && { backgroundColor: getAlphaColor(accentColor, '22') },
            ]}
            onPress={() => onTabPress(tab.id)}
            activeOpacity={0.7}
          >
            <Text style={[styles.tabIcon, isActive && { transform: [{ scale: 1.15 }] }]}>
              {tab.icon}
            </Text>
            <Text
              style={[
                styles.tabLabel,
                { color: isActive ? accentColor : subtextColor },
                isActive && { fontWeight: '900' },
              ]}
              numberOfLines={1}
            >
              {tab.label}
            </Text>
            {isActive && (
              <View style={[styles.activeDot, { backgroundColor: accentColor }]} />
            )}
          </TouchableOpacity>
        );
      })}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    height: 60,
    width: '100%',
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-around',
    borderTopWidth: 1.5,
    paddingHorizontal: 6,
  },
  tabItem: {
    flex: 1,
    height: 52,
    justifyContent: 'center',
    alignItems: 'center',
    borderRadius: 14,
    marginHorizontal: 2,
    position: 'relative',
  },
  tabIcon: {
    fontSize: 18,
  },
  tabLabel: {
    fontSize: 9,
    fontWeight: 'bold',
    marginTop: 2,
  },
  activeDot: {
    position: 'absolute',
    bottom: 3,
    width: 4,
    height: 4,
    borderRadius: 2,
  },
});

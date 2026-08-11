import React, { createContext, useContext, useState, useEffect } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import * as ImagePicker from 'expo-image-picker';

export interface NeonThemePreset {
  id: string;
  name: string;
  accentColor: string;
}

export const PRESET_NEON_THEMES: NeonThemePreset[] = [
  { id: 'neon_red', name: 'Rojo Neón (STRAWBERRY)', accentColor: '#FF073A' },
  { id: 'cyber_cyan', name: 'Cian Ciberpunk', accentColor: '#00F0FF' },
  { id: 'lilac_purple', name: 'Violeta Lila', accentColor: '#B026FF' },
  { id: 'emerald_green', name: 'Verde Esmeralda', accentColor: '#00FF9C' },
  { id: 'neon_gold', name: 'Dorado Neón', accentColor: '#FFD700' },
  { id: 'neon_pink', name: 'Rosa Neón', accentColor: '#FF10F0' },
];

export type ArtMode = 'auto' | 'custom';

export interface ThemeContextType {
  backgroundColor: string;
  cardColor: string;
  surfaceColor: string;
  textColor: string;
  subtextColor: string;
  accentColor: string;
  activeThemeId: string;
  artMode: ArtMode;
  customCoverUri: string | null;
  setPresetTheme: (themeId: string) => void;
  setCustomAccentColor: (hexColor: string) => void;
  setArtMode: (mode: ArtMode) => void;
  pickCustomCoverImage: () => Promise<void>;
  clearCustomCoverImage: () => void;
}

const STORAGE_KEY = '@custom_music_player_theme_v2';

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export const ThemeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [accentColor, setAccentColor] = useState<string>('#FF073A'); // Default Rojo Neón
  const [activeThemeId, setActiveThemeId] = useState<string>('neon_red');
  const [artMode, setArtModeState] = useState<ArtMode>('auto');
  const [customCoverUri, setCustomCoverUri] = useState<string | null>(null);

  // Colores base de identidad visual estricta (Negro Azabache)
  const backgroundColor = '#0A0A0A';
  const cardColor = '#121216';
  const surfaceColor = '#181820';
  const textColor = '#FFFFFF';
  const subtextColor = '#8E8E93';

  useEffect(() => {
    loadSavedTheme();
  }, []);

  const loadSavedTheme = async () => {
    try {
      const savedData = await AsyncStorage.getItem(STORAGE_KEY);
      if (savedData) {
        const parsed = JSON.parse(savedData);
        if (parsed.accentColor) setAccentColor(parsed.accentColor);
        if (parsed.activeThemeId) setActiveThemeId(parsed.activeThemeId);
        if (parsed.artMode) setArtModeState(parsed.artMode);
        if (parsed.customCoverUri) setCustomCoverUri(parsed.customCoverUri);
      }
    } catch (e) {
      console.warn('Error cargando preferencias de tema:', e);
    }
  };

  const persistTheme = async (updates: Partial<{
    accentColor: string;
    activeThemeId: string;
    artMode: ArtMode;
    customCoverUri: string | null;
  }>) => {
    try {
      const current = {
        accentColor,
        activeThemeId,
        artMode,
        customCoverUri,
        ...updates,
      };
      await AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(current));
    } catch (e) {
      console.warn('Error guardando preferencias de tema:', e);
    }
  };

  const setPresetTheme = (themeId: string) => {
    const preset = PRESET_NEON_THEMES.find((t) => t.id === themeId);
    if (preset) {
      setAccentColor(preset.accentColor);
      setActiveThemeId(preset.id);
      persistTheme({ accentColor: preset.accentColor, activeThemeId: preset.id });
    }
  };

  const setCustomAccentColor = (hexColor: string) => {
    setAccentColor(hexColor);
    setActiveThemeId('custom');
    persistTheme({ accentColor: hexColor, activeThemeId: 'custom' });
  };

  const setArtMode = (mode: ArtMode) => {
    setArtModeState(mode);
    persistTheme({ artMode: mode });
  };

  const pickCustomCoverImage = async () => {
    try {
      const permissionResult = await ImagePicker.requestMediaLibraryPermissionsAsync();
      if (!permissionResult.granted) {
        alert('Se requiere permiso para acceder a la galería de fotos.');
        return;
      }

      const result = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ImagePicker.MediaTypeOptions.Images,
        allowsEditing: true,
        aspect: [1, 1],
        quality: 0.9,
      });

      if (!result.canceled && result.assets && result.assets.length > 0) {
        const uri = result.assets[0].uri;
        setCustomCoverUri(uri);
        setArtModeState('custom');
        persistTheme({ customCoverUri: uri, artMode: 'custom' });
      }
    } catch (e) {
      console.warn('Error seleccionando imagen de galería:', e);
    }
  };

  const clearCustomCoverImage = () => {
    setCustomCoverUri(null);
    setArtModeState('auto');
    persistTheme({ customCoverUri: null, artMode: 'auto' });
  };

  return (
    <ThemeContext.Provider
      value={{
        backgroundColor,
        cardColor,
        surfaceColor,
        textColor,
        subtextColor,
        accentColor,
        activeThemeId,
        artMode,
        customCoverUri,
        setPresetTheme,
        setCustomAccentColor,
        setArtMode,
        pickCustomCoverImage,
        clearCustomCoverImage,
      }}
    >
      {children}
    </ThemeContext.Provider>
  );
};

export const useNeonTheme = (): ThemeContextType => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useNeonTheme debe ser usado dentro de un ThemeProvider');
  }
  return context;
};

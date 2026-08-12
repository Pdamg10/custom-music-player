import React, { createContext, useContext, useState, useEffect } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import * as ImagePicker from 'expo-image-picker';
import { normalizeHexColor, getAlphaColor, generateGradientFromHex } from '../utils/colorUtils';
import { extractColorsFromImageUri, ExtractedImageColors } from '../utils/imageColorExtractor';

export interface NeonThemePreset {
  id: string;
  name: string;
  accentColor: string;
  gradientColors: [string, string];
}

export const PRESET_NEON_THEMES: NeonThemePreset[] = [
  { id: 'neon_red', name: 'Rojo Neón (STRAWBERRY)', accentColor: '#FF073A', gradientColors: generateGradientFromHex('#FF073A') },
  { id: 'cyber_cyan', name: 'Cian Ciberpunk', accentColor: '#00F0FF', gradientColors: generateGradientFromHex('#00F0FF') },
  { id: 'lilac_purple', name: 'Violeta Lila', accentColor: '#B026FF', gradientColors: generateGradientFromHex('#B026FF') },
  { id: 'emerald_green', name: 'Verde Esmeralda', accentColor: '#00FF9C', gradientColors: generateGradientFromHex('#00FF9C') },
  { id: 'neon_gold', name: 'Dorado Neón', accentColor: '#FFD700', gradientColors: generateGradientFromHex('#FFD700') },
  { id: 'neon_pink', name: 'Rosa Neón', accentColor: '#FF10F0', gradientColors: generateGradientFromHex('#FF10F0') },
];

export type ArtMode = 'auto' | 'custom';
export type BackgroundMode = 'solid' | 'gradient';

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
  backgroundMode: BackgroundMode;
  customBgUri: string | null;
  gradientColors: [string, string];
  autoExtractColorFromArt: boolean;
  extractedColors: ExtractedImageColors | null;
  useCardGradient: boolean;
  setPresetTheme: (themeId: string) => void;
  setCustomAccentColor: (hexColor: string) => void;
  setArtMode: (mode: ArtMode) => void;
  setBackgroundMode: (mode: BackgroundMode) => void;
  setGradientColors: (colors: [string, string]) => void;
  setAutoExtractColorFromArt: (enabled: boolean) => void;
  setUseCardGradient: (enabled: boolean) => void;
  pickCustomCoverImage: () => Promise<void>;
  clearCustomCoverImage: () => void;
  pickCustomBgImage: () => Promise<void>;
  clearCustomBgImage: () => void;
  applyExtractedAccentColor: (hexColor: string) => void;
}

const STORAGE_KEY = '@custom_music_player_theme_v6';

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export const ThemeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [accentColor, setAccentColor] = useState<string>('#FF073A');
  const [activeThemeId, setActiveThemeId] = useState<string>('neon_red');
  const [artMode, setArtModeState] = useState<ArtMode>('auto');
  const [customCoverUri, setCustomCoverUri] = useState<string | null>(null);
  const [backgroundMode, setBackgroundModeState] = useState<BackgroundMode>('solid');
  const [customBgUri, setCustomBgUri] = useState<string | null>(null);
  const [gradientColors, setGradientColorsState] = useState<[string, string]>(generateGradientFromHex('#FF073A'));
  const [autoExtractColorFromArt, setAutoExtractColorFromArtState] = useState<boolean>(true);
  const [extractedColors, setExtractedColors] = useState<ExtractedImageColors | null>(null);
  const [useCardGradient, setUseCardGradientState] = useState<boolean>(true);

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
        if (parsed.accentColor) setAccentColor(normalizeHexColor(parsed.accentColor));
        if (parsed.activeThemeId) setActiveThemeId(parsed.activeThemeId);
        if (parsed.artMode) setArtModeState(parsed.artMode);
        if (parsed.customCoverUri) setCustomCoverUri(parsed.customCoverUri);
        if (parsed.backgroundMode) setBackgroundModeState(parsed.backgroundMode);
        if (parsed.customBgUri) setCustomBgUri(parsed.customBgUri);
        if (parsed.autoExtractColorFromArt !== undefined) setAutoExtractColorFromArtState(parsed.autoExtractColorFromArt);
        if (parsed.useCardGradient !== undefined) setUseCardGradientState(parsed.useCardGradient);
        if (parsed.extractedColors) setExtractedColors(parsed.extractedColors);
        if (parsed.gradientColors && Array.isArray(parsed.gradientColors) && parsed.gradientColors.length >= 2) {
          setGradientColorsState([
            normalizeHexColor(parsed.gradientColors[0]),
            normalizeHexColor(parsed.gradientColors[1]),
          ]);
        }
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
    backgroundMode: BackgroundMode;
    customBgUri: string | null;
    gradientColors: [string, string];
    autoExtractColorFromArt: boolean;
    extractedColors: ExtractedImageColors | null;
    useCardGradient: boolean;
  }>) => {
    try {
      const current = {
        accentColor,
        activeThemeId,
        artMode,
        customCoverUri,
        backgroundMode,
        customBgUri,
        gradientColors,
        autoExtractColorFromArt,
        extractedColors,
        useCardGradient,
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
      const cleanHex = normalizeHexColor(preset.accentColor);
      setAccentColor(cleanHex);
      setActiveThemeId(preset.id);
      setGradientColorsState(preset.gradientColors);

      persistTheme({
        accentColor: cleanHex,
        activeThemeId: preset.id,
        gradientColors: preset.gradientColors,
      });
    }
  };

  const setCustomAccentColor = (hexColor: string) => {
    const cleanHex = normalizeHexColor(hexColor);
    setAccentColor(cleanHex);
    setActiveThemeId('custom');

    const generatedGrad = generateGradientFromHex(cleanHex);
    setGradientColorsState(generatedGrad);

    persistTheme({
      accentColor: cleanHex,
      activeThemeId: 'custom',
      gradientColors: generatedGrad,
    });
  };

  const applyExtractedAccentColor = (hexColor: string) => {
    if (!autoExtractColorFromArt) return;
    const cleanHex = normalizeHexColor(hexColor);
    setAccentColor(cleanHex);
    const generatedGrad = generateGradientFromHex(cleanHex);
    setGradientColorsState(generatedGrad);
  };

  const setArtMode = (mode: ArtMode) => {
    setArtModeState(mode);
    persistTheme({ artMode: mode });
  };

  const setBackgroundMode = (mode: BackgroundMode) => {
    setBackgroundModeState(mode);
    persistTheme({ backgroundMode: mode });
  };

  const setGradientColors = (colors: [string, string]) => {
    const clean: [string, string] = [normalizeHexColor(colors[0]), normalizeHexColor(colors[1])];
    setGradientColorsState(clean);
    persistTheme({ gradientColors: clean });
  };

  const setAutoExtractColorFromArt = (enabled: boolean) => {
    setAutoExtractColorFromArtState(enabled);
    persistTheme({ autoExtractColorFromArt: enabled });
  };

  const setUseCardGradient = (enabled: boolean) => {
    setUseCardGradientState(enabled);
    persistTheme({ useCardGradient: enabled });
  };

  const pickCustomCoverImage = async () => {
    try {
      const permissionResult = await ImagePicker.requestMediaLibraryPermissionsAsync();
      if (!permissionResult.granted) {
        alert('Se requiere permiso para acceder a la galería de fotos.');
        return;
      }

      const result = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ['images'],
        allowsEditing: true,
        aspect: [1, 1],
        quality: 0.9,
      });

      if (!result.canceled && result.assets && result.assets.length > 0) {
        const uri = result.assets[0].uri;
        setCustomCoverUri(uri);
        setArtModeState('custom');

        const colors = await extractColorsFromImageUri(uri);
        if (colors) {
          setExtractedColors(colors);
        }

        persistTheme({ customCoverUri: uri, artMode: 'custom', extractedColors: colors });
      }
    } catch (e) {
      console.warn('Error seleccionando imagen de carátula:', e);
    }
  };

  const clearCustomCoverImage = () => {
    setCustomCoverUri(null);
    setArtModeState('auto');
    setExtractedColors(null);
    persistTheme({ customCoverUri: null, artMode: 'auto', extractedColors: null });
  };

  const pickCustomBgImage = async () => {
    try {
      const permissionResult = await ImagePicker.requestMediaLibraryPermissionsAsync();
      if (!permissionResult.granted) {
        alert('Se requiere permiso para acceder a la galería de fotos.');
        return;
      }

      const result = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ['images'],
        allowsEditing: true,
        aspect: [9, 16],
        quality: 0.9,
      });

      if (!result.canceled && result.assets && result.assets.length > 0) {
        const uri = result.assets[0].uri;
        setCustomBgUri(uri);

        const colors = await extractColorsFromImageUri(uri);
        if (colors) {
          setExtractedColors(colors);
        }

        persistTheme({ customBgUri: uri, extractedColors: colors });
      }
    } catch (e) {
      console.warn('Error seleccionando imagen de fondo de pantalla:', e);
    }
  };

  const clearCustomBgImage = () => {
    setCustomBgUri(null);
    persistTheme({ customBgUri: null });
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
        backgroundMode,
        customBgUri,
        gradientColors,
        autoExtractColorFromArt,
        extractedColors,
        useCardGradient,
        setPresetTheme,
        setCustomAccentColor,
        setArtMode,
        setBackgroundMode,
        setGradientColors,
        setAutoExtractColorFromArt,
        setUseCardGradient,
        pickCustomCoverImage,
        clearCustomCoverImage,
        pickCustomBgImage,
        clearCustomBgImage,
        applyExtractedAccentColor,
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

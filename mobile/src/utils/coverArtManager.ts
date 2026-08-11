import AsyncStorage from '@react-native-async-storage/async-storage';
import * as FileSystem from 'expo-file-system/legacy';
import * as ImagePicker from 'expo-image-picker';
import { parseBuffer } from 'music-metadata';
import { Buffer } from 'buffer';

const CUSTOM_COVERS_STORAGE_KEY = '@custom_music_player_track_covers_v1';
const EMBEDDED_COVERS_STORAGE_KEY = '@custom_music_player_embedded_covers_v1';
const COVERS_CACHE_DIR = (FileSystem.cacheDirectory || FileSystem.documentDirectory || '') + 'extracted_covers/';

let customCoversMap: Record<string, string> = {};
let embeddedCoversMap: Record<string, string> = {};
let isInitialized = false;

// INICIALIZACIÓN DE MEMORIA Y DIRECTORIO DE CACHÉ
const ensureInitialized = async () => {
  if (isInitialized) return;
  try {
    const dirInfo = await FileSystem.getInfoAsync(COVERS_CACHE_DIR);
    if (!dirInfo.exists) {
      await FileSystem.makeDirectoryAsync(COVERS_CACHE_DIR, { intermediates: true });
    }

    const savedCustom = await AsyncStorage.getItem(CUSTOM_COVERS_STORAGE_KEY);
    if (savedCustom) customCoversMap = JSON.parse(savedCustom);

    const savedEmbedded = await AsyncStorage.getItem(EMBEDDED_COVERS_STORAGE_KEY);
    if (savedEmbedded) embeddedCoversMap = JSON.parse(savedEmbedded);

    isInitialized = true;
  } catch (e) {
    console.warn('Error inicializando coverArtManager:', e);
  }
};

// ==========================================
// PARTE B: OVERRIDE DE CARÁTULA PERSONALIZADA
// ==========================================

export const getCustomCoverForTrack = async (trackId: string): Promise<string | null> => {
  await ensureInitialized();
  return customCoversMap[trackId] || null;
};

export const setCustomCoverForTrack = async (trackId: string, imageUri: string): Promise<void> => {
  await ensureInitialized();
  customCoversMap[trackId] = imageUri;
  await AsyncStorage.setItem(CUSTOM_COVERS_STORAGE_KEY, JSON.stringify(customCoversMap));
};

export const clearCustomCoverForTrack = async (trackId: string): Promise<void> => {
  await ensureInitialized();
  delete customCoversMap[trackId];
  await AsyncStorage.setItem(CUSTOM_COVERS_STORAGE_KEY, JSON.stringify(customCoversMap));
};

export const pickAndSetCustomCoverForTrack = async (trackId: string): Promise<string | null> => {
  try {
    const permissionResult = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!permissionResult.granted) {
      alert('Se requiere permiso para acceder a la galería.');
      return null;
    }

    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ['images'],
      allowsEditing: true,
      aspect: [1, 1],
      quality: 0.85,
    });

    if (!result.canceled && result.assets && result.assets.length > 0) {
      const selectedUri = result.assets[0].uri;
      await setCustomCoverForTrack(trackId, selectedUri);
      return selectedUri;
    }
  } catch (err) {
    console.warn('Error seleccionando carátula personalizada:', err);
  }
  return null;
};

// ==========================================
// PARTE A: EXTRAER Y CACHEAR CARÁTULA EMBEBIDA REAL ID3/FLAC
// ==========================================

export const getEmbeddedCoverForTrack = async (trackId: string, audioUrl: string): Promise<string | null> => {
  await ensureInitialized();

  // 1. Revisar caché persistente
  if (embeddedCoversMap[trackId]) {
    const fileCheck = await FileSystem.getInfoAsync(embeddedCoversMap[trackId]);
    if (fileCheck.exists) {
      return embeddedCoversMap[trackId];
    }
  }

  // 2. Extraer picture tag embebido con music-metadata de forma eficiente
  try {
    if (!audioUrl || (!audioUrl.startsWith('file://') && !audioUrl.startsWith('/'))) {
      return null;
    }

    // Leemos los primeros 256KB del archivo donde se encuentran los metadatos e imagen de portada
    const fileChunkBase64 = await FileSystem.readAsStringAsync(audioUrl, {
      encoding: FileSystem.EncodingType.Base64,
      length: 256 * 1024,
      position: 0,
    });

    if (!fileChunkBase64) return null;

    const chunkBuffer = Buffer.from(fileChunkBase64, 'base64');
    const metadata = await parseBuffer(chunkBuffer);

    if (metadata.common && metadata.common.picture && metadata.common.picture.length > 0) {
      const picture = metadata.common.picture[0];
      const formatExt = picture.format.includes('png') ? 'png' : 'jpg';
      const destinationUri = `${COVERS_CACHE_DIR}${trackId}_embedded.${formatExt}`;

      const base64Data = Buffer.from(picture.data).toString('base64');
      await FileSystem.writeAsStringAsync(destinationUri, base64Data, {
        encoding: FileSystem.EncodingType.Base64,
      });

      embeddedCoversMap[trackId] = destinationUri;
      await AsyncStorage.setItem(EMBEDDED_COVERS_STORAGE_KEY, JSON.stringify(embeddedCoversMap));
      return destinationUri;
    }
  } catch (e) {
    // Si no contiene tags o falla la lectura parcial, continúa sin bloquear la app
  }

  return null;
};

// ==========================================
// JERARQUÍA DE PRIORIDAD DE CARÁTULA
// ==========================================

export const getResolvedTrackCover = async (
  trackId: string,
  audioUrl: string,
  defaultFallback: any
): Promise<any> => {
  // Prioridad 1: Override personalizado de ESA canción específica (Parte B)
  const customUri = await getCustomCoverForTrack(trackId);
  if (customUri) {
    return { uri: customUri };
  }

  // Prioridad 2: Carátula embebida real extraída del archivo ID3/FLAC (Parte A)
  const embeddedUri = await getEmbeddedCoverForTrack(trackId, audioUrl);
  if (embeddedUri) {
    return { uri: embeddedUri };
  }

  // Prioridad 3: DEFAULT_FALLBACK_COVER solo si no hay ninguna de las anteriores
  return defaultFallback;
};

import AsyncStorage from '@react-native-async-storage/async-storage';
import { Track } from '../components/LibraryModal';

export const RECENT_HISTORY_STORAGE_KEY = '@custom_music_player_recent_history_v1';
const MAX_RECENT_TRACKS = 20;

/**
 * Obtiene el historial de reproducciones recientes desde AsyncStorage.
 * Retorna un arreglo de hasta 20 canciones ordenadas cronológicamente (más reciente primero).
 */
export const getRecentHistory = async (): Promise<Track[]> => {
  try {
    const raw = await AsyncStorage.getItem(RECENT_HISTORY_STORAGE_KEY);
    if (!raw) return [];
    const parsed: Track[] = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch (error) {
    console.warn('Error al leer historial reciente:', error);
    return [];
  }
};

/**
 * Registra una pista en el historial de reproducción reciente tras superar el umbral anti-skip.
 * Evita duplicados colocando la pista al inicio de la lista y limitando a MAX_RECENT_TRACKS (20).
 */
export const recordTrackPlayback = async (track: Track): Promise<Track[]> => {
  if (!track || !track.id) return [];

  try {
    const currentHistory = await getRecentHistory();

    // Filtrar si ya existía para moverlo al primer lugar
    const filtered = currentHistory.filter(
      (t) => t.id !== track.id && String(t.id) !== String(track.id)
    );

    // Insertar al inicio de la lista
    const updatedHistory: Track[] = [track, ...filtered].slice(0, MAX_RECENT_TRACKS);

    await AsyncStorage.setItem(
      RECENT_HISTORY_STORAGE_KEY,
      JSON.stringify(updatedHistory)
    );

    return updatedHistory;
  } catch (error) {
    console.warn('Error al guardar pista en historial reciente:', error);
    return [];
  }
};

/**
 * Limpia el historial de reproducciones recientes.
 */
export const clearRecentHistory = async (): Promise<void> => {
  try {
    await AsyncStorage.removeItem(RECENT_HISTORY_STORAGE_KEY);
  } catch (error) {
    console.warn('Error al limpiar historial reciente:', error);
  }
};

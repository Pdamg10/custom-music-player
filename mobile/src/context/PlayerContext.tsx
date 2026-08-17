import React, { createContext, useContext, useState, useEffect, useRef } from 'react';
import TrackPlayer, {
  State,
  usePlaybackState,
  useProgress,
} from 'react-native-track-player';
import * as MediaLibrary from 'expo-media-library';
import AsyncStorage from '@react-native-async-storage/async-storage';

import { Track } from '../components/LibraryModal';
import { setupTrackPlayer } from '../utils/trackPlayerManager';
import { mapAssetsToTracks } from '../utils/mediaScanner';
import { getRecentHistory, recordTrackPlayback } from '../utils/recentHistory';

export const PLAYLIST_STORAGE_KEY = '@custom_music_player_saved_playlist_v10';
export const TRACK_INDEX_STORAGE_KEY = '@custom_music_player_saved_index_v10';

export interface PlayerContextType {
  playlist: Track[];
  currentTrackIndex: number;
  currentTrack: Track | undefined;
  isPlaying: boolean;
  progress: { position: number; duration: number };
  isFavorite: boolean;
  isShuffle: boolean;
  isLoop: boolean;
  recentTracks: Track[];
  isLoading: boolean;
  playTrackAtIndex: (index: number) => Promise<void>;
  playTrack: (track: Track) => Promise<void>;
  togglePlayPause: () => Promise<void>;
  toggleFavorite: () => Promise<void>;
  toggleShuffle: () => Promise<void>;
  toggleLoop: () => Promise<void>;
  skipToNext: () => Promise<void>;
  skipToPrevious: () => Promise<void>;
  seekTo: (seconds: number) => Promise<void>;
  setPlaylistData: (tracks: Track[]) => Promise<void>;
  reloadPlaylistFromStorage: () => Promise<void>;
  refreshRecentHistory: () => Promise<void>;
}

const PlayerContext = createContext<PlayerContextType | undefined>(undefined);

export const PlayerProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const playbackState = usePlaybackState();
  const rawProgress = useProgress();
  const isPlaying = playbackState.state === State.Playing;

  const [playlist, setPlaylist] = useState<Track[]>([]);
  const [currentTrackIndex, setCurrentTrackIndex] = useState<number>(0);
  const [recentTracks, setRecentTracks] = useState<Track[]>([]);
  const [isFavorite, setIsFavorite] = useState<boolean>(false);
  const [isShuffle, setIsShuffle] = useState<boolean>(false);
  const [isLoop, setIsLoop] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // Flags para umbral anti-skip centralizado
  const hasRecordedRef = useRef<boolean>(false);
  const lastTrackIdRef = useRef<string | null>(null);

  const currentTrack: Track | undefined = playlist[currentTrackIndex];

  // 1. INICIALIZACIÓN DE TRACKPLAYER, HISTORIAL Y BIBLIOTECA
  useEffect(() => {
    const initPlayerSystem = async () => {
      try {
        await setupTrackPlayer();

        // Cargar historial de reproducciones
        const history = await getRecentHistory();
        setRecentTracks(history);

        // Cargar playlist guardada o escanear
        const savedPlaylistJson = await AsyncStorage.getItem(PLAYLIST_STORAGE_KEY);
        const savedIndexStr = await AsyncStorage.getItem(TRACK_INDEX_STORAGE_KEY);

        if (savedPlaylistJson) {
          const parsed: Track[] = JSON.parse(savedPlaylistJson);
          if (parsed && parsed.length > 0) {
            setPlaylist(parsed);
            if (savedIndexStr) {
              const idx = parseInt(savedIndexStr, 10);
              if (!isNaN(idx) && idx >= 0 && idx < parsed.length) {
                setCurrentTrackIndex(idx);
                setIsFavorite(Boolean(parsed[idx]?.isFavorite));
              }
            }
            setIsLoading(false);
            return;
          }
        }

        // Si no hay lista guardada, solicitar permisos y escanear almacenamiento
        const { status } = await MediaLibrary.requestPermissionsAsync();
        if (status === 'granted') {
          const page = await MediaLibrary.getAssetsAsync({
            mediaType: 'audio',
            first: 2000,
            sortBy: [[MediaLibrary.SortBy.creationTime, false]],
          });
          if (page.assets && page.assets.length > 0) {
            const mapped = mapAssetsToTracks(page.assets);
            setPlaylist(mapped);
            await AsyncStorage.setItem(PLAYLIST_STORAGE_KEY, JSON.stringify(mapped));
          }
        }
      } catch (err) {
        console.warn('Error inicializando PlayerContext:', err);
      } finally {
        setIsLoading(false);
      }
    };

    initPlayerSystem();
  }, []);

  // 2. RESET DEL FLAG ANTI-SKIP AL CAMBIAR DE PISTA
  useEffect(() => {
    if (currentTrack && currentTrack.id !== lastTrackIdRef.current) {
      lastTrackIdRef.current = currentTrack.id;
      hasRecordedRef.current = false;
      setIsFavorite(Boolean(currentTrack.isFavorite));
    }
  }, [currentTrackIndex, currentTrack]);

  // 3. UMBRAL ANTI-SKIP CENTRALIZADO (>= 10s O >= 50% de la duración)
  useEffect(() => {
    if (
      isPlaying &&
      currentTrack &&
      !hasRecordedRef.current &&
      rawProgress.position > 0
    ) {
      const duration = rawProgress.duration || currentTrack.durationSeconds || 0;
      const isThresholdMet =
        rawProgress.position >= 10 || (duration > 0 && rawProgress.position >= duration * 0.5);

      if (isThresholdMet) {
        hasRecordedRef.current = true;
        recordTrackPlayback(currentTrack).then((updatedHistory) => {
          setRecentTracks(updatedHistory);
        });
      }
    }
  }, [rawProgress.position, isPlaying, currentTrack]);

  // 4. ACCIONES DE REPRODUCCIÓN
  const playTrackAtIndex = async (index: number) => {
    if (index < 0 || index >= playlist.length) return;

    try {
      const selected = playlist[index];
      setCurrentTrackIndex(index);
      setIsFavorite(Boolean(selected.isFavorite));
      await AsyncStorage.setItem(TRACK_INDEX_STORAGE_KEY, String(index));

      await TrackPlayer.reset();
      await TrackPlayer.add({
        id: selected.id,
        url: selected.audioUrl,
        title: selected.title,
        artist: selected.artist,
        artwork: typeof selected.cover === 'object' && selected.cover.uri ? selected.cover.uri : undefined,
        duration: selected.durationSeconds,
      });
      await TrackPlayer.play();
    } catch (err) {
      console.warn('Error al reproducir pista en índice:', err);
    }
  };

  const playTrack = async (track: Track) => {
    if (!track) return;
    const idx = playlist.findIndex((t) => t.id === track.id || String(t.id) === String(track.id));
    if (idx !== -1) {
      await playTrackAtIndex(idx);
    } else {
      try {
        await TrackPlayer.reset();
        await TrackPlayer.add({
          id: track.id,
          url: track.audioUrl,
          title: track.title,
          artist: track.artist,
          artwork: typeof track.cover === 'object' && track.cover.uri ? track.cover.uri : undefined,
          duration: track.durationSeconds,
        });
        await TrackPlayer.play();
      } catch (e) {
        console.warn('Error al reproducir pista directa:', e);
      }
    }
  };

  const togglePlayPause = async () => {
    try {
      if (isPlaying) {
        await TrackPlayer.pause();
      } else {
        const queue = await TrackPlayer.getQueue();
        if (queue.length === 0 && currentTrack) {
          await playTrackAtIndex(currentTrackIndex);
        } else {
          await TrackPlayer.play();
        }
      }
    } catch (err) {
      console.warn('Error en togglePlayPause:', err);
    }
  };

  const toggleFavorite = async () => {
    if (!currentTrack) return;
    const newFav = !isFavorite;
    setIsFavorite(newFav);

    setPlaylist((prev) => {
      const updated = prev.map((t, idx) =>
        idx === currentTrackIndex ? { ...t, isFavorite: newFav } : t
      );
      AsyncStorage.setItem(PLAYLIST_STORAGE_KEY, JSON.stringify(updated)).catch(() => {});
      return updated;
    });
  };

  const toggleShuffle = async () => {
    setIsShuffle((prev) => !prev);
  };

  const toggleLoop = async () => {
    setIsLoop((prev) => !prev);
  };

  const skipToNext = async () => {
    if (playlist.length === 0) return;
    if (isShuffle) {
      const randomIdx = Math.floor(Math.random() * playlist.length);
      await playTrackAtIndex(randomIdx);
    } else {
      const nextIdx = (currentTrackIndex + 1) % playlist.length;
      await playTrackAtIndex(nextIdx);
    }
  };

  const skipToPrevious = async () => {
    if (playlist.length === 0) return;
    const prevIdx = (currentTrackIndex - 1 + playlist.length) % playlist.length;
    await playTrackAtIndex(prevIdx);
  };

  const seekTo = async (seconds: number) => {
    try {
      await TrackPlayer.seekTo(seconds);
    } catch (err) {
      console.warn('Error en seekTo:', err);
    }
  };

  const setPlaylistData = async (tracks: Track[]) => {
    setPlaylist(tracks);
    try {
      await AsyncStorage.setItem(PLAYLIST_STORAGE_KEY, JSON.stringify(tracks));
    } catch (err) {
      console.warn('Error guardando playlist:', err);
    }
  };

  const reloadPlaylistFromStorage = async () => {
    try {
      const savedPlaylistJson = await AsyncStorage.getItem(PLAYLIST_STORAGE_KEY);
      if (savedPlaylistJson) {
        const parsed: Track[] = JSON.parse(savedPlaylistJson);
        if (parsed && Array.isArray(parsed)) {
          setPlaylist(parsed);
        }
      }
    } catch (err) {
      console.warn('Error recargando playlist en PlayerContext:', err);
    }
  };

  const refreshRecentHistory = async () => {
    const history = await getRecentHistory();
    setRecentTracks(history);
  };

  return (
    <PlayerContext.Provider
      value={{
        playlist,
        currentTrackIndex,
        currentTrack,
        isPlaying,
        progress: {
          position: rawProgress.position || 0,
          duration: rawProgress.duration || (currentTrack?.durationSeconds || 0),
        },
        isFavorite,
        isShuffle,
        isLoop,
        recentTracks,
        isLoading,
        playTrackAtIndex,
        playTrack,
        togglePlayPause,
        toggleFavorite,
        toggleShuffle,
        toggleLoop,
        skipToNext,
        skipToPrevious,
        seekTo,
        setPlaylistData,
        reloadPlaylistFromStorage,
        refreshRecentHistory,
      }}
    >
      {children}
    </PlayerContext.Provider>
  );
};

export const usePlayer = (): PlayerContextType => {
  const context = useContext(PlayerContext);
  if (!context) {
    throw new Error('usePlayer debe ser utilizado dentro de un PlayerProvider');
  }
  return context;
};

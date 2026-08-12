import React, { useState, useEffect } from 'react';
import {
  StyleSheet,
  View,
  Text,
  TouchableOpacity,
  Image,
  Dimensions,
  StatusBar,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import TrackPlayer, {
  State,
  usePlaybackState,
  useProgress,
} from 'react-native-track-player';
import * as MediaLibrary from 'expo-media-library';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { LinearGradient } from 'expo-linear-gradient';
import { EKGVisualizer } from '@/components/EKGVisualizer';
import { HeartProgressSlider } from '@/components/HeartProgressSlider';
import { ControlButtonsRow } from '@/components/ControlButtonsRow';
import { CircleMenuIcon } from '@/components/CircleMenuIcon';
import { VolumeSlider } from '@/components/VolumeSlider';
import { DripCardFrame } from '@/components/DripCardFrame';
import { useNeonTheme } from '@/context/ThemeContext';
import { CustomizeModal } from '@/components/CustomizeModal';
import { LibraryModal, Track } from '@/components/LibraryModal';
import { getAlphaColor } from '@/utils/colorUtils';
import { mapAssetsToTracks } from '@/utils/mediaScanner';
import { getResolvedTrackCover } from '@/utils/coverArtManager';
import { setupTrackPlayer } from '@/utils/trackPlayerManager';
import { router } from 'expo-router';

const { width, height } = Dimensions.get('window');

const DEFAULT_FALLBACK_COVER = require('../../../assets/images/record_player.jpeg');
const PLAYLIST_STORAGE_KEY = '@custom_music_player_saved_playlist_v10';
const TRACK_INDEX_STORAGE_KEY = '@custom_music_player_saved_index_v10';

export default function PlayerScreen() {
  const {
    backgroundColor,
    cardColor,
    textColor,
    subtextColor,
    accentColor,
    artMode,
    customCoverUri,
    backgroundMode,
    customBgUri,
    gradientColors,
    useCardGradient,
  } = useNeonTheme();

  const playbackState = usePlaybackState();
  const progress = useProgress();

  const isPlaying = playbackState.state === State.Playing;

  const [playlist, setPlaylist] = useState<Track[]>([]);
  const [currentTrackIndex, setCurrentTrackIndex] = useState(0);
  const [isFavorite, setIsFavorite] = useState(true);
  const [isLoop, setIsLoop] = useState(false);
  const [isShuffle, setIsShuffle] = useState(false);
  const [volume, setVolume] = useState(85);
  const [isLoadingStorage, setIsLoadingStorage] = useState(false);
  const [scanProgressCount, setScanProgressCount] = useState(0);

  const [showCustomizeModal, setShowCustomizeModal] = useState(false);
  const [showLibraryModal, setShowLibraryModal] = useState(false);

  const track = playlist[currentTrackIndex];

  // GUARDAR LISTA E ÍNDICE EN ASYNCSTORAGE
  const savePlaylistToStorage = async (tracks: Track[]) => {
    try {
      await AsyncStorage.setItem(PLAYLIST_STORAGE_KEY, JSON.stringify(tracks));
    } catch (err) {
      console.warn('Error guardando lista en storage:', err);
    }
  };

  const saveIndexToStorage = async (idx: number) => {
    try {
      await AsyncStorage.setItem(TRACK_INDEX_STORAGE_KEY, String(idx));
    } catch (err) {
      console.warn('Error guardando posición en storage:', err);
    }
  };

  // RESTAURAR BIBLIOTECA AL ABRIR LA APP
  useEffect(() => {
    const initLibrary = async () => {
      await setupTrackPlayer();
      try {
        const savedPlaylistJson = await AsyncStorage.getItem(PLAYLIST_STORAGE_KEY);
        const savedIndexStr = await AsyncStorage.getItem(TRACK_INDEX_STORAGE_KEY);

        if (savedPlaylistJson) {
          const parsedTracks: Track[] = JSON.parse(savedPlaylistJson);
          if (parsedTracks && parsedTracks.length > 0) {
            setPlaylist(parsedTracks);
            setScanProgressCount(parsedTracks.length);
            const initialIdx = savedIndexStr ? Math.min(parseInt(savedIndexStr, 10), parsedTracks.length - 1) : 0;
            const validIdx = Math.max(0, initialIdx);
            setCurrentTrackIndex(validIdx);
            await loadTrack(validIdx, false, parsedTracks);
            setIsLoadingStorage(false);
            return;
          }
        }
      } catch (err) {
        console.warn('Error restaurando biblioteca guardada:', err);
      }

      scanPhoneMusicFolder();
    };

    initLibrary();
  }, []);

  // ESCANEAR MÚSICA COMPLETA DEL TELÉFONO
  const scanPhoneMusicFolder = async () => {
    try {
      setScanProgressCount(0);
      setIsLoadingStorage(true);
      const { status } = await MediaLibrary.requestPermissionsAsync();
      
      if (status === 'granted') {
        let allScannedTracks: Track[] = [];
        let cursor: string | undefined = undefined;
        let hasMore = true;

        while (hasMore) {
          const page = await MediaLibrary.getAssetsAsync({
            mediaType: 'audio',
            first: 2000,
            after: cursor,
            sortBy: [[MediaLibrary.SortBy.creationTime, false]],
          });

          if (page.assets && page.assets.length > 0) {
            const mappedBatch = mapAssetsToTracks(page.assets);
            allScannedTracks = [...allScannedTracks, ...mappedBatch];
            setPlaylist(allScannedTracks);
            setScanProgressCount(allScannedTracks.length);

            cursor = page.endCursor;
            hasMore = Boolean(page.hasNextPage && cursor);
          } else {
            hasMore = false;
          }
        }

        if (allScannedTracks.length > 0) {
          setCurrentTrackIndex(0);
          await savePlaylistToStorage(allScannedTracks);
          await saveIndexToStorage(0);
          await loadTrack(0, false, allScannedTracks);
        }
      }
    } catch (error) {
      console.warn('Error escaneando almacenamiento:', error);
    } finally {
      setIsLoadingStorage(false);
    }
  };

  const handleFolderTracksLoaded = async (folderTracks: Track[]) => {
    if (folderTracks.length > 0) {
      setPlaylist(folderTracks);
      setScanProgressCount(folderTracks.length);
      setCurrentTrackIndex(0);
      await savePlaylistToStorage(folderTracks);
      await saveIndexToStorage(0);
      await loadTrack(0, true, folderTracks);
      setShowLibraryModal(false);
    }
  };

  // ELIMINAR CANCIÓN INDIVIDUAL
  const handleDeleteSingleTrack = async (trackId: string) => {
    const updated = playlist.filter((t) => t.id !== trackId);
    setPlaylist(updated);
    await savePlaylistToStorage(updated);

    if (updated.length === 0) {
      await TrackPlayer.reset();
      setCurrentTrackIndex(0);
    } else if (currentTrackIndex >= updated.length) {
      const newIdx = updated.length - 1;
      setCurrentTrackIndex(newIdx);
      await loadTrack(newIdx, isPlaying, updated);
    }
  };

  // ELIMINAR MÚLTIPLES CANCIONES SELECCIONADAS
  const handleDeleteMultipleTracks = async (trackIds: string[]) => {
    const idSet = new Set(trackIds);
    const updated = playlist.filter((t) => !idSet.has(t.id));
    setPlaylist(updated);
    await savePlaylistToStorage(updated);

    if (updated.length === 0) {
      await TrackPlayer.reset();
      setCurrentTrackIndex(0);
    } else {
      const newIdx = Math.min(currentTrackIndex, updated.length - 1);
      setCurrentTrackIndex(newIdx);
      await loadTrack(newIdx, isPlaying, updated);
    }
  };

  // CARGAR PISTA EN REACT-NATIVE-TRACK-PLAYER CON NOTIFICACIÓN NATIVA
  useEffect(() => {
    if (playlist.length > 0 && currentTrackIndex < playlist.length) {
      loadTrack(currentTrackIndex, isPlaying, playlist);
    }
  }, [currentTrackIndex]);

  const loadTrack = async (index: number, autoPlay: boolean, currentList = playlist) => {
    try {
      const targetTrack = currentList[index];
      if (!targetTrack) return;

      const coverObj = await getResolvedTrackCover(targetTrack.id, targetTrack.audioUrl, DEFAULT_FALLBACK_COVER);
      const artworkUri = typeof coverObj === 'object' && coverObj.uri ? coverObj.uri : undefined;

      await TrackPlayer.reset();
      await TrackPlayer.add({
        id: targetTrack.id,
        url: targetTrack.audioUrl,
        title: targetTrack.title,
        artist: targetTrack.artist,
        album: targetTrack.album,
        artwork: artworkUri,
        duration: targetTrack.durationSeconds,
      });

      await TrackPlayer.setVolume(volume / 100);

      if (autoPlay) {
        await TrackPlayer.play();
      }
    } catch (error) {
      console.warn('TrackPlayer load error:', error);
    }
  };

  const togglePlayPause = async () => {
    if (isPlaying) {
      await TrackPlayer.pause();
    } else {
      await TrackPlayer.play();
    }
  };

  const handleNext = async () => {
    if (playlist.length === 0) return;
    const nextIdx = isShuffle
      ? Math.floor(Math.random() * playlist.length)
      : (currentTrackIndex + 1) % playlist.length;
    setCurrentTrackIndex(nextIdx);
    await saveIndexToStorage(nextIdx);
  };

  const handlePrev = async () => {
    if (playlist.length === 0) return;
    const prevIdx = (currentTrackIndex - 1 + playlist.length) % playlist.length;
    setCurrentTrackIndex(prevIdx);
    await saveIndexToStorage(prevIdx);
  };

  const handleSeek = async (seconds: number) => {
    await TrackPlayer.seekTo(seconds);
  };

  const handleVolumeChange = async (newVol: number) => {
    setVolume(newVol);
    await TrackPlayer.setVolume(newVol / 100);
  };

  const toggleLoop = () => {
    setIsLoop(!isLoop);
  };

  const [mainCoverError, setMainCoverError] = useState(false);
  const [resolvedCover, setResolvedCover] = useState<any>(DEFAULT_FALLBACK_COVER);

  useEffect(() => {
    setMainCoverError(false);
    if (artMode === 'custom' && customCoverUri) {
      setResolvedCover({ uri: customCoverUri });
      return;
    }

    if (track) {
      getResolvedTrackCover(track.id, track.audioUrl, DEFAULT_FALLBACK_COVER)
        .then((res) => setResolvedCover(res))
        .catch(() => setResolvedCover(DEFAULT_FALLBACK_COVER));
    } else {
      setResolvedCover(DEFAULT_FALLBACK_COVER);
    }
  }, [track, artMode, customCoverUri]);

  return (
    <SafeAreaView style={[styles.safeContainer, { backgroundColor: '#0A0A0A' }]}>
      <StatusBar barStyle="light-content" backgroundColor="#0A0A0A" />

      {/* COMPONENTE DE FONDO CON IMAGEN Y DEGRADADO NEÓN VIVO */}
      {backgroundMode === 'gradient' && customBgUri ? (
        <Image source={{ uri: customBgUri }} style={StyleSheet.absoluteFillObject} resizeMode="cover" />
      ) : null}

      <View style={styles.fixedRootContainer}>
        {/* CABECERA CON TÍTULO DE LA APP Y BOTONES DE ACCESO RÁPIDO */}
        <View style={styles.topHeaderBar}>
          <View style={styles.appTitleContainer}>
            <Text style={[styles.appHeaderTitle, { color: textColor }]}>CUSTOM PLAYER</Text>
            <View style={[styles.neonStatusDot, { backgroundColor: accentColor }]} />
          </View>

          <View style={styles.headerRightActions}>
            <TouchableOpacity
              style={[styles.headerCircleBtn, { borderColor: accentColor, backgroundColor: getAlphaColor(accentColor, '22') }]}
              onPress={() => setShowCustomizeModal(true)}
            >
              <Text style={[styles.headerCircleBtnText, { color: accentColor }]}>🎨</Text>
            </TouchableOpacity>

            <TouchableOpacity
              style={[styles.headerCircleBtn, { borderColor: accentColor, backgroundColor: getAlphaColor(accentColor, '22') }]}
              onPress={() => router.push('/library' as any)}
            >
              <Text style={[styles.headerCircleBtnText, { color: accentColor }]}>📚</Text>
            </TouchableOpacity>

            <CircleMenuIcon
              color={accentColor}
              backgroundColor={cardColor}
              size={36}
              onPress={() => router.push('/settings' as any)}
            />
          </View>
        </View>

        {/* CUERPO CENTRAL FIJO CON LA TARJETA DEL REPRODUCTOR Y GOTAS LÍQUIDAS INTEGRADAS */}
        <View style={styles.centerPlayerSection}>
          <View style={styles.playerWrapper}>
            <LinearGradient
              colors={useCardGradient ? gradientColors : [cardColor, cardColor]}
              start={{ x: 0.1, y: 0 }}
              end={{ x: 0.9, y: 1 }}
              style={[styles.fluidPlayerCard, { borderColor: getAlphaColor(accentColor, 'AA') }]}
            >
              {/* ESTRUCTURA MARCO DE GOTAS DE SLIME ALREDEDOR DE LA TARJETA */}
              <DripCardFrame color={accentColor} width={width * 0.92} height={height * 0.68} />

              {/* CONTENEDOR DE LA CARÁTULA DEL ÁLBUM CON GLOW EN EL BORDE */}
              <View style={[styles.albumArtContainer, { borderColor: accentColor, shadowColor: accentColor }]}>
                <Image
                  source={mainCoverError ? DEFAULT_FALLBACK_COVER : resolvedCover}
                  style={styles.albumArtImage}
                  resizeMode="cover"
                  onError={() => setMainCoverError(true)}
                />
              </View>

              {/* TÍTULO Y ARTISTA CON ESTILO DE ACENTO NEÓN */}
              <View style={styles.trackInfoWrapper}>
                <Text style={[styles.trackTitleText, { color: textColor }]} numberOfLines={1}>
                  {track ? track.title : 'Cargando biblioteca...'}
                </Text>
                <Text style={[styles.artistNameText, { color: accentColor }]} numberOfLines={1}>
                  {track ? track.artist : 'Escaneando archivos'}
                </Text>
              </View>

              {/* VISUALIZADOR DE ONDAS FRECUENCIA VITAL EKG (24 BARRAS NEÓN) */}
              <EKGVisualizer barCount={24} isPlaying={isPlaying} />

              {/* BARRAS DE PROGRESO DE CORAZONES EN TIEMPO REAL */}
              <HeartProgressSlider
                positionSec={progress.position}
                durationSec={progress.duration || (track ? track.durationSeconds : 0)}
                onSeek={handleSeek}
              />

              {/* BARRA INFERIOR DE CONTROLES PRINCIPALES */}
              <ControlButtonsRow
                isPlaying={isPlaying}
                isFavorite={isFavorite}
                isLoop={isLoop}
                onTogglePlayPause={togglePlayPause}
                onToggleFavorite={() => setIsFavorite(!isFavorite)}
                onToggleLoop={toggleLoop}
                onPrev={handlePrev}
                onNext={handleNext}
              />
            </LinearGradient>
          </View>
        </View>

        {/* BARRA INFERIOR DE CONTROL DE VOLUMEN MULTIMEDIA */}
        <View style={styles.bottomVolumeSection}>
          <VolumeSlider volume={volume} onVolumeChange={handleVolumeChange} />
        </View>
      </View>

      {/* MODAL DE PERSONALIZACIÓN */}
      <CustomizeModal visible={showCustomizeModal} onClose={() => setShowCustomizeModal(false)} />

      {/* MODAL DE BIBLIOTECA */}
      <LibraryModal
        visible={showLibraryModal}
        playlist={playlist}
        currentTrackIndex={currentTrackIndex}
        isPlaying={isPlaying}
        onClose={() => setShowLibraryModal(false)}
        onSelectTrack={(selectedTrack) => {
          const idx = playlist.findIndex((t) => t.id === selectedTrack.id);
          if (idx >= 0) {
            setCurrentTrackIndex(idx);
            loadTrack(idx, true);
          }
          setShowLibraryModal(false);
        }}
        onDeleteSingleTrack={handleDeleteSingleTrack}
        onDeleteMultipleTracks={handleDeleteMultipleTracks}
        onRescan={scanPhoneMusicFolder}
        onPickFolder={() => {}}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeContainer: {
    flex: 1,
  },
  fixedRootContainer: {
    flex: 1,
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingTop: 10,
    paddingBottom: 10,
  },
  topHeaderBar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    height: 50,
  },
  appTitleContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  appHeaderTitle: {
    fontSize: 16,
    fontWeight: '900',
    letterSpacing: 1.5,
  },
  neonStatusDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
  },
  headerRightActions: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  headerCircleBtn: {
    width: 36,
    height: 36,
    borderRadius: 18,
    borderWidth: 1.5,
    justifyContent: 'center',
    alignItems: 'center',
  },
  headerCircleBtnText: {
    fontSize: 16,
  },
  centerPlayerSection: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    marginVertical: 10,
  },
  playerWrapper: {
    width: '100%',
    alignItems: 'center',
  },
  fluidPlayerCard: {
    width: '100%',
    borderRadius: 28,
    borderWidth: 2,
    paddingVertical: 20,
    paddingHorizontal: 18,
    alignItems: 'center',
    justifyContent: 'space-between',
    position: 'relative',
    elevation: 12,
  },
  albumArtContainer: {
    width: width * 0.48,
    height: width * 0.48,
    maxWidth: 210,
    maxHeight: 210,
    borderRadius: 20,
    borderWidth: 2.5,
    overflow: 'hidden',
    marginBottom: 14,
    shadowOffset: { width: 0, height: 6 },
    shadowOpacity: 0.5,
    shadowRadius: 10,
    elevation: 8,
  },
  albumArtImage: {
    width: '100%',
    height: '100%',
  },
  trackInfoWrapper: {
    alignItems: 'center',
    width: '100%',
    paddingHorizontal: 10,
    marginBottom: 10,
  },
  trackTitleText: {
    fontSize: 17,
    fontWeight: 'bold',
    textAlign: 'center',
  },
  artistNameText: {
    fontSize: 13,
    fontWeight: '600',
    textAlign: 'center',
    marginTop: 4,
  },
  bottomVolumeSection: {
    height: 54,
    justifyContent: 'center',
  },
});

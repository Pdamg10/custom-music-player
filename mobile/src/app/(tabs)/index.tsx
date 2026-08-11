import React, { useState, useEffect, useRef } from 'react';
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
import { Audio } from 'expo-av';
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
  } = useNeonTheme();

  const [playlist, setPlaylist] = useState<Track[]>([]);
  const [currentTrackIndex, setCurrentTrackIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isFavorite, setIsFavorite] = useState(true);
  const [isLoop, setIsLoop] = useState(false);
  const [isShuffle, setIsShuffle] = useState(false);
  const [volume, setVolume] = useState(85);
  const [positionSec, setPositionSec] = useState(0);
  const [durationSec, setDurationSec] = useState(0);
  const [isLoadingStorage, setIsLoadingStorage] = useState(false);
  const [scanProgressCount, setScanProgressCount] = useState(0);

  const [showCustomizeModal, setShowCustomizeModal] = useState(false);
  const [showLibraryModal, setShowLibraryModal] = useState(false);

  const soundRef = useRef<Audio.Sound | null>(null);
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
    Audio.setAudioModeAsync({
      allowsRecordingIOS: false,
      staysActiveInBackground: true,
      playsInSilentModeIOS: true,
      shouldDuckAndroid: true,
      playThroughEarpieceAndroid: false,
    }).catch(console.error);

    const initLibrary = async () => {
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

    return () => {
      if (soundRef.current) {
        soundRef.current.unloadAsync().catch(() => {});
      }
    };
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
      if (soundRef.current) await soundRef.current.unloadAsync();
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
      if (soundRef.current) await soundRef.current.unloadAsync();
      setCurrentTrackIndex(0);
    } else {
      const newIdx = Math.min(currentTrackIndex, updated.length - 1);
      setCurrentTrackIndex(newIdx);
      await loadTrack(newIdx, isPlaying, updated);
    }
  };

  // CARGAR PISTA EN EXPO-AV
  useEffect(() => {
    if (playlist.length > 0 && currentTrackIndex < playlist.length) {
      loadTrack(currentTrackIndex, isPlaying, playlist);
    }
  }, [currentTrackIndex]);

  const loadTrack = async (index: number, autoPlay: boolean, currentList = playlist) => {
    try {
      if (soundRef.current) {
        await soundRef.current.unloadAsync();
        soundRef.current = null;
      }

      const targetTrack = currentList[index];
      if (!targetTrack) return;

      const { sound } = await Audio.Sound.createAsync(
        { uri: targetTrack.audioUrl },
        { shouldPlay: autoPlay, volume: volume / 100, isLooping: isLoop, progressUpdateIntervalMillis: 200 },
        onPlaybackStatusUpdate
      );

      soundRef.current = sound;
      setIsPlaying(autoPlay);
    } catch (error) {
      console.warn('Audio load error:', error);
    }
  };

  const onPlaybackStatusUpdate = (status: any) => {
    if (status.isLoaded) {
      setIsPlaying(status.isPlaying);
      if (status.positionMillis !== undefined) {
        setPositionSec(Math.floor(status.positionMillis / 1000));
      }
      if (status.durationMillis && status.durationMillis > 0) {
        setDurationSec(Math.floor(status.durationMillis / 1000));
      }
      if (status.didJustFinish && !status.isLooping) {
        handleNext();
      }
    }
  };

  const togglePlayPause = async () => {
    if (!soundRef.current) {
      await loadTrack(currentTrackIndex, true);
      return;
    }

    if (isPlaying) {
      await soundRef.current.pauseAsync();
    } else {
      await soundRef.current.playAsync();
    }
  };

  const handleNext = async () => {
    if (playlist.length === 0) return;
    const nextIdx = isShuffle
      ? Math.floor(Math.random() * playlist.length)
      : (currentTrackIndex + 1) % playlist.length;
    setCurrentTrackIndex(nextIdx);
  };

  const handlePrev = async () => {
    if (playlist.length === 0) return;
    const prevIdx = (currentTrackIndex - 1 + playlist.length) % playlist.length;
    setCurrentTrackIndex(prevIdx);
  };

  const handleSeek = async (seconds: number) => {
    setPositionSec(seconds);
    if (soundRef.current) {
      await soundRef.current.setPositionAsync(seconds * 1000);
    }
  };

  const handleVolumeChange = async (newVol: number) => {
    setVolume(newVol);
    if (soundRef.current) {
      await soundRef.current.setVolumeAsync(newVol / 100);
    }
  };

  const toggleLoop = async () => {
    const nextLoop = !isLoop;
    setIsLoop(nextLoop);
    if (soundRef.current) {
      await soundRef.current.setIsLoopingAsync(nextLoop);
    }
  };

  const [mainCoverError, setMainCoverError] = useState(false);
  const [resolvedCover, setResolvedCover] = useState<any>(DEFAULT_FALLBACK_COVER);

  useEffect(() => {
    setMainCoverError(false);
    if (track) {
      getResolvedTrackCover(track.id, track.audioUrl, DEFAULT_FALLBACK_COVER).then((source) => {
        setResolvedCover(source);
      });
    }
  }, [currentTrackIndex, track]);

  const displayArtSource =
    artMode === 'custom' && customCoverUri
      ? { uri: customCoverUri }
      : !mainCoverError
      ? resolvedCover
      : DEFAULT_FALLBACK_COVER;

  return (
    <SafeAreaView style={[styles.fullScreenSafeArea, { backgroundColor }]}>
      <StatusBar barStyle="light-content" backgroundColor={backgroundColor} />

      {/* RENDERIZADO DEL FONDO PERSONALIZABLE DE PANTALLA COMPLETA */}
      {customBgUri ? (
        <View style={StyleSheet.absoluteFillObject}>
          <Image source={{ uri: customBgUri }} style={styles.wallpaperImage} resizeMode="cover" />
          <View style={styles.wallpaperOverlay} />
        </View>
      ) : backgroundMode === 'gradient' ? (
        <LinearGradient colors={gradientColors} style={StyleSheet.absoluteFillObject} />
      ) : null}

      {/* ESTRUCTURA FIJA DE REPRODUCTOR TIPO POWERAMP (SIN SCROLLVIEW) */}
      <View style={styles.fixedAppContainer}>
        
        {/* CABECERA SUPERIOR FIJA */}
        <View style={[styles.styledTopHeader, { backgroundColor: getAlphaColor(cardColor, 'DD'), borderColor: getAlphaColor(accentColor, '77') }]}>
          <View style={styles.headerAppTitleRow}>
            <Image source={DEFAULT_FALLBACK_COVER} style={styles.appLogoCircle} />
            <Text style={[styles.appTitleText, { color: textColor }]}>CUSTOM MUSIC PLAYER</Text>
          </View>

          <View style={styles.actionPillsRow}>
            <TouchableOpacity
              style={[styles.headerCircleBtn, { borderColor: accentColor, backgroundColor: getAlphaColor(accentColor, '22') }]}
              onPress={() => router.push('/library' as any)}
            >
              <Text style={[styles.headerCircleBtnText, { color: accentColor }]}>📚</Text>
            </TouchableOpacity>

            <TouchableOpacity
              style={[styles.headerCircleBtn, { borderColor: accentColor, backgroundColor: getAlphaColor(accentColor, '22') }]}
              onPress={() => router.push('/library' as any)}
            >
              <Text style={[styles.headerCircleBtnText, { color: accentColor }]}>📂</Text>
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
              colors={[getAlphaColor(accentColor, '25'), cardColor, '#0A0A0E']}
              start={{ x: 0.1, y: 0 }}
              end={{ x: 0.9, y: 1 }}
              style={[styles.fluidPlayerCard, { borderColor: getAlphaColor(accentColor, 'AA') }]}
            >
              {/* ADORNOS DECORATIVOS SUPERIORES */}
              <View style={styles.topOrnamentsRow}>
                <Text style={[styles.headphoneSticker, { color: accentColor }]}>🎧🎀</Text>
                <Text style={[styles.starSticker, { color: accentColor }]}>⭐✨</Text>
              </View>

              {/* PORTADA DEL ÁLBUM RESPOSIVA FIJA */}
              <View style={[styles.fluidArtContainer, { borderColor: getAlphaColor(accentColor, '77') }]}>
                <Image
                  source={displayArtSource}
                  style={styles.fluidArtImage}
                  onError={() => setMainCoverError(true)}
                />
                <View style={styles.artOverlayBadges}>
                  <TouchableOpacity
                    style={styles.badgeCircleBtn}
                    onPress={() => setIsFavorite(!isFavorite)}
                  >
                    <Text style={styles.badgeIcon}>{isFavorite ? '❤️' : '🤍'}</Text>
                  </TouchableOpacity>
                </View>
              </View>

              {/* ETIQUETA SCRIPT "Android Player ♥" */}
              <View style={styles.deviceScriptRow}>
                <Text style={[styles.deviceScriptText, { color: accentColor }]}>Android Player ♥</Text>
              </View>

              {/* METADATOS DE LA CANCIÓN */}
              <View style={styles.fluidMetaBox}>
                <Text style={[styles.fluidTitleText, { color: textColor }]} numberOfLines={1}>
                  {track ? track.title : (isLoadingStorage ? `Escaneando (${scanProgressCount})...` : 'Selecciona o escanea tu música')}
                </Text>
                <Text style={[styles.fluidArtistText, { color: accentColor }]} numberOfLines={1}>
                  {track ? track.artist : 'Almacenamiento Interno'}
                </Text>
              </View>

              {/* VISUALIZADOR EKG NEÓN DE BARRAS VERTICALES */}
              <View style={styles.visualizerWaveBox}>
                <EKGVisualizer isPlaying={isPlaying} color={accentColor} />
              </View>

              {/* CONTROLES EN CÍRCULO */}
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

              {/* BARRA DE PROGRESO CON CORAZÓN Y TIEMPO RESTANTE NEGATIVO (-0:09) */}
              <HeartProgressSlider
                positionSec={positionSec}
                durationSec={durationSec}
                onSeek={handleSeek}
              />

              {/* BARRA DE VOLUMEN REACTIVA Y DINÁMICA */}
              <VolumeSlider volume={volume} onVolumeChange={handleVolumeChange} />
            </LinearGradient>

            {/* SILUETA DE GOTAS LÍQUIDAS (SLIME DRIP) UNIDA PERFECTAMENTE AL BORDE INFERIOR DEL REPRODUCTOR */}
            <DripCardFrame color={cardColor} borderColor={getAlphaColor(accentColor, 'AA')} width={width > 380 ? 350 : width - 30} />
          </View>
        </View>

      </View>

      {/* MODAL DE PERSONALIZACIÓN DE TEMA */}
      <CustomizeModal visible={showCustomizeModal} onClose={() => setShowCustomizeModal(false)} />

      {/* MODAL DE BIBLIOTECA COMPLETA CON CATEGORÍAS */}
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
          }
        }}
        onDeleteSingleTrack={handleDeleteSingleTrack}
        onDeleteMultipleTracks={handleDeleteMultipleTracks}
        onRescan={scanPhoneMusicFolder}
        onPickFolder={() => setShowLibraryModal(true)}
        onFolderTracksLoaded={handleFolderTracksLoaded}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  fullScreenSafeArea: {
    flex: 1,
  },
  wallpaperImage: {
    ...StyleSheet.absoluteFillObject,
    width: '100%',
    height: '100%',
  },
  wallpaperOverlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(0, 0, 0, 0.76)',
  },
  fixedAppContainer: {
    flex: 1,
    width: '100%',
    justifyContent: 'space-between',
    paddingHorizontal: 12,
  },
  styledTopHeader: {
    width: '100%',
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 18,
    borderWidth: 1.5,
    marginTop: 6,
  },
  headerAppTitleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  appLogoCircle: {
    width: 26,
    height: 26,
    borderRadius: 13,
  },
  appTitleText: {
    fontSize: 11,
    fontWeight: '900',
    letterSpacing: 1,
  },
  actionPillsRow: {
    flexDirection: 'row',
    gap: 8,
    alignItems: 'center',
  },
  headerCircleBtn: {
    width: 34,
    height: 34,
    borderRadius: 17,
    borderWidth: 1.5,
    justifyContent: 'center',
    alignItems: 'center',
  },
  headerCircleBtnText: {
    fontSize: 15,
  },
  centerPlayerSection: {
    flex: 1,
    width: '100%',
    alignItems: 'center',
    justifyContent: 'center',
  },
  playerWrapper: {
    width: '100%',
    maxWidth: 360,
    alignItems: 'center',
  },
  fluidPlayerCard: {
    width: '100%',
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    borderBottomLeftRadius: 0,
    borderBottomRightRadius: 0,
    borderWidth: 2,
    borderBottomWidth: 0,
    padding: 14,
    alignItems: 'center',
  },
  topOrnamentsRow: {
    width: '100%',
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 4,
    paddingHorizontal: 4,
  },
  headphoneSticker: {
    fontSize: 20,
  },
  starSticker: {
    fontSize: 20,
  },
  deviceScriptRow: {
    width: '100%',
    alignItems: 'flex-start',
    marginTop: 4,
    marginBottom: 2,
    paddingLeft: 4,
  },
  deviceScriptText: {
    fontSize: 13,
    fontStyle: 'italic',
    fontWeight: '700',
    letterSpacing: 0.5,
  },
  fluidArtContainer: {
    width: '100%',
    maxWidth: 340,
    height: height > 750 ? 280 : (height > 680 ? 230 : 190),
    borderRadius: 20,
    overflow: 'hidden',
    position: 'relative',
    backgroundColor: '#000000',
    marginBottom: 8,
    borderWidth: 1.5,
  },
  fluidArtImage: {
    width: '100%',
    height: '100%',
    resizeMode: 'cover',
  },
  artOverlayBadges: {
    position: 'absolute',
    bottom: 8,
    left: 8,
  },
  badgeCircleBtn: {
    width: 34,
    height: 34,
    borderRadius: 17,
    backgroundColor: 'rgba(0, 0, 0, 0.55)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  badgeIcon: {
    fontSize: 14,
  },
  fluidMetaBox: {
    width: '100%',
    alignItems: 'center',
    marginBottom: 4,
  },
  fluidTitleText: {
    fontSize: 17,
    fontWeight: '800',
    textAlign: 'center',
  },
  fluidArtistText: {
    fontSize: 12,
    marginTop: 2,
    textAlign: 'center',
    fontWeight: '600',
  },
  visualizerWaveBox: {
    width: '100%',
    height: 38,
    marginVertical: 2,
  },
});

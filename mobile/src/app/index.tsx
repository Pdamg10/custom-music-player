import React, { useState, useEffect, useRef } from 'react';
import {
  StyleSheet,
  View,
  Text,
  TouchableOpacity,
  Image,
  Dimensions,
  StatusBar,
  ScrollView,
  ActivityIndicator,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Audio } from 'expo-av';
import * as DocumentPicker from 'expo-document-picker';
import * as MediaLibrary from 'expo-media-library';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { LinearGradient } from 'expo-linear-gradient';
import { EKGVisualizer } from '@/components/EKGVisualizer';
import { EKGBackgroundVisualizer } from '@/components/EKGBackgroundVisualizer';
import { HeartProgressSlider } from '@/components/HeartProgressSlider';
import { ControlButtonsRow } from '@/components/ControlButtonsRow';
import { NeonScannerLoader } from '@/components/NeonScannerLoader';
import { EmptyScanStateCard } from '@/components/EmptyScanStateCard';
import { VirtualizedPlaylist } from '@/components/VirtualizedPlaylist';
import { CircleMenuIcon } from '@/components/CircleMenuIcon';
import { VolumeSlider } from '@/components/VolumeSlider';
import { DripCardFrame } from '@/components/DripCardFrame';
import { useNeonTheme } from '@/context/ThemeContext';
import { CustomizeModal } from '@/components/CustomizeModal';

const { width } = Dimensions.get('window');

interface Track {
  id: string;
  title: string;
  artist: string;
  album: string;
  durationSeconds: number;
  cover: any;
  audioUrl: string;
}

const DEFAULT_FALLBACK_COVER = require('../../assets/images/record_player.jpeg');
const PLAYLIST_STORAGE_KEY = '@custom_music_player_saved_playlist_v5';
const TRACK_INDEX_STORAGE_KEY = '@custom_music_player_saved_index_v5';

export default function HomeScreen() {
  const {
    backgroundColor,
    cardColor,
    surfaceColor,
    textColor,
    subtextColor,
    accentColor,
    artMode,
    customCoverUri,
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

  // RESTAURAR BIBLIOTECA AL ABRIR LA APP (CARGA INSTANTÁNEA EN <5MS)
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

      // Si es la primera vez que se abre la app sin canciones guardadas, escanea automáticamente
      scanPhoneMusicFolder();
    };

    initLibrary();

    return () => {
      if (soundRef.current) {
        soundRef.current.unloadAsync().catch(() => {});
      }
    };
  }, []);

  // ESCANEAR MÚSICA AUTOMÁTICAMENTE DE LA MEMORIA CON CONTADOR EN TIEMPO REAL
  const scanPhoneMusicFolder = async () => {
    try {
      setScanProgressCount(0);
      setIsLoadingStorage(true);
      const { status } = await MediaLibrary.requestPermissionsAsync();
      
      if (status === 'granted') {
        let media = await MediaLibrary.getAssetsAsync({
          mediaType: 'audio',
          first: 500,
          sortBy: [[MediaLibrary.SortBy.creationTime, false]],
        });

        if (media.assets && media.assets.length > 0) {
          let scannedTracks: Track[] = media.assets
            .filter((asset) => (asset.duration || 0) > 10) // Ignorar tonos cortos de notificación
            .map((asset) => {
              const albumArtUri = `content://media/external/audio/media/${asset.id}/albumart`;
              return {
                id: asset.id,
                title: asset.filename.replace(/\.[^/.]+$/, ''),
                artist: 'Música en Teléfono',
                album: 'Almacenamiento Interno',
                durationSeconds: Math.floor(asset.duration || 0),
                cover: { uri: albumArtUri },
                audioUrl: asset.uri,
              };
            });

          setPlaylist(scannedTracks);
          setScanProgressCount(scannedTracks.length);
          setCurrentTrackIndex(0);
          await savePlaylistToStorage(scannedTracks);
          await saveIndexToStorage(0);
          await loadTrack(0, false, scannedTracks);

          // Cargar paginado incremental en segundo plano actualizando el contador en vivo y carátulas
          if (media.hasNextPage && media.endCursor) {
            let cursor: string | undefined = media.endCursor;
            let hasMore: boolean = Boolean(media.hasNextPage);

            while (hasMore && cursor) {
              const nextPage = await MediaLibrary.getAssetsAsync({
                mediaType: 'audio',
                first: 500,
                after: cursor,
                sortBy: [[MediaLibrary.SortBy.creationTime, false]],
              });

              if (nextPage.assets && nextPage.assets.length > 0) {
                const moreTracks: Track[] = nextPage.assets
                  .filter((asset) => (asset.duration || 0) > 10)
                  .map((asset) => {
                    const albumArtUri = `content://media/external/audio/media/${asset.id}/albumart`;
                    return {
                      id: asset.id,
                      title: asset.filename.replace(/\.[^/.]+$/, ''),
                      artist: 'Música en Teléfono',
                      album: 'Almacenamiento Interno',
                      durationSeconds: Math.floor(asset.duration || 0),
                      cover: { uri: albumArtUri },
                      audioUrl: asset.uri,
                    };
                  });

                scannedTracks = [...scannedTracks, ...moreTracks];
                setPlaylist(scannedTracks);
                setScanProgressCount(scannedTracks.length);
                await savePlaylistToStorage(scannedTracks);
                cursor = nextPage.endCursor;
                hasMore = Boolean(nextPage.hasNextPage);
              } else {
                hasMore = false;
              }
            }
          }
        }
      }
    } catch (error) {
      console.warn('Error escaneando música del almacenamiento:', error);
    } finally {
      setIsLoadingStorage(false);
    }
  };

  // SELECCIONAR CARPETA Y GUARDAR ARCHIVOS PERMANENTEMENTE EN LA APP
  const pickMusicFolderFiles = async () => {
    try {
      const result = await DocumentPicker.getDocumentAsync({
        type: ['audio/*', 'audio/flac', 'audio/x-flac', 'audio/x-m4a', 'audio/mp4', 'audio/wav', 'audio/ogg'],
        multiple: true,
        copyToCacheDirectory: true,
      });

      if (!result.canceled && result.assets && result.assets.length > 0) {
        const folderTracks: Track[] = result.assets.map((file, idx) => ({
          id: `folder_${Date.now()}_${idx}`,
          title: file.name.replace(/\.[^/.]+$/, ''),
          artist: 'Carpeta Seleccionada',
          album: 'Memoria Local',
          durationSeconds: 200,
          cover: DEFAULT_FALLBACK_COVER,
          audioUrl: file.uri,
        }));

        setPlaylist(folderTracks);
        setCurrentTrackIndex(0);
        await savePlaylistToStorage(folderTracks);
        await saveIndexToStorage(0);
        await loadTrack(0, true, folderTracks);
      }
    } catch (error) {
      console.warn('Error en la selección de la carpeta:', error);
    }
  };

  // Cargar pista en el motor de audio expo-av
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

  const formatTime = (secs: number) => {
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return `${m}:${s < 10 ? '0' : ''}${s}`;
  };

  const formatRemainingTime = (pos: number, dur: number) => {
    const remain = Math.max(0, dur - pos);
    const m = Math.floor(remain / 60);
    const s = remain % 60;
    return `-${m}:${s < 10 ? '0' : ''}${s}`;
  };

  const [mainCoverError, setMainCoverError] = useState(false);

  // Reset main cover error when track changes
  useEffect(() => {
    setMainCoverError(false);
  }, [currentTrackIndex]);

  // Resolver la imagen a mostrar respetando artMode ('auto' vs 'custom') con fallback si falla
  const displayArtSource =
    artMode === 'custom' && customCoverUri
      ? { uri: customCoverUri }
      : !mainCoverError && track && (typeof track.cover === 'number' || (track.cover && track.cover.uri))
      ? track.cover
      : DEFAULT_FALLBACK_COVER;

  return (
    <SafeAreaView style={[styles.safeArea, { backgroundColor }]}>
      <StatusBar barStyle="light-content" backgroundColor={backgroundColor} />

      <ScrollView contentContainerStyle={styles.scrollContainer} showsVerticalScrollIndicator={false}>

        {/* BARRA SUPERIOR DE ACCIONES CON ÍCONO DE OPCIONES CIRCULAR Y SELECCIÓN DE CARPETA */}
        <View style={styles.topHeader}>
          <View style={styles.headerAppTitleRow}>
            <Image source={DEFAULT_FALLBACK_COVER} style={styles.appLogoCircle} />
            <Text style={[styles.appTitleText, { color: textColor }]}>CUSTOM MUSIC PLAYER</Text>
          </View>

          <View style={styles.actionPillsRow}>
            <TouchableOpacity
              style={[
                styles.actionPillBtn,
                { borderColor: accentColor, backgroundColor: cardColor },
              ]}
              onPress={pickMusicFolderFiles}
            >
              <Text style={[styles.actionPillText, { color: textColor }]}>📂 CARPETA</Text>
            </TouchableOpacity>

            {/* ÍCONO DE OPCIONES CIRCULAR EN LA ESQUINA (REFERENCIA EXACTA DEL USUARIO) */}
            <CircleMenuIcon
              color={accentColor}
              backgroundColor={cardColor}
              size={36}
              onPress={() => setShowCustomizeModal(true)}
            />
          </View>
        </View>

        {/* FONDO ANIMADO DE BARRAS DE ECUALIZADOR EKG A 60FPS (SVG + REANIMATED) */}
        <EKGBackgroundVisualizer isPlaying={isPlaying} />

        {/* REPRODUCTOR ESTILO LIQUID DRIP / DEGRADADO NEÓN PREMIUM (REFERENCIA DEL USUARIO) */}
        <View style={styles.playerWrapper}>
          <LinearGradient
            colors={[accentColor + '25', cardColor, '#0A0A0E']}
            start={{ x: 0.1, y: 0 }}
            end={{ x: 0.9, y: 1 }}
            style={[styles.fluidPlayerCard, { borderColor: accentColor + 'AA' }]}
          >

            {/* ADORNOS DECORATIVOS SUPERIORES ESTILO MOCKUP (Audífonos con moño + Estrella 3D) */}
            <View style={styles.topOrnamentsRow}>
              <Text style={[styles.headphoneSticker, { color: accentColor }]}>🎧🎀</Text>
              <Text style={[styles.starSticker, { color: accentColor }]}>⭐✨</Text>
            </View>

            {/* 1. PORTADA DEL ÁLBUM CUADRADA CON BORDE NEÓN Y CARÁTULA EXTRAÍDA NATIVAMENTE */}
            <View style={[styles.fluidArtContainer, { borderColor: accentColor + '77' }]}>
              <Image
                source={displayArtSource}
                style={styles.fluidArtImage}
                onError={() => setMainCoverError(true)}
              />
              <View style={styles.artOverlayBadges}>
                <TouchableOpacity style={styles.badgeCircleBtn}>
                  <Text style={styles.badgeIcon}>❤️</Text>
                </TouchableOpacity>
              </View>
            </View>

            {/* ETIQUETA "Android Player ♥" ESTILO MOCKUP */}
            <View style={styles.deviceScriptRow}>
              <Text style={[styles.deviceScriptText, { color: accentColor }]}>Android Player ♥</Text>
            </View>

            {/* 2. METADATOS DE LA CANCIÓN */}
            <View style={styles.fluidMetaBox}>
              <Text style={[styles.fluidTitleText, { color: textColor }]} numberOfLines={1}>
                {track ? track.title : 'Escaneando Música...'}
              </Text>
              <Text style={[styles.fluidArtistText, { color: accentColor }]} numberOfLines={1}>
                {track ? track.artist : 'Selecciona o escanea tu almacenamiento'}
              </Text>
            </View>

            {/* 3. VISUALIZADOR EKG NEÓN */}
            <View style={styles.visualizerWaveBox}>
              <EKGVisualizer isPlaying={isPlaying} color={accentColor} />
            </View>

            {/* 4. FILA DE CONTROLES SIMÉTRICA Y CENTRADA ([♥️] [⏮️] [(Play/Pausa)] [⏭️] [↻]) */}
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

            {/* 5. BARRA DE PROGRESO CON CORAZÓN SVG Y TIEMPO RESTANTE NEGATIVO (-1:45) */}
            <HeartProgressSlider
              positionSec={positionSec}
              durationSec={durationSec}
              onSeek={handleSeek}
            />

            {/* 6. BARRA DE VOLUMEN DEDICADA CON PARLANTES */}
            <VolumeSlider volume={volume} onVolumeChange={handleVolumeChange} />
          </LinearGradient>

          {/* EFECTO DE GOTEO LÍQUIDO / SLIME INFERIOR (DRIP SILHOUETTE) */}
          <DripCardFrame color={cardColor} borderColor={accentColor + 'AA'} width={width > 380 ? 350 : width - 30} />
        </View>

        {/* BOTÓN PARA RE-ESCANEAR ALMACENAMIENTO AUTOMÁTICO */}
        <TouchableOpacity style={[styles.scanStorageBtn, { backgroundColor: cardColor, borderColor: accentColor + '44' }]} onPress={scanPhoneMusicFolder}>
          <Text style={[styles.scanStorageBtnText, { color: accentColor }]}>
            {isLoadingStorage ? '⌛ ESCANEANDO MÚSICA...' : '🔄 RE-ESCANEAR MÚSICA DEL TELÉFONO'}
          </Text>
        </TouchableOpacity>

        {/* LISTA VIRTUALIZADA FLUIDA PARA 2,000+ CANCIONES (SIN PANTALLA NEGRA / CERO LAG) */}
        <VirtualizedPlaylist
          playlist={playlist}
          currentTrackIndex={currentTrackIndex}
          isPlaying={isPlaying}
          isLoadingStorage={isLoadingStorage}
          scanProgressCount={scanProgressCount}
          onSelectTrack={(idx) => setCurrentTrackIndex(idx)}
          onPickFolder={pickMusicFolderFiles}
          onRescan={scanPhoneMusicFolder}
        />

      </ScrollView>

      {/* MODAL DE PERSONALIZACIÓN */}
      <CustomizeModal visible={showCustomizeModal} onClose={() => setShowCustomizeModal(false)} />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
  },
  scrollContainer: {
    paddingHorizontal: 14,
    paddingTop: 8,
    paddingBottom: 40,
    alignItems: 'center',
  },
  topHeader: {
    width: '100%',
    maxWidth: 360,
    marginBottom: 12,
    alignItems: 'center',
  },
  headerAppTitleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 8,
  },
  appLogoCircle: {
    width: 28,
    height: 28,
    borderRadius: 14,
  },
  appTitleText: {
    fontSize: 13,
    fontWeight: '900',
    letterSpacing: 1.2,
  },
  actionPillsRow: {
    flexDirection: 'row',
    gap: 8,
  },
  actionPillBtn: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 14,
    borderWidth: 1.5,
  },
  actionPillText: {
    fontSize: 11,
    fontWeight: 'bold',
  },

  /* CONTENEDOR MOCKUP LIQUID DRIP */
  playerWrapper: {
    width: '100%',
    maxWidth: 360,
    alignItems: 'center',
    marginBottom: 10,
  },
  fluidPlayerCard: {
    width: '100%',
    borderRadius: 26,
    borderWidth: 2,
    padding: 16,
    alignItems: 'center',
    shadowColor: '#000000',
    shadowOffset: { width: 0, height: 10 },
    shadowOpacity: 0.6,
    shadowRadius: 20,
    elevation: 12,
  },
  topOrnamentsRow: {
    width: '100%',
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
    paddingHorizontal: 4,
  },
  headphoneSticker: {
    fontSize: 22,
  },
  starSticker: {
    fontSize: 22,
  },
  deviceScriptRow: {
    width: '100%',
    alignItems: 'flex-start',
    marginTop: 6,
    marginBottom: 4,
    paddingLeft: 4,
  },
  deviceScriptText: {
    fontSize: 14,
    fontStyle: 'italic',
    fontWeight: '700',
    letterSpacing: 0.5,
  },
  fluidArtContainer: {
    width: '100%',
    height: 300,
    borderRadius: 20,
    overflow: 'hidden',
    position: 'relative',
    backgroundColor: '#000000',
    marginBottom: 12,
    borderWidth: 1,
  },
  fluidArtImage: {
    width: '100%',
    height: '100%',
    resizeMode: 'cover',
  },
  artOverlayBadges: {
    position: 'absolute',
    bottom: 10,
    left: 10,
    flexDirection: 'row',
    gap: 8,
  },
  badgeCircleBtn: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: 'rgba(0, 0, 0, 0.55)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  badgeIcon: {
    fontSize: 15,
  },

  fluidMetaBox: {
    width: '100%',
    alignItems: 'center',
    marginBottom: 8,
  },
  fluidTitleText: {
    fontSize: 18,
    fontWeight: '800',
    textAlign: 'center',
  },
  fluidArtistText: {
    fontSize: 13,
    marginTop: 2,
    textAlign: 'center',
    fontWeight: '600',
  },

  quickActionsRow: {
    flexDirection: 'row',
    gap: 24,
    marginBottom: 8,
  },
  quickActionBtn: {
    padding: 6,
  },
  quickActionIcon: {
    fontSize: 22,
    fontWeight: 'bold',
  },

  visualizerWaveBox: {
    width: '100%',
    height: 45,
    marginVertical: 4,
  },

  bigControlsRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    width: '96%',
    marginVertical: 12,
  },
  smallControlCircle: {
    width: 44,
    height: 44,
    borderRadius: 22,
    justifyContent: 'center',
    alignItems: 'center',
  },
  smallControlIcon: {
    fontSize: 18,
  },
  mainPlayCircle: {
    width: 64,
    height: 64,
    borderRadius: 32,
    justifyContent: 'center',
    alignItems: 'center',
    shadowOffset: { width: 0, height: 6 },
    shadowOpacity: 0.6,
    shadowRadius: 12,
    elevation: 8,
  },
  mainPlayIcon: {
    color: '#000000',
    fontSize: 26,
    marginLeft: 3,
    fontWeight: 'bold',
  },

  progressSection: {
    width: '100%',
  },
  progressTrackBg: {
    height: 6,
    backgroundColor: 'rgba(255, 255, 255, 0.15)',
    borderRadius: 3,
    overflow: 'hidden',
  },
  progressTrackFill: {
    height: '100%',
    borderRadius: 3,
  },
  timePillsRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: 8,
  },
  timePillBadge: {
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 8,
  },
  timePillText: {
    fontSize: 10,
    fontWeight: 'bold',
  },

  scanStorageBtn: {
    width: '100%',
    maxWidth: 360,
    paddingVertical: 11,
    borderRadius: 14,
    alignItems: 'center',
    marginBottom: 12,
    borderWidth: 1,
  },
  scanStorageBtnText: {
    fontSize: 11,
    fontWeight: 'bold',
    letterSpacing: 0.8,
  },

  playlistCard: {
    width: '100%',
    maxWidth: 360,
    borderRadius: 18,
    padding: 12,
    borderWidth: 1,
  },
  playlistCardTitle: {
    fontSize: 12,
    fontWeight: 'bold',
    marginBottom: 8,
    letterSpacing: 0.8,
  },
  emptyPlaylistText: {
    fontSize: 11,
    textAlign: 'center',
    marginVertical: 10,
  },
  playlistTrackRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 8,
    paddingHorizontal: 8,
    borderRadius: 10,
    marginBottom: 4,
  },
  trackRowThumb: {
    width: 36,
    height: 36,
    borderRadius: 6,
  },
  trackRowMetaInfo: {
    flex: 1,
    marginLeft: 10,
  },
  trackRowTitleText: {
    fontSize: 13,
  },
  trackRowArtistText: {
    fontSize: 11,
  },
  playingStatusBadge: {
    fontSize: 9,
    fontWeight: 'bold',
  },
});

import React, { useState, useEffect, useRef, useMemo } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  Image,
  Dimensions,
  StatusBar,
  ActivityIndicator,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useLocalSearchParams, router } from 'expo-router';
import { LinearGradient } from 'expo-linear-gradient';

import { useNeonTheme } from '@/context/ThemeContext';
import { usePlayer } from '@/context/PlayerContext';
import { getAlphaColor } from '@/utils/colorUtils';
import { Track } from '@/components/LibraryModal';
import { getEmbeddedLyricsForTrack } from '@/utils/coverArtManager';
import { WaveformSeeker } from '@/components/WaveformSeeker';

const { width } = Dimensions.get('window');
const DEFAULT_FALLBACK_COVER = require('../../../assets/images/record_player.jpeg');

export interface LyricsLine {
  timeMs?: number;
  text: string;
}

export default function LyricsScreen() {
  const { trackId } = useLocalSearchParams<{ trackId?: string }>();
  const {
    backgroundColor,
    cardColor,
    textColor,
    subtextColor,
    accentColor,
    artMode,
    customCoverUri,
    gradientColors,
  } = useNeonTheme();

  const {
    currentTrack,
    playlist,
    isPlaying,
    progress,
    isShuffle,
    isLoop,
    togglePlayPause,
    toggleShuffle,
    toggleLoop,
    skipToNext,
    skipToPrevious,
    seekTo,
  } = usePlayer();

  // 1. RESOLUCIÓN DE LA PISTA OBJETIVO (TARGET TRACK)
  // Si trackId es provisto y difiere de currentTrack, mostramos esa pista en modo lectura.
  // De lo contrario, priorizamos currentTrack con sincronización en vivo.
  const targetTrack: Track | undefined = useMemo(() => {
    if (trackId && trackId !== 'current' && (!currentTrack || String(currentTrack.id) !== String(trackId))) {
      const found = playlist.find((t) => String(t.id) === String(trackId));
      if (found) return found;
    }
    return currentTrack || undefined;
  }, [trackId, currentTrack, playlist]);

  const isCurrentPlayingTrack = Boolean(
    currentTrack && targetTrack && String(currentTrack.id) === String(targetTrack.id)
  );

  const [lyricsText, setLyricsText] = useState<string | null>(null);
  const [parsedLines, setParsedLines] = useState<LyricsLine[]>([]);
  const [hasTimestamps, setHasTimestamps] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const scrollViewRef = useRef<ScrollView>(null);
  const isUserScrollingRef = useRef<boolean>(false);
  const userScrollTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const lineYPositions = useRef<{ [index: number]: number }>({});

  // 2. CARGA DE LETRAS EMBEBIDAS
  useEffect(() => {
    let isMounted = true;
    lineYPositions.current = {};

    const loadLyrics = async () => {
      if (!targetTrack || !targetTrack.audioUrl) {
        if (isMounted) {
          setLyricsText(null);
          setParsedLines([]);
          setHasTimestamps(false);
          setIsLoading(false);
        }
        return;
      }

      setIsLoading(true);
      try {
        const embedded = await getEmbeddedLyricsForTrack(targetTrack.audioUrl);
        if (isMounted) {
          if (embedded && embedded.trim().length > 0) {
            setLyricsText(embedded);
            parseLyricsFormat(embedded);
          } else {
            setLyricsText(null);
            setParsedLines([]);
            setHasTimestamps(false);
          }
        }
      } catch (err) {
        console.warn('Error al cargar letras:', err);
        if (isMounted) {
          setLyricsText(null);
          setParsedLines([]);
          setHasTimestamps(false);
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    loadLyrics();

    return () => {
      isMounted = false;
      if (userScrollTimeoutRef.current) {
        clearTimeout(userScrollTimeoutRef.current);
      }
    };
  }, [targetTrack?.id, targetTrack?.audioUrl]);

  // 3. PARSEADOR DE FORMATO LRC CON DETECCIÓN DE TIMESTAMPS [mm:ss.xx]
  const parseLyricsFormat = (rawText: string) => {
    const lines = rawText.split(/\r?\n/);
    const result: LyricsLine[] = [];
    let detectedTiming = false;

    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed) continue;

      const match = trimmed.match(/^\[(\d{2}):(\d{2})\.?(\d*)\](.*)/);
      if (match) {
        detectedTiming = true;
        const minutes = parseInt(match[1], 10);
        const seconds = parseInt(match[2], 10);
        const millis = match[3] ? parseInt(match[3].padEnd(3, '0').slice(0, 3), 10) : 0;
        const totalMs = (minutes * 60 + seconds) * 1000 + millis;
        result.push({ timeMs: totalMs, text: match[4].trim() });
      } else {
        result.push({ text: trimmed });
      }
    }

    setHasTimestamps(detectedTiming);
    setParsedLines(result);
  };

  // 4. ÍNDICE DE LÍNEA ACTIVA EN REPRODUCCIÓN VIVA
  const activeLineIndex = useMemo(() => {
    if (!isCurrentPlayingTrack || !hasTimestamps || parsedLines.length === 0) {
      return -1;
    }

    const currentMs = (progress.position || 0) * 1000;
    let foundIndex = -1;

    for (let i = 0; i < parsedLines.length; i++) {
      const line = parsedLines[i];
      if (line.timeMs !== undefined && currentMs >= line.timeMs) {
        foundIndex = i;
      } else if (line.timeMs !== undefined && currentMs < line.timeMs) {
        break;
      }
    }

    return foundIndex;
  }, [isCurrentPlayingTrack, hasTimestamps, parsedLines, progress.position]);

  // 5. AUTO-DESPLAZAMIENTO SUAVE A LA LÍNEA ACTIVA
  useEffect(() => {
    if (
      activeLineIndex >= 0 &&
      !isUserScrollingRef.current &&
      scrollViewRef.current
    ) {
      const measuredY = lineYPositions.current[activeLineIndex];
      const targetY = Math.max(0, (measuredY !== undefined ? measuredY : activeLineIndex * 46) - 120);
      scrollViewRef.current.scrollTo({ y: targetY, animated: true });
    }
  }, [activeLineIndex]);

  const handleScrollBegin = () => {
    isUserScrollingRef.current = true;
    if (userScrollTimeoutRef.current) {
      clearTimeout(userScrollTimeoutRef.current);
    }
  };

  const handleScrollEnd = () => {
    if (userScrollTimeoutRef.current) {
      clearTimeout(userScrollTimeoutRef.current);
    }
    userScrollTimeoutRef.current = setTimeout(() => {
      isUserScrollingRef.current = false;
    }, 3000);
  };

  const getCoverSource = (t?: Track) => {
    if (!t) return DEFAULT_FALLBACK_COVER;
    if (artMode === 'custom' && customCoverUri) {
      return { uri: customCoverUri };
    }
    return t.cover || DEFAULT_FALLBACK_COVER;
  };

  const duration = progress.duration || currentTrack?.durationSeconds || 0;
  const position = progress.position || 0;

  return (
    <SafeAreaView
      style={[styles.safeArea, { backgroundColor }]}
      edges={['top', 'left', 'right', 'bottom']}
    >
      <StatusBar barStyle="light-content" backgroundColor={backgroundColor} />

      {/* 1. FONDO: CARÁTULA CON BLUR FUERTE Y OVERLAY SUTIL */}
      <View style={StyleSheet.absoluteFillObject} pointerEvents="none">
        <Image
          source={getCoverSource(targetTrack)}
          style={StyleSheet.absoluteFillObject}
          resizeMode="cover"
          blurRadius={36}
        />
        <View
          style={[
            StyleSheet.absoluteFillObject,
            { backgroundColor: getAlphaColor(backgroundColor, 'B3') },
          ]}
        />
      </View>

      <View style={styles.container}>
        {/* 2. HEADER: BOTÓN ATRÁS Y TÍTULO "Lyrics" CENTRADO */}
        <View style={styles.headerRow}>
          <TouchableOpacity
            style={[
              styles.headerGlassBtn,
              {
                backgroundColor: getAlphaColor(cardColor, 'B3'),
                borderColor: getAlphaColor(accentColor, '33'),
              },
            ]}
            onPress={() => router.back()}
            activeOpacity={0.7}
          >
            <Text style={[styles.headerIconText, { color: textColor }]}>⌄</Text>
          </TouchableOpacity>

          <Text style={[styles.headerTitle, { color: textColor }]}>Lyrics</Text>

          <View style={styles.headerPlaceholderRight} />
        </View>

        {/* 3. CONTENIDO PRINCIPAL: VISUALIZADOR DE LETRAS O ESTADO VACÍO */}
        <View style={styles.lyricsContainer}>
          {isLoading ? (
            <View style={styles.loadingBox}>
              <ActivityIndicator size="large" color={accentColor} />
              <Text style={[styles.loadingText, { color: subtextColor }]}>
                Cargando letras de la pista...
              </Text>
            </View>
          ) : lyricsText && parsedLines.length > 0 ? (
            <ScrollView
              ref={scrollViewRef}
              style={styles.lyricsScrollView}
              contentContainerStyle={styles.lyricsContentContainer}
              showsVerticalScrollIndicator={false}
              onScrollBeginDrag={handleScrollBegin}
              onMomentumScrollBegin={handleScrollBegin}
              onScrollEndDrag={handleScrollEnd}
              onMomentumScrollEnd={handleScrollEnd}
              scrollEventThrottle={16}
            >
              {parsedLines.map((item, idx) => {
                const isActive = hasTimestamps && isCurrentPlayingTrack && idx === activeLineIndex;

                return (
                  <TouchableOpacity
                    key={idx}
                    onLayout={(event) => {
                      lineYPositions.current[idx] = event.nativeEvent.layout.y;
                    }}
                    activeOpacity={item.timeMs !== undefined && isCurrentPlayingTrack ? 0.7 : 1}
                    onPress={() => {
                      if (item.timeMs !== undefined && isCurrentPlayingTrack) {
                        seekTo(item.timeMs / 1000);
                      }
                    }}
                    style={[
                      styles.lyricLineRow,
                      isActive && [
                        styles.activeLyricLineRow,
                        { backgroundColor: getAlphaColor(accentColor, '18') },
                      ],
                    ]}
                  >
                    <Text
                      style={[
                        styles.lyricLineBase,
                        hasTimestamps && isCurrentPlayingTrack
                          ? isActive
                            ? [
                                styles.activeLyricText,
                                {
                                  color: textColor,
                                  textShadowColor: getAlphaColor(accentColor, '66'),
                                  textShadowRadius: 10,
                                },
                              ]
                            : [
                                styles.inactiveLyricText,
                                { color: getAlphaColor(textColor, '4D') },
                              ]
                          : [styles.plainLyricText, { color: textColor }],
                      ]}
                    >
                      {item.text || ' '}
                    </Text>
                  </TouchableOpacity>
                );
              })}
            </ScrollView>
          ) : (
            /* ESTADO VACÍO ID3 */
            <View style={styles.emptyContainer}>
              <View
                style={[
                  styles.emptyIconCircle,
                  {
                    borderColor: getAlphaColor(accentColor, '44'),
                    backgroundColor: getAlphaColor(accentColor, '15'),
                  },
                ]}
              >
                <Text style={styles.emptyIcon}>📝</Text>
              </View>

              <Text style={[styles.emptyTitle, { color: textColor }]}>
                Sin letras disponibles para esta canción
              </Text>
              <Text style={[styles.emptySubtitle, { color: subtextColor }]}>
                El archivo de audio no contiene la etiqueta de letra embebida ID3 en su cabecera
              </Text>
            </View>
          )}
        </View>

        {/* 4. SECCIÓN INFERIOR: MINI INFO + WAVEFORM + CONTROLES COMPACTOS */}
        <View
          style={[
            styles.bottomDock,
            {
              backgroundColor: getAlphaColor(cardColor, 'E6'),
              borderColor: getAlphaColor(accentColor, '26'),
            },
          ]}
        >
          {/* MINI INFO DE LA PISTA EN PANTALLA */}
          <View style={styles.miniTrackInfoRow}>
            <View style={styles.miniMeta}>
              <Text numberOfLines={1} style={[styles.miniSongTitle, { color: textColor }]}>
                {targetTrack?.title || currentTrack?.title || 'Sin reproducción'}
              </Text>
              <Text numberOfLines={1} style={[styles.miniSongArtist, { color: subtextColor }]}>
                {targetTrack?.artist || currentTrack?.artist || 'Selecciona una canción'}
              </Text>
            </View>
          </View>

          {/* WAVEFORM COMPARTIDO */}
          <View style={styles.waveformWrapper}>
            <WaveformSeeker
              trackId={currentTrack?.id || targetTrack?.id || 'lyrics_track'}
              position={position}
              duration={duration}
              onSeek={seekTo}
              accentColor={accentColor}
              textColor={textColor}
              subtextColor={subtextColor}
              height={40}
              containerWidth={width - 64}
            />
          </View>

          {/* CONTROLES DE TRANSPORTE COMPACTOS */}
          <View style={styles.controlsRow}>
            <TouchableOpacity
              style={styles.controlBtn}
              onPress={toggleShuffle}
              activeOpacity={0.7}
            >
              <Text
                style={[
                  styles.controlIcon,
                  { color: isShuffle ? accentColor : subtextColor, fontWeight: isShuffle ? 'bold' : 'normal' },
                ]}
              >
                ⇄
              </Text>
            </TouchableOpacity>

            <TouchableOpacity
              style={styles.controlBtn}
              onPress={skipToPrevious}
              activeOpacity={0.7}
            >
              <Text style={[styles.mainControlIcon, { color: textColor }]}>⏮</Text>
            </TouchableOpacity>

            {/* BOTÓN PLAY/PAUSE ELEVADO */}
            <TouchableOpacity
              style={styles.playPauseTouchable}
              onPress={togglePlayPause}
              activeOpacity={0.85}
            >
              <LinearGradient
                colors={
                  gradientColors && gradientColors.length >= 2
                    ? [gradientColors[0], gradientColors[1]]
                    : [accentColor, accentColor]
                }
                style={[styles.playPauseGradient, { shadowColor: accentColor }]}
                start={{ x: 0, y: 0 }}
                end={{ x: 1, y: 1 }}
              >
                <Text style={styles.playPauseIconText}>{isPlaying ? '⏸' : '▶'}</Text>
              </LinearGradient>
            </TouchableOpacity>

            <TouchableOpacity
              style={styles.controlBtn}
              onPress={skipToNext}
              activeOpacity={0.7}
            >
              <Text style={[styles.mainControlIcon, { color: textColor }]}>⏭</Text>
            </TouchableOpacity>

            <TouchableOpacity
              style={styles.controlBtn}
              onPress={toggleLoop}
              activeOpacity={0.7}
            >
              <Text
                style={[
                  styles.controlIcon,
                  { color: isLoop ? accentColor : subtextColor, fontWeight: isLoop ? 'bold' : 'normal' },
                ]}
              >
                ↻
              </Text>
            </TouchableOpacity>
          </View>
        </View>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
  },
  container: {
    flex: 1,
    justifyContent: 'space-between',
  },
  headerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 20,
    paddingTop: 8,
    paddingBottom: 10,
  },
  headerGlassBtn: {
    width: 40,
    height: 40,
    borderRadius: 20,
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 1,
  },
  headerIconText: {
    fontSize: 22,
    fontWeight: 'bold',
    lineHeight: 24,
  },
  headerTitle: {
    fontSize: 17,
    fontWeight: '900',
    letterSpacing: 0.8,
  },
  headerPlaceholderRight: {
    width: 40,
    height: 40,
  },
  lyricsContainer: {
    flex: 1,
    paddingHorizontal: 16,
  },
  lyricsScrollView: {
    flex: 1,
  },
  lyricsContentContainer: {
    paddingVertical: 32,
    paddingHorizontal: 8,
    alignItems: 'center',
  },
  lyricLineRow: {
    paddingVertical: 8,
    paddingHorizontal: 16,
    borderRadius: 12,
    marginVertical: 3,
    width: '100%',
    alignItems: 'center',
  },
  activeLyricLineRow: {
    borderWidth: 1,
    borderColor: 'transparent',
  },
  lyricLineBase: {
    textAlign: 'center',
    lineHeight: 28,
  },
  activeLyricText: {
    fontSize: 18,
    fontWeight: '900',
    letterSpacing: 0.3,
  },
  inactiveLyricText: {
    fontSize: 15,
    fontWeight: '600',
  },
  plainLyricText: {
    fontSize: 15,
    fontWeight: '600',
    lineHeight: 26,
  },
  loadingBox: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    gap: 12,
  },
  loadingText: {
    fontSize: 13,
  },
  emptyContainer: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 24,
  },
  emptyIconCircle: {
    width: 68,
    height: 68,
    borderRadius: 34,
    borderWidth: 2,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 16,
  },
  emptyIcon: {
    fontSize: 30,
  },
  emptyTitle: {
    fontSize: 15,
    fontWeight: 'bold',
    textAlign: 'center',
    marginBottom: 6,
  },
  emptySubtitle: {
    fontSize: 12,
    textAlign: 'center',
    lineHeight: 18,
  },
  bottomDock: {
    paddingHorizontal: 16,
    paddingTop: 12,
    paddingBottom: 10,
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    borderTopWidth: 1,
    borderLeftWidth: 1,
    borderRightWidth: 1,
  },
  miniTrackInfoRow: {
    marginBottom: 8,
    paddingHorizontal: 4,
  },
  miniMeta: {
    alignItems: 'center',
  },
  miniSongTitle: {
    fontSize: 14,
    fontWeight: 'bold',
    letterSpacing: 0.2,
  },
  miniSongArtist: {
    fontSize: 12,
    fontWeight: '500',
    marginTop: 2,
  },
  waveformWrapper: {
    width: '100%',
    marginBottom: 6,
  },
  controlsRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-around',
    paddingVertical: 2,
  },
  controlBtn: {
    padding: 8,
    justifyContent: 'center',
    alignItems: 'center',
  },
  controlIcon: {
    fontSize: 18,
  },
  mainControlIcon: {
    fontSize: 22,
    fontWeight: 'bold',
  },
  playPauseTouchable: {
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.35,
    shadowRadius: 8,
    elevation: 8,
  },
  playPauseGradient: {
    width: 52,
    height: 52,
    borderRadius: 26,
    justifyContent: 'center',
    alignItems: 'center',
  },
  playPauseIconText: {
    fontSize: 22,
    color: '#FFFFFF',
    fontWeight: 'bold',
    marginLeft: 2,
  },
});

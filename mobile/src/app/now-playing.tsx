import React, { useState, useMemo } from 'react';
import {
  StyleSheet,
  View,
  Text,
  TouchableOpacity,
  Image,
  Dimensions,
  StatusBar,
  PanResponder,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { LinearGradient } from 'expo-linear-gradient';
import { router } from 'expo-router';
import Svg, { Rect } from 'react-native-svg';

import { useNeonTheme } from '@/context/ThemeContext';
import { usePlayer } from '@/context/PlayerContext';
import { getAlphaColor } from '@/utils/colorUtils';
import { Track } from '@/components/LibraryModal';

const { width, height } = Dimensions.get('window');
const DEFAULT_FALLBACK_COVER = require('../../assets/images/record_player.jpeg');
const COVER_SIZE = Math.min(width * 0.62, 250);
const WAVEFORM_BAR_COUNT = 44;

/**
 * Generador pseudo-aleatorio determinista para las alturas del waveform por canción.
 * Garantiza alturas 100% estables por pista sin fluctuaciones entre re-renders.
 */
export const generateStableWaveform = (seedStr: string, barCount: number = WAVEFORM_BAR_COUNT): number[] => {
  let hash = 0;
  const str = seedStr || 'custom_music_player_seed';
  for (let i = 0; i < str.length; i++) {
    hash = (hash << 5) - hash + str.charCodeAt(i);
    hash |= 0;
  }

  let seed = Math.abs(hash) || 88219;
  const nextRandom = () => {
    seed = (seed * 1664525 + 1013904223) % 4294967296;
    return seed / 4294967296;
  };

  const bars: number[] = [];
  for (let i = 0; i < barCount; i++) {
    const curve = Math.sin((i / barCount) * Math.PI) * 0.45 + 0.25;
    const variation = nextRandom() * 0.42;
    const barHeight = Math.max(0.18, Math.min(1.0, curve + variation));
    bars.push(barHeight);
  }
  return bars;
};

const formatTime = (totalSeconds: number = 0): string => {
  const safeSec = Math.max(0, Math.floor(totalSeconds));
  const mins = Math.floor(safeSec / 60);
  const secs = safeSec % 60;
  return `${mins}:${secs < 10 ? '0' : ''}${secs}`;
};

export default function NowPlayingScreen() {
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

  const {
    currentTrack,
    isPlaying,
    progress,
    isFavorite,
    isShuffle,
    isLoop,
    togglePlayPause,
    toggleFavorite,
    toggleShuffle,
    toggleLoop,
    skipToNext,
    skipToPrevious,
    seekTo,
  } = usePlayer();

  const [dragRatio, setDragRatio] = useState<number | null>(null);

  // 1. WAVEFORM DETERMINISTA ESTABLE
  const waveformBars = useMemo(
    () => generateStableWaveform(currentTrack?.id || 'empty_track', WAVEFORM_BAR_COUNT),
    [currentTrack?.id]
  );

  // 2. CÁLCULO DE PROGRESO CON POSICIÓN FANTASMA DURANTE EL ARRASTRE (GHOST DRAG)
  const duration = progress.duration || currentTrack?.durationSeconds || 0;
  const position = progress.position || 0;
  const effectivePosition = dragRatio !== null ? dragRatio * duration : position;
  const progressRatio = duration > 0 ? Math.min(1.0, Math.max(0, effectivePosition / duration)) : 0;
  const activeBarIndex = Math.floor(progressRatio * WAVEFORM_BAR_COUNT);

  const getCoverSource = (t?: Track) => {
    if (!t) return DEFAULT_FALLBACK_COVER;
    if (artMode === 'custom' && customCoverUri) {
      return { uri: customCoverUri };
    }
    return t.cover || DEFAULT_FALLBACK_COVER;
  };

  return (
    <SafeAreaView style={[styles.safeArea, { backgroundColor }]} edges={['top', 'left', 'right', 'bottom']}>
      <StatusBar barStyle="light-content" backgroundColor={backgroundColor} />

      {/* FONDO DINÁMICO SEGÚN TEMA PERSONALIZADO */}
      {backgroundMode === 'gradient' && gradientColors && gradientColors.length >= 2 ? (
        <LinearGradient
          colors={[gradientColors[0], gradientColors[1], backgroundColor]}
          style={StyleSheet.absoluteFillObject}
          start={{ x: 0.5, y: 0 }}
          end={{ x: 0.5, y: 0.85 }}
        />
      ) : customBgUri ? (
        <Image source={{ uri: customBgUri }} style={StyleSheet.absoluteFillObject} resizeMode="cover" />
      ) : null}

      <View style={styles.container}>
        {/* 1. HEADER SUPERIOR CON DOWN-CHEVRON Y OPCIONES */}
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

          <Text style={[styles.headerTitle, { color: textColor }]}>Now Playing</Text>

          <TouchableOpacity
            style={[
              styles.headerGlassBtn,
              {
                backgroundColor: getAlphaColor(cardColor, 'B3'),
                borderColor: getAlphaColor(accentColor, '33'),
              },
            ]}
            onPress={() => {
              // Placeholder no funcional para menú contextual
              console.log('Menú de opciones de pista (placeholder)');
            }}
            activeOpacity={0.7}
          >
            <Text style={[styles.headerIconText, { color: textColor }]}>⋯</Text>
          </TouchableOpacity>
        </View>

        {/* 2. CARÁTULA CIRCULAR CENTRADA CON ANILLO DE CRISTAL ESMERILADO */}
        <View style={styles.coverSection}>
          <View
            style={[
              styles.concentricGlassRing,
              {
                width: COVER_SIZE + 28,
                height: COVER_SIZE + 28,
                borderRadius: (COVER_SIZE + 28) / 2,
                borderColor: getAlphaColor(accentColor, '44'),
                backgroundColor: getAlphaColor(cardColor, '55'),
                shadowColor: accentColor,
              },
            ]}
          >
            <Image
              source={getCoverSource(currentTrack)}
              style={[
                styles.circularCover,
                {
                  width: COVER_SIZE,
                  height: COVER_SIZE,
                  borderRadius: COVER_SIZE / 2,
                },
              ]}
              resizeMode="cover"
            />
          </View>
        </View>

        {/* 3. METADATOS Y ACCIONES SECUNDARIAS */}
        <View style={styles.metaSection}>
          <Text numberOfLines={1} style={[styles.songTitle, { color: textColor }]}>
            {currentTrack?.title || 'Sin reproducción'}
          </Text>
          <Text numberOfLines={1} style={[styles.songArtist, { color: subtextColor }]}>
            {currentTrack?.artist || 'Selecciona una canción'}
          </Text>
        </View>

        <View style={styles.secondaryActionsRow}>
          {/* BOTÓN AGREGAR A LISTA (PLACEHOLDER VISUAL SIN FUNCIÓN REAL TODAVÍA) */}
          <TouchableOpacity
            style={styles.addPlaylistBtn}
            onPress={() => {
              // TODO: conectar cuando exista sistema de playlists en móvil
              console.log('Añadir a lista de reproducción (placeholder)');
            }}
            activeOpacity={0.7}
          >
            <Text style={[styles.addPlaylistIcon, { color: subtextColor }]}>⊞</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.favBtn}
            onPress={toggleFavorite}
            activeOpacity={0.7}
          >
            <Text style={[styles.favIcon, { color: isFavorite ? accentColor : subtextColor }]}>
              {isFavorite ? '♥' : '♡'}
            </Text>
          </TouchableOpacity>
        </View>

        {/* 4. BARRA DE PROGRESO WAVEFORM CON SEEK RESPONDER Y GHOST DRAGGING */}
        <View style={styles.waveformSection}>
          <View
            style={styles.waveformTouchableArea}
            onStartShouldSetResponder={() => true}
            onMoveShouldSetResponder={() => true}
            onResponderGrant={(evt) => {
              const touchX = evt.nativeEvent.locationX;
              const ratio = Math.max(0, Math.min(1.0, touchX / (width - 64)));
              setDragRatio(ratio);
            }}
            onResponderMove={(evt) => {
              const touchX = evt.nativeEvent.locationX;
              const ratio = Math.max(0, Math.min(1.0, touchX / (width - 64)));
              setDragRatio(ratio);
            }}
            onResponderRelease={(evt) => {
              const touchX = evt.nativeEvent.locationX;
              const ratio = Math.max(0, Math.min(1.0, touchX / (width - 64)));
              if (duration > 0) {
                seekTo(ratio * duration);
              }
              setDragRatio(null);
            }}
            onResponderTerminate={() => {
              setDragRatio(null);
            }}
          >
            <Svg width={width - 64} height={48}>
              {waveformBars.map((barHeightRatio, index) => {
                const totalWidth = width - 64;
                const barWidth = 3;
                const gap = (totalWidth - barWidth * WAVEFORM_BAR_COUNT) / (WAVEFORM_BAR_COUNT - 1);
                const x = index * (barWidth + gap);
                const maxBarH = 44;
                const barH = Math.max(6, barHeightRatio * maxBarH);
                const y = (48 - barH) / 2;

                // DIFERENCIACIÓN VISUAL: Activas (reproducidas) vs Inactivas (restantes)
                const isPassed = index <= activeBarIndex;
                const barFill = isPassed ? accentColor : getAlphaColor(textColor, '33');

                return (
                  <Rect
                    key={index}
                    x={x}
                    y={y}
                    width={barWidth}
                    height={barH}
                    rx={1.5}
                    ry={1.5}
                    fill={barFill}
                  />
                );
              })}
            </Svg>
          </View>

          {/* ETIQUETAS DE TIEMPO (TRANSCURRIDO Y TOTAL) */}
          <View style={styles.timeLabelsRow}>
            <Text style={[styles.timeText, { color: subtextColor }]}>
              {formatTime(effectivePosition)}
            </Text>
            <Text style={[styles.timeText, { color: subtextColor }]}>
              {formatTime(duration)}
            </Text>
          </View>
        </View>

        {/* 5. CONTROLES DE TRANSPORTE PRINCIPALES */}
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

          {/* BOTÓN PLAY/PAUSE ELEVADO CON DEGRADADO */}
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
              style={[
                styles.playPauseGradient,
                {
                  shadowColor: accentColor,
                },
              ]}
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

        {/* 6. INDICADOR / PESTAÑA INFERIOR "LYRICS" */}
        <TouchableOpacity
          style={[
            styles.lyricsSheetHandle,
            {
              backgroundColor: getAlphaColor(cardColor, 'B3'),
              borderColor: getAlphaColor(accentColor, '33'),
            },
          ]}
          onPress={() => {
            // TODO: cambiar a '/lyrics' cuando exista la Pantalla 3
            console.log('Abrir pantalla de Letras / Lyrics (Pantalla 3)');
          }}
          activeOpacity={0.8}
        >
          <Text style={[styles.lyricsHandleText, { color: textColor }]}>Lyrics</Text>
          <Text style={[styles.lyricsHandleChevron, { color: accentColor }]}>⌃</Text>
        </TouchableOpacity>
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
    paddingHorizontal: 20,
    justifyContent: 'space-between',
    paddingBottom: 10,
  },
  headerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: 10,
  },
  headerTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    letterSpacing: 0.5,
  },
  headerGlassBtn: {
    width: 42,
    height: 42,
    borderRadius: 21,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
  },
  headerIconText: {
    fontSize: 18,
    fontWeight: 'bold',
  },
  coverSection: {
    alignItems: 'center',
    justifyContent: 'center',
    marginVertical: 10,
  },
  concentricGlassRing: {
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 2,
    shadowOffset: { width: 0, height: 6 },
    shadowOpacity: 0.35,
    shadowRadius: 18,
    elevation: 12,
  },
  circularCover: {
    backgroundColor: '#1E1E24',
  },
  metaSection: {
    alignItems: 'center',
    paddingHorizontal: 16,
  },
  songTitle: {
    fontSize: 22,
    fontWeight: 'bold',
    marginBottom: 4,
    textAlign: 'center',
  },
  songArtist: {
    fontSize: 14,
    textAlign: 'center',
  },
  secondaryActionsRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 12,
    marginTop: -4,
  },
  addPlaylistBtn: {
    padding: 6,
  },
  addPlaylistIcon: {
    fontSize: 20,
  },
  favBtn: {
    padding: 6,
  },
  favIcon: {
    fontSize: 22,
    fontWeight: 'bold',
  },
  waveformSection: {
    paddingHorizontal: 12,
  },
  waveformTouchableArea: {
    height: 48,
    justifyContent: 'center',
    alignItems: 'center',
  },
  timeLabelsRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: 6,
  },
  timeText: {
    fontSize: 12,
    fontWeight: '500',
  },
  controlsRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 12,
  },
  controlBtn: {
    width: 44,
    height: 44,
    alignItems: 'center',
    justifyContent: 'center',
  },
  controlIcon: {
    fontSize: 20,
  },
  mainControlIcon: {
    fontSize: 26,
  },
  playPauseTouchable: {
    width: 68,
    height: 68,
    borderRadius: 34,
  },
  playPauseGradient: {
    width: 68,
    height: 68,
    borderRadius: 34,
    alignItems: 'center',
    justifyContent: 'center',
    shadowOffset: { width: 0, height: 6 },
    shadowOpacity: 0.45,
    shadowRadius: 14,
    elevation: 10,
  },
  playPauseIconText: {
    fontSize: 24,
    color: '#FFFFFF',
    fontWeight: 'bold',
  },
  lyricsSheetHandle: {
    height: 38,
    borderRadius: 19,
    borderWidth: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    marginHorizontal: 30,
  },
  lyricsHandleText: {
    fontSize: 13,
    fontWeight: 'bold',
    letterSpacing: 0.3,
  },
  lyricsHandleChevron: {
    fontSize: 14,
    fontWeight: 'bold',
  },
});

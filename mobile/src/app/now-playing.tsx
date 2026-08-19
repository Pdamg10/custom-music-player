import React from 'react';
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
import { LinearGradient } from 'expo-linear-gradient';
import { router } from 'expo-router';

import { useNeonTheme } from '@/context/ThemeContext';
import { usePlayer } from '@/context/PlayerContext';
import { getAlphaColor } from '@/utils/colorUtils';
import { Track } from '@/components/LibraryModal';
import { WaveformSeeker } from '@/components/WaveformSeeker';

const { width } = Dimensions.get('window');
const DEFAULT_FALLBACK_COVER = require('../../assets/images/record_player.jpeg');
const COVER_SIZE = Math.min(width * 0.62, 250);

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

  const duration = progress.duration || currentTrack?.durationSeconds || 0;
  const position = progress.position || 0;

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
              console.log('Menú de opciones de pista');
            }}
            activeOpacity={0.7}
          >
            <Text style={[styles.headerIconText, { color: textColor }]}>⋯</Text>
          </TouchableOpacity>
        </View>

        {/* 2. CARÁTULA PRINCIPAL CON SOMBRA Y BORDES REDONDEADOS */}
        <View style={styles.artworkContainer}>
          <View
            style={[
              styles.artworkShadowWrapper,
              {
                shadowColor: accentColor,
                backgroundColor: cardColor,
              },
            ]}
          >
            <Image
              source={getCoverSource(currentTrack)}
              style={styles.artworkImage}
              resizeMode="cover"
            />
          </View>
        </View>

        {/* 3. INFORMACIÓN DE LA CANCIÓN Y BOTONES SECUNDARIOS */}
        <View style={styles.metaContainer}>
          <Text numberOfLines={1} style={[styles.songTitle, { color: textColor }]}>
            {currentTrack?.title || 'Sin reproducción'}
          </Text>
          <Text numberOfLines={1} style={[styles.songArtist, { color: subtextColor }]}>
            {currentTrack?.artist || 'Selecciona una canción'}
          </Text>
        </View>

        <View style={styles.secondaryActionsRow}>
          <TouchableOpacity
            style={styles.addPlaylistBtn}
            onPress={() => {
              console.log('Añadir a lista de reproducción');
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

        {/* 4. BARRA DE PROGRESO WAVEFORM COMPARTIDA */}
        <View style={styles.waveformSection}>
          <WaveformSeeker
            trackId={currentTrack?.id || 'now_playing_track'}
            position={position}
            duration={duration}
            onSeek={seekTo}
            accentColor={accentColor}
            textColor={textColor}
            subtextColor={subtextColor}
            height={48}
            containerWidth={width - 64}
          />
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

        {/* 6. INDICADOR / PESTAÑA INFERIOR "LYRICS" (CONECTADO) */}
        <TouchableOpacity
          style={[
            styles.lyricsSheetHandle,
            {
              backgroundColor: getAlphaColor(cardColor, 'B3'),
              borderColor: getAlphaColor(accentColor, '33'),
            },
          ]}
          onPress={() => {
            router.push(`/lyrics/${currentTrack?.id || 'current'}` as any);
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
    paddingTop: 8,
  },
  headerGlassBtn: {
    width: 44,
    height: 44,
    borderRadius: 22,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
  },
  headerIconText: {
    fontSize: 22,
    fontWeight: 'bold',
  },
  headerTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    letterSpacing: 0.5,
  },
  artworkContainer: {
    alignItems: 'center',
    justifyContent: 'center',
    marginVertical: 12,
  },
  artworkShadowWrapper: {
    width: COVER_SIZE,
    height: COVER_SIZE,
    borderRadius: 28,
    shadowOffset: { width: 0, height: 12 },
    shadowOpacity: 0.4,
    shadowRadius: 24,
    elevation: 14,
    overflow: 'hidden',
  },
  artworkImage: {
    width: '100%',
    height: '100%',
  },
  metaContainer: {
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

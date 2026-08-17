import React from 'react';
import {
  StyleSheet,
  View,
  Text,
  TouchableOpacity,
  Image,
  ScrollView,
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

const DEFAULT_FALLBACK_COVER = require('../../../assets/images/record_player.jpeg');

export default function HomeScreen() {
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
    playlist,
    currentTrackIndex,
    currentTrack,
    isPlaying,
    isFavorite,
    recentTracks,
    playTrackAtIndex,
    playTrack,
    togglePlayPause,
    toggleFavorite,
  } = usePlayer();

  // Obtener carátula para una pista dada
  const getCoverSource = (t?: Track) => {
    if (!t) return DEFAULT_FALLBACK_COVER;
    if (artMode === 'custom' && customCoverUri) {
      return { uri: customCoverUri };
    }
    return t.cover || DEFAULT_FALLBACK_COVER;
  };

  return (
    <SafeAreaView style={[styles.safeArea, { backgroundColor }]} edges={['top', 'left', 'right']}>
      <StatusBar barStyle="light-content" backgroundColor={backgroundColor} />

      {/* FONDO DINÁMICO SEGÚN TEMA PERSONALIZADO */}
      {backgroundMode === 'gradient' && gradientColors && gradientColors.length >= 2 ? (
        <LinearGradient
          colors={[gradientColors[0], gradientColors[1], backgroundColor]}
          style={StyleSheet.absoluteFillObject}
          start={{ x: 0.5, y: 0 }}
          end={{ x: 0.5, y: 0.7 }}
        />
      ) : customBgUri ? (
        <Image source={{ uri: customBgUri }} style={StyleSheet.absoluteFillObject} resizeMode="cover" />
      ) : null}

      <View style={styles.container}>
        {/* 1. HEADER SUPERIOR CON BOTONES DE CRISTAL */}
        <View style={styles.headerRow}>
          <TouchableOpacity
            style={[
              styles.headerGlassBtn,
              {
                backgroundColor: getAlphaColor(cardColor, 'B3'),
                borderColor: getAlphaColor(accentColor, '33'),
              },
            ]}
            onPress={() => router.push('/(tabs)/library' as any)}
            activeOpacity={0.7}
          >
            <Text style={[styles.headerIconText, { color: textColor }]}>⊞</Text>
          </TouchableOpacity>

          <Text style={[styles.headerTitle, { color: textColor }]}>Inicio</Text>

          <TouchableOpacity
            style={[
              styles.headerGlassBtn,
              {
                backgroundColor: getAlphaColor(cardColor, 'B3'),
                borderColor: getAlphaColor(accentColor, '33'),
              },
            ]}
            onPress={() => router.push('/(tabs)/search' as any)}
            activeOpacity={0.7}
          >
            <Text style={[styles.headerIconText, { color: textColor }]}>🔍</Text>
          </TouchableOpacity>
        </View>

        <ScrollView
          contentContainerStyle={styles.scrollContent}
          showsVerticalScrollIndicator={false}
        >
          {/* 2. SECCIÓN RECENTLY PLAYED */}
          <View style={styles.sectionHeaderRow}>
            <Text style={[styles.sectionTitle, { color: textColor }]}>Recently Played</Text>
            <TouchableOpacity onPress={() => router.push('/(tabs)/library' as any)} activeOpacity={0.7}>
              <Text style={[styles.sectionArrow, { color: accentColor }]}>›</Text>
            </TouchableOpacity>
          </View>

          {recentTracks.length > 0 ? (
            <ScrollView
              horizontal
              showsHorizontalScrollIndicator={false}
              contentContainerStyle={styles.recentListContainer}
            >
              {recentTracks.map((item, idx) => (
                <TouchableOpacity
                  key={`${item.id}_${idx}`}
                  style={[
                    styles.recentCard,
                    {
                      backgroundColor: getAlphaColor(cardColor, 'CC'),
                      borderColor: getAlphaColor(accentColor, '22'),
                    },
                  ]}
                  onPress={() => playTrack(item)}
                  activeOpacity={0.8}
                >
                  <Image source={getCoverSource(item)} style={styles.recentCover} />
                  <Text numberOfLines={1} style={[styles.recentTrackTitle, { color: textColor }]}>
                    {item.title}
                  </Text>
                  <Text numberOfLines={1} style={[styles.recentTrackArtist, { color: subtextColor }]}>
                    {item.artist}
                  </Text>
                </TouchableOpacity>
              ))}
            </ScrollView>
          ) : (
            <View
              style={[
                styles.emptyRecentCard,
                {
                  backgroundColor: getAlphaColor(cardColor, '80'),
                  borderColor: getAlphaColor(accentColor, '22'),
                },
              ]}
            >
              <Text style={styles.emptyRecentIcon}>🎵</Text>
              <Text style={[styles.emptyRecentTitle, { color: textColor }]}>
                Sin reproducciones recientes
              </Text>
              <Text style={[styles.emptyRecentSub, { color: subtextColor }]}>
                Las canciones que escuches aparecerán aquí
              </Text>
            </View>
          )}

          {/* 3. SECCIÓN YOU MIGHT LIKE / TU MÚSICA */}
          <View style={[styles.sectionHeaderRow, { marginTop: 22 }]}>
            <Text style={[styles.sectionTitle, { color: textColor }]}>You Might Like</Text>
            <TouchableOpacity onPress={() => router.push('/(tabs)/library' as any)} activeOpacity={0.7}>
              <Text style={[styles.sectionArrow, { color: accentColor }]}>›</Text>
            </TouchableOpacity>
          </View>

          <View style={styles.songsListContainer}>
            {playlist.slice(0, 15).map((item, idx) => {
              const isCurrent = currentTrackIndex === idx;
              return (
                <TouchableOpacity
                  key={item.id || idx}
                  style={[
                    styles.songRow,
                    {
                      backgroundColor: isCurrent
                        ? getAlphaColor(accentColor, '1A')
                        : getAlphaColor(cardColor, '66'),
                      borderColor: isCurrent
                        ? getAlphaColor(accentColor, '55')
                        : getAlphaColor(accentColor, '15'),
                    },
                  ]}
                  onPress={() => playTrackAtIndex(idx)}
                  activeOpacity={0.7}
                >
                  <Image source={getCoverSource(item)} style={styles.songThumb} />
                  <View style={styles.songMeta}>
                    <Text
                      numberOfLines={1}
                      style={[
                        styles.songTitle,
                        { color: isCurrent ? accentColor : textColor, fontWeight: isCurrent ? 'bold' : '600' },
                      ]}
                    >
                      {item.title}
                    </Text>
                    <Text numberOfLines={1} style={[styles.songArtist, { color: subtextColor }]}>
                      {item.artist} {item.album ? `• ${item.album}` : ''}
                    </Text>
                  </View>

                  <TouchableOpacity
                    style={[
                      styles.songPlayBtn,
                      {
                        backgroundColor: isCurrent ? accentColor : getAlphaColor(accentColor, '26'),
                      },
                    ]}
                    onPress={() => playTrackAtIndex(idx)}
                  >
                    <Text
                      style={[
                        styles.songPlayIcon,
                        { color: isCurrent ? '#FFFFFF' : accentColor },
                      ]}
                    >
                      {isCurrent && isPlaying ? '⏸' : '▶'}
                    </Text>
                  </TouchableOpacity>
                </TouchableOpacity>
              );
            })}
          </View>
        </ScrollView>

        {/* 4. MINI-REPRODUCTOR FIJO INFERIOR */}
        {currentTrack && (
          <View
            style={[
              styles.miniPlayerContainer,
              {
                backgroundColor: getAlphaColor(cardColor, 'F2'),
                borderColor: getAlphaColor(accentColor, '44'),
              },
            ]}
          >
            <TouchableOpacity
              style={styles.miniPlayerContent}
              activeOpacity={0.85}
              onPress={() => router.push('/now-playing' as any)}
            >
              <Image source={getCoverSource(currentTrack)} style={styles.miniPlayerCover} />
              <View style={styles.miniPlayerMeta}>
                <Text numberOfLines={1} style={[styles.miniPlayerTitle, { color: textColor }]}>
                  {currentTrack.title}
                </Text>
                <Text numberOfLines={1} style={[styles.miniPlayerArtist, { color: subtextColor }]}>
                  {currentTrack.artist}
                </Text>
              </View>
            </TouchableOpacity>

            <View style={styles.miniPlayerActions}>
              <TouchableOpacity onPress={toggleFavorite} style={styles.miniPlayerFavBtn}>
                <Text style={[styles.miniPlayerFavIcon, { color: isFavorite ? accentColor : subtextColor }]}>
                  {isFavorite ? '♥' : '♡'}
                </Text>
              </TouchableOpacity>

              <TouchableOpacity
                onPress={togglePlayPause}
                style={[
                  styles.miniPlayerPlayBtn,
                  {
                    backgroundColor: getAlphaColor(accentColor, '26'),
                    borderColor: getAlphaColor(accentColor, '55'),
                  },
                ]}
              >
                <Text style={[styles.miniPlayerPlayIcon, { color: accentColor }]}>
                  {isPlaying ? '⏸' : '▶'}
                </Text>
              </TouchableOpacity>
            </View>
          </View>
        )}
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
  },
  headerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 20,
    paddingVertical: 12,
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    letterSpacing: 0.5,
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
    fontSize: 18,
  },
  scrollContent: {
    paddingBottom: 110,
  },
  sectionHeaderRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 20,
    marginTop: 14,
    marginBottom: 12,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    letterSpacing: 0.3,
  },
  sectionArrow: {
    fontSize: 24,
    fontWeight: 'bold',
    paddingHorizontal: 6,
  },
  recentListContainer: {
    paddingHorizontal: 16,
    gap: 14,
  },
  recentCard: {
    width: 124,
    borderRadius: 16,
    padding: 10,
    borderWidth: 1,
  },
  recentCover: {
    width: 104,
    height: 104,
    borderRadius: 12,
    marginBottom: 8,
  },
  recentTrackTitle: {
    fontSize: 13,
    fontWeight: 'bold',
    marginBottom: 2,
  },
  recentTrackArtist: {
    fontSize: 11,
  },
  emptyRecentCard: {
    marginHorizontal: 20,
    borderRadius: 16,
    padding: 24,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
  },
  emptyRecentIcon: {
    fontSize: 28,
    marginBottom: 8,
  },
  emptyRecentTitle: {
    fontSize: 14,
    fontWeight: 'bold',
    marginBottom: 4,
  },
  emptyRecentSub: {
    fontSize: 12,
    textAlign: 'center',
  },
  songsListContainer: {
    paddingHorizontal: 20,
    gap: 10,
  },
  songRow: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 10,
    borderRadius: 14,
    borderWidth: 1,
  },
  songThumb: {
    width: 46,
    height: 46,
    borderRadius: 23,
    marginRight: 12,
  },
  songMeta: {
    flex: 1,
  },
  songTitle: {
    fontSize: 14,
    marginBottom: 3,
  },
  songArtist: {
    fontSize: 12,
  },
  songPlayBtn: {
    width: 36,
    height: 36,
    borderRadius: 18,
    alignItems: 'center',
    justifyContent: 'center',
    marginLeft: 8,
  },
  songPlayIcon: {
    fontSize: 13,
    fontWeight: 'bold',
  },
  miniPlayerContainer: {
    position: 'absolute',
    bottom: 8,
    left: 16,
    right: 16,
    height: 64,
    borderRadius: 32,
    borderWidth: 1,
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 12,
    shadowColor: '#000000',
    shadowOpacity: 0.4,
    shadowOffset: { width: 0, height: 4 },
    shadowRadius: 8,
    elevation: 8,
  },
  miniPlayerContent: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
  },
  miniPlayerCover: {
    width: 44,
    height: 44,
    borderRadius: 22,
    marginRight: 12,
  },
  miniPlayerMeta: {
    flex: 1,
  },
  miniPlayerTitle: {
    fontSize: 13,
    fontWeight: 'bold',
    marginBottom: 2,
  },
  miniPlayerArtist: {
    fontSize: 11,
  },
  miniPlayerActions: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  miniPlayerFavBtn: {
    padding: 6,
  },
  miniPlayerFavIcon: {
    fontSize: 18,
    fontWeight: 'bold',
  },
  miniPlayerPlayBtn: {
    width: 38,
    height: 38,
    borderRadius: 19,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
  },
  miniPlayerPlayIcon: {
    fontSize: 14,
    fontWeight: 'bold',
  },
});

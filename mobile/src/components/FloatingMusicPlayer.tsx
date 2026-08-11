import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Image,
} from 'react-native';
import { EKGVisualizer } from './EKGVisualizer';
import { useNeonTheme } from '../context/ThemeContext';

interface FloatingMusicPlayerProps {
  initialTitle?: string;
  initialArtist?: string;
}

export const FloatingMusicPlayer: React.FC<FloatingMusicPlayerProps> = () => {
  const {
    backgroundColor,
    cardColor,
    textColor,
    subtextColor,
    accentColor,
    artMode,
    customCoverUri,
  } = useNeonTheme();

  const [isPlaying, setIsPlaying] = useState(true);
  const [isCompact, setIsCompact] = useState(false);
  const [isFavorite, setIsFavorite] = useState(true);
  const [currentTrackIndex, setCurrentTrackIndex] = useState(0);

  const playlist = [
    { title: 'Break My Heart', artist: 'Cain', cover: require('../../assets/images/record_player.jpeg') },
    { title: 'Blinding Lights', artist: 'The Weeknd', cover: { uri: 'https://picsum.photos/300/300?random=2' } },
    { title: 'Cyberpunk Neon Nights', artist: 'SynthWave Core', cover: { uri: 'https://picsum.photos/300/300?random=3' } },
  ];

  const track = playlist[currentTrackIndex];

  const togglePlayPause = () => setIsPlaying(!isPlaying);
  const toggleCompact = () => setIsCompact(!isCompact);
  const toggleFavorite = () => setIsFavorite(!isFavorite);

  const handleNext = () => {
    setCurrentTrackIndex((prev) => (prev + 1) % playlist.length);
    setIsPlaying(true);
  };

  const handlePrev = () => {
    setCurrentTrackIndex((prev) => (prev - 1 + playlist.length) % playlist.length);
    setIsPlaying(true);
  };

  const displayArt =
    artMode === 'custom' && customCoverUri
      ? { uri: customCoverUri }
      : typeof track.cover === 'number'
      ? track.cover
      : track.cover;

  if (isCompact) {
    return (
      <View style={[styles.compactContainer, { backgroundColor: '#0A0A0A', borderColor: accentColor }]}>
        <Image source={displayArt} style={styles.compactCover} />
        <View style={styles.compactTextContainer}>
          <Text numberOfLines={1} style={[styles.compactTitle, { color: textColor }]}>
            {track.title}
          </Text>
          <Text numberOfLines={1} style={[styles.compactArtist, { color: accentColor }]}>
            {track.artist}
          </Text>
        </View>
        <TouchableOpacity style={styles.compactBtn} onPress={togglePlayPause}>
          <Text style={[styles.btnIcon, { color: textColor }]}>{isPlaying ? '⏸' : '▶'}</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.compactBtn} onPress={toggleCompact}>
          <Text style={[styles.btnIcon, { color: textColor }]}>⤢</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <View
      style={[
        styles.floatingCard,
        {
          backgroundColor: '#0A0A0A',
          borderColor: accentColor,
          shadowColor: accentColor,
        },
      ]}
    >
      {/* Header */}
      <View style={styles.cardHeader}>
        <TouchableOpacity onPress={toggleFavorite}>
          <Text style={styles.favIcon}>{isFavorite ? '❤️' : '🤍'}</Text>
        </TouchableOpacity>
        <Text style={[styles.headerBadge, { color: subtextColor }]}>CUSTOM NEON PLAYER</Text>
        <TouchableOpacity onPress={toggleCompact}>
          <Text style={[styles.headerBtn, { color: textColor }]}>🗗</Text>
        </TouchableOpacity>
      </View>

      {/* Album Cover & EKG Overlay */}
      <View style={[styles.coverWrapper, { borderColor: accentColor + '44' }]}>
        <Image source={displayArt} style={styles.albumCover} />
        <View style={styles.visualizerOverlay}>
          <EKGVisualizer isPlaying={isPlaying} color={accentColor} />
        </View>
      </View>

      {/* Track Info */}
      <View style={styles.infoContainer}>
        <Text style={[styles.trackTitle, { color: textColor }]} numberOfLines={1}>
          {track.title}
        </Text>
        <Text style={[styles.trackArtist, { color: accentColor }]} numberOfLines={1}>
          {track.artist}
        </Text>
      </View>

      {/* Controls */}
      <View style={styles.controlsRow}>
        <TouchableOpacity style={[styles.controlBtnSmall, { borderColor: accentColor + '44' }]} onPress={handlePrev}>
          <Text style={[styles.controlText, { color: accentColor }]}>⏮</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[
            styles.controlBtnLarge,
            { backgroundColor: accentColor, shadowColor: accentColor },
          ]}
          onPress={togglePlayPause}
        >
          <Text style={styles.controlTextPlay}>{isPlaying ? '⏸' : '▶'}</Text>
        </TouchableOpacity>

        <TouchableOpacity style={[styles.controlBtnSmall, { borderColor: accentColor + '44' }]} onPress={handleNext}>
          <Text style={[styles.controlText, { color: accentColor }]}>⏭</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  floatingCard: {
    width: 290,
    borderRadius: 20,
    borderWidth: 1.5,
    padding: 16,
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.4,
    shadowRadius: 15,
    elevation: 12,
    alignItems: 'center',
  },
  cardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    width: '100%',
    alignItems: 'center',
    marginBottom: 12,
  },
  favIcon: {
    fontSize: 18,
  },
  headerBadge: {
    fontSize: 10,
    fontWeight: 'bold',
    letterSpacing: 1,
  },
  headerBtn: {
    fontSize: 16,
  },
  coverWrapper: {
    width: 240,
    height: 180,
    borderRadius: 14,
    overflow: 'hidden',
    backgroundColor: '#000000',
    position: 'relative',
    borderWidth: 1,
  },
  albumCover: {
    width: '100%',
    height: '100%',
    borderRadius: 14,
    resizeMode: 'cover',
  },
  visualizerOverlay: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    paddingVertical: 4,
  },
  infoContainer: {
    alignItems: 'center',
    marginVertical: 14,
    width: '100%',
  },
  trackTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    textAlign: 'center',
  },
  trackArtist: {
    fontSize: 14,
    marginTop: 4,
    fontWeight: '600',
    textAlign: 'center',
  },
  controlsRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 20,
    marginTop: 4,
  },
  controlBtnSmall: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: '#121218',
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 1,
  },
  controlBtnLarge: {
    width: 58,
    height: 58,
    borderRadius: 29,
    justifyContent: 'center',
    alignItems: 'center',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.5,
    shadowRadius: 8,
    elevation: 6,
  },
  controlText: {
    fontSize: 18,
  },
  controlTextPlay: {
    color: '#000000',
    fontSize: 22,
    fontWeight: 'bold',
  },
  compactContainer: {
    width: 290,
    height: 64,
    borderRadius: 32,
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 10,
    borderWidth: 1.5,
  },
  compactCover: {
    width: 44,
    height: 44,
    borderRadius: 22,
  },
  compactTextContainer: {
    flex: 1,
    marginLeft: 10,
  },
  compactTitle: {
    fontSize: 13,
    fontWeight: 'bold',
  },
  compactArtist: {
    fontSize: 11,
  },
  compactBtn: {
    padding: 8,
  },
  btnIcon: {
    fontSize: 16,
  },
});

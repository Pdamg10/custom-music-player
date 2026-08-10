import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Image,
  Dimensions,
} from 'react-native';
import { EKGVisualizer } from './EKGVisualizer';

interface FloatingMusicPlayerProps {
  initialTitle?: string;
  initialArtist?: string;
}

export const FloatingMusicPlayer: React.FC<FloatingMusicPlayerProps> = ({
  initialTitle = 'Break My Heart',
  initialArtist = 'Cain',
}) => {
  const [isPlaying, setIsPlaying] = useState(true);
  const [isCompact, setIsCompact] = useState(false);
  const [isFavorite, setIsFavorite] = useState(true);
  const [currentTrackIndex, setCurrentTrackIndex] = useState(0);

  const playlist = [
    { title: 'Break My Heart', artist: 'Cain', cover: 'https://picsum.photos/300/300?random=1' },
    { title: 'Blinding Lights', artist: 'The Weeknd', cover: 'https://picsum.photos/300/300?random=2' },
    { title: 'Cyberpunk Neon Nights', artist: 'SynthWave Core', cover: 'https://picsum.photos/300/300?random=3' },
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

  if (isCompact) {
    return (
      <View style={styles.compactContainer}>
        <Image source={{ uri: track.cover }} style={styles.compactCover} />
        <View style={styles.compactTextContainer}>
          <Text numberOfLines={1} style={styles.compactTitle}>
            {track.title}
          </Text>
          <Text numberOfLines={1} style={styles.compactArtist}>
            {track.artist}
          </Text>
        </View>
        <TouchableOpacity style={styles.compactBtn} onPress={togglePlayPause}>
          <Text style={styles.btnIcon}>{isPlaying ? '⏸' : '▶'}</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.compactBtn} onPress={toggleCompact}>
          <Text style={styles.btnIcon}>⤢</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <View style={styles.floatingCard}>
      {/* Header */}
      <View style={styles.cardHeader}>
        <TouchableOpacity onPress={toggleFavorite}>
          <Text style={styles.favIcon}>{isFavorite ? '❤️' : '🤍'}</Text>
        </TouchableOpacity>
        <Text style={styles.headerBadge}>EXPO NEON PLAYER</Text>
        <TouchableOpacity onPress={toggleCompact}>
          <Text style={styles.headerBtn}>🗗</Text>
        </TouchableOpacity>
      </View>

      {/* Album Cover & EKG Overlay */}
      <View style={styles.coverWrapper}>
        <Image source={{ uri: track.cover }} style={styles.albumCover} />
        <View style={styles.visualizerOverlay}>
          <EKGVisualizer isPlaying={isPlaying} color="#FF1744" />
        </View>
      </View>

      {/* Track Info */}
      <View style={styles.infoContainer}>
        <Text style={styles.trackTitle} numberOfLines={1}>
          {track.title}
        </Text>
        <Text style={styles.trackArtist} numberOfLines={1}>
          {track.artist}
        </Text>
      </View>

      {/* Controls */}
      <View style={styles.controlsRow}>
        <TouchableOpacity style={styles.controlBtnSmall} onPress={handlePrev}>
          <Text style={styles.controlText}>⏮</Text>
        </TouchableOpacity>

        <TouchableOpacity style={styles.controlBtnLarge} onPress={togglePlayPause}>
          <Text style={styles.controlTextPlay}>{isPlaying ? '⏸' : '▶'}</Text>
        </TouchableOpacity>

        <TouchableOpacity style={styles.controlBtnSmall} onPress={handleNext}>
          <Text style={styles.controlText}>⏭</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  floatingCard: {
    width: 290,
    backgroundColor: '#050508',
    borderRadius: 20,
    borderWidth: 1.5,
    borderColor: '#FF174444',
    padding: 16,
    shadowColor: '#FF1744',
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.3,
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
    color: '#888899',
    fontSize: 10,
    fontWeight: 'bold',
    letterSpacing: 1,
  },
  headerBtn: {
    color: '#FFFFFF',
    fontSize: 16,
  },
  coverWrapper: {
    width: 240,
    height: 180,
    borderRadius: 14,
    overflow: 'hidden',
    backgroundColor: '#121218',
    position: 'relative',
  },
  albumCover: {
    width: '100%',
    height: '100%',
    borderRadius: 14,
    opacity: 0.85,
  },
  visualizerOverlay: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    backgroundColor: 'rgba(5, 5, 8, 0.45)',
    paddingVertical: 4,
  },
  infoContainer: {
    alignItems: 'center',
    marginVertical: 14,
    width: '100%',
  },
  trackTitle: {
    color: '#FFFFFF',
    fontSize: 18,
    fontWeight: 'bold',
    textAlign: 'center',
  },
  trackArtist: {
    color: '#FF1744',
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
    borderColor: '#FF174433',
  },
  controlBtnLarge: {
    width: 58,
    height: 58,
    borderRadius: 29,
    backgroundColor: '#FF1744',
    justifyContent: 'center',
    alignItems: 'center',
    shadowColor: '#FF1744',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.5,
    shadowRadius: 8,
    elevation: 6,
  },
  controlText: {
    color: '#FF1744',
    fontSize: 18,
  },
  controlTextPlay: {
    color: '#FFFFFF',
    fontSize: 22,
  },
  compactContainer: {
    width: 290,
    height: 64,
    backgroundColor: '#050508',
    borderRadius: 32,
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 10,
    borderWidth: 1.5,
    borderColor: '#FF1744',
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
    color: '#FFFFFF',
    fontSize: 13,
    fontWeight: 'bold',
  },
  compactArtist: {
    color: '#FF1744',
    fontSize: 11,
  },
  compactBtn: {
    padding: 8,
  },
  btnIcon: {
    color: '#FFFFFF',
    fontSize: 16,
  },
});

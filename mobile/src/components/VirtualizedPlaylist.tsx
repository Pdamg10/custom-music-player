import React, { memo } from 'react';
import { StyleSheet, View, Text, TouchableOpacity, Image } from 'react-native';
import { useNeonTheme } from '@/context/ThemeContext';
import { getAlphaColor } from '@/utils/colorUtils';
import { NeonScannerLoader } from './NeonScannerLoader';
import { EmptyScanStateCard } from './EmptyScanStateCard';

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

interface VirtualizedPlaylistProps {
  playlist: Track[];
  currentTrackIndex: number;
  isPlaying: boolean;
  isLoadingStorage: boolean;
  scanProgressCount?: number;
  onSelectTrack: (index: number) => void;
  onPickFolder: () => void;
  onRescan: () => void;
  onOpenLibrary: () => void;
}

const TrackRowItem = memo(({
  item,
  isSelected,
  isPlaying,
  accentColor,
  textColor,
  subtextColor,
  onPress,
}: {
  item: Track;
  isSelected: boolean;
  isPlaying: boolean;
  accentColor: string;
  textColor: string;
  subtextColor: string;
  onPress: () => void;
}) => {
  const [imgError, setImgError] = React.useState(false);

  const coverSource =
    !imgError && (typeof item.cover === 'number' || (item.cover && item.cover.uri))
      ? item.cover
      : DEFAULT_FALLBACK_COVER;

  return (
    <TouchableOpacity
      style={[
        styles.playlistTrackRow,
        isSelected && {
          backgroundColor: getAlphaColor(accentColor, '22'),
          borderWidth: 1,
          borderColor: accentColor,
        },
      ]}
      onPress={onPress}
    >
      <Image
        source={coverSource}
        style={styles.trackRowThumb}
        onError={() => setImgError(true)}
      />
      <View style={styles.trackRowMetaInfo}>
        <Text
          style={[
            styles.trackRowTitleText,
            { color: textColor },
            isSelected && { fontWeight: 'bold', color: accentColor },
          ]}
          numberOfLines={1}
        >
          {item.title}
        </Text>
        <Text style={[styles.trackRowArtistText, { color: subtextColor }]} numberOfLines={1}>
          {item.artist}
        </Text>
      </View>
      {isSelected && isPlaying && (
        <Text style={[styles.playingStatusBadge, { color: accentColor }]}>▶ EN ENTRADA</Text>
      )}
    </TouchableOpacity>
  );
});

export const VirtualizedPlaylist: React.FC<VirtualizedPlaylistProps> = ({
  playlist,
  currentTrackIndex,
  isPlaying,
  isLoadingStorage,
  scanProgressCount = 0,
  onSelectTrack,
  onPickFolder,
  onRescan,
  onOpenLibrary,
}) => {
  const { accentColor, textColor, subtextColor, cardColor, surfaceColor } = useNeonTheme();

  if (isLoadingStorage && playlist.length === 0) {
    return <NeonScannerLoader count={scanProgressCount} message="ANALIZANDO ALMACENAMIENTO DE MÚSICA..." />;
  }

  if (playlist.length === 0) {
    return <EmptyScanStateCard onPickFolder={onPickFolder} onRescan={onRescan} />;
  }

  const previewList = playlist.slice(0, 5);

  return (
    <View style={[styles.playlistCard, { backgroundColor: cardColor, borderColor: surfaceColor }]}>
      <View style={styles.cardHeaderRow}>
        <Text style={[styles.playlistCardTitle, { color: textColor }]}>
          🎵 BIBLIOTECA ({playlist.length.toLocaleString()} CANCIONES)
        </Text>

        <TouchableOpacity style={styles.quickOpenBtn} onPress={onOpenLibrary}>
          <Text style={[styles.quickOpenText, { color: accentColor }]}>Ver Todo ➔</Text>
        </TouchableOpacity>
      </View>

      {previewList.map((item, index) => {
        const realIndex = playlist.findIndex((t) => t.id === item.id);
        const isSelected = realIndex === currentTrackIndex;
        return (
          <TrackRowItem
            key={`${item.id}_${index}`}
            item={item}
            isSelected={isSelected}
            isPlaying={isPlaying}
            accentColor={accentColor}
            textColor={textColor}
            subtextColor={subtextColor}
            onPress={() => onSelectTrack(realIndex >= 0 ? realIndex : index)}
          />
        );
      })}

      <TouchableOpacity
        style={[styles.fullLibraryCTA, { backgroundColor: accentColor }]}
        onPress={onOpenLibrary}
      >
        <Text style={styles.fullLibraryCTAText}>
          📚 ABRIR BIBLIOTECA Y ORDENAR ({playlist.length.toLocaleString()})
        </Text>
      </TouchableOpacity>
    </View>
  );
};

const styles = StyleSheet.create({
  playlistCard: {
    width: '100%',
    maxWidth: 360,
    borderRadius: 20,
    padding: 14,
    borderWidth: 1,
    marginVertical: 8,
  },
  cardHeaderRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 10,
  },
  playlistCardTitle: {
    fontSize: 12,
    fontWeight: 'bold',
    letterSpacing: 0.8,
  },
  quickOpenBtn: {
    padding: 4,
  },
  quickOpenText: {
    fontSize: 11,
    fontWeight: 'bold',
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
  fullLibraryCTA: {
    width: '100%',
    paddingVertical: 12,
    borderRadius: 14,
    alignItems: 'center',
    marginTop: 8,
  },
  fullLibraryCTAText: {
    color: '#000000',
    fontSize: 12,
    fontWeight: '900',
    letterSpacing: 0.8,
  },
});

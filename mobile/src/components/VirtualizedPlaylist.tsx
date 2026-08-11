import React, { memo } from 'react';
import { StyleSheet, View, Text, TouchableOpacity, Image, FlatList } from 'react-native';
import { useNeonTheme } from '@/context/ThemeContext';
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
}

const TrackRowItem = memo(({
  item,
  index,
  isSelected,
  isPlaying,
  accentColor,
  textColor,
  subtextColor,
  onPress,
}: {
  item: Track;
  index: number;
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
          backgroundColor: accentColor + '22',
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
        <Text style={[styles.playingStatusBadge, { color: accentColor }]}>▶ REPRODUCIENDO</Text>
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
}) => {
  const { accentColor, textColor, subtextColor, cardColor, surfaceColor } = useNeonTheme();

  if (isLoadingStorage && playlist.length === 0) {
    return <NeonScannerLoader count={scanProgressCount} message="ANALIZANDO ALMACENAMIENTO DE MÚSICA..." />;
  }

  if (playlist.length === 0) {
    return <EmptyScanStateCard onPickFolder={onPickFolder} onRescan={onRescan} />;
  }

  return (
    <View style={[styles.playlistCard, { backgroundColor: cardColor, borderColor: surfaceColor }]}>
      <Text style={[styles.playlistCardTitle, { color: textColor }]}>
        🎵 CANCIONES DETECTADAS ({playlist.length.toLocaleString()})
      </Text>

      <FlatList
        data={playlist}
        keyExtractor={(item, index) => `${item.id}_${index}`}
        renderItem={({ item, index }) => (
          <TrackRowItem
            item={item}
            index={index}
            isSelected={index === currentTrackIndex}
            isPlaying={isPlaying}
            accentColor={accentColor}
            textColor={textColor}
            subtextColor={subtextColor}
            onPress={() => onSelectTrack(index)}
          />
        )}
        initialNumToRender={12}
        maxToRenderPerBatch={15}
        windowSize={5}
        removeClippedSubviews={true}
        scrollEnabled={false} // Desplazamiento manejado por el ScrollView padre o FlatList
      />
    </View>
  );
};

const styles = StyleSheet.create({
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

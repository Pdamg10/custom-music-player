import React, { useState, useMemo } from 'react';
import {
  Modal,
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  TextInput,
  FlatList,
  Image,
  ScrollView,
} from 'react-native';
import { useNeonTheme } from '../context/ThemeContext';
import { getAlphaColor } from '../utils/colorUtils';
import { Track } from './LibraryModal';

const DEFAULT_FALLBACK_COVER = require('../../assets/images/record_player.jpeg');

export type SearchFilterType = 'all' | 'title' | 'artist' | 'album' | 'folder';

interface SearchViewModalProps {
  visible: boolean;
  playlist: Track[];
  currentTrackIndex: number;
  onClose: () => void;
  onSelectTrack: (track: Track) => void;
}

export const SearchViewModal: React.FC<SearchViewModalProps> = ({
  visible,
  playlist,
  currentTrackIndex,
  onClose,
  onSelectTrack,
}) => {
  const { accentColor, textColor, subtextColor, cardColor, surfaceColor } = useNeonTheme();

  const [query, setQuery] = useState('');
  const [filterType, setFilterType] = useState<SearchFilterType>('all');

  const filteredResults = useMemo(() => {
    if (!query.trim()) return [];

    const q = query.toLowerCase().trim();
    return playlist.filter((t) => {
      if (filterType === 'title') return t.title.toLowerCase().includes(q);
      if (filterType === 'artist') return t.artist.toLowerCase().includes(q);
      if (filterType === 'album') return t.album.toLowerCase().includes(q);
      if (filterType === 'folder')
        return (
          t.id.startsWith('saf_') ||
          t.id.startsWith('folder_') ||
          t.artist === 'Carpeta Seleccionada'
        );

      return (
        t.title.toLowerCase().includes(q) ||
        t.artist.toLowerCase().includes(q) ||
        t.album.toLowerCase().includes(q)
      );
    });
  }, [playlist, query, filterType]);

  const currentTrack = playlist[currentTrackIndex];

  return (
    <Modal visible={visible} animationType="slide" transparent={false} onRequestClose={onClose}>
      <View style={[styles.container, { backgroundColor: '#070709' }]}>
        
        {/* HEADER DE BÚSQUEDA */}
        <View style={[styles.header, { borderColor: getAlphaColor(accentColor, '33') }]}>
          <View style={styles.headerTopRow}>
            <View style={styles.titleBadgeRow}>
              <Text style={styles.headerIcon}>🔍</Text>
              <Text style={[styles.headerTitle, { color: textColor }]}>BÚSQUEDA EN TIEMPO REAL</Text>
            </View>

            <TouchableOpacity onPress={onClose} style={styles.closeBtn}>
              <Text style={[styles.closeBtnText, { color: textColor }]}>✕</Text>
            </TouchableOpacity>
          </View>

          {/* CAMPO DE ENTRADA DE BÚSQUEDA */}
          <View style={[styles.searchInputBox, { backgroundColor: surfaceColor, borderColor: getAlphaColor(accentColor, '44') }]}>
            <Text style={styles.searchIcon}>🔍</Text>
            <TextInput
              style={[styles.inputField, { color: textColor }]}
              placeholder="Escribe título, artista, álbum o carpeta..."
              placeholderTextColor={subtextColor}
              value={query}
              onChangeText={setQuery}
              autoFocus={true}
              clearButtonMode="while-editing"
            />
            {query.length > 0 && (
              <TouchableOpacity onPress={() => setQuery('')} style={styles.clearBtn}>
                <Text style={{ color: subtextColor, fontWeight: 'bold' }}>✕</Text>
              </TouchableOpacity>
            )}
          </View>

          {/* FILTROS POR TIPO DE BÚSQUEDA */}
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.filtersRow}>
            {[
              { id: 'all', label: '🌐 Todo' },
              { id: 'title', label: '🔤 Título' },
              { id: 'artist', label: '👤 Artista' },
              { id: 'album', label: '💿 Álbum' },
              { id: 'folder', label: '📁 Carpeta' },
            ].map((f) => {
              const isActive = filterType === f.id;
              return (
                <TouchableOpacity
                  key={f.id}
                  style={[
                    styles.filterPill,
                    isActive && { backgroundColor: accentColor, borderColor: accentColor },
                  ]}
                  onPress={() => setFilterType(f.id as SearchFilterType)}
                >
                  <Text style={[styles.filterPillText, { color: isActive ? '#000' : textColor }]}>
                    {f.label}
                  </Text>
                </TouchableOpacity>
              );
            })}
          </ScrollView>
        </View>

        {/* RESULTADOS DE BÚSQUEDA FLUIDOS */}
        <FlatList
          data={filteredResults}
          keyExtractor={(item) => item.id}
          contentContainerStyle={styles.listContent}
          renderItem={({ item }) => {
            const isPlayingThis = currentTrack && currentTrack.id === item.id;
            return (
              <TouchableOpacity
                style={[
                  styles.trackRow,
                  { backgroundColor: cardColor, borderColor: getAlphaColor(accentColor, '22') },
                  isPlayingThis && { borderColor: accentColor, borderWidth: 1.5, backgroundColor: getAlphaColor(accentColor, '22') },
                ]}
                onPress={() => {
                  onSelectTrack(item);
                  onClose();
                }}
              >
                <Image
                  source={
                    typeof item.cover === 'number' || (item.cover && item.cover.uri)
                      ? item.cover
                      : DEFAULT_FALLBACK_COVER
                  }
                  style={styles.thumb}
                />
                <View style={styles.meta}>
                  <Text style={[styles.title, { color: textColor }, isPlayingThis && { color: accentColor, fontWeight: 'bold' }]} numberOfLines={1}>
                    {item.title}
                  </Text>
                  <Text style={[styles.artist, { color: subtextColor }]} numberOfLines={1}>
                    {item.artist} • {item.album}
                  </Text>
                </View>
                <Text style={[styles.arrow, { color: accentColor }]}>▶</Text>
              </TouchableOpacity>
            );
          }}
          ListEmptyComponent={
            <View style={styles.emptyContainer}>
              <Text style={styles.emptyIcon}>{query ? '🔎' : '🎵'}</Text>
              <Text style={[styles.emptyText, { color: subtextColor }]}>
                {query ? 'No se encontraron coincidencias para tu búsqueda' : 'Escribe para buscar entre tus canciones'}
              </Text>
            </View>
          }
        />
      </View>
    </Modal>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  header: {
    paddingTop: 46,
    paddingHorizontal: 16,
    paddingBottom: 12,
    borderBottomWidth: 1,
  },
  headerTopRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 10,
  },
  titleBadgeRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  headerIcon: {
    fontSize: 20,
  },
  headerTitle: {
    fontSize: 15,
    fontWeight: '900',
    letterSpacing: 1,
  },
  closeBtn: {
    padding: 6,
  },
  closeBtnText: {
    fontSize: 22,
    fontWeight: 'bold',
  },
  searchInputBox: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 12,
    height: 44,
    borderRadius: 14,
    borderWidth: 1,
    marginBottom: 10,
  },
  searchIcon: {
    fontSize: 14,
    marginRight: 8,
  },
  inputField: {
    flex: 1,
    fontSize: 13,
  },
  clearBtn: {
    padding: 4,
  },
  filtersRow: {
    flexDirection: 'row',
    gap: 6,
  },
  filterPill: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: '#333344',
  },
  filterPillText: {
    fontSize: 11,
    fontWeight: 'bold',
  },
  listContent: {
    paddingHorizontal: 16,
    paddingTop: 12,
    paddingBottom: 40,
  },
  trackRow: {
    height: 58,
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 10,
    borderRadius: 12,
    marginBottom: 6,
    borderWidth: 1,
  },
  thumb: {
    width: 40,
    height: 40,
    borderRadius: 8,
  },
  meta: {
    flex: 1,
    marginLeft: 10,
    marginRight: 8,
  },
  title: {
    fontSize: 13,
  },
  artist: {
    fontSize: 11,
    marginTop: 2,
  },
  arrow: {
    fontSize: 12,
    paddingHorizontal: 6,
  },
  emptyContainer: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 60,
  },
  emptyIcon: {
    fontSize: 40,
    marginBottom: 12,
  },
  emptyText: {
    fontSize: 13,
    textAlign: 'center',
  },
});

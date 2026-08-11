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
  Alert,
  ScrollView,
} from 'react-native';
import { useNeonTheme } from '../context/ThemeContext';
import { getAlphaColor } from '../utils/colorUtils';

export interface Track {
  id: string;
  title: string;
  artist: string;
  album: string;
  durationSeconds: number;
  cover: any;
  audioUrl: string;
  isFavorite?: boolean;
}

const DEFAULT_FALLBACK_COVER = require('../../assets/images/record_player.jpeg');

export type SortCriterion = 'title' | 'artist' | 'album' | 'duration' | 'default';
export type CategoryTab = 'all' | 'folders' | 'artists' | 'favorites' | 'recent';

interface LibraryModalProps {
  visible: boolean;
  playlist: Track[];
  currentTrackIndex: number;
  isPlaying: boolean;
  onClose: () => void;
  onSelectTrack: (track: Track) => void;
  onDeleteSingleTrack: (trackId: string) => void;
  onDeleteMultipleTracks: (trackIds: string[]) => void;
  onRescan: () => void;
  onPickFolder: () => void;
}

const ITEM_HEIGHT = 64;

export const LibraryModal: React.FC<LibraryModalProps> = ({
  visible,
  playlist,
  currentTrackIndex,
  isPlaying,
  onClose,
  onSelectTrack,
  onDeleteSingleTrack,
  onDeleteMultipleTracks,
  onRescan,
  onPickFolder,
}) => {
  const { accentColor, textColor, subtextColor, cardColor, surfaceColor } = useNeonTheme();

  const [activeTab, setActiveTab] = useState<CategoryTab>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [sortBy, setSortBy] = useState<SortCriterion>('default');
  const [sortAscending, setSortAscending] = useState(true);
  const [isMultiSelectMode, setIsMultiSelectMode] = useState(false);
  const [selectedTrackIds, setSelectedTrackIds] = useState<Set<string>>(new Set());

  // FILTRADO POR PESTAÑA DE CATEGORÍA, BÚSQUEDA Y ORDENAMIENTO EN TIEMPO REAL
  const filteredAndSortedTracks = useMemo(() => {
    let result = [...playlist];

    // 1. Filtrado por Pestaña de Categoría (Todas, Carpetas, Artistas, Favoritos, Recientes)
    if (activeTab === 'folders') {
      result = result.filter(
        (t) =>
          t.id.startsWith('saf_') ||
          t.id.startsWith('folder_') ||
          t.artist === 'Carpeta Seleccionada'
      );
    } else if (activeTab === 'artists') {
      result = result.filter((t) => t.artist && t.artist !== 'Desconocido');
    } else if (activeTab === 'favorites') {
      result = result.filter((t) => Boolean(t.isFavorite));
    } else if (activeTab === 'recent') {
      result = result.slice(-50).reverse(); // Últimas 50 canciones agregadas
    }

    // 2. Búsqueda por texto en tiempo real
    if (searchQuery.trim().length > 0) {
      const q = searchQuery.toLowerCase().trim();
      result = result.filter(
        (t) =>
          t.title.toLowerCase().includes(q) ||
          t.artist.toLowerCase().includes(q) ||
          t.album.toLowerCase().includes(q)
      );
    }

    // 3. Ordenamiento estándar de reproductor de música
    if (sortBy !== 'default') {
      result.sort((a, b) => {
        let valA: string | number = '';
        let valB: string | number = '';

        if (sortBy === 'title') {
          valA = a.title.toLowerCase();
          valB = b.title.toLowerCase();
        } else if (sortBy === 'artist') {
          valA = a.artist.toLowerCase();
          valB = b.artist.toLowerCase();
        } else if (sortBy === 'album') {
          valA = a.album.toLowerCase();
          valB = b.album.toLowerCase();
        } else if (sortBy === 'duration') {
          valA = a.durationSeconds || 0;
          valB = b.durationSeconds || 0;
        }

        if (valA < valB) return sortAscending ? -1 : 1;
        if (valA > valB) return sortAscending ? 1 : -1;
        return 0;
      });
    }

    return result;
  }, [playlist, activeTab, searchQuery, sortBy, sortAscending]);

  const toggleSort = (criterion: SortCriterion) => {
    if (sortBy === criterion) {
      setSortAscending(!sortAscending);
    } else {
      setSortBy(criterion);
      setSortAscending(true);
    }
  };

  const handleToggleSelectTrack = (id: string) => {
    const next = new Set(selectedTrackIds);
    if (next.has(id)) {
      next.delete(id);
    } else {
      next.add(id);
    }
    setSelectedTrackIds(next);
  };

  const handleSelectAll = () => {
    if (selectedTrackIds.size === filteredAndSortedTracks.length) {
      setSelectedTrackIds(new Set());
    } else {
      setSelectedTrackIds(new Set(filteredAndSortedTracks.map((t) => t.id)));
    }
  };

  const handleBatchDelete = () => {
    if (selectedTrackIds.size === 0) return;

    Alert.alert(
      'Eliminar Canciones',
      `¿Estás seguro de quitar ${selectedTrackIds.size} canción(es) de tu lista?`,
      [
        { text: 'Cancelar', style: 'cancel' },
        {
          text: 'Eliminar',
          style: 'destructive',
          onPress: () => {
            onDeleteMultipleTracks(Array.from(selectedTrackIds));
            setSelectedTrackIds(new Set());
            setIsMultiSelectMode(false);
          },
        },
      ]
    );
  };

  const confirmSingleDelete = (track: Track) => {
    Alert.alert(
      'Quitar Canción',
      `¿Deseas quitar "${track.title}" de tu lista de reproducción?`,
      [
        { text: 'Cancelar', style: 'cancel' },
        {
          text: 'Quitar',
          style: 'destructive',
          onPress: () => onDeleteSingleTrack(track.id),
        },
      ]
    );
  };

  const formatDuration = (secs: number) => {
    const m = Math.floor(secs / 60);
    const s = Math.floor(secs % 60);
    return `${m}:${s < 10 ? '0' : ''}${s}`;
  };

  const currentPlayingTrack = playlist[currentTrackIndex];

  return (
    <Modal visible={visible} animationType="slide" transparent={false} onRequestClose={onClose}>
      <View style={[styles.container, { backgroundColor: '#070709' }]}>
        
        {/* HEADER DE LA BIBLIOTECA DE MÚSICA */}
        <View style={[styles.header, { borderColor: getAlphaColor(accentColor, '33') }]}>
          <View style={styles.headerTopRow}>
            <View style={styles.titleBadgeRow}>
              <Text style={styles.headerIcon}>📚</Text>
              <Text style={[styles.headerTitle, { color: textColor }]}>BIBLIOTECA DE MÚSICA</Text>
            </View>

            <TouchableOpacity onPress={onClose} style={styles.closeBtn}>
              <Text style={[styles.closeBtnText, { color: textColor }]}>✕</Text>
            </TouchableOpacity>
          </View>

          <Text style={[styles.countSubtitle, { color: subtextColor }]}>
            {filteredAndSortedTracks.length.toLocaleString()} de {playlist.length.toLocaleString()} canciones mostradas
          </Text>

          {/* BARRA DE BÚSQUEDA */}
          <View style={styles.searchRow}>
            <View style={[styles.searchInputBox, { backgroundColor: surfaceColor, borderColor: getAlphaColor(accentColor, '44') }]}>
              <Text style={styles.searchIcon}>🔍</Text>
              <TextInput
                style={[styles.inputField, { color: textColor }]}
                placeholder="Buscar por título, artista o álbum..."
                placeholderTextColor={subtextColor}
                value={searchQuery}
                onChangeText={setSearchQuery}
                clearButtonMode="while-editing"
              />
              {searchQuery.length > 0 && (
                <TouchableOpacity onPress={() => setSearchQuery('')} style={styles.clearSearchBtn}>
                  <Text style={{ color: subtextColor, fontWeight: 'bold' }}>✕</Text>
                </TouchableOpacity>
              )}
            </View>
          </View>

          {/* PESTAÑAS DE CATEGORÍA DE NAVEGACIÓN (Todas, Carpetas, Artistas, Favoritos, Recientes) */}
          <View style={styles.categoryTabsBar}>
            <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.categoryTabsRow}>
              <TouchableOpacity
                style={[
                  styles.categoryTabBtn,
                  activeTab === 'all' && { backgroundColor: accentColor, borderColor: accentColor },
                ]}
                onPress={() => setActiveTab('all')}
              >
                <Text style={[styles.categoryTabText, { color: activeTab === 'all' ? '#000' : textColor }]}>
                  🎵 Todas ({playlist.length})
                </Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={[
                  styles.categoryTabBtn,
                  activeTab === 'folders' && { backgroundColor: accentColor, borderColor: accentColor },
                ]}
                onPress={() => setActiveTab('folders')}
              >
                <Text style={[styles.categoryTabText, { color: activeTab === 'folders' ? '#000' : textColor }]}>
                  📁 Carpetas
                </Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={[
                  styles.categoryTabBtn,
                  activeTab === 'artists' && { backgroundColor: accentColor, borderColor: accentColor },
                ]}
                onPress={() => setActiveTab('artists')}
              >
                <Text style={[styles.categoryTabText, { color: activeTab === 'artists' ? '#000' : textColor }]}>
                  👤 Artistas
                </Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={[
                  styles.categoryTabBtn,
                  activeTab === 'favorites' && { backgroundColor: accentColor, borderColor: accentColor },
                ]}
                onPress={() => setActiveTab('favorites')}
              >
                <Text style={[styles.categoryTabText, { color: activeTab === 'favorites' ? '#000' : textColor }]}>
                  ❤️ Favoritos
                </Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={[
                  styles.categoryTabBtn,
                  activeTab === 'recent' && { backgroundColor: accentColor, borderColor: accentColor },
                ]}
                onPress={() => setActiveTab('recent')}
              >
                <Text style={[styles.categoryTabText, { color: activeTab === 'recent' ? '#000' : textColor }]}>
                  🕒 Recientes
                </Text>
              </TouchableOpacity>
            </ScrollView>
          </View>

          {/* BOTONES DE ORDENAMIENTO ESTÁNDAR (Título, Artista, Álbum, Duración) */}
          <View style={styles.sortBar}>
            <Text style={[styles.sortLabel, { color: subtextColor }]}>ORDENAR POR:</Text>

            <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.sortPillsRow}>
              <TouchableOpacity
                style={[
                  styles.sortPill,
                  sortBy === 'title' && { backgroundColor: getAlphaColor(accentColor, '33'), borderColor: accentColor },
                ]}
                onPress={() => toggleSort('title')}
              >
                <Text style={[styles.sortPillText, { color: sortBy === 'title' ? accentColor : textColor }]}>
                  🔤 Título {sortBy === 'title' ? (sortAscending ? '↑' : '↓') : ''}
                </Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={[
                  styles.sortPill,
                  sortBy === 'artist' && { backgroundColor: getAlphaColor(accentColor, '33'), borderColor: accentColor },
                ]}
                onPress={() => toggleSort('artist')}
              >
                <Text style={[styles.sortPillText, { color: sortBy === 'artist' ? accentColor : textColor }]}>
                  👤 Artista {sortBy === 'artist' ? (sortAscending ? '↑' : '↓') : ''}
                </Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={[
                  styles.sortPill,
                  sortBy === 'album' && { backgroundColor: getAlphaColor(accentColor, '33'), borderColor: accentColor },
                ]}
                onPress={() => toggleSort('album')}
              >
                <Text style={[styles.sortPillText, { color: sortBy === 'album' ? accentColor : textColor }]}>
                  💿 Álbum {sortBy === 'album' ? (sortAscending ? '↑' : '↓') : ''}
                </Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={[
                  styles.sortPill,
                  sortBy === 'duration' && { backgroundColor: getAlphaColor(accentColor, '33'), borderColor: accentColor },
                ]}
                onPress={() => toggleSort('duration')}
              >
                <Text style={[styles.sortPillText, { color: sortBy === 'duration' ? accentColor : textColor }]}>
                  ⏱️ Duración {sortBy === 'duration' ? (sortAscending ? '↑' : '↓') : ''}
                </Text>
              </TouchableOpacity>

              {sortBy !== 'default' && (
                <TouchableOpacity style={styles.resetSortBtn} onPress={() => setSortBy('default')}>
                  <Text style={[styles.resetSortText, { color: accentColor }]}>Restablecer</Text>
                </TouchableOpacity>
              )}
            </ScrollView>
          </View>

          {/* FILA DE GESTIÓN Y SELECCIÓN MÚLTIPLE */}
          <View style={styles.manageRow}>
            <TouchableOpacity
              style={[
                styles.manageToggleBtn,
                isMultiSelectMode && { backgroundColor: getAlphaColor(accentColor, '33'), borderColor: accentColor },
              ]}
              onPress={() => {
                setIsMultiSelectMode(!isMultiSelectMode);
                setSelectedTrackIds(new Set());
              }}
            >
              <Text style={[styles.manageToggleText, { color: accentColor }]}>
                {isMultiSelectMode ? '✓ Cancelar Selección' : '☑️ Selección Múltiple'}
              </Text>
            </TouchableOpacity>

            {isMultiSelectMode ? (
              <View style={styles.batchActionsGroup}>
                <TouchableOpacity style={styles.selectAllBtn} onPress={handleSelectAll}>
                  <Text style={[styles.selectAllText, { color: textColor }]}>
                    {selectedTrackIds.size === filteredAndSortedTracks.length ? 'Desmarcar' : 'Marcar Todo'}
                  </Text>
                </TouchableOpacity>

                {selectedTrackIds.size > 0 && (
                  <TouchableOpacity style={styles.deleteBatchBtn} onPress={handleBatchDelete}>
                    <Text style={styles.deleteBatchText}>
                      🗑️ Eliminar ({selectedTrackIds.size})
                    </Text>
                  </TouchableOpacity>
                )}
              </View>
            ) : (
              <View style={styles.folderScanGroup}>
                <TouchableOpacity style={[styles.actionIconBtn, { borderColor: getAlphaColor(accentColor, '44') }]} onPress={onRescan}>
                  <Text style={[styles.actionIconBtnText, { color: textColor }]}>🔄 Re-escanear</Text>
                </TouchableOpacity>

                <TouchableOpacity style={[styles.actionIconBtn, { borderColor: getAlphaColor(accentColor, '44') }]} onPress={onPickFolder}>
                  <Text style={[styles.actionIconBtnText, { color: textColor }]}>📂 Carpeta</Text>
                </TouchableOpacity>
              </View>
            )}
          </View>

        </View>

        {/* LISTA VIRTUALIZADA FLUIDA DE ALTO RENDIMIENTO (60FPS CON N ARCHIVOS) */}
        <FlatList
          data={filteredAndSortedTracks}
          keyExtractor={(item) => item.id}
          getItemLayout={(_, index) => ({
            length: ITEM_HEIGHT,
            offset: ITEM_HEIGHT * index,
            index,
          })}
          initialNumToRender={20}
          maxToRenderPerBatch={25}
          windowSize={7}
          removeClippedSubviews={true}
          showsVerticalScrollIndicator={true}
          contentContainerStyle={styles.listContainer}
          renderItem={({ item }) => {
            const isPlayingThisTrack = currentPlayingTrack && currentPlayingTrack.id === item.id;
            const isChecked = selectedTrackIds.has(item.id);

            return (
              <TouchableOpacity
                style={[
                  styles.trackRow,
                  { backgroundColor: cardColor, borderColor: getAlphaColor(accentColor, '22') },
                  isPlayingThisTrack && {
                    backgroundColor: getAlphaColor(accentColor, '22'),
                    borderColor: accentColor,
                    borderWidth: 1,
                  },
                ]}
                onPress={() => {
                  if (isMultiSelectMode) {
                    handleToggleSelectTrack(item.id);
                  } else {
                    onSelectTrack(item);
                    onClose();
                  }
                }}
              >
                {/* CHECKBOX SI ESTÁ EN MODO DE SELECCIÓN MÚLTIPLE */}
                {isMultiSelectMode && (
                  <View style={[styles.checkboxCircle, isChecked && { backgroundColor: accentColor, borderColor: accentColor }]}>
                    {isChecked && <Text style={styles.checkboxCheck}>✓</Text>}
                  </View>
                )}

                {/* THUMBNAIL DE LA CANCIÓN */}
                <Image
                  source={
                    typeof item.cover === 'number' || (item.cover && item.cover.uri)
                      ? item.cover
                      : DEFAULT_FALLBACK_COVER
                  }
                  style={styles.trackThumb}
                />

                {/* METADATOS DE TÍTULO Y ARTISTA */}
                <View style={styles.trackMeta}>
                  <Text
                    style={[
                      styles.trackTitleText,
                      { color: textColor },
                      isPlayingThisTrack && { color: accentColor, fontWeight: 'bold' },
                    ]}
                    numberOfLines={1}
                  >
                    {item.title}
                  </Text>
                  <Text style={[styles.trackArtistText, { color: subtextColor }]} numberOfLines={1}>
                    {item.artist} • {item.album}
                  </Text>
                </View>

                {/* DURACIÓN */}
                <Text style={[styles.durationText, { color: subtextColor }]}>
                  {formatDuration(item.durationSeconds)}
                </Text>

                {/* BOTÓN DE ACCIÓN ELIMINAR INDIVIDUAL */}
                {!isMultiSelectMode && (
                  <TouchableOpacity
                    style={styles.singleDeleteBtn}
                    onPress={() => confirmSingleDelete(item)}
                  >
                    <Text style={styles.singleDeleteIcon}>🗑️</Text>
                  </TouchableOpacity>
                )}
              </TouchableOpacity>
            );
          }}
          ListEmptyComponent={
            <View style={styles.emptyContainer}>
              <Text style={styles.emptyIcon}>📻</Text>
              <Text style={[styles.emptyText, { color: textColor }]}>
                {searchQuery
                  ? 'No se encontraron canciones que coincidan con la búsqueda'
                  : 'No hay canciones en esta categoría'}
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
  },
  titleBadgeRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  headerIcon: {
    fontSize: 22,
  },
  headerTitle: {
    fontSize: 16,
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
  countSubtitle: {
    fontSize: 11,
    marginTop: 2,
    marginBottom: 8,
  },
  searchRow: {
    width: '100%',
    marginBottom: 8,
  },
  searchInputBox: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 12,
    height: 42,
    borderRadius: 12,
    borderWidth: 1,
  },
  searchIcon: {
    fontSize: 14,
    marginRight: 8,
  },
  inputField: {
    flex: 1,
    fontSize: 13,
  },
  clearSearchBtn: {
    padding: 4,
  },
  categoryTabsBar: {
    marginBottom: 8,
  },
  categoryTabsRow: {
    flexDirection: 'row',
    gap: 6,
    alignItems: 'center',
  },
  categoryTabBtn: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: '#333344',
  },
  categoryTabText: {
    fontSize: 11,
    fontWeight: 'bold',
  },
  sortBar: {
    marginBottom: 8,
  },
  sortLabel: {
    fontSize: 9,
    fontWeight: 'bold',
    letterSpacing: 1,
    marginBottom: 4,
  },
  sortPillsRow: {
    flexDirection: 'row',
    gap: 6,
    alignItems: 'center',
  },
  sortPill: {
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#333344',
  },
  sortPillText: {
    fontSize: 10,
    fontWeight: 'bold',
  },
  resetSortBtn: {
    paddingHorizontal: 8,
    paddingVertical: 4,
  },
  resetSortText: {
    fontSize: 10,
    fontWeight: 'bold',
  },
  manageRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: 2,
  },
  manageToggleBtn: {
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: '#333344',
  },
  manageToggleText: {
    fontSize: 11,
    fontWeight: 'bold',
  },
  batchActionsGroup: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  selectAllBtn: {
    paddingHorizontal: 8,
    paddingVertical: 6,
  },
  selectAllText: {
    fontSize: 11,
    fontWeight: 'bold',
  },
  deleteBatchBtn: {
    backgroundColor: '#FF3B30',
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 10,
  },
  deleteBatchText: {
    color: '#FFF',
    fontSize: 11,
    fontWeight: 'bold',
  },
  folderScanGroup: {
    flexDirection: 'row',
    gap: 6,
  },
  actionIconBtn: {
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 10,
    borderWidth: 1,
  },
  actionIconBtnText: {
    fontSize: 10,
    fontWeight: 'bold',
  },
  listContainer: {
    paddingHorizontal: 16,
    paddingTop: 10,
    paddingBottom: 40,
  },
  trackRow: {
    height: ITEM_HEIGHT - 6,
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 10,
    borderRadius: 12,
    marginBottom: 6,
    borderWidth: 1,
  },
  checkboxCircle: {
    width: 20,
    height: 20,
    borderRadius: 10,
    borderWidth: 1.5,
    borderColor: '#666',
    marginRight: 10,
    justifyContent: 'center',
    alignItems: 'center',
  },
  checkboxCheck: {
    color: '#000',
    fontSize: 12,
    fontWeight: 'bold',
  },
  trackThumb: {
    width: 42,
    height: 42,
    borderRadius: 8,
  },
  trackMeta: {
    flex: 1,
    marginLeft: 10,
    marginRight: 8,
  },
  trackTitleText: {
    fontSize: 13,
  },
  trackArtistText: {
    fontSize: 11,
    marginTop: 2,
  },
  durationText: {
    fontSize: 11,
    fontWeight: '600',
    marginRight: 8,
  },
  singleDeleteBtn: {
    padding: 6,
  },
  singleDeleteIcon: {
    fontSize: 15,
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

import React, { useState, useMemo, useEffect } from 'react';
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
  ActivityIndicator,
} from 'react-native';
import * as MediaLibrary from 'expo-media-library';
import { useNeonTheme } from '../context/ThemeContext';
import { getAlphaColor } from '../utils/colorUtils';
import { getDeviceMusicAlbums, getTracksFromAlbumPaginated } from '../utils/mediaScanner';
import { TrackContextMenuModal } from './TrackContextMenuModal';

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
  onFolderTracksLoaded?: (tracks: Track[]) => void;
  initialTab?: CategoryTab;
  onToggleFavoriteTrack?: (track: Track) => void;
  onShowLyricsTrack?: (track: Track) => void;
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
  onFolderTracksLoaded,
  initialTab = 'all',
  onToggleFavoriteTrack,
  onShowLyricsTrack,
}) => {
  const { accentColor, textColor, subtextColor, cardColor, surfaceColor } = useNeonTheme();

  const [activeTab, setActiveTab] = useState<CategoryTab>(initialTab);
  const [searchQuery, setSearchQuery] = useState('');
  const [sortBy, setSortBy] = useState<SortCriterion>('default');
  const [sortAscending, setSortAscending] = useState(true);
  const [isMultiSelectMode, setIsMultiSelectMode] = useState(false);
  const [selectedTrackIds, setSelectedTrackIds] = useState<Set<string>>(new Set());

  // ESTADOS PARA MENÚ CONTEXTUAL DE CANCIÓN ESTILO POWERAMP
  const [contextTrack, setContextTrack] = useState<Track | null>(null);

  // ESTADOS PARA LA VISTA DE CARPETAS / ÁLBUMES REALES
  const [deviceAlbums, setDeviceAlbums] = useState<MediaLibrary.Album[]>([]);
  const [isLoadingAlbums, setIsLoadingAlbums] = useState(false);
  const [selectedAlbumId, setSelectedAlbumId] = useState<string | null>(null);
  const [loadingAlbumCount, setLoadingAlbumCount] = useState<number>(0);

  useEffect(() => {
    if (visible && activeTab === 'folders') {
      loadAlbums();
    }
  }, [visible, activeTab]);

  const loadAlbums = async () => {
    setIsLoadingAlbums(true);
    const albums = await getDeviceMusicAlbums();
    setDeviceAlbums(albums);
    setIsLoadingAlbums(false);
  };

  const handleSelectAlbumFolder = async (album: MediaLibrary.Album) => {
    setSelectedAlbumId(album.id);
    setLoadingAlbumCount(0);
    const albumTracks = await getTracksFromAlbumPaginated(album.id, (count) => {
      setLoadingAlbumCount(count);
    });

    if (albumTracks.length > 0 && onFolderTracksLoaded) {
      onFolderTracksLoaded(albumTracks);
    }
    setSelectedAlbumId(null);
  };

  // FILTRADO POR PESTAÑA DE CATEGORÍA, BÚSQUEDA Y ORDENAMIENTO EN TIEMPO REAL
  const filteredAndSortedTracks = useMemo(() => {
    let result = [...playlist];

    // 1. Filtrado por Pestaña de Categoría
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
      result = result.slice(-50).reverse();
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
            {activeTab === 'folders'
              ? `${deviceAlbums.length} carpetas detectadas en el dispositivo`
              : `${filteredAndSortedTracks.length.toLocaleString()} de ${playlist.length.toLocaleString()} canciones mostradas`}
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
                onPress={() => {
                  setActiveTab('folders');
                  loadAlbums();
                }}
              >
                <Text style={[styles.categoryTabText, { color: activeTab === 'folders' ? '#000' : textColor }]}>
                  📁 Carpetas ({deviceAlbums.length})
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
          {activeTab !== 'folders' && (
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
          )}

          {/* FILA DE GESTIÓN Y SELECCIÓN MÚLTIPLE */}
          <View style={styles.manageRow}>
            {activeTab !== 'folders' ? (
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
            ) : (
              <Text style={[styles.manageToggleText, { color: subtextColor }]}>
                Selecciona una carpeta para cargar sus canciones sin congelamiento
              </Text>
            )}

            {isMultiSelectMode && activeTab !== 'folders' ? (
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
              </View>
            )}
          </View>

        </View>

        {/* VISTA DE LISTA DE CARPETAS / ÁLBUMES SI ACTIVE TAB === 'folders' */}
        {activeTab === 'folders' ? (
          isLoadingAlbums ? (
            <View style={styles.loadingBox}>
              <ActivityIndicator size="large" color={accentColor} />
              <Text style={[styles.loadingText, { color: subtextColor }]}>Cargando carpetas del dispositivo...</Text>
            </View>
          ) : (
            <FlatList
              data={deviceAlbums}
              keyExtractor={(item) => item.id}
              contentContainerStyle={styles.listContainer}
              renderItem={({ item }) => {
                const isLoadingThis = selectedAlbumId === item.id;
                return (
                  <TouchableOpacity
                    style={[styles.albumRow, { backgroundColor: cardColor, borderColor: getAlphaColor(accentColor, '33') }]}
                    onPress={() => handleSelectAlbumFolder(item)}
                    disabled={Boolean(selectedAlbumId)}
                  >
                    <Text style={styles.albumFolderIcon}>📁</Text>
                    <View style={styles.albumMeta}>
                      <Text style={[styles.albumTitleText, { color: textColor }]} numberOfLines={1}>
                        {item.title}
                      </Text>
                      <Text style={[styles.albumCountText, { color: accentColor }]}>
                        {item.assetCount} canciones en esta carpeta
                      </Text>
                    </View>

                    {isLoadingThis ? (
                      <View style={styles.loadingCountBox}>
                        <ActivityIndicator size="small" color={accentColor} />
                        <Text style={[styles.loadingCountText, { color: accentColor }]}>
                          {loadingAlbumCount > 0 ? `${loadingAlbumCount}` : '...'}
                        </Text>
                      </View>
                    ) : (
                      <Text style={[styles.albumArrow, { color: subtextColor }]}>➔</Text>
                    )}
                  </TouchableOpacity>
                );
              }}
              ListEmptyComponent={
                <View style={styles.emptyContainer}>
                  <Text style={styles.emptyIcon}>📁</Text>
                  <Text style={[styles.emptyText, { color: textColor }]}>
                    No se encontraron carpetas con archivos de audio en el almacenamiento
                  </Text>
                </View>
              }
            />
          )
        ) : (
          /* LISTA VIRTUALIZADA FLUIDA DE ALTO RENDIMIENTO (60FPS CON CANCIONES) */
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
                  onLongPress={() => setContextTrack(item)}
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

                  {/* BOTÓN DE MENÚ CONTEXTUAL ESTILO POWERAMP */}
                  {!isMultiSelectMode && (
                    <TouchableOpacity
                      style={styles.contextMenuBtn}
                      onPress={() => setContextTrack(item)}
                    >
                      <Text style={[styles.contextMenuIcon, { color: accentColor }]}>⋮</Text>
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
        )}

      </View>

      {/* MENÚ CONTEXTUAL DE CANCIÓN ESTILO POWERAMP */}
      <TrackContextMenuModal
        visible={Boolean(contextTrack)}
        track={contextTrack}
        onClose={() => setContextTrack(null)}
        onToggleFavorite={(t) => {
          if (onToggleFavoriteTrack) onToggleFavoriteTrack(t);
        }}
        onDeleteTrack={(t) => onDeleteSingleTrack(t.id)}
        onShowArtist={(art) => {
          setSearchQuery(art);
          setActiveTab('all');
        }}
        onShowAlbum={(alb) => {
          setSearchQuery(alb);
          setActiveTab('all');
        }}
        onOpenFolder={() => {
          setActiveTab('folders');
          loadAlbums();
        }}
        onShowLyrics={(t) => {
          if (onShowLyricsTrack) onShowLyricsTrack(t);
        }}
      />
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
  albumRow: {
    height: 60,
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 14,
    borderRadius: 14,
    marginBottom: 8,
    borderWidth: 1,
  },
  albumFolderIcon: {
    fontSize: 22,
    marginRight: 12,
  },
  albumMeta: {
    flex: 1,
  },
  albumTitleText: {
    fontSize: 14,
    fontWeight: 'bold',
  },
  albumCountText: {
    fontSize: 11,
    marginTop: 2,
    fontWeight: '600',
  },
  albumArrow: {
    fontSize: 16,
    paddingHorizontal: 6,
  },
  loadingCountBox: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  loadingCountText: {
    fontSize: 12,
    fontWeight: 'bold',
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
    marginRight: 6,
  },
  contextMenuBtn: {
    paddingHorizontal: 8,
    paddingVertical: 6,
  },
  contextMenuIcon: {
    fontSize: 20,
    fontWeight: 'bold',
  },
  loadingBox: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 60,
    gap: 12,
  },
  loadingText: {
    fontSize: 13,
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

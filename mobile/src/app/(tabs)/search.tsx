import React, { useState, useEffect, useMemo } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TextInput,
  TouchableOpacity,
  FlatList,
  Image,
  SafeAreaView,
  StatusBar,
} from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { useNeonTheme } from '@/context/ThemeContext';
import { getAlphaColor } from '@/utils/colorUtils';
import { Track } from '@/components/LibraryModal';
import { TrackContextMenuModal } from '@/components/TrackContextMenuModal';

const PLAYLIST_STORAGE_KEY = '@custom_music_player_saved_playlist_v10';
const DEFAULT_FALLBACK_COVER = require('../../../assets/images/record_player.jpeg');

export type SearchFilterType = 'all' | 'titles' | 'artists' | 'albums' | 'folders';

export default function SearchScreen() {
  const { accentColor, textColor, subtextColor, cardColor, surfaceColor } = useNeonTheme();

  const [playlist, setPlaylist] = useState<Track[]>([]);
  const [query, setQuery] = useState('');
  const [debouncedQuery, setDebouncedQuery] = useState('');
  const [activeFilter, setActiveFilter] = useState<SearchFilterType>('all');
  const [isFocused, setIsFocused] = useState(false);
  const [contextTrack, setContextTrack] = useState<Track | null>(null);

  useEffect(() => {
    loadPlaylist();
  }, []);

  const loadPlaylist = async () => {
    try {
      const saved = await AsyncStorage.getItem(PLAYLIST_STORAGE_KEY);
      if (saved) {
        const parsed = JSON.parse(saved);
        if (parsed) setPlaylist(parsed);
      }
    } catch (err) {
      console.warn('Error cargando biblioteca en búsqueda:', err);
    }
  };

  // DEBOUNCE DE BÚSQUEDA DE 300MS PARA MÁXIMA FLUIDEZ
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedQuery(query);
    }, 300);

    return () => {
      clearTimeout(handler);
    };
  }, [query]);

  // FILTRADO EN TIEMPO REAL SOBRE EL ÍNDICE YA ESCANEADO
  const searchResults = useMemo(() => {
    if (!debouncedQuery.trim()) return [];
    const q = debouncedQuery.toLowerCase().trim();

    return playlist.filter((track) => {
      const titleMatch = track.title.toLowerCase().includes(q);
      const artistMatch = track.artist.toLowerCase().includes(q);
      const albumMatch = track.album.toLowerCase().includes(q);
      const folderMatch = track.audioUrl.toLowerCase().includes(q);

      if (activeFilter === 'titles') return titleMatch;
      if (activeFilter === 'artists') return artistMatch;
      if (activeFilter === 'albums') return albumMatch;
      if (activeFilter === 'folders') return folderMatch;

      return titleMatch || artistMatch || albumMatch || folderMatch;
    });
  }, [playlist, debouncedQuery, activeFilter]);

  const formatDuration = (secs: number) => {
    const m = Math.floor(secs / 60);
    const s = Math.floor(secs % 60);
    return `${m}:${s < 10 ? '0' : ''}${s}`;
  };

  const filterTabs: { id: SearchFilterType; label: string }[] = [
    { id: 'all', label: '🌐 Todo' },
    { id: 'titles', label: '🔤 Canciones' },
    { id: 'artists', label: '👤 Artistas' },
    { id: 'albums', label: '💿 Álbumes' },
    { id: 'folders', label: '📁 Carpetas' },
  ];

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: '#0A0A0A' }]}>
      <StatusBar barStyle="light-content" backgroundColor="#0A0A0A" />

      {/* CABECERA SUPERIOR DE BÚSQUEDA */}
      <View style={[styles.header, { borderColor: getAlphaColor(accentColor, '33') }]}>
        <Text style={[styles.headerTitle, { color: textColor }]}>🔍 BÚSQUEDA GLOBAL</Text>
        <Text style={[styles.headerSubtitle, { color: subtextColor }]}>
          Busca en tu biblioteca de {playlist.length.toLocaleString()} canciones
        </Text>

        {/* CAMPO DE ENTRADA DE BÚSQUEDA CON BORDE NEÓN DE ENFOQUE */}
        <View
          style={[
            styles.inputContainer,
            {
              backgroundColor: surfaceColor,
              borderColor: isFocused ? accentColor : getAlphaColor(accentColor, '44'),
            },
          ]}
        >
          <Text style={styles.searchIcon}>🔍</Text>
          <TextInput
            style={[styles.input, { color: textColor }]}
            placeholder="Buscar canción, artista, álbum o carpeta..."
            placeholderTextColor={subtextColor}
            value={query}
            onChangeText={setQuery}
            onFocus={() => setIsFocused(true)}
            onBlur={() => setIsFocused(false)}
            autoCorrect={false}
          />
          {query.length > 0 && (
            <TouchableOpacity onPress={() => setQuery('')} style={styles.clearBtn}>
              <Text style={[styles.clearBtnText, { color: subtextColor }]}>✕</Text>
            </TouchableOpacity>
          )}
        </View>

        {/* PILLS DE FILTRO REUTILIZANDO EL PATRÓN DE BOTONES SEGMENTADOS */}
        <View style={styles.filterPillsRow}>
          {filterTabs.map((tab) => {
            const isSelected = activeFilter === tab.id;
            return (
              <TouchableOpacity
                key={tab.id}
                style={[
                  styles.segmentBtn,
                  isSelected && { backgroundColor: accentColor, borderColor: accentColor },
                ]}
                onPress={() => setActiveFilter(tab.id)}
              >
                <Text style={[styles.segmentText, { color: isSelected ? '#000000' : textColor }]}>
                  {tab.label}
                </Text>
              </TouchableOpacity>
            );
          })}
        </View>
      </View>

      {/* RESULTADOS EN TIEMPO REAL */}
      <FlatList
        data={searchResults}
        keyExtractor={(item) => item.id}
        contentContainerStyle={styles.resultsList}
        renderItem={({ item }) => (
          <TouchableOpacity
            style={[styles.trackRow, { backgroundColor: cardColor, borderColor: getAlphaColor(accentColor, '22') }]}
            onLongPress={() => setContextTrack(item)}
          >
            <Image
              source={
                typeof item.cover === 'number' || (item.cover && item.cover.uri)
                  ? item.cover
                  : DEFAULT_FALLBACK_COVER
              }
              style={styles.trackThumb}
            />

            <View style={styles.trackMeta}>
              <Text style={[styles.trackTitleText, { color: textColor }]} numberOfLines={1}>
                {item.title}
              </Text>
              <Text style={[styles.trackArtistText, { color: subtextColor }]} numberOfLines={1}>
                {item.artist} • {item.album}
              </Text>
            </View>

            <Text style={[styles.durationText, { color: subtextColor }]}>
              {formatDuration(item.durationSeconds)}
            </Text>

            <TouchableOpacity style={styles.contextBtn} onPress={() => setContextTrack(item)}>
              <Text style={[styles.contextIcon, { color: accentColor }]}>⋮</Text>
            </TouchableOpacity>
          </TouchableOpacity>
        )}
        ListEmptyComponent={
          <View style={styles.emptyContainer}>
            <View
              style={[
                styles.emptyIconCircle,
                { borderColor: getAlphaColor(accentColor, '44'), backgroundColor: getAlphaColor(accentColor, '15') },
              ]}
            >
              <Text style={styles.emptyIconText}>{debouncedQuery ? '🔍' : '🎵'}</Text>
            </View>
            <Text style={[styles.emptyTitle, { color: textColor }]}>
              {debouncedQuery ? 'Sin Resultados Coincidentes' : 'Encuentra tu Música Favorita'}
            </Text>
            <Text style={[styles.emptySubtitle, { color: subtextColor }]}>
              {debouncedQuery
                ? `No encontramos canciones que coincidan con "${debouncedQuery}" en ${activeFilter.toUpperCase()}`
                : 'Escribe el nombre de un título, artista o carpeta para comenzar'}
            </Text>
          </View>
        }
      />

      {/* MENÚ CONTEXTUAL DE CANCIÓN */}
      <TrackContextMenuModal
        visible={Boolean(contextTrack)}
        track={contextTrack}
        onClose={() => setContextTrack(null)}
        onToggleFavorite={() => {}}
        onDeleteTrack={() => {}}
        onShowArtist={(art) => setQuery(art)}
        onShowAlbum={(alb) => setQuery(alb)}
        onOpenFolder={() => {}}
        onShowLyrics={() => {}}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  header: {
    paddingTop: 40,
    paddingHorizontal: 16,
    paddingBottom: 12,
    borderBottomWidth: 1.5,
  },
  headerTitle: {
    fontSize: 16,
    fontWeight: '900',
    letterSpacing: 1.2,
  },
  headerSubtitle: {
    fontSize: 11,
    marginTop: 2,
    marginBottom: 10,
  },
  inputContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    height: 44,
    borderRadius: 14,
    borderWidth: 1.5,
    paddingHorizontal: 12,
    marginBottom: 12,
  },
  searchIcon: {
    fontSize: 14,
    marginRight: 8,
  },
  input: {
    flex: 1,
    fontSize: 13,
  },
  clearBtn: {
    padding: 6,
  },
  clearBtnText: {
    fontSize: 16,
    fontWeight: 'bold',
  },
  filterPillsRow: {
    flexDirection: 'row',
    gap: 6,
  },
  segmentBtn: {
    flex: 1,
    paddingVertical: 7,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#333344',
    alignItems: 'center',
  },
  segmentText: {
    fontSize: 10,
    fontWeight: 'bold',
  },
  resultsList: {
    padding: 16,
    paddingBottom: 40,
  },
  trackRow: {
    height: 60,
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 10,
    borderRadius: 12,
    marginBottom: 6,
    borderWidth: 1,
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
    fontWeight: 'bold',
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
  contextBtn: {
    paddingHorizontal: 8,
    paddingVertical: 6,
  },
  contextIcon: {
    fontSize: 20,
    fontWeight: 'bold',
  },
  emptyContainer: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 60,
    paddingHorizontal: 20,
  },
  emptyIconCircle: {
    width: 64,
    height: 64,
    borderRadius: 32,
    borderWidth: 2,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 16,
  },
  emptyIconText: {
    fontSize: 28,
  },
  emptyTitle: {
    fontSize: 15,
    fontWeight: 'bold',
    marginBottom: 6,
    textAlign: 'center',
  },
  emptySubtitle: {
    fontSize: 12,
    textAlign: 'center',
    lineHeight: 18,
  },
});

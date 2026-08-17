import React, { useState, useEffect, useMemo } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  SafeAreaView,
  StatusBar,
} from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import * as MediaLibrary from 'expo-media-library';
import { useNeonTheme } from '@/context/ThemeContext';
import { usePlayer } from '@/context/PlayerContext';
import { getAlphaColor } from '@/utils/colorUtils';
import { mapAssetsToTracks } from '@/utils/mediaScanner';
import { LibraryModal, Track, CategoryTab } from '@/components/LibraryModal';

const PLAYLIST_STORAGE_KEY = '@custom_music_player_saved_playlist_v10';

export default function LibraryScreen() {
  const { accentColor, textColor, subtextColor, cardColor } = useNeonTheme();
  const { reloadPlaylistFromStorage } = usePlayer();
  const [playlist, setPlaylist] = useState<Track[]>([]);
  const [activeModalTab, setActiveModalTab] = useState<CategoryTab | null>(null);

  useEffect(() => {
    loadPlaylist();
  }, []);

  const loadPlaylist = async () => {
    try {
      const saved = await AsyncStorage.getItem(PLAYLIST_STORAGE_KEY);
      if (saved) {
        const parsed = JSON.parse(saved);
        if (parsed && parsed.length > 0) {
          setPlaylist(parsed);
          return;
        }
      }
      scanPhoneMusicFolder();
    } catch (e) {
      console.warn('Error en library screen:', e);
    }
  };

  const scanPhoneMusicFolder = async () => {
    try {
      const { status } = await MediaLibrary.requestPermissionsAsync();
      if (status === 'granted') {
        const page = await MediaLibrary.getAssetsAsync({ mediaType: 'audio', first: 2000 });
        if (page.assets && page.assets.length > 0) {
          const mapped = mapAssetsToTracks(page.assets);
          setPlaylist(mapped);
          await AsyncStorage.setItem(PLAYLIST_STORAGE_KEY, JSON.stringify(mapped));
          reloadPlaylistFromStorage();
        }
      }
    } catch (err) {
      console.warn('Error escaneando biblioteca:', err);
    }
  };

  const artistCount = useMemo(() => {
    const set = new Set(playlist.map((t) => t.artist).filter(Boolean));
    return set.size;
  }, [playlist]);

  const favoritesCount = useMemo(() => {
    return playlist.filter((t) => Boolean(t.isFavorite)).length;
  }, [playlist]);

  const categories = [
    {
      id: 'all' as CategoryTab,
      icon: '🎵',
      title: 'Todas las canciones',
      desc: 'Explora y reproduce toda tu colección musical local',
      count: `${playlist.length.toLocaleString()} canciones`,
    },
    {
      id: 'folders' as CategoryTab,
      icon: '📁',
      title: 'Carpetas del dispositivo',
      desc: 'Navega por las carpetas y álbumes del almacenamiento',
      count: 'Carpetas de audio',
    },
    {
      id: 'artists' as CategoryTab,
      icon: '👤',
      title: 'Artistas',
      desc: 'Canciones agrupadas por metadatos de artista ID3',
      count: `${artistCount.toLocaleString()} artistas`,
    },
    {
      id: 'favorites' as CategoryTab,
      icon: '❤️',
      title: 'Favoritos',
      desc: 'Tus canciones preferidas guardadas con corazón',
      count: `${favoritesCount.toLocaleString()} preferidas`,
    },
    {
      id: 'recent' as CategoryTab,
      icon: '🕒',
      title: 'Reproducido recientemente',
      desc: 'Últimas canciones escuchadas en tu reproductor',
      count: 'Historial de reproducción',
    },
    {
      id: 'recent' as CategoryTab,
      icon: '🆕',
      title: 'Agregado recientemente',
      desc: 'Últimos archivos de audio añadidos al dispositivo',
      count: 'Archivos nuevos',
    },
  ];

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: '#0A0A0A' }]}>
      <StatusBar barStyle="light-content" backgroundColor="#0A0A0A" />

      {/* CABECERA ESTILO POWERAMP */}
      <View style={[styles.header, { borderColor: getAlphaColor(accentColor, '33') }]}>
        <View style={styles.titleRow}>
          <Text style={styles.headerIcon}>📚</Text>
          <Text style={[styles.headerTitle, { color: textColor }]}>BIBLIOTECA DE MÚSICA</Text>
        </View>
        <Text style={[styles.subtitle, { color: subtextColor }]}>
          {playlist.length.toLocaleString()} pistas de audio organizadas en tu dispositivo
        </Text>
      </View>

      {/* LISTA DE TARJETAS DE CATEGORÍA CON ICONOS CIRCULARES NEÓN */}
      <ScrollView contentContainerStyle={styles.scrollContent} showsVerticalScrollIndicator={false}>
        {categories.map((cat, idx) => (
          <TouchableOpacity
            key={idx}
            style={[
              styles.categoryCard,
              { backgroundColor: cardColor, borderColor: getAlphaColor(accentColor, '33') },
            ]}
            onPress={() => setActiveModalTab(cat.id)}
            activeOpacity={0.8}
          >
            {/* ICONO CIRCULAR CON ESTILO Y COLOR DE TEMA NEÓN */}
            <View
              style={[
                styles.iconCircle,
                {
                  borderColor: accentColor,
                  backgroundColor: getAlphaColor(accentColor, '1E'),
                },
              ]}
            >
              <Text style={styles.categoryIcon}>{cat.icon}</Text>
            </View>

            {/* TEXTO DE TÍTULO Y DESCRIPCIÓN */}
            <View style={styles.cardMeta}>
              <Text style={[styles.cardTitle, { color: textColor }]}>{cat.title}</Text>
              <Text style={[styles.cardDesc, { color: subtextColor }]} numberOfLines={1}>
                {cat.desc}
              </Text>
              <Text style={[styles.cardCount, { color: accentColor }]}>{cat.count}</Text>
            </View>

            {/* FLECHA INDICADORA NEÓN */}
            <Text style={[styles.arrowIcon, { color: accentColor }]}>➔</Text>
          </TouchableOpacity>
        ))}
      </ScrollView>

      {/* MODAL DE VISTA FILTRADA POR CATEGORÍA */}
      {activeModalTab && (
        <LibraryModal
          visible={Boolean(activeModalTab)}
          playlist={playlist}
          currentTrackIndex={0}
          isPlaying={false}
          initialTab={activeModalTab}
          onClose={() => setActiveModalTab(null)}
          onSelectTrack={() => setActiveModalTab(null)}
          onDeleteSingleTrack={(id) => {
            const updated = playlist.filter((t) => t.id !== id);
            setPlaylist(updated);
            AsyncStorage.setItem(PLAYLIST_STORAGE_KEY, JSON.stringify(updated));
          }}
          onDeleteMultipleTracks={(ids) => {
            const idSet = new Set(ids);
            const updated = playlist.filter((t) => !idSet.has(t.id));
            setPlaylist(updated);
            AsyncStorage.setItem(PLAYLIST_STORAGE_KEY, JSON.stringify(updated));
          }}
          onRescan={scanPhoneMusicFolder}
          onPickFolder={() => {}}
        />
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  header: {
    paddingTop: 40,
    paddingHorizontal: 20,
    paddingBottom: 14,
    borderBottomWidth: 1.5,
  },
  titleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  headerIcon: {
    fontSize: 22,
  },
  headerTitle: {
    fontSize: 16,
    fontWeight: '900',
    letterSpacing: 1.2,
  },
  subtitle: {
    fontSize: 11,
    marginTop: 4,
  },
  scrollContent: {
    padding: 16,
    paddingBottom: 40,
    gap: 12,
  },
  categoryCard: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 14,
    borderRadius: 18,
    borderWidth: 1.5,
    elevation: 3,
  },
  iconCircle: {
    width: 48,
    height: 48,
    borderRadius: 24,
    borderWidth: 2,
    justifyContent: 'center',
    alignItems: 'center',
  },
  categoryIcon: {
    fontSize: 20,
  },
  cardMeta: {
    flex: 1,
    marginLeft: 14,
    marginRight: 8,
  },
  cardTitle: {
    fontSize: 14,
    fontWeight: 'bold',
  },
  cardDesc: {
    fontSize: 11,
    marginTop: 2,
  },
  cardCount: {
    fontSize: 10,
    fontWeight: 'bold',
    marginTop: 4,
  },
  arrowIcon: {
    fontSize: 18,
    paddingHorizontal: 4,
  },
});

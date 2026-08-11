import React, { useState, useEffect } from 'react';
import { View, StyleSheet } from 'react-native';
import { LibraryModal, Track } from '@/components/LibraryModal';
import AsyncStorage from '@react-native-async-storage/async-storage';
import * as MediaLibrary from 'expo-media-library';
import { mapAssetsToTracks } from '@/utils/mediaScanner';

const PLAYLIST_STORAGE_KEY = '@custom_music_player_saved_playlist_v10';

export default function LibraryScreen() {
  const [playlist, setPlaylist] = useState<Track[]>([]);

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
      // Escaneo de fallback si no hay lista previa
      scanPhoneMusicFolder();
    } catch (e) {
      console.warn('Error en library screen:', e);
    }
  };

  const scanPhoneMusicFolder = async () => {
    try {
      const { status } = await MediaLibrary.requestPermissionsAsync();
      if (status === 'granted') {
        const page = await MediaLibrary.getAssetsAsync({ mediaType: 'audio', first: 500 });
        if (page.assets && page.assets.length > 0) {
          const mapped = mapAssetsToTracks(page.assets);
          setPlaylist(mapped);
        }
      }
    } catch (err) {
      console.warn('Error escaneando biblioteca:', err);
    }
  };

  return (
    <View style={styles.container}>
      <LibraryModal
        visible={true}
        playlist={playlist}
        currentTrackIndex={0}
        isPlaying={false}
        onClose={() => {}}
        onSelectTrack={() => {}}
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
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0A0A0A',
  },
});

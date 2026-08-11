import React, { useState, useEffect } from 'react';
import { View, StyleSheet } from 'react-native';
import { SearchViewModal } from '@/components/SearchViewModal';
import { Track } from '@/components/LibraryModal';
import AsyncStorage from '@react-native-async-storage/async-storage';

const PLAYLIST_STORAGE_KEY = '@custom_music_player_saved_playlist_v10';

export default function SearchScreen() {
  const [playlist, setPlaylist] = useState<Track[]>([]);

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
    } catch (e) {
      console.warn('Error en search screen:', e);
    }
  };

  return (
    <View style={styles.container}>
      <SearchViewModal
        visible={true}
        playlist={playlist}
        currentTrackIndex={0}
        onClose={() => {}}
        onSelectTrack={() => {}}
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

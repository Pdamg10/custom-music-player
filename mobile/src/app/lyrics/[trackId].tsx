import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  SafeAreaView,
  StatusBar,
  ActivityIndicator,
} from 'react-native';
import { useLocalSearchParams, router } from 'expo-router';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { useNeonTheme } from '@/context/ThemeContext';
import { getAlphaColor } from '@/utils/colorUtils';
import { Track } from '@/components/LibraryModal';
import { getEmbeddedLyricsForTrack } from '@/utils/coverArtManager';

const PLAYLIST_STORAGE_KEY = '@custom_music_player_saved_playlist_v10';

export interface LyricsLine {
  timeMs?: number;
  text: string;
}

export default function LyricsScreen() {
  const { trackId } = useLocalSearchParams<{ trackId: string }>();
  const { accentColor, textColor, subtextColor, cardColor } = useNeonTheme();

  const [track, setTrack] = useState<Track | null>(null);
  const [lyricsText, setLyricsText] = useState<string | null>(null);
  const [parsedLines, setParsedLines] = useState<LyricsLine[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  useEffect(() => {
    loadTrackAndLyrics();
  }, [trackId]);

  const loadTrackAndLyrics = async () => {
    setIsLoading(true);
    try {
      const saved = await AsyncStorage.getItem(PLAYLIST_STORAGE_KEY);
      if (saved) {
        const parsed: Track[] = JSON.parse(saved);
        const found = parsed.find((t) => t.id === trackId || String(t.id) === String(trackId));
        if (found) {
          setTrack(found);

          // Intentar extraer letras embebidas ID3 del archivo
          const embedded = await getEmbeddedLyricsForTrack(found.audioUrl);
          if (embedded && embedded.trim().length > 0) {
            setLyricsText(embedded);
            parseLyricsFormat(embedded);
          } else {
            setLyricsText(null);
            setParsedLines([]);
          }
        }
      }
    } catch (e) {
      console.warn('Error cargando letras de canción:', e);
    } finally {
      setIsLoading(false);
    }
  };

  // PARSEADOR PREPARADO PARA FUTURAS LETRAS SINCRONIZADAS CON TIMESTAMP [mm:ss.xx]
  const parseLyricsFormat = (rawText: string) => {
    const lines = rawText.split(/\r?\n/);
    const result: LyricsLine[] = [];

    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed) continue;

      // Detectar formato timestamp [01:23.45] texto
      const match = trimmed.match(/^\[(\d{2}):(\d{2})\.?(\d*)\](.*)/);
      if (match) {
        const minutes = parseInt(match[1], 10);
        const seconds = parseInt(match[2], 10);
        const millis = match[3] ? parseInt(match[3].padEnd(3, '0').slice(0, 3), 10) : 0;
        const totalMs = (minutes * 60 + seconds) * 1000 + millis;
        result.push({ timeMs: totalMs, text: match[4].trim() });
      } else {
        result.push({ text: trimmed });
      }
    }

    setParsedLines(result);
  };

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: '#0A0A0A' }]}>
      <StatusBar barStyle="light-content" backgroundColor="#0A0A0A" />

      {/* CABECERA SUPERIOR */}
      <View style={[styles.header, { borderColor: getAlphaColor(accentColor, '33') }]}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backBtn}>
          <Text style={[styles.backBtnText, { color: accentColor }]}>➔</Text>
        </TouchableOpacity>

        <View style={styles.headerMeta}>
          <Text style={[styles.headerTitle, { color: textColor }]} numberOfLines={1}>
            {track ? track.title : 'LETRAS DE LA CANCIÓN'}
          </Text>
          <Text style={[styles.headerSub, { color: accentColor }]} numberOfLines={1}>
            {track ? `${track.artist} • ${track.album}` : 'Metadatos ID3'}
          </Text>
        </View>
      </View>

      {/* CONTENIDO DE LETRAS */}
      {isLoading ? (
        <View style={styles.loadingBox}>
          <ActivityIndicator size="large" color={accentColor} />
          <Text style={[styles.loadingText, { color: subtextColor }]}>Leyendo metadatos del archivo audio...</Text>
        </View>
      ) : lyricsText && parsedLines.length > 0 ? (
        <ScrollView contentContainerStyle={styles.scrollBody} showsVerticalScrollIndicator={false}>
          <View style={[styles.lyricsCard, { backgroundColor: cardColor, borderColor: getAlphaColor(accentColor, '44') }]}>
            {parsedLines.map((item, idx) => (
              <Text key={idx} style={[styles.lyricLineText, { color: textColor }]}>
                {item.text}
              </Text>
            ))}
          </View>
        </ScrollView>
      ) : (
        /* ESTADO VACÍO CUANDO NO HAY LETRAS EMBEBIDAS */
        <View style={styles.emptyContainer}>
          <View
            style={[
              styles.emptyIconCircle,
              { borderColor: getAlphaColor(accentColor, '44'), backgroundColor: getAlphaColor(accentColor, '15') },
            ]}
          >
            <Text style={styles.emptyIcon}>📝</Text>
          </View>

          <Text style={[styles.emptyTitle, { color: textColor }]}>Sin letras disponibles para esta canción</Text>
          <Text style={[styles.emptySubtitle, { color: subtextColor }]}>
            El archivo de audio no contiene la etiqueta de letra embebida ID3 en su cabecera
          </Text>
        </View>
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
    paddingHorizontal: 16,
    paddingBottom: 14,
    borderBottomWidth: 1.5,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  backBtn: {
    padding: 6,
    transform: [{ rotate: '180deg' }],
  },
  backBtnText: {
    fontSize: 22,
    fontWeight: 'bold',
  },
  headerMeta: {
    flex: 1,
  },
  headerTitle: {
    fontSize: 15,
    fontWeight: '900',
    letterSpacing: 0.8,
  },
  headerSub: {
    fontSize: 11,
    marginTop: 2,
    fontWeight: 'bold',
  },
  scrollBody: {
    padding: 18,
    paddingBottom: 40,
  },
  lyricsCard: {
    padding: 22,
    borderRadius: 22,
    borderWidth: 1.5,
    alignItems: 'center',
  },
  lyricLineText: {
    fontSize: 15,
    lineHeight: 28,
    textAlign: 'center',
    fontWeight: '600',
    marginVertical: 4,
  },
  loadingBox: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    gap: 12,
  },
  loadingText: {
    fontSize: 13,
  },
  emptyContainer: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 24,
  },
  emptyIconCircle: {
    width: 68,
    height: 68,
    borderRadius: 34,
    borderWidth: 2,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 16,
  },
  emptyIcon: {
    fontSize: 30,
  },
  emptyTitle: {
    fontSize: 15,
    fontWeight: 'bold',
    textAlign: 'center',
    marginBottom: 6,
  },
  emptySubtitle: {
    fontSize: 12,
    textAlign: 'center',
    lineHeight: 18,
  },
});

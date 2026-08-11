import React from 'react';
import {
  Modal,
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  Image,
} from 'react-native';
import { useNeonTheme } from '../context/ThemeContext';
import { getAlphaColor } from '../utils/colorUtils';
import { Track } from './LibraryModal';

const DEFAULT_FALLBACK_COVER = require('../../assets/images/record_player.jpeg');

interface LyricsViewModalProps {
  visible: boolean;
  track: Track | undefined;
  onClose: () => void;
}

export const LyricsViewModal: React.FC<LyricsViewModalProps> = ({
  visible,
  track,
  onClose,
}) => {
  const { accentColor, textColor, subtextColor, cardColor } = useNeonTheme();

  return (
    <Modal visible={visible} animationType="slide" transparent={false} onRequestClose={onClose}>
      <View style={[styles.container, { backgroundColor: '#070709' }]}>
        
        {/* HEADER DE LETRAS */}
        <View style={[styles.header, { borderColor: getAlphaColor(accentColor, '33') }]}>
          <View style={styles.headerTopRow}>
            <View style={styles.titleBadgeRow}>
              <Text style={styles.headerIcon}>📝</Text>
              <Text style={[styles.headerTitle, { color: textColor }]}>LETRAS DE LA CANCIÓN</Text>
            </View>

            <TouchableOpacity onPress={onClose} style={styles.closeBtn}>
              <Text style={[styles.closeBtnText, { color: textColor }]}>✕</Text>
            </TouchableOpacity>
          </View>

          {track && (
            <View style={styles.trackInfoBox}>
              <Image
                source={
                  typeof track.cover === 'number' || (track.cover && track.cover.uri)
                    ? track.cover
                    : DEFAULT_FALLBACK_COVER
                }
                style={styles.miniCover}
              />
              <View style={styles.meta}>
                <Text style={[styles.trackTitle, { color: textColor }]} numberOfLines={1}>
                  {track.title}
                </Text>
                <Text style={[styles.trackArtist, { color: accentColor }]} numberOfLines={1}>
                  {track.artist}
                </Text>
              </View>
            </View>
          )}
        </View>

        {/* VISUALIZADOR DE LETRAS */}
        <ScrollView contentContainerStyle={styles.lyricsContent} showsVerticalScrollIndicator={false}>
          <View style={[styles.lyricsBox, { backgroundColor: cardColor, borderColor: getAlphaColor(accentColor, '33') }]}>
            <Text style={[styles.lyricLine, { color: textColor }]}>🎵 {track ? track.title : 'Canción'}</Text>
            <Text style={[styles.lyricLineSub, { color: accentColor }]}>👤 {track ? track.artist : 'Artista'}</Text>
            <View style={[styles.divider, { backgroundColor: getAlphaColor(accentColor, '44') }]} />

            <Text style={[styles.lyricsText, { color: textColor }]}>
              {`♪ (Visualizador de Letras Sincronizadas)

[Verso 1]
Escuchando el ritmo neón en mi teléfono
Cada nota resuena en la oscuridad del espacio
Con ecualizador neón y visualizador estelar

[Estribillo]
Custom Music Player en pantalla completa
Diseño azabache con brillo neón personalizado
La música no se detiene nunca

[Verso 2]
Escaneando miles de canciones sin congelamiento
Biblioteca rápida organizada a 60 cuadros por segundo
Tu reproductor preferido en Android`}
            </Text>
          </View>
        </ScrollView>
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
  trackInfoBox: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    marginTop: 4,
  },
  miniCover: {
    width: 36,
    height: 36,
    borderRadius: 8,
  },
  meta: {
    flex: 1,
  },
  trackTitle: {
    fontSize: 13,
    fontWeight: 'bold',
  },
  trackArtist: {
    fontSize: 11,
    fontWeight: '600',
  },
  lyricsContent: {
    padding: 16,
    paddingBottom: 40,
  },
  lyricsBox: {
    padding: 20,
    borderRadius: 20,
    borderWidth: 1.5,
    alignItems: 'center',
  },
  lyricLine: {
    fontSize: 16,
    fontWeight: '800',
    textAlign: 'center',
  },
  lyricLineSub: {
    fontSize: 13,
    fontWeight: '600',
    marginTop: 4,
    textAlign: 'center',
  },
  divider: {
    width: '80%',
    height: 1,
    marginVertical: 16,
  },
  lyricsText: {
    fontSize: 14,
    lineHeight: 26,
    textAlign: 'center',
    fontStyle: 'italic',
  },
});

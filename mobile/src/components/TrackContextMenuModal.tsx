import React, { useState } from 'react';
import {
  Modal,
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Image,
  ScrollView,
  Alert,
} from 'react-native';
import { useNeonTheme } from '../context/ThemeContext';
import { getAlphaColor } from '../utils/colorUtils';
import { Track } from './LibraryModal';

const DEFAULT_FALLBACK_COVER = require('../../assets/images/record_player.jpeg');

interface TrackContextMenuModalProps {
  visible: boolean;
  track: Track | null;
  onClose: () => void;
  onToggleFavorite: (track: Track) => void;
  onDeleteTrack: (track: Track) => void;
  onShowArtist: (artist: string) => void;
  onShowAlbum: (album: string) => void;
  onOpenFolder: () => void;
  onShowLyrics: (track: Track) => void;
  onChangeCover?: () => void;
}

export const TrackContextMenuModal: React.FC<TrackContextMenuModalProps> = ({
  visible,
  track,
  onClose,
  onToggleFavorite,
  onDeleteTrack,
  onShowArtist,
  onShowAlbum,
  onOpenFolder,
  onShowLyrics,
  onChangeCover,
}) => {
  const { accentColor, textColor, subtextColor, cardColor, surfaceColor } = useNeonTheme();
  const [showTagInfo, setShowTagInfo] = useState(false);

  if (!track) return null;

  const handleConfirmDelete = () => {
    Alert.alert(
      'Eliminar Canción',
      `¿Deseas eliminar "${track.title}" de tu biblioteca?`,
      [
        { text: 'Cancelar', style: 'cancel' },
        {
          text: 'Eliminar',
          style: 'destructive',
          onPress: () => {
            onDeleteTrack(track);
            onClose();
          },
        },
      ]
    );
  };

  return (
    <Modal visible={visible} animationType="fade" transparent={true} onRequestClose={onClose}>
      <TouchableOpacity style={styles.backdrop} activeOpacity={1} onPress={onClose}>
        <View
          style={[
            styles.menuCard,
            { backgroundColor: cardColor, borderColor: getAlphaColor(accentColor, '77') },
          ]}
          onStartShouldSetResponder={() => true}
        >
          {/* CABECERA CON INFORMACIÓN DE LA CANCIÓN */}
          <View style={[styles.headerBox, { borderColor: getAlphaColor(accentColor, '33') }]}>
            <Image
              source={
                typeof track.cover === 'number' || (track.cover && track.cover.uri)
                  ? track.cover
                  : DEFAULT_FALLBACK_COVER
              }
              style={styles.trackThumb}
            />
            <View style={styles.trackMetaBox}>
              <Text style={[styles.trackTitle, { color: textColor }]} numberOfLines={1}>
                {track.title}
              </Text>
              <Text style={[styles.trackArtist, { color: accentColor }]} numberOfLines={1}>
                {track.artist} • {track.album}
              </Text>
            </View>
            <TouchableOpacity onPress={onClose} style={styles.closeBtn}>
              <Text style={[styles.closeBtnText, { color: subtextColor }]}>✕</Text>
            </TouchableOpacity>
          </View>

          {/* VISTA DE ETIQUETAS E INFORMACIÓN ID3 SI SE ACTIVA */}
          {showTagInfo ? (
            <View style={styles.tagInfoBox}>
              <Text style={[styles.tagInfoTitle, { color: accentColor }]}>🏷️ ETIQUETAS E INFORMACIÓN ID3</Text>
              <Text style={[styles.tagItem, { color: textColor }]}>• Título: <Text style={{ color: subtextColor }}>{track.title}</Text></Text>
              <Text style={[styles.tagItem, { color: textColor }]}>• Artista: <Text style={{ color: subtextColor }}>{track.artist}</Text></Text>
              <Text style={[styles.tagItem, { color: textColor }]}>• Álbum: <Text style={{ color: subtextColor }}>{track.album}</Text></Text>
              <Text style={[styles.tagItem, { color: textColor }]}>• Duración: <Text style={{ color: subtextColor }}>{Math.floor(track.durationSeconds / 60)}:{(track.durationSeconds % 60 < 10 ? '0' : '') + Math.floor(track.durationSeconds % 60)}</Text></Text>
              <Text style={[styles.tagItem, { color: textColor }]} numberOfLines={2}>• Ruta de Archivo: <Text style={{ color: subtextColor, fontSize: 10 }}>{track.audioUrl}</Text></Text>

              <TouchableOpacity
                style={[styles.backBtn, { backgroundColor: getAlphaColor(accentColor, '22'), borderColor: accentColor }]}
                onPress={() => setShowTagInfo(false)}
              >
                <Text style={[styles.backBtnText, { color: accentColor }]}>← Volver al Menú</Text>
              </TouchableOpacity>
            </View>
          ) : (
            /* LISTA DE ACCIONES DEL MENÚ CONTEXTUAL ESTILO POWERAMP */
            <ScrollView contentContainerStyle={styles.actionsList} showsVerticalScrollIndicator={false}>
              {/* FAVORITO */}
              <TouchableOpacity
                style={styles.actionRow}
                onPress={() => {
                  onToggleFavorite(track);
                  onClose();
                }}
              >
                <Text style={styles.actionIcon}>{track.isFavorite ? '❤️' : '🤍'}</Text>
                <Text style={[styles.actionLabel, { color: textColor }]}>
                  {track.isFavorite ? 'Quitar de Favoritos' : 'Agregar a Favoritos'}
                </Text>
              </TouchableOpacity>

              {/* VER LETRAS */}
              <TouchableOpacity
                style={styles.actionRow}
                onPress={() => {
                  onShowLyrics(track);
                  onClose();
                }}
              >
                <Text style={styles.actionIcon}>📝</Text>
                <Text style={[styles.actionLabel, { color: textColor }]}>Ver Letras</Text>
              </TouchableOpacity>

              {/* INFORMACIÓN ID3 */}
              <TouchableOpacity style={styles.actionRow} onPress={() => setShowTagInfo(true)}>
                <Text style={styles.actionIcon}>🏷️</Text>
                <Text style={[styles.actionLabel, { color: textColor }]}>Información y Etiquetas ID3</Text>
              </TouchableOpacity>

              {/* CAMBIAR CARÁTULA */}
              {onChangeCover && (
                <TouchableOpacity
                  style={styles.actionRow}
                  onPress={() => {
                    onChangeCover();
                    onClose();
                  }}
                >
                  <Text style={styles.actionIcon}>🖼️</Text>
                  <Text style={[styles.actionLabel, { color: textColor }]}>Personalizar Carátula</Text>
                </TouchableOpacity>
              )}

              {/* CANCIONES DEL ARTISTA */}
              <TouchableOpacity
                style={styles.actionRow}
                onPress={() => {
                  onShowArtist(track.artist);
                  onClose();
                }}
              >
                <Text style={styles.actionIcon}>👤</Text>
                <Text style={[styles.actionLabel, { color: textColor }]}>Ver canciones de {track.artist}</Text>
              </TouchableOpacity>

              {/* CANCIONES DEL ÁLBUM */}
              <TouchableOpacity
                style={styles.actionRow}
                onPress={() => {
                  onShowAlbum(track.album);
                  onClose();
                }}
              >
                <Text style={styles.actionIcon}>💿</Text>
                <Text style={[styles.actionLabel, { color: textColor }]}>Ver álbum {track.album}</Text>
              </TouchableOpacity>

              {/* ABRIR CARPETA */}
              <TouchableOpacity
                style={styles.actionRow}
                onPress={() => {
                  onOpenFolder();
                  onClose();
                }}
              >
                <Text style={styles.actionIcon}>📁</Text>
                <Text style={[styles.actionLabel, { color: textColor }]}>Abrir carpeta de esta canción</Text>
              </TouchableOpacity>

              {/* ELIMINAR CANCIÓN */}
              <TouchableOpacity style={styles.actionRow} onPress={handleConfirmDelete}>
                <Text style={styles.actionIcon}>🗑️</Text>
                <Text style={[styles.actionLabel, { color: '#FF3B30', fontWeight: 'bold' }]}>Eliminar de la biblioteca</Text>
              </TouchableOpacity>
            </ScrollView>
          )}
        </View>
      </TouchableOpacity>
    </Modal>
  );
};

const styles = StyleSheet.create({
  backdrop: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.75)',
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 20,
  },
  menuCard: {
    width: '100%',
    maxWidth: 340,
    borderRadius: 22,
    borderWidth: 1.5,
    padding: 16,
    maxHeight: '80%',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.6,
    shadowRadius: 12,
    elevation: 10,
  },
  headerBox: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingBottom: 12,
    borderBottomWidth: 1,
    marginBottom: 10,
  },
  trackThumb: {
    width: 44,
    height: 44,
    borderRadius: 10,
  },
  trackMetaBox: {
    flex: 1,
    marginLeft: 12,
    marginRight: 8,
  },
  trackTitle: {
    fontSize: 14,
    fontWeight: 'bold',
  },
  trackArtist: {
    fontSize: 11,
    marginTop: 2,
    fontWeight: '600',
  },
  closeBtn: {
    padding: 4,
  },
  closeBtnText: {
    fontSize: 18,
    fontWeight: 'bold',
  },
  actionsList: {
    paddingVertical: 4,
  },
  actionRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 10,
    paddingHorizontal: 8,
    borderRadius: 12,
    gap: 12,
  },
  actionIcon: {
    fontSize: 18,
    width: 26,
    textAlign: 'center',
  },
  actionLabel: {
    fontSize: 13,
    fontWeight: '600',
  },
  tagInfoBox: {
    paddingVertical: 8,
    gap: 8,
  },
  tagInfoTitle: {
    fontSize: 13,
    fontWeight: '900',
    marginBottom: 4,
    letterSpacing: 0.8,
  },
  tagItem: {
    fontSize: 12,
    fontWeight: 'bold',
  },
  backBtn: {
    paddingVertical: 8,
    borderRadius: 12,
    borderWidth: 1,
    alignItems: 'center',
    marginTop: 10,
  },
  backBtnText: {
    fontSize: 12,
    fontWeight: 'bold',
  },
});

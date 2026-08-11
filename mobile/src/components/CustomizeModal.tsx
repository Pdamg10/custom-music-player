import React, { useState } from 'react';
import {
  Modal,
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  Image,
} from 'react-native';
import ColorPicker, { Panel1, HueSlider, OpacitySlider, PreviewText } from 'reanimated-color-picker';
import { useNeonTheme, PRESET_NEON_THEMES } from '../context/ThemeContext';

interface CustomizeModalProps {
  visible: boolean;
  onClose: () => void;
}

export const CustomizeModal: React.FC<CustomizeModalProps> = ({ visible, onClose }) => {
  const {
    backgroundColor,
    cardColor,
    textColor,
    subtextColor,
    accentColor,
    activeThemeId,
    artMode,
    customCoverUri,
    setPresetTheme,
    setCustomAccentColor,
    setArtMode,
    pickCustomCoverImage,
    clearCustomCoverImage,
  } = useNeonTheme();

  const [showPicker, setShowPicker] = useState(false);

  const onSelectColor = ({ hex }: { hex: string }) => {
    setCustomAccentColor(hex);
  };

  return (
    <Modal visible={visible} animationType="slide" transparent={true} onRequestClose={onClose}>
      <View style={styles.modalOverlay}>
        <View style={[styles.modalCard, { backgroundColor: '#0D0D11', borderColor: accentColor }]}>
          
          {/* HEADER DEL MODAL */}
          <View style={styles.modalHeaderRow}>
            <Text style={[styles.modalTitleText, { color: textColor }]}>🎨 PERSONALIZACIÓN NEÓN</Text>
            <TouchableOpacity onPress={onClose} style={styles.closeBtn}>
              <Text style={[styles.closeBtnText, { color: textColor }]}>✕</Text>
            </TouchableOpacity>
          </View>

          <ScrollView contentContainerStyle={styles.scrollBody} showsVerticalScrollIndicator={false}>
            
            {/* SECCIÓN 1: TEMAS NEÓN PREDEFINIDOS */}
            <Text style={[styles.sectionLabel, { color: subtextColor }]}>TEMAS NEÓN PREDEFINIDOS</Text>
            <View style={styles.swatchesRow}>
              {PRESET_NEON_THEMES.map((theme) => {
                const isSelected = activeThemeId === theme.id;
                return (
                  <TouchableOpacity
                    key={theme.id}
                    style={[
                      styles.swatchCircle,
                      { backgroundColor: theme.accentColor },
                      isSelected && {
                        borderColor: '#FFFFFF',
                        borderWidth: 3,
                        shadowColor: theme.accentColor,
                        shadowOpacity: 0.9,
                        shadowRadius: 10,
                        elevation: 10,
                        transform: [{ scale: 1.1 }],
                      },
                    ]}
                    onPress={() => {
                      setShowPicker(false);
                      setPresetTheme(theme.id);
                    }}
                  >
                    {isSelected && <Text style={styles.checkMark}>✓</Text>}
                  </TouchableOpacity>
                );
              })}
            </View>

            {/* SECCIÓN 2: COLOR PERSONALIZADO */}
            <View style={styles.customColorHeaderRow}>
              <Text style={[styles.sectionLabel, { color: subtextColor }]}>COLOR DE ACENTO LIBRE</Text>
              <TouchableOpacity
                style={[
                  styles.togglePickerBtn,
                  { borderColor: accentColor },
                  activeThemeId === 'custom' && { backgroundColor: accentColor + '33' },
                ]}
                onPress={() => setShowPicker(!showPicker)}
              >
                <Text style={[styles.togglePickerText, { color: accentColor }]}>
                  {showPicker ? 'Ocultar Selector' : '🎨 Abrir Color Picker'}
                </Text>
              </TouchableOpacity>
            </View>

            {showPicker && (
              <View style={[styles.pickerContainer, { backgroundColor: cardColor }]}>
                <ColorPicker
                  style={styles.pickerStyle}
                  value={accentColor}
                  onComplete={onSelectColor}
                >
                  <Panel1 style={styles.panelStyle} />
                  <HueSlider style={styles.sliderStyle} />
                  <OpacitySlider style={styles.sliderStyle} />
                  <PreviewText style={{ color: textColor, textAlign: 'center', marginTop: 8 }} />
                </ColorPicker>
              </View>
            )}

            {/* SECCIÓN 3: MODO DE CARÁTULA DEL ÁLBUM */}
            <Text style={[styles.sectionLabel, { color: subtextColor, marginTop: 18 }]}>
              MODO DE CARÁTULA DE ÁLBUM
            </Text>

            <View style={styles.artModeSegmentRow}>
              <TouchableOpacity
                style={[
                  styles.segmentBtn,
                  artMode === 'auto' && { backgroundColor: accentColor, borderColor: accentColor },
                ]}
                onPress={() => setArtMode('auto')}
              >
                <Text
                  style={[
                    styles.segmentText,
                    { color: artMode === 'auto' ? '#000000' : textColor },
                  ]}
                >
                  🎵 Automático (Canción)
                </Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={[
                  styles.segmentBtn,
                  artMode === 'custom' && { backgroundColor: accentColor, borderColor: accentColor },
                ]}
                onPress={() => setArtMode('custom')}
              >
                <Text
                  style={[
                    styles.segmentText,
                    { color: artMode === 'custom' ? '#000000' : textColor },
                  ]}
                >
                  🖼️ Fijo / Decorativo
                </Text>
              </TouchableOpacity>
            </View>

            {artMode === 'custom' && (
              <View style={[styles.customArtBox, { backgroundColor: cardColor, borderColor: accentColor + '44' }]}>
                {customCoverUri ? (
                  <View style={styles.customPreviewRow}>
                    <Image source={{ uri: customCoverUri }} style={styles.customPreviewThumb} />
                    <View style={styles.customPreviewMeta}>
                      <Text style={[styles.customPreviewTitle, { color: textColor }]}>Imagen Seleccionada</Text>
                      <TouchableOpacity onPress={clearCustomCoverImage} style={styles.removeImageBtn}>
                        <Text style={styles.removeImageText}>Quitar Imagen</Text>
                      </TouchableOpacity>
                    </View>
                  </View>
                ) : (
                  <TouchableOpacity style={[styles.pickGalleryBtn, { borderColor: accentColor }]} onPress={pickCustomCoverImage}>
                    <Text style={[styles.pickGalleryText, { color: accentColor }]}>
                      📷 Seleccionar Foto de la Galería
                    </Text>
                  </TouchableOpacity>
                )}
              </View>
            )}

          </ScrollView>

          {/* BOTÓN DE GUARDAR Y APLICAR */}
          <TouchableOpacity
            style={[styles.saveBtn, { backgroundColor: accentColor }]}
            onPress={onClose}
          >
            <Text style={styles.saveBtnText}>APLICAR Y CERRAR</Text>
          </TouchableOpacity>

        </View>
      </View>
    </Modal>
  );
};

const styles = StyleSheet.create({
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.88)',
    justifyContent: 'flex-end',
  },
  modalCard: {
    width: '100%',
    maxHeight: '88%',
    borderTopLeftRadius: 28,
    borderTopRightRadius: 28,
    borderWidth: 1.5,
    borderBottomWidth: 0,
    paddingHorizontal: 20,
    paddingTop: 18,
    paddingBottom: 30,
  },
  modalHeaderRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  modalTitleText: {
    fontSize: 16,
    fontWeight: '900',
    letterSpacing: 1,
  },
  closeBtn: {
    padding: 6,
  },
  closeBtnText: {
    fontSize: 20,
    fontWeight: 'bold',
  },
  scrollBody: {
    paddingBottom: 16,
  },
  sectionLabel: {
    fontSize: 11,
    fontWeight: 'bold',
    letterSpacing: 1.2,
    marginBottom: 10,
  },
  swatchesRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 20,
    paddingHorizontal: 4,
  },
  swatchCircle: {
    width: 44,
    height: 44,
    borderRadius: 22,
    justifyContent: 'center',
    alignItems: 'center',
  },
  checkMark: {
    color: '#000000',
    fontSize: 18,
    fontWeight: '900',
  },
  customColorHeaderRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 10,
  },
  togglePickerBtn: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 12,
    borderWidth: 1,
  },
  togglePickerText: {
    fontSize: 11,
    fontWeight: 'bold',
  },
  pickerContainer: {
    width: '100%',
    padding: 14,
    borderRadius: 16,
    marginBottom: 16,
    alignItems: 'center',
  },
  pickerStyle: {
    width: '100%',
    gap: 12,
  },
  panelStyle: {
    height: 140,
    borderRadius: 12,
  },
  sliderStyle: {
    height: 28,
    borderRadius: 14,
  },
  artModeSegmentRow: {
    flexDirection: 'row',
    gap: 10,
    marginBottom: 12,
  },
  segmentBtn: {
    flex: 1,
    paddingVertical: 10,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: '#333344',
    alignItems: 'center',
  },
  segmentText: {
    fontSize: 12,
    fontWeight: 'bold',
  },
  customArtBox: {
    width: '100%',
    padding: 12,
    borderRadius: 14,
    borderWidth: 1,
    marginTop: 4,
  },
  customPreviewRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  customPreviewThumb: {
    width: 50,
    height: 50,
    borderRadius: 10,
  },
  customPreviewMeta: {
    flex: 1,
  },
  customPreviewTitle: {
    fontSize: 12,
    fontWeight: 'bold',
    marginBottom: 4,
  },
  removeImageBtn: {
    alignSelf: 'flex-start',
  },
  removeImageText: {
    color: '#FF3B30',
    fontSize: 11,
    fontWeight: 'bold',
  },
  pickGalleryBtn: {
    paddingVertical: 12,
    borderRadius: 12,
    borderWidth: 1.5,
    borderStyle: 'dashed',
    alignItems: 'center',
  },
  pickGalleryText: {
    fontSize: 12,
    fontWeight: 'bold',
  },
  saveBtn: {
    width: '100%',
    paddingVertical: 14,
    borderRadius: 16,
    alignItems: 'center',
    marginTop: 10,
  },
  saveBtnText: {
    color: '#000000',
    fontSize: 14,
    fontWeight: '900',
    letterSpacing: 1,
  },
});

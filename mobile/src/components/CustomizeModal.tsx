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
import { useNeonTheme, PRESET_NEON_THEMES } from '../context/ThemeContext';
import { getAlphaColor } from '../utils/colorUtils';
import { PureJSNeonColorPicker } from './PureJSNeonColorPicker';

interface CustomizeModalProps {
  visible: boolean;
  onClose: () => void;
}

const PRESET_GRADIENTS: { id: string; name: string; colors: [string, string] }[] = [
  { id: 'g_red', name: '🔴 STRAWBERRY Neón', colors: ['#44000F', '#0A0A0A'] },
  { id: 'g_cyan', name: '🔵 Ciber Cán', colors: ['#003B46', '#0A0A0A'] },
  { id: 'g_purple', name: '🟣 Violeta Lila', colors: ['#32004D', '#0A0A0A'] },
  { id: 'g_green', name: '🟢 Verde Esmeralda', colors: ['#003D20', '#0A0A0A'] },
  { id: 'g_gold', name: '🟡 Dorado Neón', colors: ['#423600', '#0A0A0A'] },
  { id: 'g_pink', name: '💗 Rosa Neón', colors: ['#470043', '#0A0A0A'] },
];

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
    backgroundMode,
    customBgUri,
    gradientColors,
    setPresetTheme,
    setCustomAccentColor,
    setArtMode,
    setBackgroundMode,
    setGradientColors,
    pickCustomCoverImage,
    clearCustomCoverImage,
    pickCustomBgImage,
    clearCustomBgImage,
  } = useNeonTheme();

  const [showPicker, setShowPicker] = useState(false);

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

            {/* SECCIÓN 2: COLOR PERSONALIZADO EN PURE JS (CERO CRASHEOS) */}
            <View style={styles.customColorHeaderRow}>
              <Text style={[styles.sectionLabel, { color: subtextColor }]}>COLOR DE ACENTO LIBRE</Text>
              <TouchableOpacity
                style={[
                  styles.togglePickerBtn,
                  { borderColor: accentColor },
                  activeThemeId === 'custom' && { backgroundColor: getAlphaColor(accentColor, '33') },
                ]}
                onPress={() => setShowPicker(!showPicker)}
              >
                <Text style={[styles.togglePickerText, { color: accentColor }]}>
                  {showPicker ? 'Ocultar Selector' : '🎨 Selector de Color'}
                </Text>
              </TouchableOpacity>
            </View>

            {showPicker && (
              <PureJSNeonColorPicker
                initialColor={accentColor}
                onColorChange={(hex) => setCustomAccentColor(hex)}
                textColor={textColor}
                subtextColor={subtextColor}
                cardColor={cardColor}
              />
            )}

            {/* SECCIÓN 3: MODO DE FONDO (SÓLIDO VS DEGRADADO NEÓN) */}
            <Text style={[styles.sectionLabel, { color: subtextColor, marginTop: 18 }]}>
              ESTILO DE FONDO DE PANTALLA
            </Text>

            <View style={styles.artModeSegmentRow}>
              <TouchableOpacity
                style={[
                  styles.segmentBtn,
                  backgroundMode === 'solid' && { backgroundColor: accentColor, borderColor: accentColor },
                ]}
                onPress={() => setBackgroundMode('solid')}
              >
                <Text style={[styles.segmentText, { color: backgroundMode === 'solid' ? '#000000' : textColor }]}>
                  🖤 Azabache Sólido
                </Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={[
                  styles.segmentBtn,
                  backgroundMode === 'gradient' && { backgroundColor: accentColor, borderColor: accentColor },
                ]}
                onPress={() => setBackgroundMode('gradient')}
              >
                <Text style={[styles.segmentText, { color: backgroundMode === 'gradient' ? '#000000' : textColor }]}>
                  🌈 Tema Degradado
                </Text>
              </TouchableOpacity>
            </View>

            {/* PRESETS DE DEGRADADOS */}
            {backgroundMode === 'gradient' && (
              <View style={styles.gradientsBox}>
                <Text style={[styles.subLabel, { color: subtextColor }]}>PALETAS DE DEGRADADO NEÓN:</Text>
                <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.gradientScrollRow}>
                  {PRESET_GRADIENTS.map((g) => {
                    const isSelected = gradientColors[0] === g.colors[0];
                    return (
                      <TouchableOpacity
                        key={g.id}
                        style={[
                          styles.gradientBadge,
                          { borderColor: isSelected ? accentColor : '#333344', backgroundColor: g.colors[0] },
                        ]}
                        onPress={() => setGradientColors(g.colors)}
                      >
                        <Text style={[styles.gradientBadgeText, { color: textColor }]}>{g.name}</Text>
                      </TouchableOpacity>
                    );
                  })}
                </ScrollView>
              </View>
            )}

            {/* SECCIÓN 4: IMAGEN DE FONDO DE PANTALLA PERSONALIZADA (WALLPAPER) */}
            <Text style={[styles.sectionLabel, { color: subtextColor, marginTop: 18 }]}>
              IMAGEN DE FONDO DE PANTALLA (WALLPAPER)
            </Text>

            <View style={[styles.customArtBox, { backgroundColor: cardColor, borderColor: getAlphaColor(accentColor, '44') }]}>
              {customBgUri ? (
                <View style={styles.customPreviewRow}>
                  <Image source={{ uri: customBgUri }} style={styles.customPreviewThumb} />
                  <View style={styles.customPreviewMeta}>
                    <Text style={[styles.customPreviewTitle, { color: textColor }]}>Fondo Personalizado Activo</Text>
                    <TouchableOpacity onPress={clearCustomBgImage} style={styles.removeImageBtn}>
                      <Text style={styles.removeImageText}>Quitar Fondo</Text>
                    </TouchableOpacity>
                  </View>
                </View>
              ) : (
                <TouchableOpacity style={[styles.pickGalleryBtn, { borderColor: accentColor }]} onPress={pickCustomBgImage}>
                  <Text style={[styles.pickGalleryText, { color: accentColor }]}>
                    🌄 Cambiar Fondo desde la Galería
                  </Text>
                </TouchableOpacity>
              )}
            </View>

            {/* SECCIÓN 5: MODO DE CARÁTULA DEL ÁLBUM */}
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
                <Text style={[styles.segmentText, { color: artMode === 'auto' ? '#000000' : textColor }]}>
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
                <Text style={[styles.segmentText, { color: artMode === 'custom' ? '#000000' : textColor }]}>
                  🖼️ Fijo / Decorativo
                </Text>
              </TouchableOpacity>
            </View>

            {artMode === 'custom' && (
              <View style={[styles.customArtBox, { backgroundColor: cardColor, borderColor: getAlphaColor(accentColor, '44') }]}>
                {customCoverUri ? (
                  <View style={styles.customPreviewRow}>
                    <Image source={{ uri: customCoverUri }} style={styles.customPreviewThumb} />
                    <View style={styles.customPreviewMeta}>
                      <Text style={[styles.customPreviewTitle, { color: textColor }]}>Carátula Fija Seleccionada</Text>
                      <TouchableOpacity onPress={clearCustomCoverImage} style={styles.removeImageBtn}>
                        <Text style={styles.removeImageText}>Quitar Carátula</Text>
                      </TouchableOpacity>
                    </View>
                  </View>
                ) : (
                  <TouchableOpacity style={[styles.pickGalleryBtn, { borderColor: accentColor }]} onPress={pickCustomCoverImage}>
                    <Text style={[styles.pickGalleryText, { color: accentColor }]}>
                      📷 Seleccionar Foto para Carátula
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
    maxHeight: '90%',
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
  subLabel: {
    fontSize: 10,
    fontWeight: 'bold',
    marginBottom: 6,
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
  gradientsBox: {
    marginBottom: 12,
  },
  gradientScrollRow: {
    flexDirection: 'row',
    gap: 8,
    paddingVertical: 4,
  },
  gradientBadge: {
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 12,
    borderWidth: 1,
  },
  gradientBadgeText: {
    fontSize: 11,
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

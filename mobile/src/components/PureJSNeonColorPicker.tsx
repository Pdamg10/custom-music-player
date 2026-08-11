import React, { useState } from 'react';
import {
  StyleSheet,
  View,
  Text,
  TouchableOpacity,
  TextInput,
  ScrollView,
} from 'react-native';
import { normalizeHexColor, getAlphaColor } from '../utils/colorUtils';

interface PureJSNeonColorPickerProps {
  initialColor: string;
  onColorChange: (hex: string) => void;
  textColor: string;
  subtextColor: string;
  cardColor: string;
}

// Muestra de 18 colores Neón libres de la paleta espectral
const COLOR_SPECTRUM_PALETTE = [
  '#FF073A', '#FF355E', '#FF6037', '#FF9933', '#FFCC00', '#FFFF66',
  '#CCFF00', '#66FF66', '#50BFE6', '#00F0FF', '#0099FF', '#0066FF',
  '#6600FF', '#B026FF', '#FF00FF', '#FF10F0', '#FF007F', '#FFFFFF',
];

export const PureJSNeonColorPicker: React.FC<PureJSNeonColorPickerProps> = ({
  initialColor,
  onColorChange,
  textColor,
  subtextColor,
  cardColor,
}) => {
  const [selectedHex, setSelectedHex] = useState(normalizeHexColor(initialColor));
  const [hexInputText, setHexInputText] = useState(normalizeHexColor(initialColor));

  const handleSelect = (hex: string) => {
    const clean = normalizeHexColor(hex);
    setSelectedHex(clean);
    setHexInputText(clean);
    onColorChange(clean);
  };

  const handleTextChange = (text: string) => {
    setHexInputText(text);
    if (/^#?[0-9A-Fa-f]{6}$/.test(text.trim())) {
      const clean = normalizeHexColor(text);
      setSelectedHex(clean);
      onColorChange(clean);
    }
  };

  return (
    <View style={[styles.container, { backgroundColor: cardColor }]}>
      {/* VISTA PREVIA Y ENTRADA DE CÓDIGO HEXADECIMAL */}
      <View style={styles.previewHeaderRow}>
        <View
          style={[
            styles.previewBox,
            {
              backgroundColor: selectedHex,
              borderColor: textColor,
              shadowColor: selectedHex,
            },
          ]}
        >
          <Text style={styles.previewCheckMark}>✨</Text>
        </View>

        <View style={styles.hexInputWrapper}>
          <Text style={[styles.inputLabel, { color: subtextColor }]}>CÓDIGO HEX (NEÓN):</Text>
          <View style={styles.hexInputRow}>
            <Text style={[styles.hashSymbol, { color: selectedHex }]}>#</Text>
            <TextInput
              style={[styles.textInput, { color: textColor, borderColor: getAlphaColor(selectedHex, '66') }]}
              value={hexInputText.replace('#', '')}
              onChangeText={(txt) => handleTextChange(`#${txt}`)}
              placeholder="FF073A"
              placeholderTextColor={subtextColor}
              maxLength={6}
              autoCapitalize="characters"
            />
          </View>
        </View>
      </View>

      {/* PALETA DE SELECCIÓN RÁPIDA DE MATICES ESPECTRALES */}
      <Text style={[styles.sectionTitle, { color: subtextColor }]}>ESPECTRO DE ACENTO NEÓN LIBRE:</Text>

      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.swatchGrid}>
        {COLOR_SPECTRUM_PALETTE.map((color) => {
          const isSelected = selectedHex.toUpperCase() === color.toUpperCase();
          return (
            <TouchableOpacity
              key={color}
              style={[
                styles.swatchCircle,
                { backgroundColor: color },
                isSelected && {
                  borderColor: '#FFFFFF',
                  borderWidth: 3,
                  transform: [{ scale: 1.15 }],
                  elevation: 6,
                },
              ]}
              onPress={() => handleSelect(color)}
            >
              {isSelected && <Text style={styles.checkText}>✓</Text>}
            </TouchableOpacity>
          );
        })}
      </ScrollView>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    width: '100%',
    padding: 14,
    borderRadius: 16,
    marginBottom: 16,
  },
  previewHeaderRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 14,
    gap: 14,
  },
  previewBox: {
    width: 48,
    height: 48,
    borderRadius: 24,
    borderWidth: 2,
    justifyContent: 'center',
    alignItems: 'center',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.8,
    shadowRadius: 10,
    elevation: 8,
  },
  previewCheckMark: {
    fontSize: 16,
  },
  hexInputWrapper: {
    flex: 1,
  },
  inputLabel: {
    fontSize: 10,
    fontWeight: 'bold',
    letterSpacing: 1,
    marginBottom: 4,
  },
  hexInputRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  hashSymbol: {
    fontSize: 16,
    fontWeight: '900',
    marginRight: 4,
  },
  textInput: {
    flex: 1,
    height: 38,
    borderRadius: 10,
    borderWidth: 1.5,
    paddingHorizontal: 10,
    fontSize: 14,
    fontWeight: 'bold',
    letterSpacing: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.4)',
  },
  sectionTitle: {
    fontSize: 10,
    fontWeight: 'bold',
    letterSpacing: 1,
    marginBottom: 8,
  },
  swatchGrid: {
    flexDirection: 'row',
    gap: 10,
    paddingVertical: 6,
    paddingHorizontal: 2,
  },
  swatchCircle: {
    width: 38,
    height: 38,
    borderRadius: 19,
    justifyContent: 'center',
    alignItems: 'center',
  },
  checkText: {
    color: '#000000',
    fontSize: 16,
    fontWeight: '900',
  },
});

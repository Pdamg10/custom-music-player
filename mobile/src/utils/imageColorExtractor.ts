import { getColors } from 'react-native-image-colors';
import { normalizeHexColor } from './colorUtils';

export interface ExtractedImageColors {
  dominant: string;
  vibrant: string;
  dark: string;
}

export async function extractColorsFromImageUri(imageUri: string): Promise<ExtractedImageColors | null> {
  try {
    if (!imageUri) return null;

    const result = await getColors(imageUri, {
      fallback: '#FF073A',
      cache: true,
      key: imageUri,
    });

    let dominant = '#FF073A';
    let vibrant = '#00F0FF';
    let dark = '#121216';

    if (result.platform === 'android') {
      dominant = result.dominant || result.vibrant || result.average || '#FF073A';
      vibrant = result.vibrant || result.lightVibrant || '#00F0FF';
      dark = result.darkVibrant || result.darkMuted || '#121216';
    } else if (result.platform === 'ios') {
      dominant = result.primary || '#FF073A';
      vibrant = result.secondary || '#00F0FF';
      dark = result.background || '#121216';
    } else {
      dominant = (result as any).dominant || '#FF073A';
      vibrant = (result as any).vibrant || '#00F0FF';
      dark = (result as any).darkVibrant || '#121216';
    }

    return {
      dominant: normalizeHexColor(dominant),
      vibrant: normalizeHexColor(vibrant),
      dark: normalizeHexColor(dark),
    };
  } catch (err) {
    console.warn('Extracción de color de imagen falló silenciosamente:', err);
    return null;
  }
}

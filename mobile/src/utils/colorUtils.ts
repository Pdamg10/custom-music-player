/**
 * Utilidades para manejo y conversión segura de colores Hex y RGBA en React Native.
 * Previene errores de parseo de color nativo como #RRGGBBAAAA (10 caracteres hex) que causan crasheos.
 */

/**
 * Normaliza cualquier string de color Hex a formato estándar de 6 dígitos (#RRGGBB).
 */
export function normalizeHexColor(color: string, defaultHex = '#FF073A'): string {
  if (!color || typeof color !== 'string') return defaultHex;
  let clean = color.trim().replace(/^#/, '');

  if (clean.length >= 6) {
    clean = clean.substring(0, 6);
    return `#${clean.toUpperCase()}`;
  }

  if (clean.length === 3) {
    const r = clean[0] + clean[0];
    const g = clean[1] + clean[1];
    const b = clean[2] + clean[2];
    return `#${(r + g + b).toUpperCase()}`;
  }

  return defaultHex;
}

/**
 * Retorna un color hex con transparencia segura de 8 dígitos (#RRGGBBAA).
 */
export function getAlphaColor(hexColor: string, alpha: string | number = 'FF'): string {
  const baseHex = normalizeHexColor(hexColor);
  
  if (typeof alpha === 'number') {
    const clamped = Math.max(0, Math.min(1, alpha));
    const alphaInt = Math.round(clamped * 255);
    const alphaHex = alphaInt.toString(16).padStart(2, '0').toUpperCase();
    return `${baseHex}${alphaHex}`;
  }

  let cleanAlpha = alpha.toString().trim().replace(/^#/, '');
  if (cleanAlpha.length === 1) {
    cleanAlpha = cleanAlpha + cleanAlpha;
  } else if (cleanAlpha.length > 2) {
    cleanAlpha = cleanAlpha.substring(0, 2);
  }

  return `${baseHex}${cleanAlpha.toUpperCase()}`;
}

/**
 * Oscurece un color Hex por una proporción especificada (amount entre 0 y 1).
 */
export function darkenColor(hexColor: string, amount = 0.6): string {
  const baseHex = normalizeHexColor(hexColor);
  let r = parseInt(baseHex.substring(1, 3), 16);
  let g = parseInt(baseHex.substring(3, 5), 16);
  let b = parseInt(baseHex.substring(5, 7), 16);

  r = Math.max(0, Math.floor(r * (1 - amount)));
  g = Math.max(0, Math.floor(g * (1 - amount)));
  b = Math.max(0, Math.floor(b * (1 - amount)));

  const rHex = r.toString(16).padStart(2, '0');
  const gHex = g.toString(16).padStart(2, '0');
  const bHex = b.toString(16).padStart(2, '0');

  return `#${rHex}${gHex}${bHex}`.toUpperCase();
}

/**
 * Genera automáticamente un par de 2 colores de degradado [inicio, fin] oscureciendo un acento neón.
 */
export function generateGradientFromHex(hexColor: string): [string, string] {
  const cleanHex = normalizeHexColor(hexColor);
  const darkStart = darkenColor(cleanHex, 0.65);
  const darkEnd = darkenColor(cleanHex, 0.92);
  return [darkStart, darkEnd];
}

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

  // Si viene de un picker con 8 dígitos (#RRGGBBAA), tomamos los primeros 6
  if (clean.length >= 6) {
    clean = clean.substring(0, 6);
    return `#${clean.toUpperCase()}`;
  }

  // Si es hex corto (#RGB)
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
 * @param hexColor Color base en hex (ej: "#FF073A")
 * @param alpha Hex de 2 caracteres (ej: "44", "AA") o ratio numérico (ej: 0.3)
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

import * as MediaLibrary from 'expo-media-library';
import { Track } from '../components/LibraryModal';

const DEFAULT_FALLBACK_COVER = require('../../assets/images/record_player.jpeg');

/**
 * Mapea un listado de MediaLibrary.Asset a objetos Track de la aplicación.
 * Reutiliza la misma lógica exacta para evitar duplicar código.
 */
export const mapAssetsToTracks = (assets: MediaLibrary.Asset[]): Track[] => {
  return assets
    .filter((asset) => (asset.duration || 0) >= 2) // Filtro flexible de canciones cortas
    .map((asset) => {
      const albumArtUri = `content://media/external/audio/media/${asset.id}/albumart`;
      return {
        id: asset.id,
        title: asset.filename.replace(/\.[^/.]+$/, ''),
        artist: 'Música en Teléfono',
        album: asset.albumId || 'Almacenamiento Interno',
        durationSeconds: Math.floor(asset.duration || 0),
        cover: { uri: albumArtUri },
        audioUrl: asset.uri,
      };
    });
};

/**
 * Obtiene la lista de álbumes/carpetas reales con archivos de audio del dispositivo.
 */
export const getDeviceMusicAlbums = async (): Promise<MediaLibrary.Album[]> => {
  try {
    const { status } = await MediaLibrary.requestPermissionsAsync();
    if (status !== 'granted') return [];

    const albums = await MediaLibrary.getAlbumsAsync();
    // Filtrar solo álbumes que tengan al menos 1 archivo
    return albums.filter((alb) => alb.assetCount > 0);
  } catch (err) {
    console.warn('Error al obtener álbumes/carpetas:', err);
    return [];
  }
};

/**
 * Carga paginada de canciones de una carpeta/álbum específica usando first y after.
 * Evita el bloqueo de I/O y congelamiento de pantalla en carpetas con +500 archivos.
 */
export const getTracksFromAlbumPaginated = async (
  albumId: string,
  onProgress?: (count: number) => void
): Promise<Track[]> => {
  try {
    const { status } = await MediaLibrary.requestPermissionsAsync();
    if (status !== 'granted') return [];

    let allTracks: Track[] = [];
    let cursor: string | undefined = undefined;
    let hasMore = true;

    while (hasMore) {
      const page = await MediaLibrary.getAssetsAsync({
        mediaType: 'audio',
        album: albumId,
        first: 500, // Carga paginada de a 500 canciones
        after: cursor,
        sortBy: [[MediaLibrary.SortBy.creationTime, false]],
      });

      if (page.assets && page.assets.length > 0) {
        const mappedBatch = mapAssetsToTracks(page.assets);
        allTracks = [...allTracks, ...mappedBatch];
        if (onProgress) onProgress(allTracks.length);

        cursor = page.endCursor;
        hasMore = Boolean(page.hasNextPage && cursor);
      } else {
        hasMore = false;
      }
    }

    return allTracks;
  } catch (err) {
    console.warn('Error en la carga paginada del álbum:', err);
    return [];
  }
};

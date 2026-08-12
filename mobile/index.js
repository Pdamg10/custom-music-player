import { registerRootComponent } from 'expo';
import { ExpoRoot } from 'expo-router';
import TrackPlayer from 'react-native-track-player';
import { PlaybackService } from './src/services/playbackService';

// Registrar el servicio de reproducción en segundo plano a nivel global de la app
TrackPlayer.registerPlaybackService(() => PlaybackService);

export function App() {
  const ctx = require.context('./src/app');
  return <ExpoRoot context={ctx} />;
}

registerRootComponent(App);

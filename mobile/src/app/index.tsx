import React from 'react';
import { StyleSheet, View, Text, ScrollView, TouchableOpacity } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { FloatingMusicPlayer } from '@/components/FloatingMusicPlayer';

export default function HomeScreen() {
  return (
    <SafeAreaView style={styles.safeArea}>
      <ScrollView contentContainerStyle={styles.container}>
        {/* Title Badge */}
        <View style={styles.badgeContainer}>
          <Text style={styles.badgeTitle}>🎧 CUSTOM MUSIC PLAYER</Text>
          <Text style={styles.badgeSubtitle}>EXPO REACT NATIVE EDITION</Text>
        </View>

        {/* Floating Player Component Preview */}
        <View style={styles.playerContainer}>
          <FloatingMusicPlayer />
        </View>

        {/* Expo Go Quick Guide */}
        <View style={styles.guideCard}>
          <Text style={styles.guideHeader}>📱 ¿Cómo probarlo en tu teléfono?</Text>
          
          <View style={styles.stepRow}>
            <Text style={styles.stepNumber}>1</Text>
            <Text style={styles.stepText}>
              Descarga la app <Text style={styles.highlight}>Expo Go</Text> desde Google Play Store o App Store.
            </Text>
          </View>

          <View style={styles.stepRow}>
            <Text style={styles.stepNumber}>2</Text>
            <Text style={styles.stepText}>
              En tu terminal dentro de la carpeta <Text style={styles.highlight}>mobile/</Text>, ejecuta:
            </Text>
          </View>
          
          <View style={styles.codeBlock}>
            <Text style={styles.codeText}>npx expo start</Text>
          </View>

          <View style={styles.stepRow}>
            <Text style={styles.stepNumber}>3</Text>
            <Text style={styles.stepText}>
              Escanea el código QR desde <Text style={styles.highlight}>Expo Go</Text> ¡y listo! Se abrirá la app en vivo en tu teléfono.
            </Text>
          </View>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: '#030305',
  },
  container: {
    padding: 20,
    alignItems: 'center',
    paddingBottom: 40,
  },
  badgeContainer: {
    alignItems: 'center',
    marginVertical: 16,
  },
  badgeTitle: {
    color: '#FFFFFF',
    fontSize: 22,
    fontWeight: 'bold',
    letterSpacing: 1,
  },
  badgeSubtitle: {
    color: '#FF1744',
    fontSize: 12,
    fontWeight: 'bold',
    marginTop: 4,
    letterSpacing: 2,
  },
  playerContainer: {
    marginVertical: 20,
  },
  guideCard: {
    width: '100%',
    maxWidth: 340,
    backgroundColor: '#0C0C12',
    borderRadius: 16,
    padding: 20,
    borderWidth: 1,
    borderColor: '#1E1E2A',
    marginTop: 10,
  },
  guideHeader: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: 'bold',
    marginBottom: 16,
  },
  stepRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    marginBottom: 12,
    gap: 10,
  },
  stepNumber: {
    color: '#FF1744',
    fontWeight: 'bold',
    fontSize: 14,
    backgroundColor: '#FF174415',
    width: 24,
    height: 24,
    borderRadius: 12,
    textAlign: 'center',
    lineHeight: 24,
  },
  stepText: {
    color: '#CCCCCC',
    fontSize: 13,
    flex: 1,
    lineHeight: 18,
  },
  highlight: {
    color: '#FF1744',
    fontWeight: 'bold',
  },
  codeBlock: {
    backgroundColor: '#050508',
    paddingVertical: 10,
    paddingHorizontal: 16,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#FF174444',
    marginVertical: 6,
    marginLeft: 34,
  },
  codeText: {
    color: '#00E5FF',
    fontFamily: 'Platform',
    fontSize: 14,
    fontWeight: 'bold',
  },
});

import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  Switch,
  Linking,
  SafeAreaView,
  StatusBar,
} from 'react-native';
import { useNeonTheme } from '@/context/ThemeContext';
import { getAlphaColor } from '@/utils/colorUtils';
import { CustomizeModal } from '@/components/CustomizeModal';

export default function SettingsScreen() {
  const { accentColor, textColor, subtextColor, cardColor, surfaceColor } = useNeonTheme();

  const [showCustomizeModal, setShowCustomizeModal] = useState(false);
  const [defaultShuffle, setDefaultShuffle] = useState(false);
  const [defaultRepeat, setDefaultRepeat] = useState(true);
  const [autoRescanOnLaunch, setAutoRescanOnLaunch] = useState(true);

  const handleOpenGitHubRepo = () => {
    Linking.openURL('https://github.com/Pdamg10/custom-music-player').catch((err) =>
      console.warn('Error abriendo enlace:', err)
    );
  };

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: '#0A0A0A' }]}>
      <StatusBar barStyle="light-content" backgroundColor="#0A0A0A" />

      {/* CABECERA SUPERIOR */}
      <View style={[styles.header, { borderColor: getAlphaColor(accentColor, '33') }]}>
        <Text style={[styles.headerTitle, { color: textColor }]}>⚙️ AJUSTES Y CONFIGURACIÓN</Text>
        <Text style={[styles.headerSubtitle, { color: subtextColor }]}>
          Personalización, comportamiento del reproductor e información
        </Text>
      </View>

      <ScrollView contentContainerStyle={styles.scrollBody} showsVerticalScrollIndicator={false}>
        
        {/* SECCIÓN 1: APARIENCIA Y TEMAS */}
        <Text style={[styles.sectionTitle, { color: accentColor }]}>🎨 SECCIÓN APARIENCIA</Text>

        <TouchableOpacity
          style={[styles.settingCard, { backgroundColor: cardColor, borderColor: getAlphaColor(accentColor, '33') }]}
          onPress={() => setShowCustomizeModal(true)}
          activeOpacity={0.8}
        >
          <Text style={styles.cardIcon}>🎨</Text>
          <View style={styles.cardMeta}>
            <Text style={[styles.cardTitle, { color: textColor }]}>Personalización Neón & Fondos</Text>
            <Text style={[styles.cardSub, { color: subtextColor }]}>
              Cambia el color de acento, paleta extraída, degradados y fondos
            </Text>
          </View>
          <Text style={[styles.arrowIcon, { color: accentColor }]}>➔</Text>
        </TouchableOpacity>

        {/* SECCIÓN 2: REPRODUCCIÓN Y COMPORTAMIENTO */}
        <Text style={[styles.sectionTitle, { color: accentColor, marginTop: 22 }]}>🎵 SECCIÓN REPRODUCCIÓN</Text>

        <View style={[styles.settingCard, { backgroundColor: cardColor, borderColor: getAlphaColor(accentColor, '33') }]}>
          <Text style={styles.cardIcon}>🔀</Text>
          <View style={styles.cardMeta}>
            <Text style={[styles.cardTitle, { color: textColor }]}>Modo Aleatorio por Defecto</Text>
            <Text style={[styles.cardSub, { color: subtextColor }]}>
              Iniciar reproducción en orden aleatorio
            </Text>
          </View>
          <Switch
            value={defaultShuffle}
            onValueChange={setDefaultShuffle}
            trackColor={{ false: '#333344', true: getAlphaColor(accentColor, '66') }}
            thumbColor={defaultShuffle ? accentColor : '#888899'}
          />
        </View>

        <View style={[styles.settingCard, { backgroundColor: cardColor, borderColor: getAlphaColor(accentColor, '33') }]}>
          <Text style={styles.cardIcon}>🔁</Text>
          <View style={styles.cardMeta}>
            <Text style={[styles.cardTitle, { color: textColor }]}>Repetición Automática</Text>
            <Text style={[styles.cardSub, { color: subtextColor }]}>
              Repetir playlist completa al terminar el último tema
            </Text>
          </View>
          <Switch
            value={defaultRepeat}
            onValueChange={setDefaultRepeat}
            trackColor={{ false: '#333344', true: getAlphaColor(accentColor, '66') }}
            thumbColor={defaultRepeat ? accentColor : '#888899'}
          />
        </View>

        <View style={[styles.settingCard, { backgroundColor: cardColor, borderColor: getAlphaColor(accentColor, '33') }]}>
          <Text style={styles.cardIcon}>🔄</Text>
          <View style={styles.cardMeta}>
            <Text style={[styles.cardTitle, { color: textColor }]}>Auto Escaneo al Iniciar</Text>
            <Text style={[styles.cardSub, { color: subtextColor }]}>
              Escanear archivos nuevos del almacenamiento al abrir la app
            </Text>
          </View>
          <Switch
            value={autoRescanOnLaunch}
            onValueChange={setAutoRescanOnLaunch}
            trackColor={{ false: '#333344', true: getAlphaColor(accentColor, '66') }}
            thumbColor={autoRescanOnLaunch ? accentColor : '#888899'}
          />
        </View>

        {/* SECCIÓN 3: ACERCA DE LA APLICACIÓN */}
        <Text style={[styles.sectionTitle, { color: accentColor, marginTop: 22 }]}>ℹ️ SECCIÓN ACERCA DE</Text>

        <View style={[styles.infoCard, { backgroundColor: cardColor, borderColor: getAlphaColor(accentColor, '33') }]}>
          <Text style={[styles.infoAppName, { color: textColor }]}>Custom Music Player</Text>
          <Text style={[styles.infoVersion, { color: accentColor }]}>Versión 1.0.0 (Expo SDK 54 / Android Debug)</Text>

          <Text style={[styles.infoCredits, { color: subtextColor }]}>
            Diseño negro azabache neón con motor de audio fluido. Desarrollado por el equipo de Google DeepMind Team para Android.
          </Text>

          <TouchableOpacity style={[styles.githubBtn, { borderColor: accentColor }]} onPress={handleOpenGitHubRepo}>
            <Text style={styles.githubIcon}>📦</Text>
            <Text style={[styles.githubBtnText, { color: accentColor }]}>Ver Código Fuente en GitHub</Text>
          </TouchableOpacity>
        </View>

      </ScrollView>

      {/* MODAL DE PERSONALIZACIÓN */}
      <CustomizeModal visible={showCustomizeModal} onClose={() => setShowCustomizeModal(false)} />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  header: {
    paddingTop: 40,
    paddingHorizontal: 20,
    paddingBottom: 14,
    borderBottomWidth: 1.5,
  },
  headerTitle: {
    fontSize: 16,
    fontWeight: '900',
    letterSpacing: 1.2,
  },
  headerSubtitle: {
    fontSize: 11,
    marginTop: 4,
  },
  scrollBody: {
    padding: 16,
    paddingBottom: 40,
  },
  sectionTitle: {
    fontSize: 11,
    fontWeight: '900',
    letterSpacing: 1.2,
    marginBottom: 10,
  },
  settingCard: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 14,
    borderRadius: 16,
    borderWidth: 1.5,
    marginBottom: 10,
  },
  cardIcon: {
    fontSize: 20,
    marginRight: 12,
  },
  cardMeta: {
    flex: 1,
  },
  cardTitle: {
    fontSize: 13,
    fontWeight: 'bold',
  },
  cardSub: {
    fontSize: 11,
    marginTop: 2,
  },
  arrowIcon: {
    fontSize: 16,
    paddingLeft: 6,
  },
  infoCard: {
    padding: 18,
    borderRadius: 18,
    borderWidth: 1.5,
    alignItems: 'center',
  },
  infoAppName: {
    fontSize: 16,
    fontWeight: '900',
    letterSpacing: 1,
  },
  infoVersion: {
    fontSize: 12,
    fontWeight: 'bold',
    marginTop: 4,
  },
  infoCredits: {
    fontSize: 11,
    textAlign: 'center',
    lineHeight: 18,
    marginVertical: 14,
  },
  githubBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: 14,
    borderWidth: 1.5,
  },
  githubIcon: {
    fontSize: 16,
  },
  githubBtnText: {
    fontSize: 12,
    fontWeight: 'bold',
  },
});

import React from 'react';
import { View, StyleSheet } from 'react-native';
import { CustomizeModal } from '@/components/CustomizeModal';

export default function SettingsScreen() {
  return (
    <View style={styles.container}>
      <CustomizeModal visible={true} onClose={() => {}} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0A0A0A',
  },
});

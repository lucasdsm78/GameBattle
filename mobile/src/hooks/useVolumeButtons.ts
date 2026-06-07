import { useEffect, useRef } from 'react';

// Capture des boutons volume physiques via react-native-volume-manager.
// ⚠️ Module natif : actif uniquement dans un build natif (APK / dev build), inactif dans Expo Go.
// On charge la lib via require + try/catch pour qu'Expo Go ne crashe pas si elle est absente.

type VolumeManagerLike = {
  setVolume: (value: number) => void | Promise<void>;
  showNativeVolumeUI?: (options: { enabled: boolean }) => void;
  addVolumeListener: (callback: (result: { volume: number }) => void) => { remove: () => void };
};

let VolumeManager: VolumeManagerLike | null = null;
try {
  // eslint-disable-next-line @typescript-eslint/no-var-requires
  VolumeManager = (require('react-native-volume-manager') as { VolumeManager: VolumeManagerLike }).VolumeManager;
} catch {
  VolumeManager = null;
}

// Volume de référence : après chaque appui on remet le volume au milieu pour qu'il reste
// toujours de la marge vers le haut ET vers le bas (sinon à 100%/0% l'appui ne déclenche rien).
const BASE_VOLUME = 0.5;
const THRESHOLD = 0.01;

type Options = {
  enabled: boolean;
  onVolumeUp: () => void;
  onVolumeDown: () => void;
};

export function useVolumeButtons({ enabled, onVolumeUp, onVolumeDown }: Options): boolean {
  const onUpRef = useRef(onVolumeUp);
  const onDownRef = useRef(onVolumeDown);
  onUpRef.current = onVolumeUp;
  onDownRef.current = onVolumeDown;

  useEffect(() => {
    if (!enabled || !VolumeManager?.addVolumeListener) {
      return;
    }
    const manager = VolumeManager;
    let isResetting = false;

    try {
      manager.showNativeVolumeUI?.({ enabled: false });
      manager.setVolume(BASE_VOLUME);
    } catch {
      // Module indisponible (Expo Go) — on n'active rien.
      return;
    }

    const subscription = manager.addVolumeListener((result) => {
      // Ignore l'évènement déclenché par notre propre remise à BASE_VOLUME.
      if (isResetting) {
        isResetting = false;
        return;
      }
      if (result.volume > BASE_VOLUME + THRESHOLD) {
        onUpRef.current();
      } else if (result.volume < BASE_VOLUME - THRESHOLD) {
        onDownRef.current();
      } else {
        return;
      }
      isResetting = true;
      try {
        manager.setVolume(BASE_VOLUME);
      } catch {
        // ignore
      }
    });

    return () => subscription?.remove?.();
  }, [enabled]);

  return VolumeManager !== null;
}

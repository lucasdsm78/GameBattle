const { withInfoPlist, withAndroidManifest } = require('expo/config-plugins');

function withGameBattleSpotifySdk(config) {
  config = withInfoPlist(config, (mod) => {
    mod.modResults.LSApplicationQueriesSchemes = Array.from(
      new Set([...(mod.modResults.LSApplicationQueriesSchemes || []), 'spotify'])
    );
    return mod;
  });

  config = withAndroidManifest(config, (mod) => {
    const manifest = mod.modResults.manifest;
    manifest.queries = manifest.queries || [];
    const hasSpotifyPackage = manifest.queries.some((query) => query.package?.[0]?.$?.['android:name'] === 'com.spotify.music');
    if (!hasSpotifyPackage) {
      manifest.queries.push({ package: [{ $: { 'android:name': 'com.spotify.music' } }] });
    }
    return mod;
  });

  return config;
}

module.exports = withGameBattleSpotifySdk;


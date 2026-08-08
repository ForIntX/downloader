const appName = 'Downloader';
const appVersion = '1.0 Beta';
const appWebsite = 'https://muhammetburakakkas.com';
const engineMethodChannel = 'com.forintx.videoindirici/engine';
const engineEventChannel = 'com.forintx.videoindirici/events';
const playlistEventChannel = 'com.forintx.videoindirici/playlist';
const shareEventChannel = 'com.forintx.videoindirici/share';

const defaultOutputTemplate = '%(title).180B [%(id)s].%(ext)s';
const progressThrottle = Duration(milliseconds: 200);

import 'dart:convert';

enum DownloadStatus {
  pending,
  preparing,
  downloading,
  processing,
  paused,
  completed,
  failed,
  cancelled;

  bool get isActive =>
      this == preparing || this == downloading || this == processing;
  bool get isFinished =>
      this == completed || this == failed || this == cancelled;
}

enum MediaKind { video, audio }

class DownloadPreset {
  const DownloadPreset({
    required this.id,
    required this.label,
    required this.kind,
    required this.format,
    this.audioBitrate,
    this.height,
    this.extension,
  });

  final String id;
  final String label;
  final MediaKind kind;
  final String format;
  final int? audioBitrate;
  final int? height;
  final String? extension;

  Map<String, Object?> toJson() => {
    'id': id,
    'label': label,
    'kind': kind.name,
    'format': format,
    'audio_bitrate': audioBitrate,
    'height': height,
    'extension': extension,
  };

  factory DownloadPreset.fromJson(Map<Object?, Object?> json) => DownloadPreset(
    id: json['id'] as String,
    label: json['label'] as String,
    kind: MediaKind.values.byName(json['kind'] as String),
    format: json['format'] as String,
    audioBitrate: json['audio_bitrate'] as int?,
    height: json['height'] as int?,
    extension: json['extension'] as String?,
  );

  static const presets = <DownloadPreset>[
    DownloadPreset(
      id: 'video-best',
      label: 'En iyi MP4',
      kind: MediaKind.video,
      format: 'bestvideo+bestaudio/best',
      extension: 'mp4',
    ),
    DownloadPreset(
      id: 'video-2160',
      label: '2160p MP4',
      kind: MediaKind.video,
      format: 'bestvideo[height<=2160]+bestaudio/best[height<=2160]',
      height: 2160,
      extension: 'mp4',
    ),
    DownloadPreset(
      id: 'video-1440',
      label: '1440p MP4',
      kind: MediaKind.video,
      format: 'bestvideo[height<=1440]+bestaudio/best[height<=1440]',
      height: 1440,
      extension: 'mp4',
    ),
    DownloadPreset(
      id: 'video-1080',
      label: '1080p MP4',
      kind: MediaKind.video,
      format: 'bestvideo[height<=1080]+bestaudio/best[height<=1080]',
      height: 1080,
      extension: 'mp4',
    ),
    DownloadPreset(
      id: 'video-720',
      label: '720p MP4',
      kind: MediaKind.video,
      format: 'bestvideo[height<=720]+bestaudio/best[height<=720]',
      height: 720,
      extension: 'mp4',
    ),
    DownloadPreset(
      id: 'video-480',
      label: '480p MP4',
      kind: MediaKind.video,
      format: 'bestvideo[height<=480]+bestaudio/best[height<=480]',
      height: 480,
      extension: 'mp4',
    ),
    DownloadPreset(
      id: 'audio-128',
      label: 'MP3 128 kbps',
      kind: MediaKind.audio,
      format: 'bestaudio/best',
      audioBitrate: 128,
      extension: 'mp3',
    ),
    DownloadPreset(
      id: 'audio-192',
      label: 'MP3 192 kbps',
      kind: MediaKind.audio,
      format: 'bestaudio/best',
      audioBitrate: 192,
      extension: 'mp3',
    ),
    DownloadPreset(
      id: 'audio-256',
      label: 'MP3 256 kbps',
      kind: MediaKind.audio,
      format: 'bestaudio/best',
      audioBitrate: 256,
      extension: 'mp3',
    ),
    DownloadPreset(
      id: 'audio-320',
      label: 'MP3 320 kbps',
      kind: MediaKind.audio,
      format: 'bestaudio/best',
      audioBitrate: 320,
      extension: 'mp3',
    ),
    DownloadPreset(
      id: 'audio-m4a',
      label: 'M4A',
      kind: MediaKind.audio,
      format: 'bestaudio[ext=m4a]/bestaudio/best',
      extension: 'm4a',
    ),
    DownloadPreset(
      id: 'audio-opus',
      label: 'Opus',
      kind: MediaKind.audio,
      format: 'bestaudio[ext=webm]/bestaudio/best',
      extension: 'opus',
    ),
    DownloadPreset(
      id: 'custom',
      label: 'Özel yt-dlp formatı',
      kind: MediaKind.video,
      format: '',
      extension: 'mp4',
    ),
  ];

  static DownloadPreset byId(String id) => presets.firstWhere(
    (preset) => preset.id == id,
    orElse: () => presets.first,
  );
}

class PlaylistEntry {
  const PlaylistEntry({
    required this.id,
    required this.url,
    required this.title,
    this.channel,
    this.durationSeconds,
    this.thumbnailUrl,
    this.selected = true,
    this.available = true,
  });

  final String id;
  final String url;
  final String title;
  final String? channel;
  final int? durationSeconds;
  final String? thumbnailUrl;
  final bool selected;
  final bool available;

  PlaylistEntry copyWith({bool? selected}) => PlaylistEntry(
    id: id,
    url: url,
    title: title,
    channel: channel,
    durationSeconds: durationSeconds,
    thumbnailUrl: thumbnailUrl,
    selected: selected ?? this.selected,
    available: available,
  );

  Map<String, Object?> toJson() => {
    'id': id,
    'url': url,
    'title': title,
    'channel': channel,
    'duration_seconds': durationSeconds,
    'thumbnail_url': thumbnailUrl,
    'selected': selected,
    'available': available,
  };

  factory PlaylistEntry.fromJson(Map<Object?, Object?> json) => PlaylistEntry(
    id: (json['id'] ?? '') as String,
    url: (json['url'] ?? json['webpage_url'] ?? '') as String,
    title: (json['title'] ?? 'Başlık bulunamadı') as String,
    channel: (json['channel'] ?? json['uploader']) as String?,
    durationSeconds: (json['duration_seconds'] ?? json['duration']) as int?,
    thumbnailUrl: (json['thumbnail_url'] ?? json['thumbnail']) as String?,
    selected: json['selected'] as bool? ?? true,
    available: json['available'] as bool? ?? true,
  );
}

class VideoMetadata {
  const VideoMetadata({
    required this.id,
    required this.url,
    required this.title,
    this.channel,
    this.description,
    this.thumbnailUrl,
    this.durationSeconds,
    this.viewCount,
    this.width,
    this.height,
    this.uploadDate,
  });

  final String id;
  final String url;
  final String title;
  final String? channel;
  final String? description;
  final String? thumbnailUrl;
  final int? durationSeconds;
  final int? viewCount;
  final int? width;
  final int? height;
  final String? uploadDate;

  factory VideoMetadata.fromJson(Map<Object?, Object?> json) => VideoMetadata(
    id: (json['id'] ?? '') as String,
    url: (json['webpage_url'] ?? json['url'] ?? '') as String,
    title: (json['title'] ?? 'Başlık bulunamadı') as String,
    channel: (json['channel'] ?? json['uploader']) as String?,
    description: json['description'] as String?,
    thumbnailUrl: (json['thumbnail_url'] ?? json['thumbnail']) as String?,
    durationSeconds: (json['duration_seconds'] ?? json['duration']) as int?,
    viewCount: json['view_count'] as int?,
    width: json['width'] as int?,
    height: json['height'] as int?,
    uploadDate: json['upload_date'] as String?,
  );
}

class DownloadJob {
  const DownloadJob({
    required this.id,
    required this.url,
    required this.title,
    required this.presetId,
    required this.createdAt,
    this.status = DownloadStatus.pending,
    this.progress = 0,
    this.speed,
    this.etaSeconds,
    this.outputPath,
    this.thumbnailUrl,
    this.error,
    this.position = 0,
    this.updatedAt,
    this.sourceId = '',
    this.customFormat = '',
    this.speedLimit = '',
    this.concurrentFragments = 4,
    this.filenameTemplate = '%(title).180B [%(id)s].%(ext)s',
    this.cookieMode = 'none',
    this.cookieBrowser = 'firefox',
    this.cookieProfile = '',
    this.cookieFile = '',
  });

  final String id;
  final String url;
  final String title;
  final String presetId;
  final DateTime createdAt;
  final DownloadStatus status;
  final double progress;
  final String? speed;
  final int? etaSeconds;
  final String? outputPath;
  final String? thumbnailUrl;
  final String? error;
  final int position;
  final DateTime? updatedAt;
  final String sourceId;
  final String customFormat;
  final String speedLimit;
  final int concurrentFragments;
  final String filenameTemplate;
  final String cookieMode;
  final String cookieBrowser;
  final String cookieProfile;
  final String cookieFile;

  DownloadPreset get preset => DownloadPreset.byId(presetId);

  DownloadJob copyWith({
    DownloadStatus? status,
    double? progress,
    String? speed,
    int? etaSeconds,
    String? outputPath,
    String? error,
    int? position,
    DateTime? updatedAt,
    bool clearError = false,
  }) => DownloadJob(
    id: id,
    url: url,
    title: title,
    presetId: presetId,
    createdAt: createdAt,
    status: status ?? this.status,
    progress: progress ?? this.progress,
    speed: speed ?? this.speed,
    etaSeconds: etaSeconds ?? this.etaSeconds,
    outputPath: outputPath ?? this.outputPath,
    thumbnailUrl: thumbnailUrl,
    error: clearError ? null : error ?? this.error,
    position: position ?? this.position,
    updatedAt: updatedAt ?? this.updatedAt,
    sourceId: sourceId,
    customFormat: customFormat,
    speedLimit: speedLimit,
    concurrentFragments: concurrentFragments,
    filenameTemplate: filenameTemplate,
    cookieMode: cookieMode,
    cookieBrowser: cookieBrowser,
    cookieProfile: cookieProfile,
    cookieFile: cookieFile,
  );

  Map<String, Object?> toJson() => {
    'id': id,
    'url': url,
    'title': title,
    'preset_id': presetId,
    'created_at': createdAt.toIso8601String(),
    'updated_at': updatedAt?.toIso8601String(),
    'status': status.name,
    'progress': progress,
    'speed': speed,
    'eta_seconds': etaSeconds,
    'output_path': outputPath,
    'thumbnail_url': thumbnailUrl,
    'error': error,
    'position': position,
    'source_id': sourceId,
    'custom_format': customFormat,
    'speed_limit': speedLimit,
    'concurrent_fragments': concurrentFragments,
    'filename_template': filenameTemplate,
    'cookie_mode': cookieMode,
    'cookie_browser': cookieBrowser,
    'cookie_profile': cookieProfile,
    'cookie_file': cookieFile,
    'media_kind': preset.kind.name,
    'height': preset.height,
    'audio_bitrate': preset.audioBitrate,
    'extension': preset.extension,
  };

  Map<String, Object?> toDatabaseJson() {
    final json = toJson();
    json.remove('media_kind');
    json.remove('height');
    json.remove('audio_bitrate');
    json.remove('extension');
    return json;
  }

  factory DownloadJob.fromJson(Map<Object?, Object?> json) => DownloadJob(
    id: json['id'] as String,
    url: json['url'] as String,
    title: json['title'] as String,
    presetId: json['preset_id'] as String,
    createdAt: DateTime.parse(json['created_at'] as String),
    updatedAt: json['updated_at'] == null
        ? null
        : DateTime.parse(json['updated_at'] as String),
    status: DownloadStatus.values.byName(json['status'] as String),
    progress: (json['progress'] as num?)?.toDouble() ?? 0,
    speed: json['speed'] as String?,
    etaSeconds: json['eta_seconds'] as int?,
    outputPath: json['output_path'] as String?,
    thumbnailUrl: json['thumbnail_url'] as String?,
    error: json['error'] as String?,
    position: json['position'] as int? ?? 0,
    sourceId: json['source_id'] as String? ?? '',
    customFormat: json['custom_format'] as String? ?? '',
    speedLimit: json['speed_limit'] as String? ?? '',
    concurrentFragments: json['concurrent_fragments'] as int? ?? 4,
    filenameTemplate:
        json['filename_template'] as String? ??
        '%(title).180B [%(id)s].%(ext)s',
    cookieMode: json['cookie_mode'] as String? ?? 'none',
    cookieBrowser: json['cookie_browser'] as String? ?? 'firefox',
    cookieProfile: json['cookie_profile'] as String? ?? '',
    cookieFile: json['cookie_file'] as String? ?? '',
  );

  String encode() => jsonEncode(toJson());
}

class DownloadEvent {
  const DownloadEvent({
    required this.jobId,
    required this.status,
    this.progress,
    this.speed,
    this.etaSeconds,
    this.outputPath,
    this.error,
  });

  final String jobId;
  final DownloadStatus status;
  final double? progress;
  final String? speed;
  final int? etaSeconds;
  final String? outputPath;
  final String? error;

  factory DownloadEvent.fromJson(Map<Object?, Object?> json) => DownloadEvent(
    jobId: json['job_id'] as String,
    status: DownloadStatus.values.byName(json['status'] as String),
    progress: (json['progress'] as num?)?.toDouble(),
    speed: json['speed'] as String?,
    etaSeconds: json['eta_seconds'] as int?,
    outputPath: json['output_path'] as String?,
    error: json['error'] as String?,
  );
}

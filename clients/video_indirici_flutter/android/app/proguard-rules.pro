# Chaquopy bu sınıfların public metotlarını adlarıyla çağırır. R8 metot
# adlarını değiştirirse indirme ilk ilerleme olayında AttributeError ile durur.
-keep class com.forintx.videoindirici.EngineRuntime$PythonDownloadCallback { public *; }
-keep class com.forintx.videoindirici.MainActivity$PlaylistScanCallback { public *; }

# Flutter medya eklentileri MethodChannel ve Android servis geri çağrılarıyla
# çalışır. Release R8 bu köprüleri yeniden adlandırmamalıdır.
-keep class com.ryanheise.audioservice.** { *; }
-keep class com.ryanheise.just_audio.** { *; }

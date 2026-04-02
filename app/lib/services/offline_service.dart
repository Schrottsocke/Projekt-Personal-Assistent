import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';

/// Lokaler Offline-Cache fuer API-Responses.
/// Speichert GET-Responses und gibt sie zurueck wenn kein Netz verfuegbar ist.
class OfflineService {
  static const _prefix = 'offline_cache_';
  static const _queueKey = 'offline_queue';

  final SharedPreferences _prefs;

  OfflineService(this._prefs);

  /// Cached eine API-Response unter dem gegebenen Key.
  Future<void> cacheResponse(String path, Map<String, dynamic> data) async {
    final key = '$_prefix$path';
    await _prefs.setString(key, jsonEncode({
      'data': data,
      'cached_at': DateTime.now().toIso8601String(),
    }));
  }

  /// Gibt gecachte Response zurueck oder null.
  Map<String, dynamic>? getCachedResponse(String path) {
    final key = '$_prefix$path';
    final raw = _prefs.getString(key);
    if (raw == null) return null;
    final decoded = jsonDecode(raw) as Map<String, dynamic>;
    return decoded['data'] as Map<String, dynamic>?;
  }

  /// Fuegt eine Schreiboperation zur Offline-Queue hinzu.
  Future<void> queueWrite(String method, String path, Map<String, dynamic>? body) async {
    final queue = _getQueue();
    queue.add({
      'method': method,
      'path': path,
      'body': body,
      'queued_at': DateTime.now().toIso8601String(),
    });
    await _prefs.setString(_queueKey, jsonEncode(queue));
  }

  /// Gibt alle ausstehenden Schreiboperationen zurueck.
  List<Map<String, dynamic>> getPendingWrites() => _getQueue();

  /// Entfernt verarbeitete Items aus der Queue.
  Future<void> clearProcessed(int count) async {
    final queue = _getQueue();
    if (count >= queue.length) {
      await _prefs.remove(_queueKey);
    } else {
      await _prefs.setString(_queueKey, jsonEncode(queue.sublist(count)));
    }
  }

  List<Map<String, dynamic>> _getQueue() {
    final raw = _prefs.getString(_queueKey);
    if (raw == null) return [];
    return (jsonDecode(raw) as List).cast<Map<String, dynamic>>();
  }
}

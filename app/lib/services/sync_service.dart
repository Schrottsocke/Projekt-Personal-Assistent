import 'dart:async';
import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:flutter/foundation.dart';
import 'offline_service.dart';
import 'api_service.dart';

/// Sync-Service: Ueberwacht Konnektivitaet und synchronisiert Offline-Queue.
class SyncService {
  final OfflineService _offline;
  final ApiService _api;
  StreamSubscription? _connectivitySub;
  bool _syncing = false;

  final ValueNotifier<bool> isOnline = ValueNotifier(true);
  final ValueNotifier<int> pendingCount = ValueNotifier(0);

  SyncService(this._offline, this._api);

  /// Startet die Konnektivitaets-Ueberwachung.
  void start() {
    _connectivitySub = Connectivity().onConnectivityChanged.listen((results) {
      final online = results.any((r) => r != ConnectivityResult.none);
      isOnline.value = online;
      if (online) syncPending();
    });
    _updatePendingCount();
  }

  /// Versucht alle ausstehenden Schreiboperationen zu synchronisieren.
  Future<void> syncPending() async {
    if (_syncing) return;
    _syncing = true;
    try {
      final pending = _offline.getPendingWrites();
      int processed = 0;
      for (final item in pending) {
        try {
          final method = item['method'] as String;
          final path = item['path'] as String;
          final body = item['body'];

          if (method == 'POST') {
            await _api.post(path, data: body);
          } else if (method == 'PATCH') {
            await _api.patch(path, data: body);
          } else if (method == 'DELETE') {
            await _api.delete(path);
          }
          processed++;
        } catch (e) {
          break; // Stop on first failure
        }
      }
      if (processed > 0) {
        await _offline.clearProcessed(processed);
      }
    } finally {
      _syncing = false;
      _updatePendingCount();
    }
  }

  void _updatePendingCount() {
    pendingCount.value = _offline.getPendingWrites().length;
  }

  void dispose() {
    _connectivitySub?.cancel();
    isOnline.dispose();
    pendingCount.dispose();
  }
}

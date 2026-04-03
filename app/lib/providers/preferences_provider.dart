import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../config/api_config.dart';
import '../providers/auth_provider.dart';

/// User preferences (nav config, dashboard widgets, appearance).
final preferencesProvider =
    AsyncNotifierProvider<PreferencesNotifier, Map<String, dynamic>>(
        PreferencesNotifier.new);

class PreferencesNotifier extends AsyncNotifier<Map<String, dynamic>> {
  @override
  Future<Map<String, dynamic>> build() async {
    final api = ref.watch(apiServiceProvider);
    final resp = await api.get(ApiConfig.preferencesPath);
    return resp.data as Map<String, dynamic>;
  }

  Future<void> updatePreferences(Map<String, dynamic> updates) async {
    final api = ref.read(apiServiceProvider);
    final resp =
        await api.patch(ApiConfig.preferencesPath, data: updates);
    state = AsyncData(resp.data as Map<String, dynamic>);
  }
}

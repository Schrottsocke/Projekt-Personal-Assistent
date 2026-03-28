import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'auth_provider.dart';

class FeaturesNotifier extends AsyncNotifier<List<Map<String, dynamic>>> {
  @override
  Future<List<Map<String, dynamic>>> build() async {
    final api = ref.read(apiServiceProvider);
    final resp = await api.get('/features');
    return List<Map<String, dynamic>>.from(resp.data as List);
  }

  Future<void> toggle(String featureId) async {
    final api = ref.read(apiServiceProvider);
    await api.post('/features/$featureId/toggle');
    ref.invalidateSelf();
  }
}

final featuresProvider =
    AsyncNotifierProvider<FeaturesNotifier, List<Map<String, dynamic>>>(FeaturesNotifier.new);

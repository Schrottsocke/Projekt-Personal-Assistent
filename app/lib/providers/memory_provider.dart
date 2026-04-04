import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/memory_item.dart';
import '../services/memory_api_service.dart';
import 'auth_provider.dart';

final memoryApiServiceProvider = Provider<MemoryApiService>((ref) {
  return MemoryApiService(ref.watch(apiServiceProvider));
});

class MemoryNotifier extends AsyncNotifier<List<MemoryItem>> {
  @override
  Future<List<MemoryItem>> build() async {
    return ref.read(memoryApiServiceProvider).getAll();
  }

  Future<void> refresh({String? query}) async {
    state = const AsyncLoading();
    state = await AsyncValue.guard(
      () => ref.read(memoryApiServiceProvider).getAll(query: query),
    );
  }

  Future<void> loadMore({String? query, required int offset}) async {
    final current = state.value ?? [];
    final more = await ref.read(memoryApiServiceProvider).getAll(
      query: query,
      offset: offset,
    );
    state = AsyncData([...current, ...more]);
  }

  Future<void> search(String query) async {
    state = const AsyncLoading();
    state = await AsyncValue.guard(
      () => ref.read(memoryApiServiceProvider).search(query),
    );
  }

  Future<void> delete(String id) async {
    await ref.read(memoryApiServiceProvider).delete(id);
    final current = state.value ?? [];
    state = AsyncData(current.where((m) => m.id != id).toList());
  }
}

final memoryProvider = AsyncNotifierProvider<MemoryNotifier, List<MemoryItem>>(
  MemoryNotifier.new,
);

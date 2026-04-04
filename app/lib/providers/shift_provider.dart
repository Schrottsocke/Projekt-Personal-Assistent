import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/shift.dart';
import '../services/shift_service.dart';
import 'auth_provider.dart';

final shiftServiceProvider = Provider<ShiftService>((ref) {
  return ShiftService(ref.watch(apiServiceProvider));
});

class ShiftNotifier extends AsyncNotifier<Map<String, dynamic>> {
  String _currentMonth = '';

  @override
  Future<Map<String, dynamic>> build() async {
    final now = DateTime.now();
    _currentMonth = '${now.year}-${now.month.toString().padLeft(2, '0')}';
    return _load();
  }

  Future<Map<String, dynamic>> _load() async {
    final svc = ref.read(shiftServiceProvider);
    final types = await svc.getTypes();
    final entries = await svc.getEntries(_currentMonth);
    return {
      'types': types,
      'entries': entries,
      'month': _currentMonth,
    };
  }

  Future<void> loadMonth(String month) async {
    _currentMonth = month;
    state = const AsyncLoading();
    state = await AsyncValue.guard(() => _load());
  }

  Future<void> refresh() async {
    state = const AsyncLoading();
    state = await AsyncValue.guard(() => _load());
  }

  Future<void> addType({
    required String name,
    required String color,
    required String category,
  }) async {
    await ref.read(shiftServiceProvider).createType(
          name: name,
          color: color,
          category: category,
        );
    await refresh();
  }

  Future<void> deleteType(int id) async {
    await ref.read(shiftServiceProvider).deleteType(id);
    await refresh();
  }

  Future<void> addEntry({
    required String date,
    required int shiftTypeId,
    String? notes,
  }) async {
    await ref.read(shiftServiceProvider).createEntry(
          date: date,
          shiftTypeId: shiftTypeId,
          notes: notes,
        );
    await refresh();
  }

  Future<void> deleteEntry(int id) async {
    await ref.read(shiftServiceProvider).deleteEntry(id);
    await refresh();
  }
}

final shiftProvider = AsyncNotifierProvider<ShiftNotifier, Map<String, dynamic>>(
  ShiftNotifier.new,
);

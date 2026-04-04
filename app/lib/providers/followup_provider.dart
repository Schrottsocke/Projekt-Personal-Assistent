import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/followup.dart';
import '../services/followup_service.dart';
import 'auth_provider.dart';

final followUpServiceProvider = Provider<FollowUpService>((ref) {
  return FollowUpService(ref.watch(apiServiceProvider));
});

class FollowUpNotifier extends AsyncNotifier<List<FollowUp>> {
  @override
  Future<List<FollowUp>> build() async {
    return ref.read(followUpServiceProvider).getAll();
  }

  Future<void> refresh() async {
    state = const AsyncLoading();
    state = await AsyncValue.guard(
      () => ref.read(followUpServiceProvider).getAll(),
    );
  }

  Future<void> create({
    required String title,
    String type = 'custom',
    DateTime? dueDate,
    String? notes,
    String? reference,
  }) async {
    await ref.read(followUpServiceProvider).create(
          title: title,
          type: type,
          dueDate: dueDate,
          notes: notes,
          reference: reference,
        );
    await refresh();
  }

  Future<void> markDone(int id) async {
    await ref.read(followUpServiceProvider).update(id, status: 'done');
    await refresh();
  }

  Future<void> cancel(int id) async {
    await ref.read(followUpServiceProvider).update(id, status: 'cancelled');
    await refresh();
  }
}

final followUpProvider =
    AsyncNotifierProvider<FollowUpNotifier, List<FollowUp>>(
  FollowUpNotifier.new,
);

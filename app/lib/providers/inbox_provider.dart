import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/inbox_item.dart';
import '../services/inbox_service.dart';
import 'auth_provider.dart';

final inboxServiceProvider = Provider<InboxService>((ref) {
  return InboxService(ref.watch(apiServiceProvider));
});

class InboxNotifier extends AsyncNotifier<List<InboxItem>> {
  @override
  Future<List<InboxItem>> build() async {
    return ref.read(inboxServiceProvider).getAll();
  }

  Future<void> refresh({String? status, String? category}) async {
    state = const AsyncLoading();
    state = await AsyncValue.guard(
      () => ref.read(inboxServiceProvider).getAll(status: status, category: category),
    );
  }

  Future<void> performAction(int id, String action) async {
    await ref.read(inboxServiceProvider).performAction(id, action);
    await refresh();
  }
}

final inboxProvider = AsyncNotifierProvider<InboxNotifier, List<InboxItem>>(
  InboxNotifier.new,
);

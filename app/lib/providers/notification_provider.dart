import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/notification_item.dart';
import '../services/notification_service.dart';
import 'auth_provider.dart';

final notificationServiceProvider = Provider<NotificationService>((ref) {
  return NotificationService(ref.watch(apiServiceProvider));
});

class NotificationNotifier extends AsyncNotifier<List<NotificationItem>> {
  @override
  Future<List<NotificationItem>> build() async {
    return ref.read(notificationServiceProvider).getAll();
  }

  Future<void> refresh() async {
    state = const AsyncLoading();
    state = await AsyncValue.guard(
      () => ref.read(notificationServiceProvider).getAll(),
    );
  }

  Future<void> markRead(int id) async {
    await ref.read(notificationServiceProvider).markRead(id);
    await refresh();
  }

  Future<void> markAllRead() async {
    await ref.read(notificationServiceProvider).markAllRead();
    await refresh();
  }

  Future<void> archive(int id) async {
    await ref.read(notificationServiceProvider).archive(id);
    await refresh();
  }
}

final notificationProvider = AsyncNotifierProvider<NotificationNotifier, List<NotificationItem>>(
  NotificationNotifier.new,
);

final unreadCountProvider = FutureProvider<int>((ref) async {
  return ref.read(notificationServiceProvider).getCount();
});

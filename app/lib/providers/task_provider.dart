import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/task.dart';
import '../services/task_service.dart';
import 'auth_provider.dart';

final taskServiceProvider = Provider<TaskService>((ref) {
  return TaskService(ref.watch(apiServiceProvider));
});

class TaskNotifier extends AsyncNotifier<List<Task>> {
  @override
  Future<List<Task>> build() async {
    return ref.read(taskServiceProvider).getTasks();
  }

  Future<void> refresh() async {
    state = const AsyncLoading();
    state = await AsyncValue.guard(
      () => ref.read(taskServiceProvider).getTasks(),
    );
  }

  Future<void> addTask(String title, {String priority = 'medium'}) async {
    await ref.read(taskServiceProvider).createTask(title, priority: priority);
    await refresh();
  }

  Future<void> completeTask(int id) async {
    await ref.read(taskServiceProvider).completeTask(id);
    await refresh();
  }

  Future<void> deleteTask(int id) async {
    await ref.read(taskServiceProvider).deleteTask(id);
    await refresh();
  }
}

final taskProvider = AsyncNotifierProvider<TaskNotifier, List<Task>>(
  TaskNotifier.new,
);

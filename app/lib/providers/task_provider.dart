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

  Future<void> addTask(String title, {String priority = 'medium', String? recurrence}) async {
    await ref.read(taskServiceProvider).createTask(title, priority: priority, recurrence: recurrence);
    await refresh();
  }

  Future<void> completeTask(int id) async {
    await ref.read(taskServiceProvider).completeTask(id);
    await refresh();
  }

  Future<void> updateStatus(int id, String status) async {
    await ref.read(taskServiceProvider).updateStatus(id, status);
    await refresh();
  }

  Future<void> updateTask(int id, {String? title, String? description}) async {
    await ref.read(taskServiceProvider).updateTask(id, title: title, description: description);
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

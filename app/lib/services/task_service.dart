import '../config/api_config.dart';
import '../models/task.dart';
import 'api_service.dart';

class TaskService {
  final ApiService _api;
  TaskService(this._api);

  Future<List<Task>> getTasks({bool all = false}) async {
    final resp = await _api.get(ApiConfig.tasksPath, params: {'all': all});
    return (resp.data as List).map((e) => Task.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<Task> createTask(String title, {String priority = 'medium', String description = '', String? recurrence}) async {
    final resp = await _api.post(ApiConfig.tasksPath, data: {
      'title': title,
      'priority': priority,
      'description': description,
      if (recurrence != null) 'recurrence': recurrence,
    });
    return Task.fromJson(resp.data as Map<String, dynamic>);
  }

  Future<void> updateStatus(int id, String status) async {
    await _api.patch('${ApiConfig.tasksPath}/$id', data: {'status': status});
  }

  Future<void> completeTask(int id) async {
    await updateStatus(id, 'done');
  }

  Future<void> updateTask(int id, {String? title, String? description, String? status, String? recurrence}) async {
    final data = <String, dynamic>{};
    if (title != null) data['title'] = title;
    if (description != null) data['description'] = description;
    if (status != null) data['status'] = status;
    if (recurrence != null) data['recurrence'] = recurrence;
    if (data.isNotEmpty) {
      await _api.patch('${ApiConfig.tasksPath}/$id', data: data);
    }
  }

  Future<void> deleteTask(int id) async {
    await _api.delete('${ApiConfig.tasksPath}/$id');
  }
}

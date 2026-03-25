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

  Future<Task> createTask(String title, {String priority = 'medium', String description = ''}) async {
    final resp = await _api.post(ApiConfig.tasksPath, data: {
      'title': title,
      'priority': priority,
      'description': description,
    });
    return Task.fromJson(resp.data as Map<String, dynamic>);
  }

  Future<void> completeTask(int id) async {
    await _api.patch('${ApiConfig.tasksPath}/$id', data: {'status': 'done'});
  }

  Future<void> deleteTask(int id) async {
    await _api.delete('${ApiConfig.tasksPath}/$id');
  }
}

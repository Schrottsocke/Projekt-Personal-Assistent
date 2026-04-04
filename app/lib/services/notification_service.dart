import '../config/api_config.dart';
import '../models/notification_item.dart';
import 'api_service.dart';

class NotificationService {
  final ApiService _api;
  NotificationService(this._api);

  Future<List<NotificationItem>> getAll({String? status}) async {
    final params = <String, dynamic>{};
    if (status != null) params['status'] = status;
    final resp = await _api.get(ApiConfig.notificationsPath, params: params);
    return (resp.data as List).map((e) => NotificationItem.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<int> getCount() async {
    final resp = await _api.get(ApiConfig.notificationsCountPath);
    return resp.data as int;
  }

  Future<void> markRead(int id) async {
    await _api.patch('${ApiConfig.notificationsPath}/$id', data: {'status': 'read'});
  }

  Future<void> markAllRead() async {
    await _api.post(ApiConfig.notificationsMarkAllReadPath);
  }

  Future<void> archive(int id) async {
    await _api.patch('${ApiConfig.notificationsPath}/$id', data: {'status': 'archived'});
  }
}

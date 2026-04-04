import '../config/api_config.dart';
import '../models/inbox_item.dart';
import 'api_service.dart';

class InboxService {
  final ApiService _api;
  InboxService(this._api);

  Future<List<InboxItem>> getAll({String? status, String? category}) async {
    final params = <String, dynamic>{};
    if (status != null) params['status'] = status;
    if (category != null) params['category'] = category;
    final resp = await _api.get(ApiConfig.inboxPath, params: params);
    return (resp.data as List)
        .map((e) => InboxItem.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<int> getCount() async {
    final resp = await _api.get('${ApiConfig.inboxPath}/count');
    return (resp.data as Map<String, dynamic>)['count'] as int? ?? 0;
  }

  Future<void> performAction(int id, String action) async {
    await _api.post('${ApiConfig.inboxPath}/$id/action', data: {'action': action});
  }
}

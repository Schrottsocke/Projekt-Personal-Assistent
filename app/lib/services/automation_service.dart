import '../config/api_config.dart';
import '../models/automation_rule.dart';
import 'api_service.dart';

class AutomationService {
  final ApiService _api;
  AutomationService(this._api);

  Future<List<AutomationRule>> getAll() async {
    final resp = await _api.get(ApiConfig.automationsPath);
    return (resp.data as List)
        .map((e) => AutomationRule.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<Map<String, dynamic>> getMeta() async {
    final resp = await _api.get('${ApiConfig.automationsPath}/meta');
    return resp.data as Map<String, dynamic>;
  }

  Future<AutomationRule> create({
    required String name,
    String? description,
    required Map<String, dynamic> trigger,
    required Map<String, dynamic> action,
  }) async {
    final resp = await _api.post(ApiConfig.automationsPath, data: {
      'name': name,
      if (description != null) 'description': description,
      'trigger': trigger,
      'action': action,
    });
    return AutomationRule.fromJson(resp.data as Map<String, dynamic>);
  }

  Future<void> update(int id, {
    String? name,
    String? description,
    Map<String, dynamic>? trigger,
    Map<String, dynamic>? action,
  }) async {
    final data = <String, dynamic>{};
    if (name != null) data['name'] = name;
    if (description != null) data['description'] = description;
    if (trigger != null) data['trigger'] = trigger;
    if (action != null) data['action'] = action;
    if (data.isNotEmpty) {
      await _api.patch('${ApiConfig.automationsPath}/$id', data: data);
    }
  }

  Future<void> toggle(int id) async {
    await _api.post('${ApiConfig.automationsPath}/$id/toggle');
  }

  Future<void> delete(int id) async {
    await _api.delete('${ApiConfig.automationsPath}/$id');
  }

  Future<void> evaluate(int id) async {
    await _api.post('${ApiConfig.automationsPath}/$id/evaluate');
  }
}

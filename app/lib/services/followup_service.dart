import '../config/api_config.dart';
import '../models/followup.dart';
import 'api_service.dart';

class FollowUpService {
  final ApiService _api;
  FollowUpService(this._api);

  Future<List<FollowUp>> getAll({String? status}) async {
    final params = <String, dynamic>{};
    if (status != null) params['status'] = status;
    final resp = await _api.get(ApiConfig.followupsPath, params: params);
    return (resp.data as List)
        .map((e) => FollowUp.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<List<FollowUp>> getDue() async {
    final resp = await _api.get(ApiConfig.followupsDuePath);
    return (resp.data as List)
        .map((e) => FollowUp.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<FollowUp> create({
    required String title,
    String type = 'custom',
    DateTime? dueDate,
    String? notes,
    String? reference,
  }) async {
    final data = <String, dynamic>{
      'title': title,
      'type': type,
    };
    if (dueDate != null) data['due_date'] = dueDate.toIso8601String();
    if (notes != null) data['notes'] = notes;
    if (reference != null) data['reference'] = reference;
    final resp = await _api.post(ApiConfig.followupsPath, data: data);
    return FollowUp.fromJson(resp.data as Map<String, dynamic>);
  }

  Future<void> update(int id, {String? status, String? notes}) async {
    final data = <String, dynamic>{};
    if (status != null) data['status'] = status;
    if (notes != null) data['notes'] = notes;
    if (data.isNotEmpty) {
      await _api.patch('${ApiConfig.followupsPath}/$id', data: data);
    }
  }
}

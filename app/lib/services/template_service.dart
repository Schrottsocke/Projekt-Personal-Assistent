import '../config/api_config.dart';
import '../models/template.dart';
import 'api_service.dart';

class TemplateService {
  final ApiService _api;
  TemplateService(this._api);

  Future<List<Template>> getAll({String? category}) async {
    final params = <String, dynamic>{};
    if (category != null) params['category'] = category;
    final resp = await _api.get(ApiConfig.templatesPath, params: params);
    return (resp.data as List)
        .map((e) => Template.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<Template> create({
    required String name,
    required String category,
    Map<String, dynamic> content = const {},
  }) async {
    final resp = await _api.post(ApiConfig.templatesPath, data: {
      'name': name,
      'category': category,
      'content': content,
    });
    return Template.fromJson(resp.data as Map<String, dynamic>);
  }

  Future<void> update(int id, {String? name, Map<String, dynamic>? content}) async {
    final data = <String, dynamic>{};
    if (name != null) data['name'] = name;
    if (content != null) data['content'] = content;
    if (data.isNotEmpty) {
      await _api.patch('${ApiConfig.templatesPath}/$id', data: data);
    }
  }

  Future<void> delete(int id) async {
    await _api.delete('${ApiConfig.templatesPath}/$id');
  }

  Future<void> apply(int id) async {
    await _api.post('${ApiConfig.templatesPath}/$id/apply');
  }
}

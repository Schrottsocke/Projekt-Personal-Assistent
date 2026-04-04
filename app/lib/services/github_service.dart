import '../config/api_config.dart';
import 'api_service.dart';

class GitHubService {
  final ApiService _api;
  GitHubService(this._api);

  Future<List<Map<String, dynamic>>> getIssues({String? state, String? labels}) async {
    final params = <String, dynamic>{};
    if (state != null) params['state'] = state;
    if (labels != null) params['labels'] = labels;
    final resp = await _api.get(ApiConfig.githubIssuesPath, params: params);
    return (resp.data as List).cast<Map<String, dynamic>>();
  }

  Future<List<Map<String, dynamic>>> getLabels() async {
    final resp = await _api.get(ApiConfig.githubLabelsPath);
    return (resp.data as List).cast<Map<String, dynamic>>();
  }

  Future<Map<String, dynamic>> createIssue({
    required String title,
    String? body,
    List<String>? labels,
  }) async {
    final resp = await _api.post(ApiConfig.githubIssuesPath, data: {
      'title': title,
      if (body != null) 'body': body,
      if (labels != null) 'labels': labels,
    });
    return resp.data as Map<String, dynamic>;
  }
}

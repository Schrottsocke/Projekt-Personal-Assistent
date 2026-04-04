import '../config/api_config.dart';
import 'api_service.dart';

class SearchService {
  final ApiService _api;
  SearchService(this._api);

  Future<List<Map<String, dynamic>>> globalSearch(
    String query, {
    int limit = 20,
  }) async {
    final resp = await _api.get(
      ApiConfig.searchPath,
      params: {'q': query, 'limit': limit},
    );
    return (resp.data as List)
        .map((e) => e as Map<String, dynamic>)
        .toList();
  }
}

import '../config/api_config.dart';
import '../models/memory_item.dart';
import 'api_service.dart';

class MemoryApiService {
  final ApiService _api;
  MemoryApiService(this._api);

  Future<List<MemoryItem>> getAll({String? query, int limit = 20, int offset = 0}) async {
    final params = <String, dynamic>{
      'limit': limit,
      'offset': offset,
    };
    if (query != null && query.isNotEmpty) params['q'] = query;
    final resp = await _api.get(ApiConfig.memoryPath, params: params);
    return (resp.data as List)
        .map((e) => MemoryItem.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<List<MemoryItem>> search(String query) async {
    final resp = await _api.get('${ApiConfig.memoryPath}/search', params: {'q': query});
    return (resp.data as List)
        .map((e) => MemoryItem.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<void> delete(String id) async {
    await _api.delete('${ApiConfig.memoryPath}/$id');
  }
}

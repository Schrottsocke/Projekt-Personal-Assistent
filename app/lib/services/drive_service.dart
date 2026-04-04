import '../config/api_config.dart';
import 'api_service.dart';

class DriveService {
  final ApiService _api;
  DriveService(this._api);

  Future<List<Map<String, dynamic>>> listFiles({String? query}) async {
    final params = <String, dynamic>{};
    if (query != null && query.isNotEmpty) params['q'] = query;
    final resp = await _api.get(ApiConfig.driveFilesPath, params: params);
    return (resp.data as List).map((e) => e as Map<String, dynamic>).toList();
  }
}

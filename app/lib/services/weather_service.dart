import '../config/api_config.dart';
import 'api_service.dart';

class WeatherService {
  final ApiService _api;
  WeatherService(this._api);

  Future<Map<String, dynamic>> getCurrent({String? location}) async {
    final params = <String, dynamic>{};
    if (location != null && location.isNotEmpty) params['location'] = location;
    final resp = await _api.get(ApiConfig.weatherCurrentPath, params: params);
    return resp.data as Map<String, dynamic>;
  }

  Future<List<Map<String, dynamic>>> getForecast({String? location, int days = 5}) async {
    final params = <String, dynamic>{'days': days};
    if (location != null && location.isNotEmpty) params['location'] = location;
    final resp = await _api.get(ApiConfig.weatherForecastPath, params: params);
    return (resp.data as List).map((e) => e as Map<String, dynamic>).toList();
  }
}

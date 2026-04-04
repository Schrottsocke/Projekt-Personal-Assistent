import '../config/api_config.dart';
import 'api_service.dart';

class MobilityService {
  final ApiService _api;
  MobilityService(this._api);

  Future<List<Map<String, dynamic>>> getDailyFlow() async {
    final resp = await _api.get(ApiConfig.mobilityDailyFlowPath);
    return (resp.data as List).cast<Map<String, dynamic>>();
  }

  Future<Map<String, dynamic>> getTravelTime({
    required String origin,
    required String destination,
    String profile = 'driving-car',
  }) async {
    final resp = await _api.post(ApiConfig.mobilityTravelTimePath, data: {
      'origin': origin,
      'destination': destination,
      'profile': profile,
    });
    return resp.data as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> getDepartureTime({
    required String origin,
    required String destination,
    required String arrivalTime,
  }) async {
    final resp = await _api.post(ApiConfig.mobilityDepartureTimePath, data: {
      'origin': origin,
      'destination': destination,
      'arrival_time': arrivalTime,
    });
    return resp.data as Map<String, dynamic>;
  }
}

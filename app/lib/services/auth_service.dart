import '../config/api_config.dart';
import 'api_service.dart';

class AuthService {
  final ApiService _api;
  AuthService(this._api);

  Future<bool> login(String username, String password) async {
    try {
      final resp = await _api.post(ApiConfig.loginPath, data: {
        'username': username,
        'password': password,
      });
      await _api.saveTokens(
        resp.data['access_token'] as String,
        resp.data['refresh_token'] as String,
        resp.data['user_key'] as String,
      );
      return true;
    } catch (_) {
      return false;
    }
  }

  Future<void> logout() => _api.clearTokens();
  Future<bool> isLoggedIn() => _api.isLoggedIn();
  Future<String?> currentUser() => _api.getUserKey();
}

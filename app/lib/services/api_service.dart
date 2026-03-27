import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import '../config/api_config.dart';

/// Zentraler HTTP-Client mit JWT-Interceptor und Auto-Refresh.
class ApiService {
  late final Dio _dio;
  final FlutterSecureStorage _storage;

  static const _tokenKey = 'access_token';
  static const _refreshKey = 'refresh_token';
  static const _userKey = 'user_key';

  ApiService({FlutterSecureStorage? storage})
      : _storage = storage ?? const FlutterSecureStorage() {
    _dio = Dio(BaseOptions(
      baseUrl: ApiConfig.baseUrl,
      connectTimeout: ApiConfig.connectTimeout,
      receiveTimeout: ApiConfig.receiveTimeout,
      headers: {'Content-Type': 'application/json'},
    ));
    _dio.interceptors.add(_AuthInterceptor(_storage, _dio));
  }

  Future<Response<T>> get<T>(String path, {Map<String, dynamic>? params}) =>
      _dio.get<T>(path, queryParameters: params);

  Future<Response<T>> post<T>(String path, {dynamic data}) =>
      _dio.post<T>(path, data: data);

  Future<Response<T>> patch<T>(String path, {dynamic data}) =>
      _dio.patch<T>(path, data: data);

  Future<Response<T>> delete<T>(String path) => _dio.delete<T>(path);

  Future<Response<T>> upload<T>(String path, FormData formData) =>
      _dio.post<T>(path, data: formData);

  // Auth-Helfer
  Future<void> saveTokens(String access, String refresh, String user) async {
    await _storage.write(key: _tokenKey, value: access);
    await _storage.write(key: _refreshKey, value: refresh);
    await _storage.write(key: _userKey, value: user);
  }

  Future<void> clearTokens() async {
    await _storage.deleteAll();
  }

  Future<String?> getUserKey() => _storage.read(key: _userKey);
  Future<bool> isLoggedIn() async => (await _storage.read(key: _tokenKey)) != null;
}

class _AuthInterceptor extends Interceptor {
  final FlutterSecureStorage _storage;
  final Dio _dio;
  Completer<bool>? _refreshCompleter;

  _AuthInterceptor(this._storage, this._dio);

  @override
  void onRequest(RequestOptions options, RequestInterceptorHandler handler) async {
    final token = await _storage.read(key: 'access_token');
    if (token != null) {
      options.headers['Authorization'] = 'Bearer $token';
    }
    handler.next(options);
  }

  @override
  void onError(DioException err, ErrorInterceptorHandler handler) async {
    if (err.response?.statusCode != 401) {
      handler.next(err);
      return;
    }

    // If another request is already refreshing, wait for it.
    if (_refreshCompleter != null) {
      final success = await _refreshCompleter!.future;
      if (success) {
        final token = await _storage.read(key: 'access_token');
        err.requestOptions.headers['Authorization'] = 'Bearer $token';
        final retry = await _dio.fetch(err.requestOptions);
        handler.resolve(retry);
        return;
      }
      handler.next(err);
      return;
    }

    _refreshCompleter = Completer<bool>();
    try {
      final refresh = await _storage.read(key: 'refresh_token');
      if (refresh == null) {
        await _storage.deleteAll();
        _refreshCompleter!.complete(false);
        handler.next(err);
        return;
      }

      final resp = await Dio(BaseOptions(baseUrl: ApiConfig.baseUrl))
          .post(ApiConfig.refreshPath, data: {'refresh_token': refresh});
      final newToken = resp.data['access_token'] as String;
      final newRefresh = resp.data['refresh_token'] as String;
      await _storage.write(key: 'access_token', value: newToken);
      await _storage.write(key: 'refresh_token', value: newRefresh);
      _refreshCompleter!.complete(true);

      err.requestOptions.headers['Authorization'] = 'Bearer $newToken';
      final retry = await _dio.fetch(err.requestOptions);
      handler.resolve(retry);
      return;
    } on DioException catch (e) {
      // Only clear tokens if the refresh endpoint itself returns 401.
      // Network errors (timeout, connection) keep tokens intact.
      if (e.response?.statusCode == 401) {
        await _storage.deleteAll();
      }
      _refreshCompleter!.complete(false);
    } finally {
      _refreshCompleter = null;
    }
    handler.next(err);
  }
}

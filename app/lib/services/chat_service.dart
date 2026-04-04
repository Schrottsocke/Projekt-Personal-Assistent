import 'dart:async';
import 'dart:convert';

import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../config/api_config.dart';
import '../models/chat_message.dart';
import 'api_service.dart';

class ChatService {
  final ApiService _api;
  ChatService(this._api);

  Future<String> sendMessage(String message) async {
    final resp = await _api.post(ApiConfig.chatMessagePath, data: {'message': message});
    return resp.data['response'] as String? ?? '';
  }

  Future<List<ChatMessage>> getHistory({int limit = 50}) async {
    final resp = await _api.get(ApiConfig.chatHistoryPath, params: {'limit': limit});
    return (resp.data as List).map((e) => ChatMessage.fromJson(e as Map<String, dynamic>)).toList();
  }

  /// SSE-Streaming: sendet Nachricht und liefert Tokens als Stream.
  Stream<String> sendMessageStream(String message) async* {
    final storage = const FlutterSecureStorage();
    final token = await storage.read(key: 'access_token');

    final dio = Dio(BaseOptions(
      baseUrl: ApiConfig.baseUrl,
      connectTimeout: ApiConfig.connectTimeout,
      receiveTimeout: const Duration(seconds: 120),
      headers: {
        'Content-Type': 'application/json',
        if (token != null) 'Authorization': 'Bearer $token',
      },
      responseType: ResponseType.stream,
    ));

    final resp = await dio.post<ResponseBody>(
      ApiConfig.chatStreamPath,
      data: {'message': message},
    );

    final stream = resp.data!.stream;
    String buffer = '';

    await for (final chunk in stream) {
      buffer += utf8.decode(chunk);
      final lines = buffer.split('\n');
      // Behalte letzte unvollstaendige Zeile im Buffer
      buffer = lines.removeLast();

      for (final line in lines) {
        final trimmed = line.trim();
        if (trimmed.isEmpty) continue;
        if (trimmed.startsWith('data: ')) {
          final data = trimmed.substring(6);
          if (data == '[DONE]') return;
          yield data;
        }
      }
    }

    // Verarbeite Rest im Buffer
    if (buffer.trim().startsWith('data: ')) {
      final data = buffer.trim().substring(6);
      if (data != '[DONE]') yield data;
    }
  }

  /// Voice-Upload: sendet Audio-Datei, erhaelt Transkription + Antwort.
  Future<String> sendVoice(String filePath) async {
    final formData = FormData.fromMap({
      'file': await MultipartFile.fromFile(filePath),
    });
    final resp = await _api.upload(ApiConfig.chatVoicePath, formData);
    return resp.data['response'] as String? ?? '';
  }

  /// Lade Vorschlaege fuer den Chat.
  Future<List<String>> getSuggestions() async {
    final resp = await _api.get(ApiConfig.chatSuggestionsPath);
    final data = resp.data;
    if (data is List) {
      return data.map((e) => e.toString()).toList();
    }
    if (data is Map && data['suggestions'] is List) {
      return (data['suggestions'] as List).map((e) => e.toString()).toList();
    }
    return [];
  }
}

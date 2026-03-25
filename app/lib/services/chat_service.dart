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
}

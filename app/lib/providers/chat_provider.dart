import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/chat_message.dart';
import '../services/chat_service.dart';
import 'auth_provider.dart';

final chatServiceProvider = Provider<ChatService>((ref) {
  return ChatService(ref.watch(apiServiceProvider));
});

class ChatNotifier extends AsyncNotifier<List<ChatMessage>> {
  @override
  Future<List<ChatMessage>> build() async {
    return ref.read(chatServiceProvider).getHistory();
  }

  Future<void> sendMessage(String text) async {
    final userMsg = ChatMessage(role: 'user', content: text, createdAt: DateTime.now());
    state = AsyncData([...state.value ?? [], userMsg]);

    final response = await ref.read(chatServiceProvider).sendMessage(text);
    final botMsg = ChatMessage(role: 'assistant', content: response, createdAt: DateTime.now());
    state = AsyncData([...state.value ?? [], botMsg]);
  }
}

final chatProvider = AsyncNotifierProvider<ChatNotifier, List<ChatMessage>>(ChatNotifier.new);

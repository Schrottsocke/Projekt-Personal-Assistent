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

  /// Streaming: Sendet Nachricht und aktualisiert die letzte Bot-Nachricht
  /// Token fuer Token.
  Future<void> sendMessageStream(String text) async {
    final userMsg = ChatMessage(role: 'user', content: text, createdAt: DateTime.now());
    final messages = [...state.value ?? [], userMsg];
    state = AsyncData(messages);

    // Leere Bot-Nachricht als Platzhalter
    final botMsg = ChatMessage(role: 'assistant', content: '', createdAt: DateTime.now());
    state = AsyncData([...messages, botMsg]);

    String accumulated = '';
    try {
      await for (final token in ref.read(chatServiceProvider).sendMessageStream(text)) {
        accumulated += token;
        final updated = ChatMessage(role: 'assistant', content: accumulated, createdAt: DateTime.now());
        final current = [...messages, updated];
        state = AsyncData(current);
      }
    } catch (_) {
      // Bei Streaming-Fehler: Fallback auf synchronen Aufruf
      if (accumulated.isEmpty) {
        final response = await ref.read(chatServiceProvider).sendMessage(text);
        final fallback = ChatMessage(role: 'assistant', content: response, createdAt: DateTime.now());
        state = AsyncData([...messages, fallback]);
      }
    }
  }

  /// Voice-Nachricht senden.
  Future<void> sendVoice(String filePath) async {
    final userMsg = ChatMessage(role: 'user', content: '🎤 Sprachnachricht', createdAt: DateTime.now());
    state = AsyncData([...state.value ?? [], userMsg]);

    final response = await ref.read(chatServiceProvider).sendVoice(filePath);
    final botMsg = ChatMessage(role: 'assistant', content: response, createdAt: DateTime.now());
    state = AsyncData([...state.value ?? [], botMsg]);
  }
}

final chatProvider = AsyncNotifierProvider<ChatNotifier, List<ChatMessage>>(ChatNotifier.new);

/// Provider fuer Chat-Vorschlaege (Suggestion Chips).
final chatSuggestionsProvider = FutureProvider<List<String>>((ref) async {
  final service = ref.watch(chatServiceProvider);
  try {
    return await service.getSuggestions();
  } catch (_) {
    return [];
  }
});

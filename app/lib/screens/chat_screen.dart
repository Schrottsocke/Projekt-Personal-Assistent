import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:path_provider/path_provider.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:record/record.dart';

import '../providers/chat_provider.dart';
import '../widgets/chat_bubble.dart';

class ChatScreen extends ConsumerStatefulWidget {
  const ChatScreen({super.key});
  @override
  ConsumerState<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends ConsumerState<ChatScreen> {
  final _ctrl = TextEditingController();
  final _scrollCtrl = ScrollController();
  bool _sending = false;
  bool _streaming = false;
  bool _recording = false;
  AudioRecorder? _recorder;

  @override
  void dispose() {
    _ctrl.dispose();
    _scrollCtrl.dispose();
    _recorder?.dispose();
    super.dispose();
  }

  Future<void> _send() async {
    final text = _ctrl.text.trim();
    if (text.isEmpty || _sending) return;
    _ctrl.clear();
    setState(() {
      _sending = true;
      _streaming = true;
    });
    try {
      await ref.read(chatProvider.notifier).sendMessageStream(text);
    } catch (_) {
      // Fallback wurde bereits im Provider behandelt
    }
    setState(() {
      _sending = false;
      _streaming = false;
    });
    _scrollToBottom();
  }

  Future<void> _sendSuggestion(String text) async {
    _ctrl.text = text;
    await _send();
  }

  Future<void> _toggleRecording() async {
    if (_recording) {
      await _stopRecording();
    } else {
      await _startRecording();
    }
  }

  Future<void> _startRecording() async {
    final status = await Permission.microphone.request();
    if (!status.isGranted) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Mikrofon-Berechtigung benoetigt')),
        );
      }
      return;
    }

    _recorder ??= AudioRecorder();
    final dir = await getTemporaryDirectory();
    final path = '${dir.path}/voice_${DateTime.now().millisecondsSinceEpoch}.m4a';

    if (await _recorder!.hasPermission()) {
      await _recorder!.start(
        const RecordConfig(encoder: AudioEncoder.aacLc),
        path: path,
      );
      setState(() => _recording = true);
    }
  }

  Future<void> _stopRecording() async {
    if (_recorder == null) return;
    final path = await _recorder!.stop();
    setState(() => _recording = false);

    if (path != null && File(path).existsSync()) {
      setState(() => _sending = true);
      try {
        await ref.read(chatProvider.notifier).sendVoice(path);
      } catch (e) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Sprachnachricht fehlgeschlagen: $e')),
          );
        }
      }
      setState(() => _sending = false);
      _scrollToBottom();
      // Temp-Datei aufraeumen
      try { File(path).deleteSync(); } catch (_) {}
    }
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollCtrl.hasClients) {
        _scrollCtrl.animateTo(
          _scrollCtrl.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(chatProvider);

    // Scroll bei jeder State-Aenderung waehrend Streaming
    if (_streaming) {
      _scrollToBottom();
    }

    return Scaffold(
      appBar: AppBar(
        title: const Text('Chat'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => ref.invalidate(chatProvider),
          ),
        ],
      ),
      body: Column(
        children: [
          Expanded(child: state.when(
            loading: () => const Center(child: CircularProgressIndicator()),
            error: (e, _) => Center(child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                const Icon(Icons.cloud_off, size: 48, color: Colors.grey),
                const SizedBox(height: 16),
                const Text('Daten konnten nicht geladen werden'),
                const SizedBox(height: 8),
                FilledButton(
                  onPressed: () => ref.invalidate(chatProvider),
                  child: const Text('Erneut versuchen'),
                ),
              ],
            )),
            data: (messages) => messages.isEmpty
                ? Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        const Icon(Icons.chat_bubble_outline, size: 48, color: Colors.grey),
                        const SizedBox(height: 16),
                        const Text('Schreib mir etwas!', style: TextStyle(color: Colors.grey)),
                        const SizedBox(height: 8),
                        const Text('Ich helfe dir mit Terminen, Aufgaben,\nEinkauf und mehr.', textAlign: TextAlign.center, style: TextStyle(color: Colors.grey, fontSize: 13)),
                      ],
                    ),
                  )
                : ListView.builder(
                    controller: _scrollCtrl,
                    padding: const EdgeInsets.symmetric(vertical: 8),
                    itemCount: messages.length,
                    itemBuilder: (_, i) {
                      final isLast = i == messages.length - 1;
                      final msg = messages[i];
                      return ChatBubble(
                        message: msg,
                        isStreaming: isLast && _streaming && msg.isAssistant,
                      );
                    },
                  ),
          )),
          if (_sending)
            const LinearProgressIndicator(minHeight: 2),
          _buildSuggestionChips(),
          _buildInput(context),
        ],
      ),
    );
  }

  Widget _buildSuggestionChips() {
    final suggestions = ref.watch(chatSuggestionsProvider);
    return suggestions.when(
      loading: () => const SizedBox.shrink(),
      error: (_, __) => const SizedBox.shrink(),
      data: (chips) {
        if (chips.isEmpty) return const SizedBox.shrink();
        return SizedBox(
          height: 44,
          child: ListView.separated(
            scrollDirection: Axis.horizontal,
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
            itemCount: chips.length,
            separatorBuilder: (_, __) => const SizedBox(width: 8),
            itemBuilder: (context, i) => ActionChip(
              label: Text(chips[i], style: const TextStyle(fontSize: 13)),
              onPressed: _sending ? null : () => _sendSuggestion(chips[i]),
            ),
          ),
        );
      },
    );
  }

  Widget _buildInput(BuildContext context) {
    return SafeArea(
      child: Container(
        padding: const EdgeInsets.fromLTRB(12, 8, 12, 12),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surface,
          border: Border(top: BorderSide(color: Colors.grey.shade800)),
        ),
        child: Row(
          children: [
            Expanded(
              child: TextField(
                controller: _ctrl,
                maxLines: null,
                textInputAction: TextInputAction.send,
                onSubmitted: (_) => _send(),
                decoration: const InputDecoration(
                  hintText: 'Nachricht schreiben…',
                  border: OutlineInputBorder(),
                  isDense: true,
                  contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                ),
              ),
            ),
            const SizedBox(width: 8),
            IconButton(
              onPressed: _sending ? null : _toggleRecording,
              icon: Icon(
                _recording ? Icons.stop_circle : Icons.mic,
                color: _recording ? Colors.red : null,
              ),
              tooltip: _recording ? 'Aufnahme stoppen' : 'Sprachnachricht',
            ),
            IconButton.filled(
              onPressed: _sending ? null : _send,
              icon: const Icon(Icons.send),
            ),
          ],
        ),
      ),
    );
  }
}

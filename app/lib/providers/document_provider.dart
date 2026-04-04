import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/document.dart';
import '../services/document_service.dart';
import 'auth_provider.dart';

final documentServiceProvider = Provider<DocumentService>((ref) {
  return DocumentService(ref.watch(apiServiceProvider));
});

class DocumentNotifier extends AsyncNotifier<List<ScannedDocument>> {
  @override
  Future<List<ScannedDocument>> build() async {
    return ref.read(documentServiceProvider).getAll();
  }

  Future<void> refresh() async {
    state = const AsyncLoading();
    state = await AsyncValue.guard(
      () => ref.read(documentServiceProvider).getAll(),
    );
  }

  Future<void> triggerAction(int id, String action) async {
    await ref.read(documentServiceProvider).triggerAction(id, action);
  }
}

final documentProvider =
    AsyncNotifierProvider<DocumentNotifier, List<ScannedDocument>>(
  DocumentNotifier.new,
);

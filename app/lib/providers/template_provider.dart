import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/template.dart';
import '../services/template_service.dart';
import 'auth_provider.dart';

final templateServiceProvider = Provider<TemplateService>((ref) {
  return TemplateService(ref.watch(apiServiceProvider));
});

class TemplateNotifier extends AsyncNotifier<List<Template>> {
  @override
  Future<List<Template>> build() async {
    return ref.read(templateServiceProvider).getAll();
  }

  Future<void> refresh({String? category}) async {
    state = const AsyncLoading();
    state = await AsyncValue.guard(
      () => ref.read(templateServiceProvider).getAll(category: category),
    );
  }

  Future<void> create({
    required String name,
    required String category,
    Map<String, dynamic> content = const {},
  }) async {
    await ref.read(templateServiceProvider).create(
      name: name,
      category: category,
      content: content,
    );
    await refresh();
  }

  Future<void> apply(int id) async {
    await ref.read(templateServiceProvider).apply(id);
  }

  Future<void> delete(int id) async {
    await ref.read(templateServiceProvider).delete(id);
    await refresh();
  }
}

final templateProvider = AsyncNotifierProvider<TemplateNotifier, List<Template>>(
  TemplateNotifier.new,
);

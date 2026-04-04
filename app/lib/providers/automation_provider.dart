import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/automation_rule.dart';
import '../services/automation_service.dart';
import 'auth_provider.dart';

final automationServiceProvider = Provider<AutomationService>((ref) {
  return AutomationService(ref.watch(apiServiceProvider));
});

class AutomationNotifier extends AsyncNotifier<List<AutomationRule>> {
  @override
  Future<List<AutomationRule>> build() async {
    return ref.read(automationServiceProvider).getAll();
  }

  Future<void> refresh() async {
    state = const AsyncLoading();
    state = await AsyncValue.guard(
      () => ref.read(automationServiceProvider).getAll(),
    );
  }

  Future<void> create({
    required String name,
    String? description,
    required Map<String, dynamic> trigger,
    required Map<String, dynamic> action,
  }) async {
    await ref.read(automationServiceProvider).create(
      name: name,
      description: description,
      trigger: trigger,
      action: action,
    );
    await refresh();
  }

  Future<void> toggle(int id) async {
    await ref.read(automationServiceProvider).toggle(id);
    await refresh();
  }

  Future<void> evaluate(int id) async {
    await ref.read(automationServiceProvider).evaluate(id);
  }

  Future<void> delete(int id) async {
    await ref.read(automationServiceProvider).delete(id);
    await refresh();
  }
}

final automationProvider = AsyncNotifierProvider<AutomationNotifier, List<AutomationRule>>(
  AutomationNotifier.new,
);

import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/contact.dart';
import '../services/contact_service.dart';
import 'auth_provider.dart';

final contactServiceProvider = Provider<ContactService>((ref) {
  return ContactService(ref.watch(apiServiceProvider));
});

class ContactNotifier extends AsyncNotifier<List<Contact>> {
  @override
  Future<List<Contact>> build() async {
    return ref.read(contactServiceProvider).getAll();
  }

  Future<void> refresh({String? search}) async {
    state = const AsyncLoading();
    state = await AsyncValue.guard(
      () => ref.read(contactServiceProvider).getAll(search: search),
    );
  }

  Future<void> addContact({
    required String name,
    String? email,
    String? phone,
    String? notes,
    List<String>? tags,
  }) async {
    await ref.read(contactServiceProvider).create(
          name: name,
          email: email,
          phone: phone,
          notes: notes,
          tags: tags,
        );
    await refresh();
  }

  Future<void> updateContact(int id, {
    String? name,
    String? email,
    String? phone,
    String? notes,
    List<String>? tags,
  }) async {
    await ref.read(contactServiceProvider).update(id,
          name: name,
          email: email,
          phone: phone,
          notes: notes,
          tags: tags,
        );
    await refresh();
  }

  Future<void> deleteContact(int id) async {
    await ref.read(contactServiceProvider).delete(id);
    await refresh();
  }
}

final contactProvider = AsyncNotifierProvider<ContactNotifier, List<Contact>>(
  ContactNotifier.new,
);

import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../services/api_service.dart';
import '../services/auth_service.dart';

final apiServiceProvider = Provider<ApiService>((ref) => ApiService());

final authServiceProvider = Provider<AuthService>((ref) {
  return AuthService(ref.watch(apiServiceProvider));
});

class AuthNotifier extends AsyncNotifier<String?> {
  @override
  Future<String?> build() async {
    final auth = ref.read(authServiceProvider);
    if (await auth.isLoggedIn()) {
      return auth.currentUser();
    }
    return null;
  }

  Future<bool> login(String username, String password) async {
    final auth = ref.read(authServiceProvider);
    final ok = await auth.login(username, password);
    if (ok) {
      state = AsyncData(await auth.currentUser());
    }
    return ok;
  }

  Future<void> logout() async {
    await ref.read(authServiceProvider).logout();
    state = const AsyncData(null);
  }
}

final authProvider = AsyncNotifierProvider<AuthNotifier, String?>(AuthNotifier.new);

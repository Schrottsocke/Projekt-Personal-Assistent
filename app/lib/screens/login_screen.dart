import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../providers/auth_provider.dart';

class LoginScreen extends ConsumerStatefulWidget {
  const LoginScreen({super.key});
  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen> {
  String? _selectedUser;
  final _pwController = TextEditingController();
  bool _loading = false;
  bool _obscure = true;
  String? _error;

  @override
  void dispose() {
    _pwController.dispose();
    super.dispose();
  }

  Future<void> _login() async {
    if (_selectedUser == null) {
      setState(() => _error = 'Bitte Nutzer auswählen.');
      return;
    }
    if (_pwController.text.isEmpty) {
      setState(() => _error = 'Bitte Passwort eingeben.');
      return;
    }
    setState(() { _loading = true; _error = null; });
    final ok = await ref.read(authProvider.notifier).login(_selectedUser!, _pwController.text);
    setState(() => _loading = false);
    if (ok && mounted) {
      context.go('/home');
    } else {
      setState(() => _error = 'Falsches Passwort.');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(32),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                const Icon(Icons.smart_toy, size: 64, color: Colors.blue),
                const SizedBox(height: 16),
                Text('DualMind', style: Theme.of(context).textTheme.headlineMedium?.copyWith(fontWeight: FontWeight.bold)),
                const SizedBox(height: 8),
                Text('Persönlicher Assistent', style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: Colors.grey)),
                const SizedBox(height: 40),
                Text('Nutzer auswählen', style: Theme.of(context).textTheme.titleMedium),
                const SizedBox(height: 16),
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: ['taake', 'nina'].map((u) {
                    final selected = _selectedUser == u;
                    return Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 12),
                      child: InkWell(
                        onTap: () => setState(() { _selectedUser = u; _error = null; }),
                        borderRadius: BorderRadius.circular(16),
                        child: Container(
                          width: 100,
                          padding: const EdgeInsets.all(16),
                          decoration: BoxDecoration(
                            borderRadius: BorderRadius.circular(16),
                            border: Border.all(color: selected ? Colors.blue : Colors.grey.shade700, width: selected ? 2 : 1),
                            color: selected ? Colors.blue.withOpacity(0.15) : null,
                          ),
                          child: Column(
                            children: [
                              CircleAvatar(
                                radius: 28,
                                backgroundColor: selected ? Colors.blue : Colors.grey.shade700,
                                child: Text(u[0].toUpperCase(), style: const TextStyle(fontSize: 22, color: Colors.white, fontWeight: FontWeight.bold)),
                              ),
                              const SizedBox(height: 8),
                              Text(u[0].toUpperCase() + u.substring(1), style: TextStyle(fontWeight: selected ? FontWeight.bold : FontWeight.normal)),
                            ],
                          ),
                        ),
                      ),
                    );
                  }).toList(),
                ),
                const SizedBox(height: 32),
                TextField(
                  controller: _pwController,
                  obscureText: _obscure,
                  decoration: InputDecoration(
                    labelText: 'Passwort',
                    border: const OutlineInputBorder(),
                    suffixIcon: IconButton(
                      icon: Icon(_obscure ? Icons.visibility_off : Icons.visibility),
                      onPressed: () => setState(() => _obscure = !_obscure),
                    ),
                  ),
                  onSubmitted: (_) => _login(),
                ),
                if (_error != null) ...[
                  const SizedBox(height: 12),
                  Text(_error!, style: const TextStyle(color: Colors.red)),
                ],
                const SizedBox(height: 24),
                SizedBox(
                  width: double.infinity,
                  child: FilledButton(
                    onPressed: _loading ? null : _login,
                    child: _loading ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white)) : const Text('Anmelden'),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

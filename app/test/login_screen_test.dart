import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:dualmind/screens/login_screen.dart';
import 'package:dualmind/providers/auth_provider.dart';

// ─── Fake AuthNotifier (ersetzt echten Auth-Flow komplett) ──────────
class FakeAuthNotifier extends AsyncNotifier<String?> implements AuthNotifier {
  bool loginResult = true;

  @override
  Future<String?> build() async => null;

  @override
  Future<bool> login(String username, String password) async {
    if (loginResult) {
      state = AsyncData(username);
    }
    return loginResult;
  }

  @override
  Future<void> logout() async {
    state = const AsyncData(null);
  }
}

// ─── Helper: LoginScreen in Test-App wrappen ────────────────────────
Widget createTestApp({required FakeAuthNotifier authNotifier}) {
  return ProviderScope(
    overrides: [
      authProvider.overrideWith(() => authNotifier),
    ],
    child: const MaterialApp(
      home: LoginScreen(),
    ),
  );
}

void main() {
  group('LoginScreen – UI-Elemente', () {
    testWidgets('zeigt App-Titel und Untertitel', (tester) async {
      await tester.pumpWidget(createTestApp(authNotifier: FakeAuthNotifier()));
      await tester.pumpAndSettle();

      expect(find.text('DualMind'), findsOneWidget);
      expect(find.text('Persönlicher Assistent'), findsOneWidget);
    });

    testWidgets('zeigt zwei Nutzer-Karten (Taake und Nina)', (tester) async {
      await tester.pumpWidget(createTestApp(authNotifier: FakeAuthNotifier()));
      await tester.pumpAndSettle();

      expect(find.text('Taake'), findsOneWidget);
      expect(find.text('Nina'), findsOneWidget);
    });

    testWidgets('zeigt Passwort-Feld', (tester) async {
      await tester.pumpWidget(createTestApp(authNotifier: FakeAuthNotifier()));
      await tester.pumpAndSettle();

      expect(find.widgetWithText(TextField, 'Passwort'), findsOneWidget);
    });

    testWidgets('zeigt Anmelden-Button', (tester) async {
      await tester.pumpWidget(createTestApp(authNotifier: FakeAuthNotifier()));
      await tester.pumpAndSettle();

      expect(find.widgetWithText(FilledButton, 'Anmelden'), findsOneWidget);
    });

    testWidgets('zeigt App-Icon', (tester) async {
      await tester.pumpWidget(createTestApp(authNotifier: FakeAuthNotifier()));
      await tester.pumpAndSettle();

      expect(find.byIcon(Icons.smart_toy), findsOneWidget);
    });
  });

  group('LoginScreen – Nutzer-Auswahl', () {
    testWidgets('kein Nutzer initial ausgewaehlt', (tester) async {
      await tester.pumpWidget(createTestApp(authNotifier: FakeAuthNotifier()));
      await tester.pumpAndSettle();

      // Beide Avatare sollten existieren
      expect(find.text('T'), findsOneWidget);
      expect(find.text('N'), findsOneWidget);
    });

    testWidgets('Nutzer-Karte anklickbar', (tester) async {
      await tester.pumpWidget(createTestApp(authNotifier: FakeAuthNotifier()));
      await tester.pumpAndSettle();

      await tester.tap(find.text('Taake'));
      await tester.pumpAndSettle();

      // Nach Tap sollte kein Fehler auftreten
      expect(find.text('Taake'), findsOneWidget);
    });
  });

  group('LoginScreen – Passwort-Sichtbarkeit', () {
    testWidgets('Passwort initial verdeckt', (tester) async {
      await tester.pumpWidget(createTestApp(authNotifier: FakeAuthNotifier()));
      await tester.pumpAndSettle();

      final textField = tester.widget<TextField>(find.byType(TextField));
      expect(textField.obscureText, isTrue);
    });

    testWidgets('Sichtbarkeits-Toggle wechselt obscureText', (tester) async {
      await tester.pumpWidget(createTestApp(authNotifier: FakeAuthNotifier()));
      await tester.pumpAndSettle();

      // Initial: visibility_off Icon
      expect(find.byIcon(Icons.visibility_off), findsOneWidget);

      // Tap auf Toggle
      await tester.tap(find.byIcon(Icons.visibility_off));
      await tester.pumpAndSettle();

      // Jetzt: visibility Icon sichtbar
      expect(find.byIcon(Icons.visibility), findsOneWidget);

      // TextField nicht mehr obscured
      final textField = tester.widget<TextField>(find.byType(TextField));
      expect(textField.obscureText, isFalse);
    });
  });

  group('LoginScreen – Validierung', () {
    testWidgets('Fehler wenn kein Nutzer ausgewaehlt', (tester) async {
      await tester.pumpWidget(createTestApp(authNotifier: FakeAuthNotifier()));
      await tester.pumpAndSettle();

      // Passwort eingeben, aber keinen Nutzer waehlen
      await tester.enterText(find.byType(TextField), 'geheim');
      await tester.tap(find.text('Anmelden'));
      await tester.pumpAndSettle();

      expect(find.text('Bitte Nutzer auswählen.'), findsOneWidget);
    });

    testWidgets('Fehler wenn Passwort leer', (tester) async {
      await tester.pumpWidget(createTestApp(authNotifier: FakeAuthNotifier()));
      await tester.pumpAndSettle();

      // Nutzer waehlen, aber kein Passwort
      await tester.tap(find.text('Taake'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Anmelden'));
      await tester.pumpAndSettle();

      expect(find.text('Bitte Passwort eingeben.'), findsOneWidget);
    });
  });

  group('LoginScreen – Login-Flow', () {
    testWidgets('erfolgreicher Login', (tester) async {
      final notifier = FakeAuthNotifier()..loginResult = true;
      await tester.pumpWidget(createTestApp(authNotifier: notifier));
      await tester.pumpAndSettle();

      await tester.tap(find.text('Taake'));
      await tester.pumpAndSettle();
      await tester.enterText(find.byType(TextField), 'geheim');
      await tester.tap(find.text('Anmelden'));
      await tester.pumpAndSettle();

      // Kein Fehler sichtbar
      expect(find.text('Falsches Passwort.'), findsNothing);
      expect(find.text('Bitte Nutzer auswählen.'), findsNothing);
    });

    testWidgets('fehlgeschlagener Login zeigt Fehler', (tester) async {
      final notifier = FakeAuthNotifier()..loginResult = false;
      await tester.pumpWidget(createTestApp(authNotifier: notifier));
      await tester.pumpAndSettle();

      await tester.tap(find.text('Nina'));
      await tester.pumpAndSettle();
      await tester.enterText(find.byType(TextField), 'falsch');
      await tester.tap(find.text('Anmelden'));
      await tester.pumpAndSettle();

      expect(find.text('Falsches Passwort.'), findsOneWidget);
    });

    testWidgets('Fehler-Text verschwindet bei Nutzer-Wechsel', (tester) async {
      final notifier = FakeAuthNotifier()..loginResult = false;
      await tester.pumpWidget(createTestApp(authNotifier: notifier));
      await tester.pumpAndSettle();

      // Fehlschlag provozieren
      await tester.tap(find.text('Taake'));
      await tester.pumpAndSettle();
      await tester.enterText(find.byType(TextField), 'falsch');
      await tester.tap(find.text('Anmelden'));
      await tester.pumpAndSettle();
      expect(find.text('Falsches Passwort.'), findsOneWidget);

      // Anderen Nutzer waehlen – Fehler sollte verschwinden
      await tester.tap(find.text('Nina'));
      await tester.pumpAndSettle();
      expect(find.text('Falsches Passwort.'), findsNothing);
    });
  });
}

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../services/weather_service.dart';
import '../providers/auth_provider.dart';

final weatherServiceProvider = Provider<WeatherService>((ref) {
  return WeatherService(ref.watch(apiServiceProvider));
});

final weatherCurrentProvider = FutureProvider.family<Map<String, dynamic>, String?>((ref, location) {
  return ref.read(weatherServiceProvider).getCurrent(location: location);
});

final weatherForecastProvider = FutureProvider.family<List<Map<String, dynamic>>, String?>((ref, location) {
  return ref.read(weatherServiceProvider).getForecast(location: location);
});

class WeatherScreen extends ConsumerStatefulWidget {
  const WeatherScreen({super.key});
  @override
  ConsumerState<WeatherScreen> createState() => _WeatherScreenState();
}

class _WeatherScreenState extends ConsumerState<WeatherScreen> {
  final _locationController = TextEditingController();
  String? _location;
  bool _loaded = false;

  @override
  void initState() {
    super.initState();
    _loadDefaultLocation();
  }

  Future<void> _loadDefaultLocation() async {
    final prefs = await SharedPreferences.getInstance();
    final saved = prefs.getString('weather_default_location');
    if (saved != null && saved.isNotEmpty) {
      _locationController.text = saved;
      _location = saved;
    }
    setState(() => _loaded = true);
  }

  Future<void> _saveAndSearch() async {
    final loc = _locationController.text.trim();
    final prefs = await SharedPreferences.getInstance();
    if (loc.isNotEmpty) {
      await prefs.setString('weather_default_location', loc);
    }
    setState(() => _location = loc.isEmpty ? null : loc);
    ref.invalidate(weatherCurrentProvider);
    ref.invalidate(weatherForecastProvider);
  }

  @override
  void dispose() {
    _locationController.dispose();
    super.dispose();
  }

  IconData _weatherIcon(String? condition) {
    final c = (condition ?? '').toLowerCase();
    if (c.contains('sun') || c.contains('clear')) return Icons.wb_sunny;
    if (c.contains('cloud') || c.contains('overcast')) return Icons.cloud;
    if (c.contains('rain') || c.contains('drizzle')) return Icons.water_drop;
    if (c.contains('snow')) return Icons.ac_unit;
    if (c.contains('storm') || c.contains('thunder')) return Icons.thunderstorm;
    if (c.contains('fog') || c.contains('mist')) return Icons.foggy;
    if (c.contains('wind')) return Icons.air;
    return Icons.wb_cloudy;
  }

  @override
  Widget build(BuildContext context) {
    if (!_loaded) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }

    final current = ref.watch(weatherCurrentProvider(_location));
    final forecast = ref.watch(weatherForecastProvider(_location));
    final cs = Theme.of(context).colorScheme;

    return Scaffold(
      appBar: AppBar(title: const Text('Wetter')),
      body: RefreshIndicator(
        onRefresh: () async {
          ref.invalidate(weatherCurrentProvider);
          ref.invalidate(weatherForecastProvider);
        },
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            // Location field
            Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _locationController,
                    decoration: const InputDecoration(
                      hintText: 'Standort eingeben...',
                      border: OutlineInputBorder(),
                      isDense: true,
                      prefixIcon: Icon(Icons.location_on_outlined),
                      contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                    ),
                    onSubmitted: (_) => _saveAndSearch(),
                  ),
                ),
                const SizedBox(width: 8),
                FilledButton(
                  onPressed: _saveAndSearch,
                  child: const Icon(Icons.search),
                ),
              ],
            ),
            const SizedBox(height: 16),

            // Current weather
            current.when(
              loading: () => const Center(child: Padding(
                padding: EdgeInsets.all(32),
                child: CircularProgressIndicator(),
              )),
              error: (e, _) => Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    children: [
                      const Icon(Icons.cloud_off, size: 48, color: Colors.grey),
                      const SizedBox(height: 8),
                      const Text('Wetterdaten konnten nicht geladen werden'),
                      const SizedBox(height: 8),
                      FilledButton(
                        onPressed: () {
                          ref.invalidate(weatherCurrentProvider);
                          ref.invalidate(weatherForecastProvider);
                        },
                        child: const Text('Erneut versuchen'),
                      ),
                    ],
                  ),
                ),
              ),
              data: (data) => _buildCurrentCard(data, cs),
            ),
            const SizedBox(height: 16),

            // Forecast
            Text('Vorhersage', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 8),
            forecast.when(
              loading: () => const Center(child: Padding(
                padding: EdgeInsets.all(16),
                child: CircularProgressIndicator(),
              )),
              error: (e, _) => const Card(
                child: Padding(
                  padding: EdgeInsets.all(16),
                  child: Text('Vorhersage nicht verfuegbar'),
                ),
              ),
              data: (days) => Column(
                children: days.map((day) => _buildForecastTile(day, cs)).toList(),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildCurrentCard(Map<String, dynamic> data, ColorScheme cs) {
    final temp = data['temperature'] ?? data['temp'];
    final desc = data['description'] ?? data['condition'] ?? '';
    final humidity = data['humidity'];
    final wind = data['wind'] ?? data['wind_speed'];
    final location = data['location'] ?? data['city'] ?? '';

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          children: [
            if (location.toString().isNotEmpty)
              Text(location.toString(), style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 8),
            Icon(_weatherIcon(desc.toString()), size: 64, color: cs.primary),
            const SizedBox(height: 8),
            Text(
              '${temp ?? '--'}\u00b0C',
              style: Theme.of(context).textTheme.displaySmall?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
            ),
            const SizedBox(height: 4),
            Text(desc.toString(), style: Theme.of(context).textTheme.bodyLarge),
            const SizedBox(height: 12),
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                if (humidity != null) ...[
                  const Icon(Icons.water_drop_outlined, size: 18),
                  const SizedBox(width: 4),
                  Text('$humidity%'),
                  const SizedBox(width: 16),
                ],
                if (wind != null) ...[
                  const Icon(Icons.air, size: 18),
                  const SizedBox(width: 4),
                  Text('$wind km/h'),
                ],
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildForecastTile(Map<String, dynamic> day, ColorScheme cs) {
    final date = day['date'] ?? '';
    final desc = day['description'] ?? day['condition'] ?? '';
    final minTemp = day['min_temp'] ?? day['temp_min'];
    final maxTemp = day['max_temp'] ?? day['temp_max'];

    return Card(
      child: ListTile(
        leading: Icon(_weatherIcon(desc.toString()), color: cs.primary),
        title: Text(date.toString()),
        subtitle: Text(desc.toString()),
        trailing: Text(
          '${minTemp ?? '--'}\u00b0 / ${maxTemp ?? '--'}\u00b0',
          style: const TextStyle(fontWeight: FontWeight.bold),
        ),
      ),
    );
  }
}

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../config/api_config.dart';

class WeatherScreen extends ConsumerStatefulWidget {
  const WeatherScreen({super.key});
  @override
  ConsumerState<WeatherScreen> createState() => _WeatherScreenState();
}

class _WeatherScreenState extends ConsumerState<WeatherScreen> {
  bool _loading = true;
  String? _error;
  Map<String, dynamic>? _weatherData;
  final _locationCtrl = TextEditingController(text: 'Schwerin');

  @override
  void initState() {
    super.initState();
    _loadWeather();
  }

  @override
  void dispose() {
    _locationCtrl.dispose();
    super.dispose();
  }

  Future<void> _loadWeather() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      // TODO: Implement API call via Dio/http provider
      // final data = await ref.read(apiProvider).get(
      //   '${ApiConfig.weatherCurrentPath}?location=${_locationCtrl.text}',
      // );
      // setState(() { _weatherData = data; _loading = false; });
      setState(() => _loading = false);
    } catch (e) {
      setState(() {
        _error = e.toString();
        _loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Wetter'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _loadWeather,
          ),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const Icon(Icons.cloud_off, size: 48, color: Colors.grey),
                      const SizedBox(height: 16),
                      Text(_error!, style: const TextStyle(color: Colors.grey)),
                      const SizedBox(height: 8),
                      FilledButton(
                        onPressed: _loadWeather,
                        child: const Text('Erneut versuchen'),
                      ),
                    ],
                  ),
                )
              : Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    children: [
                      Row(
                        children: [
                          Expanded(
                            child: TextField(
                              controller: _locationCtrl,
                              decoration: const InputDecoration(
                                hintText: 'Ort eingeben...',
                                border: OutlineInputBorder(),
                                isDense: true,
                              ),
                              onSubmitted: (_) => _loadWeather(),
                            ),
                          ),
                          const SizedBox(width: 8),
                          IconButton.filled(
                            onPressed: _loadWeather,
                            icon: const Icon(Icons.search),
                          ),
                        ],
                      ),
                      const SizedBox(height: 16),
                      const Expanded(
                        child: Center(
                          child: Text(
                            'Wetter-Daten werden hier angezeigt',
                            style: TextStyle(color: Colors.grey),
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
    );
  }
}

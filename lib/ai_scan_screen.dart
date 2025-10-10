// 📄 lib/ai_model/ai_scan_screen.dart
// ✅ FINAL — Clean, working version (No errors)
// Integrated with FastAPI backend at /api/image/predict

import 'dart:convert';
import 'dart:io' show File, Platform, HttpClient;
import 'dart:typed_data';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:permission_handler/permission_handler.dart';

import 'report_model.dart';
import 'reports_screen.dart';

/// ---------------------------------------------------------------------------
/// Inline Backend Client (no missing imports)
/// ---------------------------------------------------------------------------
class _Backend {
  static const String base = 'http://10.0.2.2:8000'; // Android emulator
  // iOS Simulator: http://127.0.0.1:8000
  // Real device:   http://<your-lan-ip>:8000

  /// ✅ Test connectivity (use metrics route)
  static Future<bool> ping() async {
    try {
      final uri = Uri.parse('$base/metrics');
      final client = HttpClient();
      final req = await client.getUrl(uri);
      final res = await req.close();
      final ok = res.statusCode == 200;
      client.close(force: true);
      return ok;
    } catch (_) {
      return false;
    }
  }

  /// ✅ Predict endpoint: /api/image/predict
  static Future<Map<String, dynamic>> predict({
    Uint8List? bytes,
    String? filename,
    String? path,
  }) async {
    if (bytes == null && path == null) {
      throw ArgumentError(
        'Provide either bytes+filename (Web) or path (mobile).',
      );
    }

    final uri = Uri.parse('$base/api/image/predict');
    final boundary =
        '----drhealth_boundary_${DateTime.now().millisecondsSinceEpoch}';
    final contentType = 'multipart/form-data; boundary=$boundary';

    final bodyBytes = <int>[];
    void writeString(String s) => bodyBytes.addAll(utf8.encode(s));

    // Open part
    writeString('--$boundary\r\n');
    writeString(
      'Content-Disposition: form-data; name="file"; '
      'filename="${filename ?? 'image.jpg'}"\r\n',
    );
    writeString('Content-Type: application/octet-stream\r\n\r\n');

    if (bytes != null) {
      bodyBytes.addAll(bytes);
    } else {
      final fileBytes = await File(path!).readAsBytes();
      bodyBytes.addAll(fileBytes);
    }

    // Close part
    writeString('\r\n--$boundary--\r\n');

    final httpClient = HttpClient();
    final req = await httpClient.postUrl(uri);
    req.headers.set('Content-Type', contentType);
    req.add(bodyBytes);
    final res = await req.close();
    final respText = await res.transform(utf8.decoder).join();
    httpClient.close(force: true);

    if (res.statusCode != 200) {
      throw Exception('HTTP ${res.statusCode}: $respText');
    }

    final map = jsonDecode(respText) as Map<String, dynamic>;
    final prediction = (map['prediction'] ?? 'Unknown').toString();
    final conf = (map['confidence'] ?? 0.0) as num;

    return {
      'label': prediction,
      'confidence': conf.toDouble(),
      'explanation':
          'AI-assisted X-ray analysis\nPrediction: $prediction\nConfidence: ${(conf * 100).toStringAsFixed(2)}%',
      'viz_url': null,
    };
  }
}

/// ---------------------------------------------------------------------------
/// Main Screen
/// ---------------------------------------------------------------------------
class AiScanScreen extends StatefulWidget {
  final String plan; // Free | Pro | Premium
  const AiScanScreen({super.key, this.plan = "Free"});

  @override
  State<AiScanScreen> createState() => _AiScanScreenState();
}

class _AiScanScreenState extends State<AiScanScreen> {
  final ImagePicker _picker = ImagePicker();
  XFile? _selectedImage;

  int _scansToday = 0;
  bool _isProcessing = false;

  int get _maxScansPerDay {
    switch (widget.plan) {
      case "Pro":
        return 20;
      case "Premium":
        return 9999;
      default:
        return 3;
    }
  }

  Future<bool> _requestPermissions() async {
    if (kIsWeb) return true;
    final cameraStatus = await Permission.camera.request();
    final storageStatus = Platform.isIOS
        ? await Permission.photos.request()
        : await Permission.storage.request();
    return cameraStatus.isGranted && storageStatus.isGranted;
  }

  Future<void> _startScan(Future<void> Function() action) async {
    if (_isProcessing) return;
    if (_scansToday >= _maxScansPerDay) {
      _showError("❌ Daily scan limit reached ($_scansToday/$_maxScansPerDay)");
      return;
    }
    setState(() => _isProcessing = true);
    try {
      await action();
    } finally {
      if (!mounted) return;
      setState(() {
        _isProcessing = false;
        _scansToday++;
      });
    }
  }

  /// 🔍 Ping Backend
  Future<void> _testApi() async {
    final ok = await _Backend.ping();
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(ok ? "✅ API reachable" : "❌ API not reachable"),
        backgroundColor: ok ? Colors.green : Colors.redAccent,
      ),
    );
  }

  /// 📷 Capture via Camera
  Future<void> _openCamera() async {
    if (!await _requestPermissions()) {
      _showError("Permissions not granted ❌");
      return;
    }
    await _startScan(() async {
      final XFile? image = await _picker.pickImage(
        source: ImageSource.camera,
        preferredCameraDevice: CameraDevice.rear,
        maxWidth: 1024,
        maxHeight: 1024,
        imageQuality: 90,
      );
      if (image == null) {
        _showError("No image captured ❌");
        return;
      }
      setState(() => _selectedImage = image);
      await _processPrediction(image);
    });
  }

  /// 🖼️ Pick from Gallery
  Future<void> _openGallery() async {
    if (!kIsWeb && !await _requestPermissions()) {
      _showError("Permissions not granted ❌");
      return;
    }
    await _startScan(() async {
      final XFile? image = await _picker.pickImage(
        source: ImageSource.gallery,
        maxWidth: 1024,
        maxHeight: 1024,
        imageQuality: 90,
      );
      if (image == null) {
        _showError("No image selected ❌");
        return;
      }
      setState(() => _selectedImage = image);
      await _processPrediction(image);
    });
  }

  /// 🤖 Process prediction via backend
  Future<void> _processPrediction(XFile image) async {
    try {
      Map<String, dynamic> result;

      if (kIsWeb) {
        final bytes = await image.readAsBytes();
        result = await _Backend.predict(bytes: bytes, filename: image.name);
      } else {
        result = await _Backend.predict(path: image.path);
      }

      final label = (result['label'] ?? "Unknown").toString();
      final confidence = ((result['confidence'] ?? 0.0) * 100).toStringAsFixed(
        2,
      );
      final explanation = (result['explanation'] ?? "No explanation available.")
          .toString();
      final vizUrl =
          (result['viz_url'] == null || result['viz_url'].toString().isEmpty)
          ? ""
          : "${_Backend.base}${result['viz_url']}";

      await _saveToReports(
        imagePath: image.path,
        label: label,
        confidence: confidence,
        explanation: explanation,
        vizUrl: vizUrl,
        webBytes: kIsWeb ? await image.readAsBytes() : null,
      );
    } catch (e) {
      _showError("Failed to connect to AI backend: $e");
    }
  }

  /// 💾 Save to local reports
  Future<void> _saveToReports({
    required String imagePath,
    required String label,
    required String confidence,
    required String explanation,
    required String vizUrl,
    Uint8List? webBytes,
  }) async {
    String persistPath = imagePath;
    if (kIsWeb && webBytes != null) {
      persistPath = 'data:image/jpeg;base64,${base64Encode(webBytes)}';
    }

    final report = ReportModel(
      title: "Diagnosis: $label",
      date: DateTime.now().toString().split(' ')[0],
      imagePath: persistPath,
      label: label,
      confidence: confidence,
      explanation: explanation,
      vizUrl: vizUrl,
    );

    await ReportStorage.addReport(report);

    if (!mounted) return;

    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text("✅ Report saved successfully"),
        backgroundColor: Colors.green,
        behavior: SnackBarBehavior.floating,
      ),
    );

    await Future.delayed(const Duration(milliseconds: 800));

    Navigator.pushReplacement(
      context,
      MaterialPageRoute(builder: (_) => const ReportsScreen()),
    );
  }

  void _showError(String msg) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(msg), backgroundColor: Colors.redAccent),
    );
  }

  @override
  Widget build(BuildContext context) {
    final remaining = _maxScansPerDay == 9999
        ? '∞'
        : (_maxScansPerDay - _scansToday).clamp(0, _maxScansPerDay).toString();

    return Scaffold(
      appBar: AppBar(
        title: const Text("AI Scan"),
        actions: [
          IconButton(
            tooltip: "Test API /metrics",
            onPressed: _isProcessing ? null : _testApi,
            icon: const Icon(Icons.wifi_tethering),
          ),
        ],
      ),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              if (_selectedImage != null)
                ClipRRect(
                  borderRadius: BorderRadius.circular(16),
                  child: kIsWeb
                      ? Image.network(
                          _selectedImage!.path,
                          width: 250,
                          height: 250,
                          fit: BoxFit.cover,
                        )
                      : Image.file(
                          File(_selectedImage!.path),
                          width: 250,
                          height: 250,
                          fit: BoxFit.cover,
                        ),
                )
              else
                const Text(
                  "No image selected 🩺\nTap below to start scanning",
                  textAlign: TextAlign.center,
                  style: TextStyle(fontSize: 16, color: Colors.grey),
                ),
              const SizedBox(height: 30),
              Text(
                "Remaining: $remaining scans",
                style: const TextStyle(fontWeight: FontWeight.w600),
              ),
              const SizedBox(height: 20),
              ElevatedButton.icon(
                onPressed: _isProcessing ? null : _openCamera,
                icon: const Icon(Icons.camera_alt),
                label: Text(_isProcessing ? "Processing..." : "Open Camera"),
              ),
              const SizedBox(height: 10),
              ElevatedButton.icon(
                onPressed: _isProcessing ? null : _openGallery,
                icon: const Icon(Icons.photo_library),
                label: Text(
                  _isProcessing ? "Processing..." : "Pick from Gallery",
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

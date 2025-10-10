// 📄 lib/ai_api.dart
import 'dart:convert';
import 'dart:typed_data';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:http/http.dart' as http;

class AIBackend {
  // ⚠️ Make sure this matches your Flask host/IP
  static const String base = "http://192.168.29.86:8000";

  static Uri _u(String path) => Uri.parse("$base$path");

  /// Simple GET /health
  static Future<bool> ping() async {
    try {
      final r = await http
          .get(_u("/health"))
          .timeout(const Duration(seconds: 5));
      return r.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  /// Universal multipart request:
  /// - Web: pass [bytes] and [filename]
  /// - Mobile/Desktop: pass [path]
  static Future<Map<String, dynamic>> predict({
    String? path,
    Uint8List? bytes,
    String filename = "image.jpg",
  }) async {
    final req = http.MultipartRequest('POST', _u('/predict'));

    if (kIsWeb) {
      if (bytes == null) {
        throw Exception("On Web, 'bytes' must be provided");
      }
      req.files.add(
        http.MultipartFile.fromBytes('file', bytes, filename: filename),
      );
    } else {
      if (path == null) {
        throw Exception("On Mobile/Desktop, 'path' must be provided");
      }
      req.files.add(await http.MultipartFile.fromPath('file', path));
    }

    final streamRes = await req.send();
    final res = await http.Response.fromStream(streamRes);

    if (res.statusCode == 200) {
      return json.decode(res.body) as Map<String, dynamic>;
    }
    throw Exception("Prediction failed: ${res.statusCode} ${res.body}");
  }
}

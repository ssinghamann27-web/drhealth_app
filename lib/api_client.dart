import 'dart:convert';
import 'dart:typed_data';
import 'dart:io' show File;
import 'package:http/http.dart' as http;

class ApiClient {
  // Android Emulator → http://10.0.2.2:8000
  // iOS Simulator  → http://127.0.0.1:8000
  // Real Device    → http://<YOUR_LAN_IP>:8000
  static const String baseUrl = 'http://10.0.2.2:8000';

  final Map<String, String> _headers = {'Accept': 'application/json'};

  Uri _u(String path) => Uri.parse('$baseUrl$path');

  // -------------------- Lab Analyzer --------------------
  Future<Map<String, dynamic>> labAnalyze(File file) async {
    final req = http.MultipartRequest('POST', _u('/api/lab/analyze'));
    req.files.add(await http.MultipartFile.fromPath('file', file.path));
    req.headers.addAll(_headers);
    return _jsonStream(await req.send());
  }

  Future<Map<String, dynamic>> labAnalyzeBytes(
    Uint8List bytes,
    String filename,
  ) async {
    final req = http.MultipartRequest('POST', _u('/api/lab/analyze'));
    req.files.add(
      http.MultipartFile.fromBytes('file', bytes, filename: filename),
    );
    req.headers.addAll(_headers);
    return _jsonStream(await req.send());
  }

  // -------------------- OCR Extract ---------------------
  Future<Map<String, dynamic>> ocrExtract(File file) async {
    final req = http.MultipartRequest('POST', _u('/api/ocr/extract'));
    req.files.add(await http.MultipartFile.fromPath('file', file.path));
    req.headers.addAll(_headers);
    return _jsonStream(await req.send());
  }

  Future<Map<String, dynamic>> ocrExtractBytes(
    Uint8List bytes,
    String filename,
  ) async {
    final req = http.MultipartRequest('POST', _u('/api/ocr/extract'));
    req.files.add(
      http.MultipartFile.fromBytes('file', bytes, filename: filename),
    );
    req.headers.addAll(_headers);
    return _jsonStream(await req.send());
  }

  // -------------------- Voice Transcribe ----------------
  Future<Map<String, dynamic>> voiceTranscribe(File file) async {
    final req = http.MultipartRequest('POST', _u('/api/voice/transcribe'));
    req.files.add(await http.MultipartFile.fromPath('file', file.path));
    req.headers.addAll(_headers);
    return _jsonStream(await req.send());
  }

  Future<Map<String, dynamic>> voiceTranscribeBytes(
    Uint8List bytes,
    String filename,
  ) async {
    final req = http.MultipartRequest('POST', _u('/api/voice/transcribe'));
    req.files.add(
      http.MultipartFile.fromBytes('file', bytes, filename: filename),
    );
    req.headers.addAll(_headers);
    return _jsonStream(await req.send());
  }

  // -------------------- Chat & Translate ----------------
  Future<Map<String, dynamic>> chatSymptoms(
    String question, {
    String lang = 'en',
  }) async {
    final res = await http.post(
      _u('/api/chat/symptoms'),
      headers: _headers,
      body: {'question': question, 'lang': lang},
    );
    return _json(res);
  }

  Future<Map<String, dynamic>> translate(String text, String targetLang) async {
    final res = await http.post(
      _u('/api/translate'),
      headers: _headers,
      body: {'text': text, 'target_lang': targetLang},
    );
    return _json(res);
  }

  // -------------------- Export PDF ----------------------
  Future<Uint8List> exportPdf(String title, String content) async {
    final req = http.MultipartRequest('POST', _u('/api/export/pdf'));
    req.fields['title'] = title;
    req.fields['content'] = content;
    req.headers.addAll(_headers);

    final streamed = await req.send();
    if (streamed.statusCode != 200) {
      final body = await streamed.stream.bytesToString();
      throw Exception('PDF export failed (${streamed.statusCode}): $body');
    }
    return Uint8List.fromList(await streamed.stream.toBytes());
  }

  // -------------------- Helpers -------------------------
  Map<String, dynamic> _json(http.Response res) {
    if (res.statusCode != 200) {
      throw Exception('HTTP ${res.statusCode}: ${res.body}');
    }
    final decoded = jsonDecode(res.body);
    if (decoded is Map<String, dynamic>) return decoded;
    throw Exception('Unexpected JSON: ${res.body}');
  }

  Future<Map<String, dynamic>> _jsonStream(http.StreamedResponse res) async {
    final body = await res.stream.bytesToString();
    if (res.statusCode != 200) {
      throw Exception('HTTP ${res.statusCode}: $body');
    }
    final decoded = jsonDecode(body);
    if (decoded is Map<String, dynamic>) return decoded;
    throw Exception('Unexpected JSON: $body');
  }
}

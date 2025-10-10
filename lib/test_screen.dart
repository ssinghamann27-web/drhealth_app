import 'dart:convert';
import 'dart:io' show File;
import 'dart:typed_data';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';

import 'api_client.dart';

class TestScreen extends StatefulWidget {
  const TestScreen({super.key});

  @override
  State<TestScreen> createState() => _TestScreenState();
}

class _TestScreenState extends State<TestScreen> {
  final ApiClient api = ApiClient();
  bool busy = false;
  String output = '';

  final titleCtrl = TextEditingController(text: 'AI Health Report');
  final contentCtrl = TextEditingController(text: 'Summary: Patient stable.');

  Future<void> _pickAndSend(
    Future<Map<String, dynamic>> Function(Uint8List, String) sender,
  ) async {
    if (kIsWeb) {
      _toast('⚠️ File picker is mobile/desktop only here.');
      return;
    }

    final picked = await FilePicker.platform.pickFiles(type: FileType.any);
    if (picked == null || picked.files.isEmpty) return;

    final path = picked.files.single.path;
    if (path == null) return;

    final bytes = await File(path).readAsBytes();
    final filename = p.basename(path);

    setState(() => busy = true);
    try {
      final res = await sender(bytes, filename);
      setState(() => output = _pretty(res));
    } catch (e) {
      setState(() => output = '❌ Error: $e');
    } finally {
      setState(() => busy = false);
    }
  }

  Future<void> _exportPdf() async {
    setState(() => busy = true);
    try {
      final bytes = await api.exportPdf(
        titleCtrl.text.trim(),
        contentCtrl.text.trim(),
      );

      if (kIsWeb) {
        setState(
          () => output =
              '✅ PDF generated (${bytes.lengthInBytes} bytes). Download manually.',
        );
      } else {
        final dir = await getApplicationDocumentsDirectory();
        final file = File(
          p.join(
            dir.path,
            'drhealth_report_${DateTime.now().millisecondsSinceEpoch}.pdf',
          ),
        );
        await file.writeAsBytes(bytes);
        setState(() => output = '✅ Saved: ${file.path}');
      }
    } catch (e) {
      setState(() => output = '❌ Export failed: $e');
    } finally {
      setState(() => busy = false);
    }
  }

  String _pretty(Map<String, dynamic> data) {
    try {
      return const JsonEncoder.withIndent('  ').convert(data);
    } catch (_) {
      return data.toString();
    }
  }

  void _toast(String msg) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(msg), behavior: SnackBarBehavior.floating),
    );
  }

  @override
  void dispose() {
    titleCtrl.dispose();
    contentCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final buttons = <Widget>[
      ElevatedButton(
        onPressed: busy ? null : () => _pickAndSend(api.labAnalyzeBytes),
        child: const Text('🧪 Lab Analyze'),
      ),
      ElevatedButton(
        onPressed: busy ? null : () => _pickAndSend(api.ocrExtractBytes),
        child: const Text('🔠 OCR Extract'),
      ),
      ElevatedButton(
        onPressed: busy
            ? null
            : () async {
                setState(() => busy = true);
                try {
                  final res = await api.chatSymptoms('I have fever');
                  setState(() => output = _pretty(res));
                } catch (e) {
                  setState(() => output = '❌ Error: $e');
                } finally {
                  setState(() => busy = false);
                }
              },
        child: const Text('💬 Chat Symptoms'),
      ),
      ElevatedButton(
        onPressed: busy
            ? null
            : () async {
                setState(() => busy = true);
                try {
                  final res = await api.translate('Hello', 'hi');
                  setState(() => output = _pretty(res));
                } catch (e) {
                  setState(() => output = '❌ Error: $e');
                } finally {
                  setState(() => busy = false);
                }
              },
        child: const Text('🌍 Translate'),
      ),
      ElevatedButton(
        onPressed: busy ? null : () => _pickAndSend(api.voiceTranscribeBytes),
        child: const Text('🎙️ Voice Transcribe'),
      ),
    ];

    return Scaffold(
      appBar: AppBar(
        title: const Text('DrHealth API Test'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: 'Clear Output',
            onPressed: busy ? null : () => setState(() => output = ''),
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Wrap(
              spacing: 12,
              runSpacing: 12,
              alignment: WrapAlignment.center,
              children: buttons
                  .map((w) => SizedBox(width: 220, child: w))
                  .toList(),
            ),
            const SizedBox(height: 20),
            const Divider(),
            const SizedBox(height: 12),
            TextField(
              controller: titleCtrl,
              decoration: const InputDecoration(
                labelText: 'Title',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 8),
            TextField(
              controller: contentCtrl,
              minLines: 2,
              maxLines: 6,
              decoration: const InputDecoration(
                labelText: 'Content',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 10),
            ElevatedButton.icon(
              icon: const Icon(Icons.picture_as_pdf),
              onPressed: busy ? null : _exportPdf,
              label: const Text('🧾 Export PDF'),
            ),
            const SizedBox(height: 16),
            if (busy)
              const Center(
                child: Padding(
                  padding: EdgeInsets.all(12),
                  child: CircularProgressIndicator(),
                ),
              ),
            const SizedBox(height: 12),
            const Text(
              'Output:',
              style: TextStyle(fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 6),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.black12,
                borderRadius: BorderRadius.circular(8),
              ),
              child: SelectableText(
                output.isEmpty ? '—' : output,
                style: const TextStyle(fontSize: 12, height: 1.4),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// 📄 lib/reports_screen.dart
import 'dart:io' show File;
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:share_plus/share_plus.dart';
import 'package:cross_file/cross_file.dart';

import 'report_model.dart';
import 'full_report_screen.dart'; // ✅ Added import

class ReportsScreen extends StatefulWidget {
  const ReportsScreen({super.key});

  @override
  State<ReportsScreen> createState() => _ReportsScreenState();
}

class _ReportsScreenState extends State<ReportsScreen> {
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _loadReports();
  }

  Future<void> _loadReports() async {
    await ReportStorage.loadReports();
    setState(() => _loading = false);
  }

  Future<void> _delete(int index) async {
    await ReportStorage.deleteReport(index);
    setState(() {});
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }

    final reports = ReportStorage.reports.reversed.toList();

    return Scaffold(
      appBar: AppBar(
        title: const Text("My Reports"),
        actions: [
          if (reports.isNotEmpty)
            IconButton(
              icon: const Icon(Icons.share),
              tooltip: "Share All",
              onPressed: () async {
                final paths = reports.map((e) => e.imagePath).toList();
                if (kIsWeb) {
                  await Share.share(paths.join("\n"));
                } else {
                  await Share.shareXFiles(paths.map((e) => XFile(e)).toList());
                }
              },
            ),
        ],
      ),
      body: reports.isEmpty
          ? const Center(
              child: Text(
                "No reports yet 🧠\nStart an AI scan to create one.",
                textAlign: TextAlign.center,
                style: TextStyle(color: Colors.grey),
              ),
            )
          : ListView.builder(
              itemCount: reports.length,
              padding: const EdgeInsets.all(12),
              itemBuilder: (_, i) {
                final r = reports[i];
                final isNet =
                    r.imagePath.startsWith("http") ||
                    r.imagePath.startsWith("data:");

                return Card(
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                  elevation: 4,
                  child: Padding(
                    padding: const EdgeInsets.all(10),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        ListTile(
                          contentPadding: EdgeInsets.zero,
                          leading: isNet
                              ? Image.network(
                                  r.imagePath,
                                  width: 60,
                                  height: 60,
                                  fit: BoxFit.cover,
                                )
                              : Image.file(
                                  File(r.imagePath),
                                  width: 60,
                                  height: 60,
                                  fit: BoxFit.cover,
                                ),
                          title: Text(
                            r.title,
                            style: const TextStyle(
                              fontWeight: FontWeight.bold,
                              fontSize: 16,
                            ),
                          ),
                          subtitle: Text(
                            "📅 ${r.date}\n🎯 ${r.confidence}%",
                            style: const TextStyle(height: 1.4),
                          ),
                          trailing: Wrap(
                            spacing: 8,
                            children: [
                              IconButton(
                                icon: const Icon(
                                  Icons.visibility,
                                  color: Colors.blue,
                                ),
                                tooltip: "View Report",
                                // ✅ Updated to open Full Report Screen
                                onPressed: () => Navigator.push(
                                  context,
                                  MaterialPageRoute(
                                    builder: (_) => FullReportScreen(
                                      report: r,
                                      index:
                                          ReportStorage.reports.length - 1 - i,
                                    ),
                                  ),
                                ),
                              ),
                              IconButton(
                                icon: const Icon(
                                  Icons.share,
                                  color: Colors.teal,
                                ),
                                tooltip: "Share",
                                onPressed: () async {
                                  if (kIsWeb) {
                                    await Share.share(r.imagePath);
                                  } else {
                                    await Share.shareXFiles([
                                      XFile(r.imagePath),
                                    ]);
                                  }
                                },
                              ),
                              IconButton(
                                icon: const Icon(
                                  Icons.delete,
                                  color: Colors.redAccent,
                                ),
                                tooltip: "Delete",
                                onPressed: () => _delete(
                                  ReportStorage.reports.length - 1 - i,
                                ),
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(height: 8),
                        // 🧠 Show Explanation
                        if (r.explanation.isNotEmpty)
                          Container(
                            width: double.infinity,
                            padding: const EdgeInsets.all(10),
                            decoration: BoxDecoration(
                              color: Colors.blueGrey.withOpacity(0.08),
                              borderRadius: BorderRadius.circular(8),
                            ),
                            child: Text(
                              "🧠 ${r.explanation}",
                              style: const TextStyle(fontSize: 14, height: 1.5),
                            ),
                          ),
                      ],
                    ),
                  ),
                );
              },
            ),
    );
  }
}

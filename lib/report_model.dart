// 📄 lib/report_model.dart
import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';

class ReportModel {
  final String title;
  final String date;
  final String imagePath;
  final String label;
  final String confidence;
  final String explanation;
  final String vizUrl;

  ReportModel({
    required this.title,
    required this.date,
    required this.imagePath,
    required this.label,
    required this.confidence,
    required this.explanation,
    required this.vizUrl,
  });

  Map<String, dynamic> toJson() => {
    'title': title,
    'date': date,
    'imagePath': imagePath,
    'label': label,
    'confidence': confidence,
    'explanation': explanation,
    'vizUrl': vizUrl,
  };

  factory ReportModel.fromJson(Map<String, dynamic> json) {
    return ReportModel(
      title: json['title'] ?? '',
      date: json['date'] ?? '',
      imagePath: json['imagePath'] ?? '',
      label: json['label'] ?? '',
      confidence: json['confidence'] ?? '',
      explanation: json['explanation'] ?? '',
      vizUrl: json['vizUrl'] ?? '',
    );
  }
}

class ReportStorage {
  static const String _key = "saved_reports";
  static List<ReportModel> reports = [];

  static Future<void> loadReports() async {
    final prefs = await SharedPreferences.getInstance();
    final jsonString = prefs.getString(_key);

    if (jsonString != null) {
      try {
        final decoded = jsonDecode(jsonString) as List;
        reports = decoded
            .map((e) => ReportModel.fromJson(e as Map<String, dynamic>))
            .toList();
        // ignore: avoid_print
        print("📦 Loaded ${reports.length} reports from storage");
      } catch (e) {
        // ignore: avoid_print
        print("❌ Failed to decode reports: $e");
        reports = [];
      }
    } else {
      // ignore: avoid_print
      print("📭 No saved reports found");
      reports = [];
    }
  }

  static Future<void> _saveAll() async {
    final prefs = await SharedPreferences.getInstance();
    final jsonString = jsonEncode(reports.map((e) => e.toJson()).toList());
    await prefs.setString(_key, jsonString);
    // ignore: avoid_print
    print("💾 Saved ${reports.length} reports to storage");
  }

  static Future<void> addReport(ReportModel report) async {
    reports.add(report);
    await _saveAll();
    // ignore: avoid_print
    print("➕ Added new report: ${report.title}");
  }

  static Future<void> deleteReport(int index) async {
    if (index >= 0 && index < reports.length) {
      // ignore: avoid_print
      print("🗑️ Deleted report: ${reports[index].title}");
      reports.removeAt(index);
      await _saveAll();
    } else {
      // ignore: avoid_print
      print("⚠️ Invalid index: $index");
    }
  }

  static Future<void> clearAll() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_key);
    reports.clear();
    // ignore: avoid_print
    print("🧹 Cleared all reports");
  }
}

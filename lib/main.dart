// 📄 lib/main.dart
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'theme_provider.dart';
import 'report_model.dart';
import 'login_page.dart';

Future<void> main() async {
  // ✅ Ensure everything ready
  WidgetsFlutterBinding.ensureInitialized();

  // ✅ Load saved reports before runApp
  await ReportStorage.loadReports();

  runApp(
    ChangeNotifierProvider(
      create: (_) => ThemeProvider(),
      child: const HealthApp(),
    ),
  );
}

class HealthApp extends StatelessWidget {
  const HealthApp({super.key});

  @override
  Widget build(BuildContext context) {
    final themeProvider = Provider.of<ThemeProvider>(context);

    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'Health App',
      themeMode: themeProvider.isDarkMode ? ThemeMode.dark : ThemeMode.light,
      theme: ThemeData(
        primarySwatch: Colors.blue,
        brightness: Brightness.light,
        snackBarTheme: const SnackBarThemeData(
          behavior: SnackBarBehavior.floating,
        ),
      ),
      darkTheme: ThemeData(
        brightness: Brightness.dark,
        colorScheme: const ColorScheme.dark(primary: Colors.blueAccent),
      ),
      home: const LoginPage(),
    );
  }
}

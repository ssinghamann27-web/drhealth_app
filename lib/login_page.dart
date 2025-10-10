import 'package:flutter/material.dart';
import 'signup_page.dart';
import 'forgot_password_page.dart';
import 'home_page.dart';
import 'doctor_signup_page.dart'; // ✅ Added Import

class LoginPage extends StatefulWidget {
  const LoginPage({super.key});

  @override
  State<LoginPage> createState() => _LoginPageState();
}

class _LoginPageState extends State<LoginPage> {
  final _formKey = GlobalKey<FormState>();
  final TextEditingController _emailCtrl = TextEditingController();
  final TextEditingController _passCtrl = TextEditingController();
  bool _obscure = true;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Padding(
        padding: const EdgeInsets.all(20.0),
        child: Center(
          child: SingleChildScrollView(
            child: Form(
              key: _formKey,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  // 🧠💻 App Icon (Added at top center)
                  Center(
                    child: Container(
                      decoration: BoxDecoration(
                        boxShadow: [
                          BoxShadow(
                            color: Colors.blue.withOpacity(0.6),
                            blurRadius: 40,
                            spreadRadius: 10,
                          ),
                        ],
                      ),
                      child: Image.asset(
                        'assets/images/dr_health_logo.png',
                        height: 120,
                        width: 120,
                      ),
                    ),
                  ),
                  const SizedBox(height: 25),

                  const Text(
                    "Welcome Back 👋",
                    textAlign: TextAlign.center,
                    style: TextStyle(fontSize: 28, fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 10),
                  const Text(
                    "Login to continue",
                    textAlign: TextAlign.center,
                    style: TextStyle(fontSize: 16, color: Colors.grey),
                  ),
                  const SizedBox(height: 30),

                  // 📧 Email
                  TextFormField(
                    controller: _emailCtrl,
                    decoration: const InputDecoration(
                      labelText: "Email",
                      prefixIcon: Icon(Icons.email),
                      border: OutlineInputBorder(),
                    ),
                    validator: (value) =>
                        value!.isEmpty ? "Enter your email" : null,
                  ),
                  const SizedBox(height: 20),

                  // 🔒 Password
                  TextFormField(
                    controller: _passCtrl,
                    obscureText: _obscure,
                    decoration: InputDecoration(
                      labelText: "Password",
                      prefixIcon: const Icon(Icons.lock),
                      suffixIcon: IconButton(
                        icon: Icon(
                          _obscure ? Icons.visibility : Icons.visibility_off,
                        ),
                        onPressed: () {
                          setState(() => _obscure = !_obscure);
                        },
                      ),
                      border: const OutlineInputBorder(),
                    ),
                    validator: (value) =>
                        value!.isEmpty ? "Enter your password" : null,
                  ),

                  const SizedBox(height: 10),

                  // 🔁 Forgot Password
                  Align(
                    alignment: Alignment.centerRight,
                    child: TextButton(
                      onPressed: () {
                        Navigator.push(
                          context,
                          MaterialPageRoute(
                            builder: (context) => const ForgotPasswordPage(),
                          ),
                        );
                      },
                      child: const Text("Forgot Password?"),
                    ),
                  ),

                  const SizedBox(height: 20),

                  // 🔘 Login Button
                  ElevatedButton(
                    onPressed: () {
                      if (_formKey.currentState!.validate()) {
                        Navigator.pushReplacement(
                          context,
                          MaterialPageRoute(
                            builder: (context) => const HomePage(),
                          ),
                        );
                      }
                    },
                    style: ElevatedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(vertical: 16),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12),
                      ),
                    ),
                    child: const Text("Login"),
                  ),

                  const SizedBox(height: 20),

                  // 👤 User Signup Redirect
                  Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const Text("Don’t have an account?"),
                      TextButton(
                        onPressed: () {
                          Navigator.push(
                            context,
                            MaterialPageRoute(
                              builder: (context) => const SignupPage(),
                            ),
                          );
                        },
                        child: const Text("Sign Up"),
                      ),
                    ],
                  ),

                  // 👨‍⚕️ Doctor Signup
                  const SizedBox(height: 8),
                  Center(
                    child: TextButton.icon(
                      icon: const Icon(Icons.medical_services,
                          color: Colors.blueAccent),
                      label: const Text(
                        "Register as Doctor",
                        style: TextStyle(color: Colors.blueAccent),
                      ),
                      onPressed: () {
                        Navigator.push(
                          context,
                          MaterialPageRoute(
                            builder: (_) => const DoctorSignupPage(),
                          ),
                        );
                      },
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

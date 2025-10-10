import 'package:flutter/material.dart';
import 'doctor_dashboard_page.dart'; // ✅ Doctor Dashboard after signup

class DoctorSignupPage extends StatefulWidget {
  const DoctorSignupPage({super.key});

  @override
  State<DoctorSignupPage> createState() => _DoctorSignupPageState();
}

class _DoctorSignupPageState extends State<DoctorSignupPage> {
  final _formKey = GlobalKey<FormState>();

  // Controllers
  final TextEditingController _nameCtrl = TextEditingController();
  final TextEditingController _emailCtrl = TextEditingController();
  final TextEditingController _passwordCtrl = TextEditingController();
  final TextEditingController _regNumberCtrl = TextEditingController();
  final TextEditingController _specialityCtrl = TextEditingController();
  final TextEditingController _experienceCtrl = TextEditingController();
  final TextEditingController _clinicCtrl = TextEditingController();

  bool _obscure = true;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("Doctor Registration")),
      body: Padding(
        padding: const EdgeInsets.all(20.0),
        child: SingleChildScrollView(
          child: Form(
            key: _formKey,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                const Text(
                  "Register as Doctor 👨‍⚕️",
                  textAlign: TextAlign.center,
                  style: TextStyle(fontSize: 26, fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 20),

                // Name
                TextFormField(
                  controller: _nameCtrl,
                  decoration: const InputDecoration(
                    labelText: "Full Name",
                    prefixIcon: Icon(Icons.person),
                    border: OutlineInputBorder(),
                  ),
                  validator: (v) =>
                      v!.isEmpty ? "Please enter your full name" : null,
                ),
                const SizedBox(height: 16),

                // Email
                TextFormField(
                  controller: _emailCtrl,
                  decoration: const InputDecoration(
                    labelText: "Email Address",
                    prefixIcon: Icon(Icons.email),
                    border: OutlineInputBorder(),
                  ),
                  validator: (v) =>
                      v!.isEmpty ? "Please enter your email" : null,
                ),
                const SizedBox(height: 16),

                // Password
                TextFormField(
                  controller: _passwordCtrl,
                  obscureText: _obscure,
                  decoration: InputDecoration(
                    labelText: "Password",
                    prefixIcon: const Icon(Icons.lock),
                    suffixIcon: IconButton(
                      icon: Icon(
                        _obscure ? Icons.visibility : Icons.visibility_off,
                      ),
                      onPressed: () => setState(() => _obscure = !_obscure),
                    ),
                    border: const OutlineInputBorder(),
                  ),
                  validator: (v) =>
                      v!.isEmpty ? "Please enter a password" : null,
                ),
                const SizedBox(height: 16),

                // Registration Number
                TextFormField(
                  controller: _regNumberCtrl,
                  decoration: const InputDecoration(
                    labelText: "Medical Registration Number",
                    prefixIcon: Icon(Icons.badge),
                    border: OutlineInputBorder(),
                  ),
                  validator: (v) => v!.isEmpty
                      ? "Please enter your registration number"
                      : null,
                ),
                const SizedBox(height: 16),

                // Specialization
                TextFormField(
                  controller: _specialityCtrl,
                  decoration: const InputDecoration(
                    labelText: "Specialization (e.g. Cardiologist)",
                    prefixIcon: Icon(Icons.local_hospital),
                    border: OutlineInputBorder(),
                  ),
                  validator: (v) =>
                      v!.isEmpty ? "Please enter specialization" : null,
                ),
                const SizedBox(height: 16),

                // Experience
                TextFormField(
                  controller: _experienceCtrl,
                  keyboardType: TextInputType.number,
                  decoration: const InputDecoration(
                    labelText: "Experience (Years)",
                    prefixIcon: Icon(Icons.work),
                    border: OutlineInputBorder(),
                  ),
                  validator: (v) =>
                      v!.isEmpty ? "Please enter experience" : null,
                ),
                const SizedBox(height: 16),

                // Clinic Name / Address
                TextFormField(
                  controller: _clinicCtrl,
                  decoration: const InputDecoration(
                    labelText: "Clinic / Hospital Name",
                    prefixIcon: Icon(Icons.location_on),
                    border: OutlineInputBorder(),
                  ),
                  validator: (v) =>
                      v!.isEmpty ? "Please enter clinic/hospital" : null,
                ),
                const SizedBox(height: 24),

                // Submit Button
                ElevatedButton.icon(
                  icon: const Icon(Icons.medical_information),
                  label: const Text("Sign Up as Doctor"),
                  style: ElevatedButton.styleFrom(
                    padding: const EdgeInsets.symmetric(vertical: 16),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12),
                    ),
                    backgroundColor: Colors.blueAccent,
                  ),
                  onPressed: () {
                    if (_formKey.currentState!.validate()) {
                      // ✅ Dummy success (no Firebase yet)
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(
                          content: Text("✅ Doctor Registered Successfully!"),
                        ),
                      );

                      // ✅ Navigate to Doctor Dashboard
                      Navigator.pushReplacement(
                        context,
                        MaterialPageRoute(
                          builder: (context) => const DoctorDashboardPage(),
                        ),
                      );
                    }
                  },
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

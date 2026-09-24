# Demo Vulnerable Repository

This repository contains intentional security vulnerabilities for testing SecureAgent:
- **CWE-89**: SQL Injection in `/user` endpoint
- **CWE-798**: Use of Hardcoded Credentials in `DATABASE_API_KEY`
- **CWE-79**: Cross-Site Scripting (XSS) via `render_template_string` in `/greet`
- **CWE-502**: Deserialization of Untrusted Data via `pickle.loads`
- Outdated Python dependencies in `requirements.txt`

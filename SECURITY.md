# Security Policy

## Supported Versions

We release patches for security vulnerabilities in the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 2.1.x   | :white_check_mark: |
| 2.0.x   | :white_check_mark: |
| < 2.0   | :x:                |

## Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

If you discover a security vulnerability in ePACK, please report it responsibly:

### Preferred Method

Email your findings to: **security@epack.app** (or the project maintainer's email)

### What to Include

Please include as much information as possible:

1. **Type of vulnerability** (e.g., SQL injection, XSS, authentication bypass)
2. **Full path** of source file(s) related to the vulnerability
3. **Location** of the affected source code (tag/branch/commit)
4. **Step-by-step instructions** to reproduce the issue
5. **Proof-of-concept or exploit code** (if possible)
6. **Impact** of the vulnerability
7. **Suggested fix** (if you have one)

### Response Timeline

- **Initial response**: Within 48 hours
- **Status update**: Within 7 days
- **Fix timeline**: Depends on severity (see below)

### Severity Levels

| Severity | Description | Response Time |
|----------|-------------|---------------|
| **Critical** | Remote code execution, authentication bypass, data breach | 24-48 hours |
| **High** | Privilege escalation, SQL injection, XSS | 3-7 days |
| **Medium** | CSRF, information disclosure | 14 days |
| **Low** | Minor issues with low impact | 30 days |

## Security Best Practices

### For Users

1. **Keep ePACK updated** to the latest version
2. **Use strong SECRET_KEY** in production (never use default)
3. **Enable HTTPS** for production deployments
4. **Restrict database access** to localhost only
5. **Review OAuth credentials** and keep them secure
6. **Monitor logs** for suspicious activity
7. **Use environment variables** for sensitive configuration (never commit .env files)

### For Developers

#### Authentication & Authorization

```python
# ✅ Good: Use environment variables
SECRET_KEY = os.getenv('SECRET_KEY')

# ❌ Bad: Hardcoded secrets
SECRET_KEY = 'hardcoded-secret-key'
```

#### Input Validation

```python
# ✅ Good: Validate and sanitize input
from werkzeug.utils import secure_filename

filename = secure_filename(user_input)
if not allowed_file(filename):
    raise ValueError("Invalid file type")
```

#### SQL Injection Prevention

```python
# ✅ Good: Use parameterized queries
cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))

# ❌ Bad: String concatenation
cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")
```

#### XSS Prevention

```typescript
// ✅ Good: Use React's built-in XSS protection
<div>{userContent}</div>

// ❌ Bad: Dangerous HTML injection
<div dangerouslySetInnerHTML={{__html: userContent}} />
```

#### CORS Configuration

```python
# ✅ Good: Restrict origins in production
CORS(app, origins=['https://yourdomain.com'])

# ❌ Bad: Allow all origins
CORS(app, origins='*')
```

#### File Upload Security

```python
# ✅ Good: Validate file type and size
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov'}
MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
```

## Security Features

### Current Implementations

- ✅ **OAuth 2.0**: Secure Google authentication
- ✅ **Encrypted credentials**: Using Fernet symmetric encryption
- ✅ **RSA license validation**: Secure license management
- ✅ **Environment-based configuration**: No hardcoded secrets
- ✅ **SQLite WAL mode**: Database integrity
- ✅ **Input sanitization**: Secure filename handling
- ✅ **CSRF protection**: Flask-WTF integration ready

### Planned Improvements

- ⏳ **Rate limiting**: API request throttling
- ⏳ **2FA support**: Two-factor authentication
- ⏳ **Security headers**: HSTS, CSP, X-Frame-Options
- ⏳ **Audit logging**: Security event tracking
- ⏳ **Content Security Policy**: XSS protection
- ⏳ **Dependency scanning**: Automated vulnerability checks

## Known Security Considerations

### Development Mode

- **Flask development server** is not secure for production
  - ✅ **Solution**: Use Gunicorn with gevent workers (see Dockerfile)

### Database

- **SQLite** is suitable for single-user desktop application
  - ⚠️ **Note**: For multi-user production, consider PostgreSQL

### File Storage

- **Local file storage** may expose uploaded videos
  - ✅ **Mitigation**: Files stored in `var/uploads/` with access control
  - 🔄 **Future**: Implement cloud storage with signed URLs

### API Security

- **No built-in rate limiting** for API endpoints
  - 🔄 **TODO**: Implement rate limiting (Flask-Limiter)

## Security Checklist for Deployment

### Production Environment

- [ ] Change default SECRET_KEY
- [ ] Enable HTTPS with valid SSL certificate
- [ ] Configure firewall to restrict access
- [ ] Disable debug mode (FLASK_ENV=production)
- [ ] Use environment variables for all secrets
- [ ] Set up regular backups
- [ ] Configure log rotation
- [ ] Review CORS origins
- [ ] Set up monitoring and alerting
- [ ] Run security audit (npm audit, safety check)

### Docker Deployment

- [ ] Use non-root user in containers
- [ ] Scan images for vulnerabilities (Trivy, Snyk)
- [ ] Use secrets management (Docker secrets, Kubernetes secrets)
- [ ] Limit container resources
- [ ] Use read-only filesystems where possible
- [ ] Keep base images updated

## Security Updates

We regularly update dependencies to patch known vulnerabilities:

- **Dependabot**: Automated dependency updates
- **GitHub Security Advisories**: Monitoring for CVEs
- **npm audit**: Frontend dependency scanning
- **Safety**: Backend dependency scanning

## Disclosure Policy

When a security issue is reported:

1. **Acknowledgment**: We acknowledge receipt within 48 hours
2. **Investigation**: We investigate and validate the issue
3. **Fix development**: We develop and test a fix
4. **Coordinated disclosure**: We work with the reporter on disclosure timeline
5. **Public disclosure**: After fix is released, we publish security advisory
6. **Credit**: Reporter is credited (unless they prefer to remain anonymous)

## Security Hall of Fame

We thank the following security researchers who have helped improve ePACK:

*(No reports yet)*

## Contact

For security-related questions or concerns:

- **Email**: security@epack.app (or maintainer email)
- **PGP Key**: [Link to PGP key if available]
- **Response time**: 48 hours for initial response

## Additional Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Flask Security Best Practices](https://flask.palletsprojects.com/en/latest/security/)
- [Next.js Security Headers](https://nextjs.org/docs/advanced-features/security-headers)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)

---

Thank you for helping keep ePACK and our users safe! 🔒

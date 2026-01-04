# Resume Parser AI Agent - Production Ready

A high-performance resume parsing application with a modern web UI, LLM integration, and secure API key management. Parse bulk resumes to extract structured candidate information (name, email, phone, experience, qualifications, etc.).

## Features

- 🚀 **Fast batch processing** with concurrent file parsing
- 📊 **Modern responsive web UI** with real-time progress tracking
- 🤖 **LLM-assisted extraction** (GPT-4o-mini, Grok, etc.)
- 🔐 **Server-side encrypted key storage** with MASTER_KEY support
- 🌓 **Dark/Light theme support** with enforced theme option
- 📥 **Export to Excel & JSON** formats
- 🎯 **10+ structured fields** extracted per resume
- 📝 **Supports PDF, DOCX, DOC, TXT** formats

## Installation

### Requirements
- Python 3.8+
- pip

### Setup

```bash
# Install dependencies
python -m pip install -r requirements.txt

# Generate encryption key (for server-side key storage)
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

## Usage

### Web Server (Recommended)

```bash
# Basic usage
python app.py

# With LLM API key stored in environment
set GROK_API_KEY=sk-...
python app.py

# With encrypted key storage and admin token
set MASTER_KEY=<generated-key-above>
set ADMIN_TOKEN=your-secret-token
python app.py

# Force dark theme globally
set DEFAULT_THEME=dark
python app.py
```

Visit: http://localhost:5050

### Command Line (Batch Processing)

```bash
# Parse directory of resumes
python resume_parser.py ./resumes output.xlsx output.json

# With LLM extraction enabled
set GROK_API_KEY=sk-...
python resume_parser.py ./resumes output.xlsx output.json --use-llm

# With concurrency control
python resume_parser.py ./resumes output.xlsx output.json --concurrency 8 --limit 100
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GROK_API_KEY` | - | OpenAI/Grok API key for LLM extraction |
| `GROK_API_URL` | https://api.openai.com/v1/chat/completions | LLM endpoint URL |
| `GROK_MODEL` | gpt-4o-mini | LLM model name |
| `MASTER_KEY` | - | Fernet encryption key for server-side key storage |
| `ADMIN_TOKEN` | - | Token for admin endpoints (set API key, delete, etc.) |
| `DEFAULT_THEME` | light | Enforce theme: `light`, `dark`, or unset |
| `PARSE_MAX_UPLOADS` | 500 | Max files per upload session |
| `PARSE_MAX_FILE_MB` | 5 | Max file size in MB |
| `PARSE_WORKERS` | 4 | Concurrent parser threads |
| `PARSE_LLM_CONCURRENCY` | 2 | Concurrent LLM requests |
| `PARSE_BATCH_SIZE` | 50 | Batch size for processing |
| `STORE_ORIGINALS` | 0 | Save original files (1=yes, 0=no) |

### Server-Side API Key Storage

For production, store API keys securely on the server:

```bash
# Generate a master key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Set environment variables
set MASTER_KEY=<generated-key>
set ADMIN_TOKEN=your-admin-token

# Store API key via admin endpoint
curl -X POST http://localhost:5050/admin/set_api_key \
  -H "X-ADMIN-TOKEN: your-admin-token" \
  -H "Content-Type: application/json" \
  -d '{"api_key":"sk-..."}'

# Check if key is stored
curl -X GET "http://localhost:5050/admin/has_api_key?admin_token=your-admin-token"

# Delete stored key
curl -X DELETE http://localhost:5050/admin/delete_api_key \
  -H "X-ADMIN-TOKEN: your-admin-token"
```

## Extracted Fields

Each resume is parsed to extract:
- `full_name` - Candidate's full name
- `email` - Email address
- `phone_number` - Primary phone (normalized)
- `alternate_phone_number` - Secondary phone (if present)
- `highest_qualification` - Highest degree (PhD, Masters, Bachelors, etc.)
- `years_of_experience` - Years of work experience (numeric)
- `current_company` - Most recent employer
- `current_designation` - Current job title
- `city` - Location city
- `state` - Location state/region

## Deployment

### Docker (Coming Soon)
```bash
docker build -t resume-parser .
docker run -p 5050:5050 -e GROK_API_KEY=sk-... resume-parser
```

### Production Best Practices

1. **Use HTTPS** - Run behind a reverse proxy (nginx, Apache)
2. **Secrets Management** - Use AWS Secrets Manager, Azure Key Vault, or HashiCorp Vault
3. **Rate Limiting** - Implement on reverse proxy to prevent abuse
4. **CORS** - Configure CORS headers for cross-origin requests
5. **Logging** - Enable structured logging for monitoring
6. **Monitoring** - Set up health checks at `/` endpoint
7. **Scaling** - Increase `PARSE_WORKERS` and `PARSE_LLM_CONCURRENCY` for high throughput

## API Endpoints

### Parse Resume
```
POST /parse
Content-Type: multipart/form-data

files: [resume files]
X-API-KEY: (optional) API key for LLM
X-MODEL: (optional) Model name
```

### Export Results
```
POST /export
Content-Type: application/json

{
  "data": [parsed resume objects]
}
```

### Admin - Set API Key
```
POST /admin/set_api_key
X-ADMIN-TOKEN: your-admin-token
Content-Type: application/json

{
  "api_key": "sk-..."
}
```

### Admin - Check API Key
```
GET /admin/has_api_key?admin_token=your-admin-token
```

### Admin - Delete API Key
```
DELETE /admin/delete_api_key
X-ADMIN-TOKEN: your-admin-token
```

## Troubleshooting

### Issue: "MASTER_KEY not set; persistent storage is disabled"
**Solution:** Generate and set `MASTER_KEY` environment variable, or set `GROK_API_KEY` instead.

### Issue: LLM extraction not working
**Solution:** Ensure `GROK_API_KEY` is set and valid. Check API endpoint with `GROK_API_URL`.

### Issue: Large file upload fails
**Solution:** Increase `PARSE_MAX_FILE_MB` environment variable.

### Issue: Slow parsing
**Solution:** Increase `PARSE_WORKERS` (default 4) to match CPU cores.

## Project Structure

```
.
├── app.py                  # Flask web server
├── resume_parser.py        # CLI batch parser
├── llm_helper.py          # LLM integration
├── secrets_store.py       # Encrypted key storage
├── requirements.txt       # Python dependencies
├── README.md              # This file
└── uploads/               # Generated resume previews (auto-created)
    └── originals/         # Original uploaded files (if STORE_ORIGINALS=1)
```

## Performance

- **Parsing Speed**: ~50-100 resumes/minute (single worker, depends on file size)
- **Concurrency**: Configurable workers (default 4) for parallel processing
- **LLM Rate Limit**: 2 concurrent LLM requests (adjust `PARSE_LLM_CONCURRENCY`)
- **Memory**: ~200MB for 100 resume batch (varies with file sizes)

## Contributing

Issues and pull requests welcome. Follow PEP 8 style guide.

## License

MIT License - See LICENSE file

## Support

For issues, questions, or feedback, please create an issue or contact the maintainer.

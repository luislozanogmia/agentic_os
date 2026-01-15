# Troubleshooting

## Common Issues

### 1. "AXErrorSuccess" or Permission Denied
- **Symptoms**: `ax-executor` fails to find elements or click.
- **Fix**: Ensure your Terminal/IDE has **Accessibility** permissions in System Settings. Restart the app after granting.

### 2. "osascript" is not allowed to send keystrokes
- **Symptoms**: Chrome control fails or keyboard shortcuts don't work.
- **Fix**: Ensure your Terminal/IDE has **Input Monitoring** permissions.

### 3. Missing API Keys
- **Symptoms**: `swarm-skill` or `W08` worker errors out.
- **Fix**: Check that `~/.claude/.env` exists and contains a valid `GROQ_API_KEY`.

### 4. Search function returns no results
- **Symptoms**: `search_function.py` fails to find known text.
- **Fix**: Verify that your documents are in `~/Documents/artificial_minds/` and are named correctly.

# Audit Monitor

To build audit monitor

> :paperclip: Note: the **nexus** configuration is optional 
```
py -m pip install [--trusted-host nexus.hostname.org.au --index-url "https://userid:password@nexus.hostname.org.au/repository/pypi-org/simple"] -r requirements.txt --target "./pylib"
```

To execute the audit monitor

```
py -X pylib src/monitor pylib 8083
```

# cURL / Smoke Tests

Health
```
curl http://localhost:5581/api/health
```

Upload
```
curl -F "file=@sample.pdf" http://localhost:5581/api/documents/upload
```

List Docs
```
curl http://localhost:5581/api/documents
```

Lines
```
curl "http://localhost:5581/api/documents/1/lines?limit=5&offset=0"
```

LLM Headers
```
curl -X POST http://localhost:5581/api/documents/1/headers/llm
curl http://localhost:5581/api/documents/1/headers
```

Chunking
```
curl -X POST http://localhost:5581/api/documents/1/chunk
curl http://localhost:5581/api/documents/1/chunks
```

Search
```
curl "http://localhost:5581/api/documents/1/search?q=vision"
```

Spec Extract
```
curl -X POST http://localhost:5581/api/documents/1/extract/specs
```

Status/Version
```
curl http://localhost:5581/api/documents/1/status
curl http://localhost:5581/api/version
```

# cURL Cheatsheet

Health:
```
curl http://localhost:5581/api/health
```

Upload:
```
curl -F "file=@sample.pdf" http://localhost:5581/api/documents/upload
```

Documents:
```
curl http://localhost:5581/api/documents
curl http://localhost:5581/api/documents/1
```

Lines:
```
curl "http://localhost:5581/api/documents/1/lines?limit=5&offset=0"
```

Headers LLM:
```
curl -X POST http://localhost:5581/api/documents/1/headers/llm
curl http://localhost:5581/api/documents/1/headers
```

Chunking:
```
curl -X POST http://localhost:5581/api/documents/1/chunk
curl http://localhost:5581/api/documents/1/chunks
curl http://localhost:5581/api/documents/1/chunks/301
```

Search:
```
curl "http://localhost:5581/api/documents/1/search?q=vision"
```

Specs:
```
curl -X POST http://localhost:5581/api/documents/1/extract/specs
```

Status & Version:
```
curl http://localhost:5581/api/documents/1/status
curl http://localhost:5581/api/version
```

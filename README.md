# speech_pool service

Python (>=3.6) test project


## Demo

- run service (it just converts text to uppercase):
```commandline
./run-speech-pool-srv.py --tts-api-url ignored --tts-api-limit=10 -v

```

- run client:
```commandline
./run-client-emulator.py --api-url http://localhost:8080/api/v1 -t "greeting message" -d 100

```

- you should see incoming data (letters in uppercase).
- if you run client with the same text again, data will be streamed from cache


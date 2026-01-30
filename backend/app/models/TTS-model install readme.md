## Usage:
Due to GitHub file upload limitations, tts_models will be uploaded to onedrive/sprint2 folder:

Extract tts_models to backend/app/models/
The specific folder structure is as follows:

backend/app/models/
├── __init__.py
├── __pycache__/
├── conversation.py
├── license_key.py
├── transcript.py
├── tts_models/
│   ├── EN/
│   │   ├── checkpoint.pth        (~198 MB)
│   │   └── config.json
│   └── ZH/
│       ├── checkpoint.pth         (~198 MB)
│       ├── config.json
│       └── pytorch_model.bin      (~641 MB)
└── user.py
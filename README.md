# HTTP File Server

## Instructions

Implementation details are written in the `HTTP File Server.docx` document

### Requirement

* `python 3.X`

## Run tests

### Locally on linux

1. Install dependencies: `pip install -r requirements.txt`
2. Run command: `python run.py main.py config.json`

### With Docker

1. Build `docker build -t image-name .`
2. Run `docker run -it -v "$(pwd)":/sandbox image-name`
<br> change  - "image-name"

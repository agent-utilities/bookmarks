# Bookmarks CLI

A command-line interface tool for managing bookmarks using JSONBin.io
as a backend but with flexibility to add oher backends. This CLI
provides an easy way to save and organize bookmarks while
automatically extracting metadata from various web sources.

## Features

- Store and organize bookmarks in JSONBin.io collections
- View bookmarks within predefined collections
- Add new bookmarks with automatic metadata extraction from URLs
- Smart source handling for different types of URLs (YouTube, Reddit, etc.)
- Interactive CLI with rich formatting and user prompts
- Configuration-driven collection management
- Secure API key management using environment variables

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd bookmarks
```

2. Install required dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the project root and add your JSONBin.io keys:
```bash
JSONBIN_API_KEY=your_api_key_here
JSONBIN_ACCESS_KEY=your_access_key_here
```

4. Configure your collections in `config.yaml`:
```yaml
jsonbin:
  base_url: "https://api.jsonbin.io/v3"
collections:
  collection_name:
    id: "your_collection_id_here"
    name: "Display Name"
    backend: "jsonbin"  # Optional, defaults to jsonbin
categories:
  - Technology
  - Programming
  - Design
  - Articles
  - Tools
  - Research
  - Other
```

## Usage

### List Bookmarks

View all bookmarks in a collection:

```bash
python bookmarks.py list collection_name [--ascending] [--all]
```

Options:
- `--ascending`: Sort in ascending order
- `--all`: Fetch all objects (not just first 10)

### Show Bookmark Details

View detailed information about a specific bookmark:

```bash
python bookmarks.py show collection_name object_id
```

This will display rich information including:
- Basic bookmark information
- Description and notes
- Source-specific metadata (YouTube, Reddit, etc.)
- System metadata (creation date, visibility, etc.)

### Add New Bookmark

Add a new bookmark interactively:

```bash
python bookmarks.py add collection_name
```

The CLI will:
1. Prompt for the URL
2. Automatically extract metadata based on the URL type
3. Allow you to review and customize the extracted information
4. Prompt for additional details like notes and category
5. Save the bookmark to JSONBin.io

### Delete Bookmark

Delete a specific bookmark:

```bash
python bookmarks.py delete collection_name object_id
```

## Project Structure

```
bookmarks/
├── bookmarks.py        # Main CLI implementation
├── sources.py          # URL source handlers
├── storage.py          # Storage backend implementations
├── config.yaml         # Configuration file
├── requirements.txt    # Python dependencies
├── .env               # Environment variables
└── README.md          # Documentation
```

### Key Components

1. `bookmarks.py`: Main CLI application
   - Implements commands (list, show, add, delete)
   - Handles user interaction using questionary
   - Formats output with rich formatting

2. `sources.py`: URL metadata extraction
   - Base Source class with factory method
   - Specialized handlers for different URL types:
     - YouTube (title, author, thumbnail)
     - Reddit (subreddit, score, author)
     - Twitter/X (currently unsupported)
     - Default (general webpage metadata)

3. `storage.py`: Storage backend interface
   - Abstract StorageBackend class
   - JsonBinBackend implementation
   - StorageManager for handling multiple backends

## Configuration

The `config.yaml` file requires:

```yaml
jsonbin:
  base_url: "https://api.jsonbin.io/v3"
collections:
  collection_name:
    id: "your_collection_id_here"
    name: "Display Name"
    backend: "jsonbin"  # Optional
categories:
  - Category1
  - Category2
  # ...
```

## Security

- API keys stored in `.env` file (not in repository)
- Private bins by default
- HTTPS used for all API communications
- API and Access keys passed securely in headers

## Requirements

Required Python packages:
- click
- python-dotenv
- requests
- PyYAML
- questionary
- newspaper3k
- tabulate

## Error Handling

The CLI includes comprehensive error handling for:
- Invalid URLs or unsupported sources
- Missing or invalid configuration
- API authentication issues
- Failed operations (add/list/show/delete)
- Metadata extraction failures

## License

MIT
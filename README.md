# JSONBin CLI

A command-line interface tool for managing collections and items in JSONBin.io. This CLI provides an easy way to interact with JSONBin.io's API, with a specific implementation for managing bookmarks.

## Features

- Manage JSONBin.io collections and bins
- View items within predefined collections
- Add new items interactively
- Configuration-driven collection management
- Secure API key management using environment variables
- Extensible architecture for different item types (currently implements bookmarks)

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

3. Install datasets
```
python3 -m spacy download en_core_web_sm
python3 -c "import nltk; nltk.download('punkt_tab')"
```

4. Create a `.env` file in the project root and add your JSONBin.io API key:
```bash
JSONBIN_API_KEY=your_api_key_here
JSONBIN_ACCESS_KEY=your_access_key_here
```

5. Configure your collections in `config.yaml`:
```yaml
jsonbin:
  base_url: "https://api.jsonbin.io/v3"
collections:
  tech_bookmarks:
    id: "your_collection_id_here"
    name: "Bookmarks"
  research_papers:
    id: "your_collection_id_here"
    name: "Papers"
categories:
  - Technology
  - Programming
  - Design
  - Articles
  - Tools
  - Research
  - Other
```

The `config.yaml` file is required and must contain:
- JSONBin.io API configuration
- Collection definitions (name and ID mappings)
- List of available categories for items

## Usage

### List Items in a Collection

View all items in a specific collection:

```bash
python bookmarks.py items tech_bookmarks
```

Example output:
```
URL: https://example.com
Text: Example Website
Category: Technology
Note: Interesting resource for future reference
---
```

### Add New Item

Add a new item interactively:

```bash
python bookmarks.py add tech_bookmarks
```

The CLI will prompt you for:
- URL
- Description
- Note (optional)
- Category (select from predefined list)

## Project Structure

```
jsonbin-cli/
├── bookmarks.py        # Bookmark-specific CLI implementation
├── libjsonbin.py       # Core JSONBin.io interaction library
├── config.yaml         # Configuration file (required)
├── requirements.txt    # Python dependencies
├── .env               # Environment variables (not in repo)
└── README.md          # This file
```

## Configuration

The `config.yaml` file is required and contains all necessary configuration:

```yaml
jsonbin:
  api_key: ${JSONBIN_API_KEY}
  base_url: "https://api.jsonbin.io/v3"
collections:
  collection_name:
    id: "your_collection_id_here"
    name: "Display Name"
categories:
  - Technology
  - Programming
  - Design
  - Articles
  - Tools
  - Research
  - Other
```

### Configuration Sections

1. `jsonbin`: API configuration
   - `api_key`: Referenced from environment variables
   - `base_url`: JSONBin.io API endpoint

2. `collections`: Mapping of collection names to their JSONBin.io IDs
   - Each collection needs a unique name (used in CLI commands)
   - Each collection needs its JSONBin.io ID
   - Optional display name for each collection

3. `categories`: List of predefined categories for bookmarks

## Development

### Project Components

1. `libjsonbin.py`:
   - Core library for JSONBin.io API interactions
   - Handles collection management and configuration
   - Processes API responses and errors

2. `bookmarks.py`:
   - Example implementation for bookmark management
   - Implements CLI commands using Click
   - Handles user interaction and input
   - Formats and displays output

### Creating New Implementations

The project is designed to be extensible. To create a new implementation:

1. Use `libjsonbin.py` as your core library
2. Create a new CLI file similar to `bookmarks.py`
3. Update configuration in `config.yaml` as needed

### Error Handling

The CLI includes error handling for:
- Missing or invalid configuration
- Invalid collection names
- Missing or invalid API keys
- Failed operations (add/list)

## Security

- API keys are stored in `.env` file (not in repository)
- Collection IDs are stored in configuration file
- HTTPS is used for all API communications
- API key is passed securely in headers

## Requirements

- Python 3.7+
- click==8.1.7
- python-dotenv==1.0.0
- requests==2.31.0
- PyYAML==6.0.1
- questionary==2.0.1

## License

MIT



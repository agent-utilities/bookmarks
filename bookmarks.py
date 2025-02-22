#!/usr/bin/env python3

import os
import json
from datetime import datetime
from typing import Dict, Any

import click
import questionary
import yaml
from dotenv import load_dotenv
from tabulate import tabulate
from sources import Source
from storage import StorageManager

from crawl import crawl

load_dotenv()

def format_bookmark_response(result: Dict[str, Any], backend_type: str, command: str = 'default') -> Dict[str, Any]:
    """
    Normalize response from different backends into a consistent format.
    Different commands may return different response structures.

    Args:
        result: Raw response from the backend
        backend_type: 'jsonbin' or 'supabase'
        command: Command type ('show', 'create', 'list', 'default')

    Returns:
        Normalized response dictionary
    """
    if backend_type == 'jsonbin':
        if command == 'list':
            return {
                'id': result['record'],
                'name': result.get('snippetMeta', {}).get('name'),
                'data': result['record'],
                'created_at': result['createdAt'],
                'is_private': result.get('private', True)
            }
        else:  # show, create, default
            return {
                'id': result['metadata']['id'],
                'name': result.get('snippetMeta', {}).get('name'),
                'data': result['record'],
                'created_at': result['metadata']['createdAt'],
                'is_private': result['metadata'].get('private', True)
            }

    elif backend_type == 'supabase':
        # Supabase response structure is consistent across commands
        data = result.get('data', {}) if isinstance(result.get('data'), dict) else {}
        return {
            'id': result['id'],
            'name': result['name'],
            'data': {
                'url': result['url'],
                'title': result['title'],
                'description': result['description'],
                'author': result['author'],
                'thumbnail': result['thumbnail'],
                'type': result['type'],
                'category': result['category'],
                'note': result.get('note'),
                'data': data  # Source-specific extra data
            },
            'created_at': result['created_at'],
            'is_private': True  # Supabase handles privacy through RLS
        }
    else:
        raise ValueError(f"Unknown backend type: {backend_type}")

def extract_source_data(bookmark: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract source-specific data from a bookmark.
    Handles both old and new data structures.
    """
    if 'data' in bookmark and isinstance(bookmark['data'], dict):
        # New structure where source data is in data field
        source_data = bookmark['data'].get('data', {})
        base_data = bookmark['data']
    else:
        # Old structure where everything is flat
        source_data = bookmark
        base_data = bookmark

    return {
        'base': base_data,
        'source': source_data,
        'type': base_data.get('type', 'generic')
    }


@click.group()
@click.option('--config', default='config.yaml', help='Path to config file')
@click.pass_context
def cli(ctx, config):
    """Bookmark Manager CLI"""
    with open(config, 'r') as f:
        config_data = yaml.safe_load(f)
    ctx.obj = StorageManager(config_data)


@cli.command()
@click.argument('collection_name')
@click.argument('object_id')
@click.pass_obj
def show(manager, collection_name, object_id):
    """Show detailed information about a bookmark"""
    backend = manager.get_backend(collection_name)
    collection_id = manager.config['collections'][collection_name]['id']
    backend_type = manager.config['collections'][collection_name]['backend']

    result = backend.read_object(collection_id, object_id)
    formatted = format_bookmark_response(result, backend_type, 'show')
    data = extract_source_data(formatted)

    # Create a clean layout with boxed sections
    click.echo("\n" + "=" * 50)
    click.echo(click.style(" 📚 Bookmark Details ", fg="blue", bold=True).center(50))
    click.echo("=" * 50 + "\n")

    # Basic Information
    click.echo(click.style("📌 Basic Information", fg="green", bold=True))
    click.echo("-" * 50)
    if formatted['name']:
        click.echo(f"Name:     {click.style(formatted['name'], bold=True)}")
    click.echo(f"URL:      {click.style(data['base']['url'], fg='blue', underline=True)}")
    click.echo(f"Category: {click.style(data['base']['category'], fg='yellow')}")

    # Description
    click.echo("\n" + click.style("📝 Description", fg="green", bold=True))
    click.echo("-" * 50)
    click.echo(data['base']['description'])

    # Notes (if any)
    if data['base'].get('note'):
        click.echo("\n" + click.style("📔 Notes", fg="green", bold=True))
        click.echo("-" * 50)
        click.echo(data['base']['note'])

    # Source-specific metadata
    click.echo("\n" + click.style("🔍 Source Details", fg="green", bold=True))
    click.echo("-" * 50)
    click.echo(f"Type: {click.style(data['type'], fg='magenta')}")

    if data['type'] == 'reddit':
        click.echo(f"Subreddit: r/{data['source'].get('subreddit')}")
        click.echo(f"Score:     {data['source'].get('score')}")
        if data['base'].get('author'):
            click.echo(f"Author:    u/{data['base']['author']}")

    elif data['type'] == 'youtube':
        if data['base'].get('author'):
            click.echo(f"Channel:    {data['base']['author']}")
        if data['base'].get('title'):
            click.echo(f"Title:      {data['base']['title']}")

    elif data['type'] == 'article':
        if data['base'].get('author'):
            click.echo(f"Author:     {data['base']['author']}")
        if data['base'].get('title'):
            click.echo(f"Title:      {data['base']['title']}")

    # System metadata
    click.echo("\n" + click.style("⚙️ System Metadata", fg="green", bold=True))
    click.echo("-" * 50)
    created_at = datetime.fromisoformat(formatted['created_at'].replace('Z', '+00:00'))
    click.echo(f"Created:   {created_at.strftime('%Y-%m-%d %H:%M:%S')}")
    click.echo(f"ID:        {formatted['id']}")
    click.echo(f"Visibility: {'Private' if formatted['is_private'] else 'Public'}")

    click.echo("\n" + "=" * 50 + "\n")

@cli.command("list")
@click.argument('collection_name')
@click.option('--ascending', is_flag=True, help='Sort in ascending order')
@click.option('--all', 'fetch_all', is_flag=True, help='Fetch all objects (not just first 10)')
@click.pass_obj
def _list(manager, collection_name, ascending, fetch_all):
    """List bookmarks in a collection"""
    backend = manager.get_backend(collection_name)
    collection_id = manager.config['collections'][collection_name]['id']
    backend_type = manager.config['collections'][collection_name]['backend']

    all_objects = []
    last_id = None

    while True:
        objects = backend.list_objects(collection_id, ascending, last_id)
        if not objects:
            break

        all_objects.extend(objects)

        if not fetch_all or len(objects) < 10:
            break

        last_id = format_bookmark_response(objects[-1], backend_type, 'list')['id']

    if not all_objects:
        click.echo(f"No bookmarks found in collection '{collection_name}'")
        return

    # Prepare table data
    table_data = []
    for obj in all_objects:
        formatted = format_bookmark_response(obj, backend_type, 'list')
        created_at = datetime.fromisoformat(formatted['created_at'].replace('Z', '+00:00'))

        table_data.append([
            formatted['id'],
            formatted['name'] or 'Unnamed',
            created_at.strftime('%Y-%m-%d %H:%M'),
            'Private' if formatted['is_private'] else 'Public'
        ])

    # Display table using tabulate
    headers = ['ID', 'Name', 'Created', 'Visibility']
    click.echo(tabulate(table_data, headers=headers, tablefmt='grid'))

@cli.command()
@click.argument('collection_name')
@click.pass_obj
def add(manager, collection_name):
    """Add a bookmark to a collection"""
    backend = manager.get_backend(collection_name)
    collection_id = manager.config['collections'][collection_name]['id']
    backend_type = manager.config['collections'][collection_name]['backend']

    url = questionary.text("Enter URL:").ask()

    # Extract metadata using source handler
    try:
        handler = Source.get_handler(url)
        metadata = handler.extract()
        click.echo(json.dumps(metadata, indent=4))

        name = metadata.get('title', url)
        if metadata.get('description'):
            use_auto = questionary.confirm(
                f"Use automatically generated description?\n{metadata['description']}",
                default=True
            ).ask()
            description = metadata['description'] if use_auto else questionary.text("Enter description:").ask()
        else:
            description = questionary.text("Enter description:").ask()

    except Exception as e:
        click.echo(f"Warning: Could not extract metadata: {str(e)}")
        description = questionary.text("Enter description:").ask()
        metadata = {}

    note = questionary.text("Enter note (optional):").ask()
    category = questionary.select(
        "Select category:",
        choices=manager.config['categories']
    ).ask()
    name = questionary.text("Enter bookmark name:", default=name).ask()

    bookmark_data = {
        "url": url,
        "name": name,
        "description": description,
        "category": category,
        "note": note,
        **metadata
    }

    result = backend.create_object(
        collection_id=collection_id,
        data=bookmark_data,
        name=name
    )

    formatted = format_bookmark_response(result, backend_type)

    click.echo("Bookmark added successfully!")
    click.echo(f"Collection: {collection_name}")
    click.echo(f"Object ID: {formatted['id']}")
    click.echo(f"Type: {metadata.get('type', 'generic')}")

# Add other commands
cli.add_command(crawl)

if __name__ == '__main__':
    cli()

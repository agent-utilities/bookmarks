#!/usr/bin/env python3

import os
import json

import click
import questionary
import yaml

from datetime import datetime

from dotenv import load_dotenv
from tabulate import tabulate
from sources import Source
from storage import StorageManager

load_dotenv()

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

    result = backend.read_object(collection_id, object_id)
    bookmark = result['record']
    metadata = result['metadata']

    # Create a clean layout with boxed sections
    click.echo("\n" + "=" * 50)
    click.echo(click.style(" 📚 Bookmark Details ", fg="blue", bold=True).center(50))
    click.echo("=" * 50 + "\n")

    # Basic Information
    click.echo(click.style("📌 Basic Information", fg="green", bold=True))
    click.echo("-" * 50)
    if metadata.get('name'):
        click.echo(f"Name:     {click.style(metadata['name'], bold=True)}")
    click.echo(f"URL:      {click.style(bookmark['url'], fg='blue', underline=True)}")
    click.echo(f"Category: {click.style(bookmark['category'], fg='yellow')}")

    # Description
    click.echo("\n" + click.style("📝 Description", fg="green", bold=True))
    click.echo("-" * 50)
    click.echo(bookmark['text'])

    # Notes (if any)
    if bookmark.get('note'):
        click.echo("\n" + click.style("📔 Notes", fg="green", bold=True))
        click.echo("-" * 50)
        click.echo(bookmark['note'])

    # Source-specific metadata
    click.echo("\n" + click.style("🔍 Source Details", fg="green", bold=True))
    click.echo("-" * 50)
    click.echo(f"Type: {click.style(bookmark.get('type', 'generic'), fg='magenta')}")

    if bookmark.get('type') == 'reddit':
        click.echo(f"Subreddit: r/{bookmark.get('subreddit')}")
        click.echo(f"Score:     {bookmark.get('score')}")
        if bookmark.get('author'):
            click.echo(f"Author:    u/{bookmark.get('author')}")

    elif bookmark.get('type') == 'youtube':
        if bookmark.get('author'):
            click.echo(f"Channel:    {bookmark.get('author')}")
        if bookmark.get('title'):
            click.echo(f"Title:      {bookmark.get('title')}")

    elif bookmark.get('type') == 'article':
        if bookmark.get('author'):
            click.echo(f"Author:     {bookmark.get('author')}")
        if bookmark.get('title'):
            click.echo(f"Title:      {bookmark.get('title')}")

    # System metadata
    click.echo("\n" + click.style("⚙️ System Metadata", fg="green", bold=True))
    click.echo("-" * 50)
    created_at = datetime.fromisoformat(metadata['createdAt'].replace('Z', '+00:00'))
    click.echo(f"Created:   {created_at.strftime('%Y-%m-%d %H:%M:%S')}")
    click.echo(f"ID:        {metadata['id']}")
    click.echo(f"Visibility: {'Private' if metadata['private'] else 'Public'}")

    click.echo("\n" + "=" * 50 + "\n")


@cli.command()
@click.argument('collection_name')
@click.pass_obj
def add(manager, collection_name):
    """Add a bookmark to a collection"""
    backend = manager.get_backend(collection_name)
    collection_id = manager.config['collections'][collection_name]['id']

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
            text = metadata['description'] if use_auto else questionary.text("Enter description:").ask()
        else:
            text = questionary.text("Enter description:").ask()

    except Exception as e:
        click.echo(f"Warning: Could not extract metadata: {str(e)}")
        text = questionary.text("Enter description:").ask()
        metadata = {}

    note = questionary.text("Enter note (optional):").ask()
    category = questionary.select(
        "Select category:",
        choices=manager.config['categories']
    ).ask()
    name = questionary.text("Enter bookmark name:", default=name).ask()

    bookmark_data = {
        "url": url,
        "text": text,
        "category": category,
        "note": note,
        **metadata
    }

    result = backend.create_object(
        collection_id=collection_id,
        data=bookmark_data,
        name=name
    )

    click.echo("Bookmark added successfully!")
    click.echo(f"Object ID: {result['metadata']['id']}")
    click.echo(f"Collection: {collection_name}")
    click.echo(f"Type: {metadata.get('type', 'generic')}")

@cli.command()
@click.argument('collection_name')
@click.argument('object_id')
@click.pass_obj
def delete(manager, collection_name, object_id):
    """Delete a bookmark"""
    if not click.confirm(f"Are you sure you want to delete bookmark {object_id}?"):
        click.echo("Deletion cancelled.")
        return

    backend = manager.get_backend(collection_name)
    collection_id = manager.config['collections'][collection_name]['id']

    result = backend.delete_object(collection_id, object_id)
    click.echo(f"Bookmark {object_id} deleted successfully!")

@cli.command("list")
@click.argument('collection_name')
@click.option('--ascending', is_flag=True, help='Sort in ascending order')
@click.option('--all', 'fetch_all', is_flag=True, help='Fetch all objects (not just first 10)')
@click.pass_obj
def _list(manager, collection_name, ascending, fetch_all):
    """List bookmarks in a collection"""
    backend = manager.get_backend(collection_name)
    collection_id = manager.config['collections'][collection_name]['id']

    all_objects = []
    last_id = None

    while True:
        objects = backend.list_objects(collection_id, ascending, last_id)
        if not objects:
            break

        all_objects.extend(objects)

        if not fetch_all or len(objects) < 10:
            break

        last_id = objects[-1].get('record')

    if not all_objects:
        click.echo(f"No bookmarks found in collection '{collection_name}'")
        return

    # Prepare table data
    table_data = []
    for obj in all_objects:
        created_at = datetime.fromisoformat(obj['createdAt'].replace('Z', '+00:00'))
        name = obj['snippetMeta'].get('name', 'Unnamed')
        record = obj['record']

        table_data.append([
            record,
            name,
            created_at.strftime('%Y-%m-%d %H:%M'),
            'Private' if obj['private'] else 'Public'
        ])

    # Display table using tabulate
    headers = ['ID', 'Name', 'Created', 'Visibility']
    click.echo(tabulate(table_data, headers=headers, tablefmt='grid'))

if __name__ == '__main__':
    cli()

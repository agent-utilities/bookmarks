#!/usr/bin/env python3

import yaml
import json

from urllib.parse import urlparse, parse_qs

import click

from youtube_transcript_api import YouTubeTranscriptApi
from newspaper import Article


from sources import Source
from storage import StorageManager

def get_youtube_id(url):
    """Extract YouTube video ID from URL"""
    if 'youtu.be' in url:
        return url.split('/')[-1].split('?')[0]
    else:
        parsed_url = urlparse(url)
        return parse_qs(parsed_url.query)['v'][0]

def crawl_youtube(url):
    """Get YouTube video transcript"""
    try:
        video_id = get_youtube_id(url)
        transcript = YouTubeTranscriptApi.get_transcript(video_id)

        # Combine all transcript texts
        full_text = ' '.join([entry['text'] for entry in transcript])

        return {
            'text': full_text,
            'source': 'youtube_transcript',
            'segments': transcript  # Keep the original segments for reference
        }
    except Exception as e:
        return {
            'text': f"Error fetching transcript: {str(e)}",
            'source': 'youtube_transcript',
            'error': str(e)
        }

def crawl_generic(url):
    """Crawl generic webpage using newspaper3k"""
    try:
        article = Article(url)
        article.download()
        article.parse()
        article.nlp()  # This gets summary, keywords etc.

        return {
            'text': article.text,
            'source': 'newspaper3k',
            'summary': article.summary,
            'keywords': article.keywords,
            'html': article.html  # Store original HTML for reference
        }
    except Exception as e:
        return {
            'text': f"Error crawling page: {str(e)}",
            'source': 'newspaper3k',
            'error': str(e)
        }

@click.command()
@click.argument('collection_name')
@click.argument('object_id')
@click.option('--config', default='config.yaml', help='Path to config file')
def crawl(collection_name, object_id, config):
    """Crawl and update content for a bookmark"""
    # Initialize storage manager
    with open(config, 'r') as f:
        config_data = yaml.safe_load(f)
    manager = StorageManager(config_data)

    # Get the bookmark
    backend = manager.get_backend(collection_name)
    collection_id = manager.config['collections'][collection_name]['id']
    result = backend.read_object(collection_id, object_id)
    bookmark = result['record']

    click.echo(f"Crawling content for bookmark: {bookmark['url']}")

    # Determine content type and crawl accordingly
    if bookmark.get('type') == 'youtube':
        content = crawl_youtube(bookmark['url'])
    else:
        content = crawl_generic(bookmark['url'])

    # Update the bookmark with new content
    bookmark['content'] = content
    backend.update_object(collection_id, object_id, bookmark)

    # Show summary of crawled content
    click.echo("\nCrawl Summary:")
    click.echo(f"Source: {content['source']}")
    if 'error' in content:
        click.echo(f"Error: {content['error']}")
    else:
        text_preview = content['text'][:200] + "..." if len(content['text']) > 200 else content['text']
        click.echo(f"Content preview: {text_preview}")

    click.echo("\nBookmark updated successfully!")

if __name__ == '__main__':
    crawl()

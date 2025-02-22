#!/usr/bin/env python3

import re
import traceback
from urllib.parse import urlparse
from abc import ABC, abstractmethod

from newspaper import Article
import requests

class Source(ABC):
    """Base class for all source handlers"""

    @classmethod
    def get_handler(cls, url):
        """
        Factory method to get the appropriate handler for a URL
        Returns an instance of the appropriate Source subclass
        """
        domain = urlparse(url).netloc.lower()

        # Check all subclasses to find a matching handler
        for handler in cls.__subclasses__():
            if handler.can_handle(domain):
                return handler(url)

        # If no specific handler found, return default handler
        return DefaultSource(url)

    def __init__(self, url):
        self.url = url
        self.domain = urlparse(url).netloc.lower()

    @classmethod
    @abstractmethod
    def can_handle(cls, domain):
        """
        Check if this handler can handle the given domain
        Must be implemented by subclasses
        """
        pass

    @abstractmethod
    def extract(self):
        """
        Extract metadata from the URL
        Returns a dict with at least 'description' key
        Other possible keys: 'author', 'title', 'thumbnail', etc.
        """
        pass


class YouTubeSource(Source):
    """Handler for YouTube URLs"""

    @classmethod
    def can_handle(cls, domain):
        return 'youtube.com' in domain or 'youtu.be' in domain

    def extract(self):
        # Extract video ID from various YouTube URL formats
        if 'youtu.be' in self.domain:
            video_id = self.url.split('/')[-1].split('?')[0]
        else:
            parsed_url = urlparse(self.url)
            path = parsed_url.path
            query = parsed_url.query

            # Handle different URL patterns
            if '/live/' in path:
                video_id = path.split('/live/')[-1].split('?')[0]
            elif '/shorts/' in path:
                video_id = path.split('/shorts/')[-1].split('?')[0]
            elif '/embed/' in path:
                video_id = path.split('/embed/')[-1].split('?')[0]
            elif 'v=' in query:
                video_id = parse_qs(query)['v'][0]
            else:
                raise ValueError("Could not extract YouTube video ID from URL")

        try:
            # Use oEmbed API (doesn't require API key)
            oembed_url = f"https://www.youtube.com/oembed?url={self.url}&format=json"
            response = requests.get(oembed_url)
            data = response.json()

            # Common fields go in the main table
            result = {
                'url': self.url,
                'title': data.get('title', ''),
                'description': data.get('title', ''),  # YouTube often has same title/description
                'author': data.get('author_name', ''),
                'thumbnail': data.get('thumbnail_url', ''),
                'type': 'youtube',
                # Extra data goes in the JSONB field
                'data': {
                    'video_id': video_id,
                    'provider_name': data.get('provider_name', ''),
                    'width': data.get('width'),
                    'height': data.get('height'),
                }
            }
            return result
        except Exception as e:
            return {
                'url': self.url,
                'title': f"YouTube video {video_id}",
                'description': f"YouTube video {video_id}",
                'type': 'youtube',
                'data': {
                    'video_id': video_id,
                    'error': str(e)
                }
            }

class RedditSource(Source):
    """Handler for Reddit URLs"""

    @classmethod
    def can_handle(cls, domain):
        return 'reddit.com' in domain

    def extract(self):
        # Extract post ID and subreddit
        reddit_pattern = r'reddit\.com/r/([^/]+)/comments/([^/]+)'
        match = re.search(reddit_pattern, self.url)

        if not match:
            raise ValueError("Invalid Reddit URL format")

        subreddit, post_id = match.groups()

        try:
            # Use Reddit's JSON API (doesn't require authentication)
            json_url = f"{self.url}.json"
            headers = {
                'User-Agent': 'Mozilla/5.0 (compatible; BookmarkManager/1.0)',
                'Accept': 'application/json'
            }
            response = requests.get(json_url, headers=headers)
            data = response.json()

            post_data = data[0]['data']['children'][0]['data']

            # Get comments if available
            comments = []
            if len(data) > 1:
                comments = self._extract_comments(data[1]['data']['children'])

            return {
                'url': self.url,
                'title': post_data.get('title', ''),
                'description': post_data.get('selftext', '')[:1000],  # Limit description length
                'author': post_data.get('author', ''),
                'thumbnail': post_data.get('thumbnail', '') if post_data.get('thumbnail', '').startswith('http') else None,
                'type': 'reddit',
                'data': {
                    'subreddit': subreddit,
                    'post_id': post_id,
                    'score': post_data.get('score', 0),
                    'upvote_ratio': post_data.get('upvote_ratio', 0),
                    'num_comments': post_data.get('num_comments', 0),
                    'comments': comments[:5],  # Store top 5 comments
                    'full_selftext': post_data.get('selftext', ''),  # Store full text in data
                }
            }
        except Exception as e:
            return {
                'url': self.url,
                'title': f"Reddit post in r/{subreddit}",
                'description': '',
                'type': 'reddit',
                'data': {
                    'subreddit': subreddit,
                    'post_id': post_id,
                    'error': str(e)
                }
            }

class DefaultSource(Source):
    """Default handler for URLs without a specific handler"""

    @classmethod
    def can_handle(cls, domain):
        return True  # Can handle any domain

    def extract(self):
        try:
            article = Article(self.url)
            article.download()
            article.parse()
            article.nlp()

            return {
                'url': self.url,
                'title': article.title,
                'description': article.summary[:1000] if article.summary else '',  # Limit description length
                'author': article.authors[0] if article.authors else None,
                'thumbnail': article.top_image if article.top_image else None,
                'type': 'article',
                'data': {
                    'keywords': article.keywords,
                    'publish_date': article.publish_date.isoformat() if article.publish_date else None,
                    'full_text': article.text,  # Store full text in data
                    'images': article.images,
                    'movies': article.movies,
                }
            }
        except Exception as e:
            traceback.print_exc()
            return {
                'url': self.url,
                'title': f"Content from {self.domain}",
                'description': '',
                'type': 'generic',
                'data': {
                    'error': str(e)
                }
            }

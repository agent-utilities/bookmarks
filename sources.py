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

class TwitterSource(Source):
    """Handler for Twitter/X URLs"""
    
    @classmethod
    def can_handle(cls, domain):
        return domain in ['twitter.com', 'x.com']
    
    def extract(self):
        twitter_pattern = r'(?:twitter\.com|x\.com)/([^/]+)/status/(\d+)'
        match = re.search(twitter_pattern, self.url)
        
        if not match:
            raise ValueError("Invalid Twitter URL format")

        raise ValueError("Twitter not supported")


class YouTubeSource(Source):
    """Handler for YouTube URLs"""
    
    @classmethod
    def can_handle(cls, domain):
        return 'youtube.com' in domain or 'youtu.be' in domain
    
    def extract(self):
        # Extract video ID
        if 'youtu.be' in self.domain:
            video_id = self.url.split('/')[-1].split('?')[0]
        else:
            query = urlparse(self.url).query
            video_id = re.search(r'v=([^&]+)', query).group(1)
        
        # TODO: Add YouTube API integration for better metadata
        # For now return basic info
        try:
            # Use oEmbed API (doesn't require API key)
            oembed_url = f"https://www.youtube.com/oembed?url={self.url}&format=json"
            response = requests.get(oembed_url)
            data = response.json()
            
            return {
                'description': data.get('title', ''),
                'author': data.get('author_name', ''),
                'title': data.get('title', ''),
                'thumbnail': data.get('thumbnail_url', ''),
                'type': 'youtube'
            }
        except Exception as e:
            return {
                'description': f"YouTube video {video_id}",
                'type': 'youtube'
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
            response = requests.get(json_url, headers={'User-Agent': 'Mozilla/5.0'})
            data = response.json()
            
            post_data = data[0]['data']['children'][0]['data']
            
            return {
                'description': post_data.get('title', ''),
                'author': post_data.get('author', ''),
                'subreddit': subreddit,
                'score': post_data.get('score', 0),
                'type': 'reddit'
            }
        except Exception as e:
            return {
                'description': f"Reddit post in r/{subreddit}",
                'type': 'reddit'
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
            
            description = article.summary
            return {
                'description': description or '',
                'author': article.authors[0] if article.authors else None,
                'title': article.title,
                'type': 'article'
            }
        except Exception as e:
            traceback.print_exc()
            return {
                'description': f"Content from {self.domain}",
                'type': 'generic'
            }

# Usage example:
if __name__ == '__main__':
    # Test URLs
    urls = [
        "https://twitter.com/username/status/123456789",
        "https://youtube.com/watch?v=dQw4w9WgXcQ",
        "https://reddit.com/r/Python/comments/abc123",
        "https://example.com/article"
    ]
    
    for url in urls:
        handler = Source.get_handler(url)
        print(f"\nProcessing {url}")
        print(f"Handler: {handler.__class__.__name__}")
        try:
            metadata = handler.extract()
            print(f"Metadata: {metadata}")
        except Exception as e:
            print(f"Error: {str(e)}")

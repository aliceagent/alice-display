#!/usr/bin/env python3
"""
Configuration template for Alice Gallery Integration
Copy this file to config_secrets.py and fill in your actual API keys.

IMPORTANT: config_secrets.py is git-ignored. Do not commit API keys to the repository.
"""

import os

# Cloudinary Configuration
# Get these from your Cloudinary dashboard
CLOUDINARY_CLOUD_NAME = os.environ.get("CLOUDINARY_CLOUD_NAME", "your_cloud_name")
CLOUDINARY_API_KEY = os.environ.get("CLOUDINARY_API_KEY", "your_api_key")
CLOUDINARY_API_SECRET = os.environ.get("CLOUDINARY_API_SECRET", "your_api_secret")

# Notion Configuration  
# Get these from your Notion integration settings
NOTION_DATABASE_ID = os.environ.get("NOTION_DATABASE_ID", "your_database_id")
NOTION_API_KEY = os.environ.get("NOTION_API_KEY", "your_notion_token")
NOTION_VERSION = "2022-06-28"

# Alternative: Set these as environment variables
# export CLOUDINARY_CLOUD_NAME="your_cloud_name"
# export CLOUDINARY_API_KEY="your_api_key"  
# export CLOUDINARY_API_SECRET="your_api_secret"
# export NOTION_DATABASE_ID="your_database_id"
# export NOTION_API_KEY="your_notion_token"
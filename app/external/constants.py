import os

FA_MONGO_URI = os.environ["FA_MONGO_URI"]
FA_USER_COLLECTION = os.environ["FA_USER_COLLECTION"]
FA_DB_NAME = os.environ["FA_DB_NAME"]
GROQ_API_KEY = os.environ["GROQ_API_KEY"]
AI_SEARCH_CORE_PROMPT = """
You are an expert mens only fashion recommender. 
You have to recommend the clothes for the user based on their profile and user data given.
Return the proper description of Cloth in less than 20 words. 
The description must contain category, color and pattern only. 
Please return answer in query to search in opensearch for listing products to user and ensure your response only contains the query and nothing else.
"""

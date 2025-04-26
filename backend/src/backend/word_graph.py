from flask import Blueprint, request, jsonify
import google.generativeai as genai
import os
from typing import List, Dict
import random
import json
import re
from dotenv import load_dotenv
from pathlib import Path

# Initialize Gemini - the Gemini SDK uses GOOGLE_API_KEY
api_key = os.getenv('GOOGLE_API_KEY')
if not api_key:
    print("WARNING: GOOGLE_API_KEY environment variable not found.")
    # Also check for GEMINI_API_KEY for backward compatibility
    api_key = os.getenv('GEMINI_API_KEY')
    if api_key:
        print("Using GEMINI_API_KEY instead.")
        os.environ['GOOGLE_API_KEY'] = api_key
    else:
        print("WARNING: Neither GOOGLE_API_KEY nor GEMINI_API_KEY found.")

genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-2.0-flash')

word_graph_bp = Blueprint('word_graph', __name__)

@word_graph_bp.route('/api/word-graph/generate', methods=['POST'])
def generate_word_graph():
    try:
        data = request.get_json()
        topic = data.get('topic', 'Technology')
        num_words = data.get('num_words', 5)

        # Check if API key is available
        api_key = os.getenv('GOOGLE_API_KEY')
        if not api_key:
            raise ValueError("GOOGLE_API_KEY environment variable not set")

        # Print API key first few characters for debugging
        if api_key:
            print(f"Using API key starting with: {api_key[:4]}...")

        # Generate words related to the topic
        prompt = f"""Generate {num_words} key concepts or terms related to {topic}.
        For each term, provide:
        1. A brief summary (1-2 sentences)
        2. A detailed description (2-3 paragraphs)
        3. 2-3 related concepts (IMPORTANT: make sure these are actual terms that could appear as other nodes)
        4. 2-3 practical examples or use cases
        
        Format the response as a JSON object with the following structure:
        {{
            "words": [
                {{
                    "term": "term name",
                    "summary": "brief summary",
                    "description": "detailed description",
                    "related_concepts": ["concept1", "concept2"],
                    "examples": ["example1", "example2"]
                }}
            ]
        }}"""

        # Generate content using Gemini
        try:
            response = model.generate_content(prompt)
            if not response.text:
                raise ValueError("Empty response from Gemini")
        except Exception as e:
            print(f"Gemini API error: {str(e)}")
            raise ValueError(f"Error calling Gemini API: {str(e)}")

        # Parse the response and extract JSON
        try:
            # Extract JSON from the response
            json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
            if not json_match:
                raise ValueError("Could not find JSON in response")
            
            json_string = json_match.group()
            print(f"Extracted JSON: {json_string[:100]}...")  # Print first 100 chars for debugging
            
            words_data = json.loads(json_string)
            if not isinstance(words_data, dict) or 'words' not in words_data:
                raise ValueError("Invalid JSON structure")
        except json.JSONDecodeError as e:
            print(f"JSON parse error: {str(e)}, Content: {response.text[:200]}")
            raise ValueError(f"Failed to parse JSON: {str(e)}")

        words = words_data['words']
        print(f"Successfully parsed {len(words)} words")
        
        # Create a dictionary to map terms to their indices
        term_to_index = {word['term'].lower(): i for i, word in enumerate(words)}
        
        # Generate correlations based on related concepts
        correlations = []
        for i, word1 in enumerate(words):
            # Check if any of word1's related concepts match other nodes' terms
            for related_concept in word1.get('related_concepts', []):
                related_concept_lower = related_concept.lower()
                # If the related concept exists as a node
                if related_concept_lower in term_to_index:
                    j = term_to_index[related_concept_lower]
                    # Don't create self-loops
                    if i != j:
                        correlations.append({
                            'source': f"node-{i}",
                            'target': f"node-{j}",
                            'explanation': f"{word1['term']} includes {related_concept} as a related concept"
                        })
                        
            # Also check if this word is mentioned in other nodes' related concepts
            for j, word2 in enumerate(words):
                if i != j:  # Don't create self-loops
                    if any(word1['term'].lower() == related.lower() for related in word2.get('related_concepts', [])):
                        correlations.append({
                            'source': f"node-{j}",
                            'target': f"node-{i}",
                            'explanation': f"{word2['term']} includes {word1['term']} as a related concept"
                        })

        # Format the response for React Flow
        nodes = [
            {
                'id': f"node-{i}",
                'data': {
                    'label': word['term'],
                    'summary': word['summary'],
                    'description': word['description'],
                    'relatedTopics': word['related_concepts'],
                    'examples': word['examples']
                },
                'position': {'x': i * 250, 'y': 0},
                'type': 'wordNode',
                'sourcePosition': 'right',
                'targetPosition': 'left'
            }
            for i, word in enumerate(words)
        ]

        edges = [
            {
                'id': f"edge-{i}",
                'source': corr['source'],
                'target': corr['target'],
                'animated': True,
                'style': {'stroke': '#3b82f6', 'strokeWidth': 2},
                'data': {'explanation': corr['explanation']}
            }
            for i, corr in enumerate(correlations)
        ]

        return jsonify({
            'nodes': nodes,
            'edges': edges
        })

    except Exception as e:
        print(f"Error in generate_word_graph: {str(e)}")
        return jsonify({'error': str(e)}), 500 
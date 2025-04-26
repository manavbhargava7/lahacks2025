from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
import random
import google.generativeai as genai
from typing import Dict, List, Any, Optional

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Configure your LLM provider
genai.configure(api_key=os.environ.get("AIzaSyDhir02NpWjE4LcokbTwYjV8w2XsvxCK4s"))

# Types for our graph data
class Node:
    def __init__(self, id: str, label: str, x: Optional[float] = None, y: Optional[float] = None):
        self.id = id
        self.label = label
        self.x = x
        self.y = y
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "x": self.x,
            "y": self.y
        }

class Link:
    def __init__(self, source: str, target: str):
        self.source = source
        self.target = target
    
    def to_dict(self) -> Dict[str, str]:
        return {
            "source": self.source,
            "target": self.target
        }

class GraphData:
    def __init__(self, nodes: List[Node], links: List[Link]):
        self.nodes = nodes
        self.links = links
    
    def to_dict(self) -> Dict[str, List[Dict]]:
        return {
            "nodes": [node.to_dict() for node in self.nodes],
            "links": [link.to_dict() for link in self.links]
        }

def generate_graph_with_llm(topic: str) -> GraphData:
    """
    Generate a DAG using an LLM based on the provided topic.
    
    Args:
        topic: A string describing what kind of DAG to generate
        
    Returns:
        A GraphData object containing nodes and links
    """
    # Define the prompt for the LLM
    prompt = f"""
    Generate a directed acyclic graph (DAG) for the topic: "{topic}".
    
    Return the result as a JSON object with the following structure:
    {{
        "nodes": [
            {{"id": "1", "label": "Node 1 Label"}},
            {{"id": "2", "label": "Node 2 Label"}},
            ...
        ],
        "links": [
            {{"source": "1", "target": "2"}},
            ...
        ]
    }}
    
    Important rules:
    1. Make sure it's a valid DAG (no cycles)
    2. Node IDs should be unique strings
    3. Every link's source and target must refer to existing node IDs
    4. Generate between 5-15 nodes based on the complexity of the topic
    5. Make sure the labels are descriptive and relevant to the topic
    6. Each node should be connected to at least one other node
    """
    
    try:
        # Initialize the model
        model = genai.GenerativeModel('gemini-pro')
        
        # Generate content
        response = model.generate_content(prompt)
        if not response.text:
            raise ValueError("Empty response from Gemini")
        
        # Extract and parse the JSON response
        result_text = response.text.strip()
        
        # Extract just the JSON part (in case the LLM adds explanations)
        import re
        json_match = re.search(r'```json\n(.*?)\n```', result_text, re.DOTALL)
        if json_match:
            result_text = json_match.group(1)
        else:
            # Try to find JSON between curly braces if no code block is found
            json_match = re.search(r'({.*})', result_text, re.DOTALL)
            if json_match:
                result_text = json_match.group(1)
            else:
                raise ValueError("Could not find JSON in response")
        
        # Parse the JSON
        data = json.loads(result_text)
        
        # Validate the data structure
        if not isinstance(data, dict) or 'nodes' not in data or 'links' not in data:
            raise ValueError("Invalid JSON structure")
        
        # Convert to our data classes
        nodes = [Node(n["id"], n["label"]) for n in data["nodes"]]
        links = [Link(l["source"], l["target"]) for l in data["links"]]
        
        return GraphData(nodes, links)
    
    except Exception as e:
        # Return a fallback simple graph
        return generate_fallback_graph(topic)

def generate_fallback_graph(topic: str) -> GraphData:
    """Generate a simple fallback graph if the LLM fails"""
    nodes = [
        Node("1", f"{topic} - Start"),
        Node("2", "Research"),
        Node("3", "Planning"),
        Node("4", "Implementation"),
        Node("5", "Testing"),
        Node("6", f"{topic} - Complete")
    ]
    
    links = [
        Link("1", "2"),
        Link("1", "3"),
        Link("2", "4"),
        Link("3", "4"),
        Link("4", "5"),
        Link("5", "6")
    ]
    
    return GraphData(nodes, links)

@app.route('/api/generate_graph', methods=['POST'])
def api_generate_graph():
    """API endpoint to generate a graph based on the provided topic"""
    data = request.json
    topic = data.get('topic', 'Generic Process')
    
    try:
        graph_data = generate_graph_with_llm(topic)
        return jsonify(graph_data.to_dict())
    except Exception as e:
        print(f"Error generating graph with LLM: {e}")
        # graph_data = generate_fallback_graph(topic)
        # return jsonify(graph_data.to_dict())
        return jsonify({"error": "failed to generate graph"})
    

@app.route('/api/health', methods=['GET'])
def health_check():
    """Simple health check endpoint"""
    return jsonify({"status": "healthy"})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

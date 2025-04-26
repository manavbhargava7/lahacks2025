from flask import Flask, jsonify, request
from flask_cors import CORS
import google.generativeai as genai
import json
import os
import networkx as nx

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Configure Gemini API - in a production environment, use proper env variables
# Replace with your actual API key
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

@app.route('/api/dag/generate', methods=['POST'])
def generate_dag():
    """Generate a DAG structure using Gemini and return it in React Flow format"""
    try:
        # Get the prompt from the request
        data = request.json
        prompt = data.get('prompt', 'Generate an execution DAG for a machine learning pipeline')
        
        # Call Gemini API to generate DAG structure
        # TODO: This isn't working properly. it throws an error for some reason.
        #i believe this has to do with our call of the .Content() function, as it does not yet exist.
        # i switched back to using backend.py 2 
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content([
            genai.types.Content(
                parts=[genai.types.Part(text="You are a DAG generation assistant that outputs valid JSON. Create a directed acyclic graph (DAG) for execution dependencies based on the following prompt. The output should be a JSON object with 'nodes' and 'edges' arrays in a format compatible with React Flow. Each node should have an 'id', 'data' object with 'label' and 'status' properties, and a 'type' field set to 'taskNode'. Each edge should have an 'id', 'source', 'target', 'animated', and 'style' properties.")]
            ),
            genai.types.Content(
                parts=[genai.types.Part(text=prompt)]
            )
        ], generation_config=genai.types.GenerationConfig(
            temperature=0.7,
            max_output_tokens=1000
        ))
        
        # Extract JSON from response
        response_text = response.text
        
        # Sometimes the model might wrap the JSON in markdown code blocks, so we need to extract it
        if "```json" in response_text:
            # Extract JSON from markdown code block
            json_start = response_text.find("```json") + 7
            json_end = response_text.find("```", json_start)
            json_string = response_text[json_start:json_end].strip()
        elif "```" in response_text:
            # Extract JSON from generic code block
            json_start = response_text.find("```") + 3
            json_end = response_text.find("```", json_start)
            json_string = response_text[json_start:json_end].strip()
        else:
            # Assume the entire response is JSON
            json_string = response_text
        
        # Parse the JSON
        dag_data = json.loads(json_string)
        
        # Create a NetworkX graph for layout calculation
        G = nx.DiGraph()
        
        # Add nodes
        for node in dag_data.get('nodes', []):
            G.add_node(node['id'], **node.get('data', {}))
        
        # Add edges
        for edge in dag_data.get('edges', []):
            G.add_edge(edge['source'], edge['target'])
        
        # Compute positions using a layered layout algorithm
        try:
            # Try to use graphviz layout if available
            pos = nx.nx_agraph.graphviz_layout(G, prog='dot')
        except:
            # Fall back to a simpler layout algorithm
            pos = nx.spring_layout(G)
        
        # Scale positions for better visualization
        scale_factor = 200
        for node in dag_data.get('nodes', []):
            node_id = node['id']
            # Use node position from layout algorithm
            if node_id in pos:
                x, y = pos[node_id]
                node['position'] = {"x": x * scale_factor, "y": y * scale_factor}
            else:
                # Fallback position if layout fails
                node['position'] = {"x": 0, "y": 0}
        
        return jsonify(dag_data)
    
    except Exception as e:
        return jsonify({
            "error": str(e),
            "message": "Failed to generate DAG"
        }), 500

# Not yet used
@app.route('/api/dag/status', methods=['POST'])
def update_status():
    """Update the status of a task in the DAG"""
    data = request.json
    task_id = data.get('taskId')
    new_status = data.get('status')
    
    # In a real application, you would update your execution engine or database
    # For this example, we'll just return a success message
    return jsonify({
        "success": True,
        "message": f"Updated status of {task_id} to {new_status}"
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)

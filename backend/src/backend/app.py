from flask import Flask
from flask_cors import CORS
from .word_graph import word_graph_bp

app = Flask(__name__)
CORS(app)

# Register blueprints
app.register_blueprint(word_graph_bp)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8000) 
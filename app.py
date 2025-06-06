from flask import Flask, request, jsonify, render_template
from pymongo import MongoClient
from datetime import datetime, timezone
import os
from dotenv import load_dotenv

load_dotenv()

# Load environment variables from .env file
app = Flask(__name__)

# MongoDB connection
try:
    client = MongoClient(os.getenv("MONGO_URI"))
    client.admin.command('ping')
    print("Successfully connected to MongoDB!")
except Exception as e:
    print(f"Error connecting to MongoDB: {e}")
    exit(1)

# Access the 'webhook_db' database and 'events' collection
db = client.webhook_db
events_collection = db.events

@app.route('/webhook', methods=['POST'])
def webhook():
    # Get the event type from GitHub webhook header
    event_type = request.headers.get('X-GitHub-Event')
    # Get the actual payload (event data) from GitHub webhook
    payload = request.json

    print("📬 Webhook received:")
    print("Event type:", event_type)
    print("Payload:", payload)

    # If the event type is neither 'push' nor 'pull_request', return an error
    if event_type not in ['push', 'pull_request']:
        return jsonify({'error': 'Unsupported event type'}), 400

    # Prepare the data to be stored in MongoDB
    event_data = {
        'event_type': event_type,
        'timestamp': datetime.now(timezone.utc).isoformat()
    }

    # Handle 'push' event type
    if event_type == 'push':
        event_data.update({
            'author': payload['pusher']['name'],
            'to_branch': payload['ref'].split('/')[-1]
        })

    # Handle 'pull_request' event type
    elif event_type == 'pull_request':
        action = payload.get('action')
        pr = payload.get('pull_request', {})

        # Check if the PR was closed and merged
        if action == 'closed' and pr.get('merged'):
            event_data['event_type'] = 'merge'
            event_data.update({
                'author': pr['user']['login'],
                'from_branch': pr['head']['ref'],
                'to_branch': pr['base']['ref']
            })
        else:
            # If it's not a merge (open or update), store normal PR details
            event_data.update({
                'author': pr['user']['login'],
                'from_branch': pr['head']['ref'],
                'to_branch': pr['base']['ref']
            })

    # Insert the event data into MongoDB's 'events' collection
    events_collection.insert_one(event_data)
    return jsonify({'status': 'success'}), 200

# Fetch events from MongoDB, exclude '_id' field, and sort by timestamp
@app.route('/events', methods=['GET'])
def get_events():
    events = list(events_collection.find({}, {'_id': 0}).sort('timestamp', -1))
    return jsonify(events)

 # Render the HTML template (index.html) for the frontend
@app.route('/')
def index():
    return render_template('index.html')

# Insert a fake 'push' event into MongoDB for testing purposes
@app.route('/fake')
def insert_fake_event():
    test_event = {
        "event_type": "push",
        "author": "Ranit-007",
        "to_branch": "main",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    events_collection.insert_one(test_event)
    return "Fake event inserted!"

# Run the Flask app in debug mode
if __name__ == '__main__':
    app.run(debug=True) 
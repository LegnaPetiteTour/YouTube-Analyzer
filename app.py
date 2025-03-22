from flask import Flask, request, jsonify, render_template, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from youtube_client import YouTubeClient
from claude_client import ClaudeClient
from models import db, User, Analysis
from dotenv import load_dotenv
import os
from datetime import datetime

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-this'  # Used for session security
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db.init_app(app)

# Create tables
with app.app_context():
    db.create_all()

# Initialize login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Initialize API clients
youtube_client = YouTubeClient()
claude_client = ClaudeClient()

# Authentication routes
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Check if username or email already exists
        user = User.query.filter_by(username=username).first()
        if user:
            flash('Username already exists')
            return redirect(url_for('register'))
        
        user = User.query.filter_by(email=email).first()
        if user:
            flash('Email already exists')
            return redirect(url_for('register'))
        
        # Create new user
        new_user = User(username=username, email=email)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registration successful! Please log in.')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        else:
            flash('Invalid username or password')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# Main routes
@app.route('/')
@login_required
def index():
    return render_template('index.html')

# YouTube API routes
@app.route('/api/search', methods=['POST'])
@login_required
def search_videos():
    data = request.json
    query = data.get('query')
    
    if not query:
        return jsonify({'error': 'Query is required'}), 400
    
    # Get optional parameters
    max_results = data.get('maxResults', 10)
    order = data.get('order')
    video_duration = data.get('videoDuration')
    published_after = data.get('publishedAfter')
    published_before = data.get('publishedBefore')
    
    videos = youtube_client.search_videos(
        query, 
        max_results=max_results,
        order=order,
        video_duration=video_duration,
        published_after=published_after,
        published_before=published_before
    )
    
    return jsonify({'videos': videos})

@app.route('/api/video/<video_id>', methods=['GET'])
@login_required
def get_video(video_id):
    video = youtube_client.get_video_details(video_id)
    
    if not video:
        return jsonify({'error': 'Video not found'}), 404
    
    return jsonify({'video': video})

@app.route('/api/video/<video_id>/comments', methods=['GET'])
@login_required
def get_comments(video_id):
    page_token = request.args.get('pageToken')
    comments, next_page_token = youtube_client.get_video_comments(video_id, page_token=page_token)
    return jsonify({
        'comments': comments,
        'nextPageToken': next_page_token
    })

@app.route('/api/video/<video_id>/transcript', methods=['GET'])
@login_required
def get_video_transcript(video_id):
    try:
        transcript = youtube_client.get_video_transcript(video_id)
        return jsonify({
            'transcript': transcript
        })
    except Exception as e:
        print(f"Error getting transcript: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/analyze/transcript', methods=['POST'])
@login_required
def analyze_transcript():
    data = request.json
    video_id = data.get('video_id')
    instruction = data.get('instruction')
    
    if not video_id or not instruction:
        return jsonify({'error': 'Missing video_id or instruction'}), 400
    
    try:
        # Get the transcript
        transcript = youtube_client.get_video_transcript(video_id)
        
        if transcript.startswith("Error") or transcript.startswith("No transcript"):
            return jsonify({'analysis': transcript})
        
        # Analyze with Claude
        analysis = claude_client.analyze_video_data(
            {"transcript": transcript[:10000]},  # Limit to 10k chars to avoid token limits
            instruction
        )
        
        return jsonify({
            'analysis': analysis
        })
    except Exception as e:
        print(f"Error analyzing transcript: {e}")
        return jsonify({'error': str(e)}), 500
    
@app.route('/api/search/channels', methods=['POST'])
@login_required
def search_channels():
    data = request.json
    query = data.get('query')
    
    if not query:
        return jsonify({'error': 'Query is required'}), 400
    
    max_results = data.get('maxResults', 5)
    
    channels = youtube_client.search_channels(query, max_results=max_results)
    
    return jsonify({'channels': channels})

@app.route('/api/channel/<channel_id>', methods=['GET'])
@login_required
def get_channel(channel_id):
    channel = youtube_client.get_channel_details(channel_id)
    
    if not channel:
        return jsonify({'error': 'Channel not found'}), 404
    
    return jsonify({'channel': channel})

@app.route('/api/channel/<channel_id>/videos', methods=['GET'])
@login_required
def get_channel_videos(channel_id):
    max_results = request.args.get('maxResults', 10, type=int)
    videos = youtube_client.get_channel_videos(channel_id, max_results=max_results)
    
    return jsonify({'videos': videos})    

# Claude API routes
@app.route('/api/analyze/video', methods=['POST'])
@login_required
def analyze_video():
    data = request.json
    video_id = data.get('video_id')
    instruction = data.get('instruction')
    
    if not video_id or not instruction:
        return jsonify({'error': 'Video ID and instruction are required'}), 400
    
    video = youtube_client.get_video_details(video_id)
    
    if not video:
        return jsonify({'error': 'Video not found'}), 404
    
    analysis = claude_client.analyze_video_data(video, instruction)
    return jsonify({'analysis': analysis})

@app.route('/api/analyze/comments', methods=['POST'])
@login_required
def analyze_video_comments():
    data = request.json
    video_id = data.get('video_id')
    instruction = data.get('instruction')
    
    print(f"Analyzing comments for video ID: {video_id}")
    print(f"Instruction: {instruction}")
    
    if not video_id or not instruction:
        return jsonify({'error': 'Video ID and instruction are required'}), 400
    
    comments, _ = youtube_client.get_video_comments(video_id)
    
    print(f"Number of comments retrieved: {len(comments)}")
    
    if not comments:
        return jsonify({'error': 'No comments found'}), 404
    
    print("Sending comments to Claude for analysis...")
    analysis = claude_client.analyze_comments(comments, instruction)
    print("Analysis received from Claude")
    
    return jsonify({'analysis': analysis})

@app.route('/api/analyze/channel', methods=['POST'])
@login_required
def analyze_channel():
    data = request.json
    channel_id = data.get('channel_id')
    instruction = data.get('instruction')
    video_sample_size = data.get('video_sample_size', 5)
    
    if not channel_id or not instruction:
        return jsonify({'error': 'Channel ID and instruction are required'}), 400
    
    channel = youtube_client.get_channel_details(channel_id)
    
    if not channel:
        return jsonify({'error': 'Channel not found'}), 404
        
    # Get a sample of videos from the channel
    videos = youtube_client.get_channel_videos(channel_id, max_results=video_sample_size)
    
    # Analyze with Claude
    analysis = claude_client.analyze_channel_data(channel, videos, instruction)
    return jsonify({'analysis': analysis})

# Analysis management routes
@app.route('/api/analyses', methods=['GET'])
@login_required
def get_analyses():
    analyses = Analysis.query.filter_by(user_id=current_user.id).order_by(Analysis.created_at.desc()).all()
    return jsonify({'analyses': [analysis.to_dict() for analysis in analyses]})

@app.route('/api/analyses', methods=['POST'])
@login_required
def save_analysis():
    data = request.json
    
    if not all(key in data for key in ['type', 'video_id', 'instruction', 'content']):
        return jsonify({'error': 'Missing required fields'}), 400
    
    analysis = Analysis(
        user_id=current_user.id,
        type=data['type'],
        video_id=data['video_id'],
        instruction=data['instruction'],
        content=data['content'],
        created_at=datetime.utcnow()
    )
    
    db.session.add(analysis)
    db.session.commit()
    
    return jsonify({'message': 'Analysis saved successfully', 'analysis': analysis.to_dict()})

@app.route('/api/analyses/<int:analysis_id>', methods=['DELETE'])
@login_required
def delete_analysis(analysis_id):
    analysis = Analysis.query.get_or_404(analysis_id)
    
    # Check if the analysis belongs to the current user
    if analysis.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    db.session.delete(analysis)
    db.session.commit()
    
    return jsonify({'message': 'Analysis deleted successfully'})

if __name__ == '__main__':
    app.run(debug=True, port=5002)